"""Opérations de stock, au niveau du service (lot D5) : saisie, droits par type, quarantaine
(décision de Mohamed, C-01), validation, annulation, blocages. Chaque essai travaille dans une
transaction annulée à la fin (`fabriques.stock.s`).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fabriques import stock as fabriques_stock
from fabriques.operations import Monde, acteur, ligne, monde, motif, ordre_valide, saisie
from fabriques.stock import JOUR, autre_magasin, jour
from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Lot, Mouvement, Solde
from gestion_mp_pro.modeles.enums import Role, StatutDocument
from gestion_mp_pro.services import operations as ops
from gestion_mp_pro.services.operations import gestes, lecture

s = fabriques_stock.s
"""La session de l'essai, annulée à la fin (fixture du lot S4)."""


def _solde(s: Session, lot: Lot, magasin_id: int) -> Decimal:
    return s.scalar(
        select(Solde.quantite).where(Solde.lot_id == lot.id, Solde.magasin_id == magasin_id)
    ) or Decimal(0)


def _refus(fonction: object, *args: object, **kw: object) -> Refus:
    """Le refus d'un geste ; ce qu'il avait commencé est défait (comme la route le ferait)."""
    s = next(x for x in args if isinstance(x, Session))
    point = s.begin_nested()
    with pytest.raises(Refus) as e:
        fonction(*args, **kw)  # type: ignore[operator]
    point.rollback()
    return e.value


def _liberation(s: Session, m: Monde, q: float = 100, nom_motif: str = "Libération de quarantaine"):
    return saisie(
        "transfert",
        ligne(
            m.a1.id,
            m.quarantaine.id,
            q,
            lot_id=m.lots["E-Q1"].id,
            magasin_destination_id=m.courant.id,
        ),  # fmt: skip
        motif_id=motif(s, "transfert", nom_motif),
        commentaire="contrôle conforme",
    )


def test_quarantaine_liberee_par_les_achats_seulement(s: Session) -> None:
    """Hérité : test_stock_atelier::test_quarantaine_liberee_par_les_achats_seulement —
    l'alimentation ne crée ni ne valide une libération (403) ; motif « Rangement » → 422
    « Libération » ; validée par les achats : TRF-, lot disponible 100."""
    m = monde(s)
    achats, atelier = acteur(s, Role.achats), acteur(s, Role.alimentation)
    assert _refus(ops.creer, s, atelier, _liberation(s, m)).http == 403
    r = _refus(ops.creer, s, achats, _liberation(s, m, nom_motif="Rangement"))
    assert r.http == 422 and "Libération" in r.detail
    o = ops.creer(s, achats, _liberation(s, m))
    r = _refus(ops.valider, s, atelier, o.id, o.version)
    assert r.http == 403 and r.detail == gestes.droits.REFUS_LIBERATION == (
        "Libérer une quarantaine est une décision de la direction ou des achats, après contrôle "
        "de la matière."
    )  # RESTES3 (F6) : la règle est « direction ou achats », la phrase le dit
    o = ops.valider(s, achats, o.id, o.version)
    assert o.numero is not None and o.numero.startswith("TRF-")
    assert _solde(s, m.lots["E-Q1"], m.courant.id) == 100
    assert _solde(s, m.lots["E-Q1"], m.quarantaine.id) == 0


def _mise_en_quarantaine(s: Session, m: Monde, q: float, commentaire: str = "fil taché"):
    return saisie(
        "transfert",
        ligne(
            m.a1.id,
            m.courant.id,
            q,
            lot_id=m.lots["E-L1"].id,
            magasin_destination_id=m.quarantaine.id,
        ),  # fmt: skip
        motif_id=motif(s, "transfert", "Mise en quarantaine"),
        commentaire=commentaire,
    )


