"""Inventaires, au niveau du service (lot D5) : périmètre et suspension limitée (K2), comptages,
recomptage, lots trouvés créés à la validation, abandon conservé, annulation d'un inventaire
validé par contre-passation unique, inventaire tournant. Chaque essai travaille dans une
transaction annulée, sur un magasin à lui.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fabriques import stock as fabriques_stock
from fabriques.operations import Monde, acteur, monde
from fabriques.stock import JOUR, autre_magasin, entree, jour, lot, sortie
from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Inventaire, InventaireMatiere, Lot, Mouvement, Solde
from gestion_mp_pro.modeles.enums import StatutInventaire
from gestion_mp_pro.services import inventaires as inv
from gestion_mp_pro.services import numerotation
from gestion_mp_pro.services.inventaires import Comptage, Criteres, LotTrouve, Ouverture

s = fabriques_stock.s
"""La session de l'essai, annulée à la fin (fixture du lot S4)."""


def _refus(fonction: object, *args: object, **kw: object) -> Refus:
    """Le refus d'un geste ; ce qu'il avait commencé est défait (comme la route le ferait)."""
    session = next(x for x in args if isinstance(x, Session))
    point = session.begin_nested()
    with pytest.raises(Refus) as e:
        fonction(*args, **kw)  # type: ignore[operator]
    point.rollback()
    return e.value


def _monde(s: Session) -> Monde:
    return monde(s, courant=autre_magasin(s))


def _solde(s: Session, x: Lot, magasin_id: int) -> Decimal:
    return s.scalar(
        select(Solde.quantite).where(Solde.lot_id == x.id, Solde.magasin_id == magasin_id)
    ) or Decimal(0)


def _compter(s: Session, qui: object, i: Inventaire, *comptages: Comptage) -> Inventaire:
    return inv.compter(s, qui, i.id, i.version, list(comptages))  # type: ignore[arg-type]


def _ligne(i: Inventaire, x: Lot) -> int:
    return next(y.id for y in i.lignes if y.lot_id == x.id)


def test_perimetre_par_role_et_tolerance(s: Session) -> None:
    """Hérité : test_stock_atelier::test_inventaire_tolerance_perimetre_et_feuille (partie
    service) — tolérance du réglage (2 %) ; matière inconnue → 422 ; rôle Franges : seul le lot
    de franges est figé ; ligne étrangère → 422 ; −50 justifié → validé ; la matière comptée
    sort du tournant, l'autre y reste."""
    m = _monde(s)
    achats = acteur(s)
    defauts = inv.defauts(s)
    assert defauts.tolerance == pytest.approx(0.02) and "Poil" in [r.code for r in defauts.roles]
    inconnue = Ouverture(JOUR, m.courant.id, criteres=Criteres(matieres=(999999,)))
    r = _refus(inv.ouvrir, s, achats, inconnue)
    assert (r.http, r.detail) == (422, "Matière inconnue : n° 999999.")
    franges = Criteres(roles=(m.a3.role_id,))
    i = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id, criteres=franges))
    assert i.tolerance == Decimal("0.02") and i.numero.startswith("INV-")
    assert [x.lot_id for x in i.lignes] == [m.lots["E-F1"].id]
    r = _refus(_compter, s, achats, i, Comptage(999999, {"compte": Decimal(1)}))
    assert (r.http, r.detail) == (422, "Ligne étrangère à cet inventaire.")
    i = _compter(s, achats, i, Comptage(i.lignes[0].id, {
        "compte": Decimal(950), "justification": "chutes non déclarées"}))  # fmt: skip
    i = inv.valider(s, achats, i.id, i.version)
    assert i.statut == StatutInventaire.valide and i.valide_le is not None
    assert _solde(s, m.lots["E-F1"], m.courant.id) == 950
    dues = {x.article_id for x in inv.a_compter(s, m.courant.id)}
    assert m.a3.id not in dues and m.a1.id in dues
    lu = inv.fiche(s, i.id)
    assert lu.perimetre.startswith("Par famille : Franges") and lu.ecart_total == -50