def test_alimentation_met_en_quarantaine_mais_n_en_sort_rien(s: Session) -> None:
    """Hérité : test_defauts_c::test_alimentation_ne_peut_annuler_une_mise_en_quarantaine et
    ::test_alimentation_ne_supprime_ni_n_annule_une_liberation_des_achats (C-01, bloquant)."""
    m = monde(s)
    achats, atelier = acteur(s, Role.achats), acteur(s, Role.alimentation)
    r = _refus(ops.creer, s, atelier, _mise_en_quarantaine(s, m, 100, commentaire=""))
    assert r.detail == "Une mise en quarantaine se justifie : écrire ce qui est douteux."
    o = ops.creer(s, atelier, _mise_en_quarantaine(s, m, 100), valider=True)
    assert _solde(s, m.lots["E-L1"], m.quarantaine.id) == 100
    r = _refus(ops.annuler, s, atelier, o.id, o.version)
    assert r.http == 403 and "achats" in r.detail
    assert _solde(s, m.lots["E-L1"], m.quarantaine.id) == 100
    lib = ops.creer(s, achats, _liberation(s, m, 40))
    assert _refus(ops.supprimer, s, atelier, lib.id, lib.version).http == 403
    assert _refus(ops.modifier, s, atelier, lib.id, lib.version, _liberation(s, m, 30)).http == 403
    lib = ops.valider(s, achats, lib.id, lib.version)
    assert _refus(ops.annuler, s, atelier, lib.id, lib.version).http == 403
    assert _solde(s, m.lots["E-Q1"], m.quarantaine.id) == 60
    ops.annuler(s, achats, o.id, o.version)  # les achats, eux, l'annulent
    assert _solde(s, m.lots["E-L1"], m.quarantaine.id) == 0


def test_ajustement_en_bobines_sans_numero_au_brouillon(s: Session) -> None:
    """Hérité : test_stock_atelier::test_ajustement_en_palettes — −2 bobines = −4 kg ; pas de
    numéro au brouillon ; aucun blocage. D-08 : une bobine se compte entière."""
    m = monde(s)
    achats = acteur(s)
    e = saisie(
        "ajustement",
        ligne(m.a1.id, m.courant.id, -2, lot_id=m.lots["E-L1"].id, unite="bobine"),
        motif_id=motif(s, "ajustement", "Perte / casse"),
        commentaire="bobines écrasées",
    )
    o = ops.creer(s, achats, e)
    lu = ops.fiche(s, o.id, Role.achats)
    assert (lu.lignes[0].quantite, lu.numero, lu.blocages) == (-4, None, [])
    demi = saisie(
        "ajustement",
        ligne(m.a1.id, m.courant.id, "-2.5", lot_id=m.lots["E-L1"].id, unite="bobine"),
        motif_id=motif(s, "ajustement", "Perte / casse"),
        commentaire="bobines écrasées",
    )
    assert "une bobine se compte entière" in _refus(ops.creer, s, achats, demi).detail
    palette = saisie(
        "ajustement",
        ligne(m.a2.id, m.courant.id, 1, lot_id=m.lots["E-T1"].id, unite="palette"),
        motif_id=motif(s, "ajustement", "Perte / casse"),
        commentaire="palette en trop",
    )
    assert "bobines par palette" in _refus(ops.creer, s, achats, palette).detail


def test_un_ajustement_se_justifie_a_la_creation(s: Session) -> None:
    """Hérité : test_parcours::test_un_ajustement_se_justifie (essai faible : un code, une
    étape) ; et le motif dit pourquoi le stock bouge ; un motif hors liste est refusé (C-09)."""
    m = monde(s)
    achats = acteur(s)
    x = ligne(m.a1.id, m.courant.id, -1, lot_id=m.lots["E-L1"].id)
    r = _refus(ops.creer, s, achats, saisie("ajustement", x, commentaire="vu"))
    assert (r.http, r.detail) == (422, "Choisir le motif : il dit pourquoi le stock bouge.")
    casse = motif(s, "ajustement", "Perte / casse")
    r = _refus(ops.creer, s, achats, saisie("ajustement", x, motif_id=casse, commentaire="vu"))
    assert r.detail == "Un ajustement se justifie : écrire en quelques mots ce qui a été constaté."
    reliquat = motif(s, "retour_machine", "Reliquat de fin d'ordre")
    e = saisie("ajustement", x, motif_id=reliquat, commentaire="un essai C")
    r = _refus(ops.creer, s, achats, e)
    assert r.http == 422 and r.detail.startswith("Motif « Reliquat de fin d'ordre » inconnu pour")


def test_droits_par_type(s: Session) -> None:
    """OR2 : chaque type a ses rôles (une seule table) ; la direction passe partout."""
    m = monde(s)
    atelier, achats = acteur(s, Role.alimentation), acteur(s, Role.achats)
    ouverture = saisie("ouverture", ligne(m.a1.id, m.courant.id, 1, lot_numero="X1"))
    r = _refus(ops.creer, s, atelier, ouverture)
    assert (r.http, r.detail) == (403, "« Stock d'ouverture » est réservé à : responsable achats.")
    o = ordre_valide(s, [(m.lots["E-L2"], 40)])
    retour = saisie(
        "retour_machine", ligne(m.a1.id, m.courant.id, 3, lot_id=m.lots["E-L2"].id),
        ordre_id=o.id, motif_id=motif(s, "retour_machine", "Reliquat de fin d'ordre"),
    )  # fmt: skip
    r = _refus(ops.creer, s, achats, retour)
    assert r.detail == "« Retour des machines » est réservé à : responsable alimentation machines."
    assert ops.creer(s, acteur(s, Role.direction), retour).statut == StatutDocument.brouillon


def test_retour_en_bobines_motif_code(s: Session) -> None:
    """Hérité : test_stock_atelier::test_retour_en_bobines_et_deplacement — 3 bobines × 2 kg =
    6 kg, code R1 ; le lot revient de 6 kg."""
    m = monde(s)
    atelier = acteur(s, Role.alimentation)
    o = ordre_valide(s, [(m.lots["E-L2"], 40)])
    e = saisie(
        "retour_machine",
        ligne(m.a1.id, m.courant.id, 3, lot_id=m.lots["E-L2"].id, unite="bobine"),
        ordre_id=o.id, motif_id=motif(s, "retour_machine", "Reliquat de fin d'ordre"),
        commentaire="fin de série",
    )  # fmt: skip
    r = ops.creer(s, atelier, e, valider=True)
    lu = ops.fiche(s, r.id, Role.alimentation)
    assert (lu.lignes[0].quantite, lu.code_motif, lu.numero[:4]) == (6, "R1", "RET-")  # type: ignore[index]
    assert _solde(s, m.lots["E-L2"], m.courant.id) == 300 - 40 + 6
    mvt = s.scalars(select(Mouvement).where(Mouvement.operation_id == r.id)).one()
    assert mvt.ordre_id == o.id and mvt.motif_texte == "Reliquat de fin d'ordre"


def test_un_retour_ne_se_date_pas_avant_son_ordre(s: Session) -> None:
    """Hérité : test_audit2_atelier::test_un_retour_ne_se_date_pas_avant_son_ordre — 422
    « avant l'ordre » ; 20 + 20 pour 30 partis : blocage « 30,00 kg partis … 40,00 kg rendus »,
    puis 409 à la validation, sans « -0 »."""
    m = monde(s)
    atelier = acteur(s, Role.alimentation)
    o = ordre_valide(s, [(m.lots["E-L1"], 30)])
    reliquat = motif(s, "retour_machine", "Reliquat de fin d'ordre")
    x = ligne(m.a1.id, m.courant.id, 20, lot_id=m.lots["E-L1"].id)
    r = _refus(ops.creer, s, atelier, saisie("retour_machine", x, le=jour(-1), ordre_id=o.id,
                                             motif_id=reliquat))  # fmt: skip
    assert r.http == 422 and "avant l'ordre" in r.detail
    b = ops.creer(s, atelier, saisie("retour_machine", x, x, ordre_id=o.id, motif_id=reliquat))
    lu = ops.fiche(s, b.id, Role.alimentation)
    assert any("30,00 kg partis pour cet ordre, 40,00 kg rendus" in x for x in lu.blocages)
    r = _refus(ops.valider, s, atelier, b.id, b.version)
    assert r.http == 409 and "-0" not in r.detail and "40,00 kg rendus" in r.detail