def test_second_comptage(s: Session) -> None:
    """Hérité : test_stock_atelier::test_inventaire_second_comptage — recomptage sans premier
    comptage → 422 ; −40 : à recompter ; recompté −1 : retenu, dans la tolérance, par Achats ;
    un enregistrement qui ne parle pas du recomptage ne l'efface pas (C-08) ; ajustement −1
    « recompté par Achats »."""
    m = _monde(s)
    achats = acteur(s)
    i = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id, criteres=Criteres(matieres=(m.a2.id,))))
    ligne = i.lignes[0].id
    r = _refus(
        _compter, s, achats, i, Comptage(ligne, {"compte": None, "second_compte": Decimal(3)})
    )
    assert r.detail.endswith(": un recomptage suit un premier comptage.")
    i = _compter(s, achats, i, Comptage(ligne, {"compte": Decimal(360)}))
    lu = inv.fiche(s, i.id)
    assert lu.a_recompter == 1 and lu.lignes[0].a_recompter
    i = _compter(s, achats, i, Comptage(ligne, {"second_compte": Decimal(399)}))
    vue = inv.fiche(s, i.id).lignes[0]
    assert (vue.second_par, vue.retenu, vue.hors_tolerance) == ("Achats", 399, False)
    assert vue.quatre_yeux.startswith("même personne que le premier comptage")
    i = _compter(s, achats, i, Comptage(ligne, {"compte": Decimal(360), "justification": "vu"}))
    assert i.lignes[0].second_compte == 399 and i.lignes[0].justification == "vu"
    i = _compter(s, achats, i, Comptage(ligne, {"palettes": Decimal(1)}))
    assert i.lignes[0].justification == "vu"  # un champ absent ne change rien (C-08)
    i = inv.valider(s, achats, i.id, i.version)
    assert inv.fiche(s, i.id).ecart_total == -1
    mvt = s.scalars(select(Mouvement).where(Mouvement.inventaire_id == i.id)).one()
    assert mvt.quantite == -1 and "recompté par Achats" in mvt.commentaire
    assert mvt.motif_texte == "Écart d'inventaire" and mvt.date_effet == JOUR


def test_suspension_limitee_au_perimetre(s: Session) -> None:
    """Hérité : test_parcours::test_l_inventaire_suspend_puis_ajuste — une sortie d'une matière
    comptée → 409 « inventaire » ; −50 non justifié → 422 ; justifié → validé, lot −50. K2 : une
    autre matière du même magasin bouge librement (N3, « comme en usine »)."""
    m = _monde(s)
    achats = acteur(s)
    i = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id, criteres=Criteres(matieres=(m.a2.id,))))
    with pytest.raises(Refus) as e:
        sortie(s, m.lots["E-T1"], 1, g=m.courant)
    assert e.value.code == "inventaire_en_cours" and i.numero in e.value.detail
    sortie(s, m.lots["E-L1"], 1, g=m.courant)  # hors périmètre : il passe
    ligne = i.lignes[0].id
    i = _compter(s, achats, i, Comptage(ligne, {"compte": Decimal(350)}))
    r = _refus(inv.valider, s, achats, i.id, i.version)
    assert (r.http, r.detail) == (
        422,
        f"Écart hors tolérance sans justification : {m.a2.reference}.",
    )
    assert inv.fiche(s, i.id).blocages[0].startswith("Écart hors tolérance sans justification")
    i = _compter(s, achats, i, Comptage(ligne, {"justification": "palette abîmée"}))
    inv.valider(s, achats, i.id, i.version)
    assert _solde(s, m.lots["E-T1"], m.courant.id) == 350
    sortie(s, m.lots["E-T1"], 1, g=m.courant)  # validé : les mouvements reprennent