def test_une_ecriture_datee_avant_l_entree_du_lot_est_bloquee(s: Session) -> None:
    """Hérité : test_valeur_et_dates::test_une_sortie_datee_avant_l_entree_du_lot_est_refusee —
    transfert, ajustement, retour au fournisseur datés de l'avant-veille sur un lot entré la
    veille : blocage « n'est entré », 409 avec la date ; le lot garde ses 500 kg."""
    m = monde(s)
    achats, avant = acteur(s), jour(-2)
    x = m.lots["E-L1"]
    saisies = [
        saisie("transfert", ligne(m.a1.id, m.courant.id, 10, lot_id=x.id,
                                  magasin_destination_id=autre_magasin(s).id), le=avant,
               motif_id=motif(s, "transfert", "Rangement")),
        saisie("ajustement", ligne(m.a1.id, m.courant.id, -10, lot_id=x.id), le=avant,
               motif_id=motif(s, "ajustement", "Perte / casse"), commentaire="casse constatée"),
        saisie("retour_fournisseur", ligne(m.a1.id, m.courant.id, 10, lot_id=x.id), le=avant,
               motif_id=motif(s, "retour_fournisseur", "Bobines endommagées")),
    ]  # fmt: skip
    for e in saisies:
        o = ops.creer(s, achats, e)
        assert any("n'est entré dans" in b for b in ops.fiche(s, o.id, Role.achats).blocages)
        r = _refus(ops.valider, s, achats, o.id, o.version)
        assert r.http == 409 and f"{avant:%d/%m/%Y}" in r.detail
    assert _solde(s, x, m.courant.id) == 500


def test_ouverture_devise_inconnue_et_un_seul_total(s: Session) -> None:
    """Hérité : test_valeur_et_dates::test_ouverture_devise_inconnue_et_un_seul_total — XXX →
    422 ; 130 + 13 → 143 ; le lot est créé à la validation, le lot interne numéroté alors."""
    m = monde(s)
    achats = acteur(s)
    x = ligne(m.a2.id, m.courant.id, 5, lot_numero="O-1", prix=Decimal(2), devise="XXX")
    r = _refus(ops.creer, s, achats, saisie("ouverture", x))
    assert r.http == 422 and "devise inconnue (« XXX »)" in r.detail
    e = saisie(
        "ouverture",
        ligne(m.a2.id, m.courant.id, 130, lot_numero="O-1", prix=Decimal(8)),
        ligne(m.a2.id, m.courant.id, 13, lot_interne=True, prix=Decimal(8)),
    )
    o = ops.creer(s, achats, e)
    lu = ops.fiche(s, o.id, Role.achats)
    assert lu.total == 143 and [x.lot for x in lu.lignes] == ["O-1", "LOT INTERNE"]
    assert [(v.devise, v.montant) for v in lu.valeurs] == [("MAD", Decimal("1144.00"))]
    o = ops.valider(s, achats, o.id, o.version)
    lu = ops.fiche(s, o.id, Role.achats)
    assert lu.lignes[1].lot.startswith(f"LOT-{JOUR.year}-") and all(x.lot_id for x in lu.lignes)


def test_valider_une_operation_annulee_et_annuler_deux_fois(s: Session) -> None:
    """Hérité : test_defauts_c::test_valider_operation_annulee_message (C-11) ; une annulation
    se fait une fois, datée comme l'original, avec son auteur et son motif."""
    m = monde(s)
    achats = acteur(s)
    o = ops.creer(s, achats, _mise_en_quarantaine(s, m, 1), valider=True)
    o = ops.annuler(s, achats, o.id, o.version, motif="erreur de lot")
    assert (o.statut, o.annulee_par_id, o.annulation_motif) == (
        "annulee",
        achats.id,
        "erreur de lot",
    )
    r = _refus(ops.valider, s, achats, o.id, o.version)
    assert (r.http, r.detail) == (409, "Cette opération est annulée : elle ne se valide plus.")
    r = _refus(ops.annuler, s, achats, o.id, o.version)
    assert (r.http, r.detail) == (409, "Cette opération est déjà annulée.")
    inverses = s.scalars(select(Mouvement).where(Mouvement.contrepasse_id.is_not(None),
                                                 Mouvement.operation_id == o.id)).all()  # fmt: skip
    assert len(inverses) == 2 and all(x.date_effet == o.date for x in inverses)