def test_perimetre_vide_conflits_et_date(s: Session) -> None:
    """C-04 : un périmètre sans stock n'ouvre rien (aucun numéro consommé) ; C-07 : le refus
    dit le conflit (« sur « CODE » », « sur tous les magasins ») ; IR7 : pas d'inventaire daté
    avant le dernier mouvement d'un lot figé."""
    m = _monde(s)
    achats = acteur(s)
    vide = autre_magasin(s)
    avant = numerotation.dernier(s, "INV", JOUR.year)
    r = _refus(inv.ouvrir, s, achats, Ouverture(JOUR, vide.id))
    assert r.detail == (
        "Aucun lot en stock dans ce périmètre : rien à compter, l'inventaire n'est pas ouvert."
    )
    assert numerotation.dernier(s, "INV", JOUR.year) == avant
    r = _refus(inv.ouvrir, s, achats, Ouverture(jour(-2), m.courant.id))
    assert r.http == 409 and "ont bougé depuis" in r.detail
    i = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id))
    r = _refus(inv.ouvrir, s, achats, Ouverture(JOUR, m.courant.id))
    assert r.detail == f"L'inventaire {i.numero} est déjà ouvert sur « {m.courant.code} »."
    r = _refus(inv.ouvrir, s, achats, Ouverture(JOUR))
    assert r.detail.startswith(f"L'inventaire {i.numero} est déjà ouvert sur « {m.courant.code} »")
    assert "un inventaire de tous les magasins attend" in r.detail


def test_abandon_garde_le_numero_et_les_comptages(s: Session) -> None:
    """C-05 : abandonner garde l'inventaire (statut, numéro, comptages, motif exigé) ; C-06 : le
    lot trouvé n'a jamais été créé ; un abandonné ne se compte, ne se valide ni ne s'annule."""
    m = _monde(s)
    achats = acteur(s)
    i = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id))
    trouve = LotTrouve(m.a2.id, lot_numero="TROUVE-1", compte=Decimal(8), justification="derrière")
    i = inv.lot_trouve(s, achats, i.id, i.version, trouve)
    r = _refus(inv.abandonner, s, achats, i.id, i.version, "")
    assert (r.http, r.detail) == (422, "Dire pourquoi l'inventaire est abandonné.")
    i = inv.abandonner(s, achats, i.id, i.version, "comptage reporté")
    assert (i.statut, i.abandon_motif, i.annulation_motif) == (
        StatutInventaire.abandonne,
        "comptage reporté",
        "",
    )  # RESTES3 : sa colonne (0005), plus annulation_motif
    assert any(x.lot_trouve and x.compte == 8 for x in i.lignes)
    assert s.scalars(select(Lot).where(Lot.numero == "TROUVE-1")).first() is None
    r = _refus(inv.valider, s, achats, i.id, i.version)
    assert r.detail == f"L'inventaire {i.numero} a été abandonné : en ouvrir un nouveau."
    r = _refus(inv.annuler, s, achats, i.id, i.version, "erreur")
    assert r.detail == "Seul un inventaire validé s'annule ; un inventaire en cours s'abandonne."
    autre = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id))
    assert autre.numero != i.numero and inv.liste(s, StatutInventaire.abandonne)


def test_lot_trouve_cree_a_la_validation(s: Session) -> None:
    """C-06 : le lot trouvé (nommé, ou « Lot interne ») n'est créé qu'à la validation ; une
    matière hors périmètre y entre (sa suspension commence) ; pas deux fois le même lot."""
    m = _monde(s)
    achats = acteur(s)
    i = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id, criteres=Criteres(matieres=(m.a2.id,))))
    nomme = LotTrouve(m.a1.id, lot_numero="TR-9", compte=Decimal(12), justification="sous bâche")
    i = inv.lot_trouve(s, achats, i.id, i.version, nomme)
    r = _refus(inv.lot_trouve, s, achats, i.id, i.version, nomme)
    assert r.detail == "Ce lot est déjà dans l'inventaire : saisir son comptage sur sa ligne."
    interne = LotTrouve(
        m.a1.id, lot_interne=True, compte=Decimal(3), justification="sans étiquette"
    )
    i = inv.lot_trouve(s, achats, i.id, i.version, interne)
    suspendues = s.scalars(select(InventaireMatiere.matiere_id).where(
        InventaireMatiere.inventaire_id == i.id)).all()  # fmt: skip
    assert set(suspendues) == {m.a1.id, m.a2.id}
    r = _refus(
        inv.lot_trouve, s, achats, i.id, i.version, LotTrouve(m.a1.id, autre_magasin(s).id, "X")
    )
    assert r.detail == "Cet inventaire ne compte qu'un magasin : le lot trouvé y est rangé."
    t1 = next(x.id for x in i.lignes if x.lot_id == m.lots["E-T1"].id)
    i = _compter(s, achats, i, Comptage(t1, {"compte": Decimal(400)}))
    inv.valider(s, achats, i.id, i.version)
    tr9 = s.scalars(select(Lot).where(Lot.numero == "TR-9", Lot.matiere_id == m.a1.id)).one()
    assert _solde(s, tr9, m.courant.id) == 12 and tr9.entre_le == JOUR
    lu = inv.fiche(s, i.id)
    assert any(x.lot.startswith(f"LOT-{JOUR.year}-") and x.compte == 3 for x in lu.lignes)