def test_version_perimee_et_etats(s: Session) -> None:
    """Version périmée → 409 qui nomme l'auteur ; un brouillon ne s'annule pas ; une opération
    validée ne se modifie ni ne se supprime (OR29, OR31, OR36)."""
    m = monde(s)
    achats = acteur(s)
    e = _mise_en_quarantaine(s, m, 1)
    o = ops.creer(s, achats, e)
    r = _refus(ops.valider, s, achats, o.id, o.version + 1)
    assert r.code == "conflit_version" and "Achats" in r.detail
    r = _refus(ops.annuler, s, achats, o.id, o.version)
    assert r.detail == "Seule une opération validée s'annule ; un brouillon se supprime."
    v = ops.modifier(s, achats, o.id, o.version, _mise_en_quarantaine(s, m, 2))
    assert v.version == 2 and v.lignes[0].quantite == 2
    o = ops.valider(s, achats, o.id, v.version)
    r = _refus(ops.modifier, s, achats, o.id, o.version, e)
    assert r.detail == "Une opération validée ne se modifie plus : l'annuler."
    r = _refus(ops.supprimer, s, achats, o.id, o.version)
    assert r.detail == "Une opération validée ne se supprime pas : l'annuler."
    assert _refus(ops.fiche, s, 999999, Role.achats).http == 404


def test_retour_fournisseur_un_seul_fournisseur(s: Session) -> None:
    """Hérité : test_defauts_c::test_retour_fournisseur_lot_d_ouverture_au_fournisseur_de_la_matiere
    (C-10) : le lot sans fournisseur rend à celui de la matière ; deux fournisseurs → 422."""
    m = monde(s)
    achats = acteur(s)
    endommagees = motif(s, "retour_fournisseur", "Bobines endommagées")
    x = ligne(m.a1.id, m.courant.id, 1, lot_id=m.lots["E-L1"].id)
    o = ops.creer(s, achats, saisie("retour_fournisseur", x, motif_id=endommagees))
    assert o.fournisseur_id == m.fournisseur
    from fabriques import referentiels as ref

    autre = s.get_one(Lot, ref.stock_initial(ref.matiere(s=s), 5, s=s))
    y = ligne(autre.matiere_id, m.courant.id, 1, lot_id=autre.id)
    r = _refus(ops.creer, s, achats, saisie("retour_fournisseur", x, y, motif_id=endommagees))
    assert r.detail == "Un retour au fournisseur ne mêle pas deux fournisseurs."


def test_les_commandes_sont_recalees(s: Session) -> None:
    """Hérité : test_parcours::test_la_quarantaine_se_libere_par_un_transfert (partie stock) :
    disponible, quarantaine vidée ; le crochet des commandes (D3, D4) reçoit les lots et la
    raison « sortie de quarantaine », puis « TRF-… annulé »."""
    m = monde(s)
    achats = acteur(s)
    appels: list[tuple[set[int], str]] = []
    gestes.RECALAGES.append(lambda _s, _q, lots, raison: appels.append((lots, raison)))
    try:
        o = ops.creer(s, achats, _liberation(s, m), valider=True)
        assert _solde(s, m.lots["E-Q1"], m.courant.id) == 100
        ops.annuler(s, achats, o.id, o.version)
    finally:
        gestes.RECALAGES.pop()
    assert appels == [({m.lots["E-Q1"].id}, "sortie de quarantaine"),
                      ({m.lots["E-Q1"].id}, f"{o.numero} annulé")]  # fmt: skip
    assert lecture.fiche(s, o.id, Role.achats).liberation