def test_annuler_un_inventaire_valide(s: Session) -> None:
    """Hérité : test_defauts_c::test_annuler_inventaire_valide_remet_les_soldes (C-20) : motif
    exigé ; ajustements contre-passés une fois, datés comme eux ; numéro gardé ; refusé si la
    matière ajustée est repartie, ou si un inventaire ouvert la suspend."""
    m = _monde(s)
    achats = acteur(s)
    i = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id, criteres=Criteres(matieres=(m.a1.id,))))
    l1, l2 = _ligne(i, m.lots["E-L1"]), _ligne(i, m.lots["E-L2"])
    i = _compter(s, achats, i, Comptage(l1, {"compte": Decimal(520), "justification": "trouvé"}),
                 Comptage(l2, {"compte": Decimal(290), "justification": "manque"}))  # fmt: skip
    i = inv.valider(s, achats, i.id, i.version)
    r = _refus(inv.annuler, s, achats, i.id, i.version, " ")
    assert (r.http, r.detail) == (422, "Dire pourquoi l'inventaire est annulé.")
    autre = inv.ouvrir(
        s, achats, Ouverture(JOUR, m.courant.id, criteres=Criteres(matieres=(m.a1.id,)))
    )
    r = _refus(inv.annuler, s, achats, i.id, i.version, "erreur de magasin")
    assert r.code == "inventaire_en_cours" and autre.numero in r.detail
    inv.abandonner(s, achats, autre.id, autre.version, "contrôle")
    sortie(s, m.lots["E-L1"], 515, g=m.courant)
    r = _refus(inv.annuler, s, achats, i.id, i.version, "erreur de magasin")
    assert r.code == "stock_insuffisant"
    entree(s, m.lots["E-L1"], 515, g=m.courant)
    i = inv.annuler(s, achats, i.id, i.version, "erreur de magasin")
    assert i.statut == StatutInventaire.annule and i.valide_le is not None
    assert _solde(s, m.lots["E-L2"], m.courant.id) == 300
    inverses = s.scalars(select(Mouvement).where(
        Mouvement.inventaire_id == i.id, Mouvement.contrepasse_id.is_not(None))).all()  # fmt: skip
    assert len(inverses) == 2 and {x.date_effet for x in inverses} == {JOUR}
    r = _refus(inv.annuler, s, achats, i.id, i.version, "encore")
    assert r.detail == f"L'inventaire {i.numero} est déjà annulé."


def test_un_comptage_ne_vaut_que_pour_le_magasin_compte(s: Session) -> None:
    """Hérité : test_valeur_et_dates::test_un_comptage_ne_vaut_que_pour_le_magasin_compte : la
    matière comptée dans un magasin reste due pour l'autre (50 kg) ; filtrée sur le magasin
    compté, elle n'est plus due."""
    m = _monde(s)
    achats = acteur(s)
    ailleurs = autre_magasin(s)
    entree(s, lot(s, m.a2, entre_le=jour(-1)), 50, jour(-1), ailleurs)
    i = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id, criteres=Criteres(matieres=(m.a2.id,))))
    i = _compter(s, achats, i, Comptage(i.lignes[0].id, {"compte": Decimal(400)}))
    inv.valider(s, achats, i.id, i.version)
    due = next(x for x in inv.a_compter(s) if x.article_id == m.a2.id)
    assert due.stock == 50 and due.magasins == [ailleurs.code]
    assert m.a2.id not in {x.article_id for x in inv.a_compter(s, m.courant.id)}
