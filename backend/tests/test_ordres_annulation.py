"""Ordres de fabrication (lot D6) : annulation avec les retours, retours en brouillon supprimés,
prévu et taux de perte figés, consommation, lots sortis. Au niveau du service, dans une
transaction annulée à la fin (`fabriques.stock.s`) ; les retours passent par le service des
opérations (lot D5).
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from fabriques import referentiels as ref
from fabriques import stock as fabriques_stock
from fabriques.ordres import JOUR, acteur, atelier, retour, retour_repris, saisie, valide
from fabriques.stock import entree, lot
from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Journal,
    Lot,
    Matiere,
    Operation,
    Ordre,
    OrdrePrevu,
    Parametre,
    ParametreHistorique,
    QualitePoids,
    Solde,
)
from gestion_mp_pro.modeles.enums import Role, StatutDocument, StatutOrdre
from gestion_mp_pro.services import donnees_moteur, horloge, ordres
from gestion_mp_pro.services.conversions import Unite
from gestion_mp_pro.services.ordres import consommation

s = fabriques_stock.s
"""La session de l'essai, annulée à la fin (fixture du lot S4)."""


def _solde(s: Session, x: Lot, magasin_id: int) -> Decimal:
    s.flush()
    return s.scalar(
        select(Solde.quantite).where(Solde.lot_id == x.id, Solde.magasin_id == magasin_id)
    ) or Decimal(0)


def test_annuler_un_ordre_annule_ses_retours(s: Session) -> None:
    """Hérité : test_stock_atelier::test_annuler_un_ordre_annule_ses_retours — 20 sortis, 5
    rendus : l'annulation rend 15 (le lot retrouve son stock d'avant l'ordre) ; le retour est
    « annulee » ; la réponse le dit."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    trame = a.lot("E-T1")
    avant = _solde(s, trame, a.m.courant.id)
    o = valide(s, qui, saisie(a.m.courant.id, [(trame, 20)]))
    r = retour(s, qui, o, [(trame, 5)])
    assert _solde(s, trame, a.m.courant.id) == avant - 15
    o, phrase = ordres.annuler(s, qui, o.id, o.version, "erreur de saisie")
    assert o.statut == StatutOrdre.annule and o.annulation_motif == "erreur de saisie"
    assert s.get_one(Operation, r.id).statut == StatutDocument.annulee
    assert _solde(s, trame, a.m.courant.id) == avant
    assert r.numero in phrase and "revenue en stock" in phrase
    lu = ordres.fiche(s, o.id)
    assert lu.revenu == 0 and lu.net == 0 and lu.retours == []


def test_d10_annuler_un_ordre_retire_ses_retours_en_brouillon(s: Session) -> None:
    """Hérité : test_defauts_d::test_d10_annuler_un_ordre_retire_ses_retours_en_brouillon —
    supprimé, et dit au journal et dans la réponse."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    o = valide(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 20)]))
    r = retour(s, qui, o, [(a.lot("E-L1"), 5)], valider=False)
    ident = r.id
    o, phrase = ordres.annuler(s, qui, o.id, o.version)
    s.flush()
    assert s.get(Operation, ident) is None
    assert "1 retour(s) en brouillon supprimé(s)" in phrase
    actions = ["annulation ordre", "suppression opération"]
    details = s.scalars(
        select(Journal.detail)
        .where(Journal.action.in_(actions))
        .where(Journal.objet_id.in_([o.id, ident]))
    ).all()
    assert any("brouillon" in x for x in details)


def test_un_ordre_repris_s_annule_avec_ses_retours_sans_document(s: Session) -> None:
    """Hérité : test_audit2_atelier::test_un_ordre_repris_s_annule_avec_ses_retours_sans_document
    — revenu 12,5 + 40 = 52,5 ; net 400 − 52,5 ; « ERP Fil » ; annulé : revenu 0, lots
    revenus à l'état d'avant (1 000 de franges)."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    trame, frange = a.lot("E-T1"), a.lot("E-F1")
    avant = _solde(s, trame, a.m.courant.id)
    o = valide(s, qui, saisie(a.m.courant.id, [(trame, 100), (frange, 300)]))
    retour_repris(s, o, trame, "12.5")
    retour_repris(s, o, frange, 40)
    lu = ordres.fiche(s, o.id)
    assert lu.revenu == Decimal("52.5") and lu.net == pytest.approx(400 - 52.5)
    assert lu.retours and "ERP Fil" in lu.retours[0].numero
    liste = ordres.lister(s, ordres.FiltresOrdres(q=o.numero or ""))
    assert [x.revenu for x in liste] == [Decimal("52.5")]
    o, phrase = ordres.annuler(s, qui, o.id, o.version)
    assert "repris de l'ERP Fil" in phrase
    assert ordres.fiche(s, o.id).revenu == 0
    assert _solde(s, trame, a.m.courant.id) == avant
    assert _solde(s, frange, a.m.courant.id) == 1000


def test_sortie_vers_la_machine_puis_retour(s: Session) -> None:
    """Hérité : test_parcours::test_sortie_vers_la_machine_puis_retour (valeurs exactes, ESSAIS
    § 15) — 50 bobines au poids pesé du lot (998 / 500) = 99,8 kg ; retour de 150 refusé
    (D5) ; retour de 20 ; l'annulation rend tout : 998."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    rouge = lot(
        s, a.m.a1, "ROUGE", entre_le=JOUR - timedelta(days=1), poids_bobine=Decimal("1.996")
    )
    entree(s, rouge, 998, JOUR - timedelta(days=1), a.m.courant)
    o = valide(s, qui, saisie(a.m.courant.id, [(rouge, 50, Unite.bobine)], [(a.e1, 50)]))
    assert o.numero is not None and o.lignes[0].quantite == Decimal("99.8")
    assert _solde(s, rouge, a.m.courant.id) == Decimal("898.2")
    point = s.begin_nested()
    with pytest.raises(Refus) as refus:
        retour(s, qui, o, [(rouge, 150)])
    point.rollback()
    assert refus.value.http == 409
    retour(s, qui, o, [(rouge, 20)])
    assert _solde(s, rouge, a.m.courant.id) == Decimal("918.2")
    assert [(x.lot, x.sorti_net) for x in ordres.lots_sortis(s, o)] == [("ROUGE", Decimal("79.8"))]
    ordres.annuler(s, qui, o.id, o.version)
    assert _solde(s, rouge, a.m.courant.id) == 998
    assert ordres.lots_sortis(s, o) == []


def _frangee(s: Session, a: object) -> tuple[int, int, int, Lot, Lot]:
    """La qualité PB1 de `test_plan_besoins` : poil 1 kg/m², franges 2 ml/m² (0,01 kg/ml)."""
    poil = ref.matiere(s=s)
    frange = ref.matiere(role="Franges", densite="0.01", s=s)
    q = ref.qualite(recette={poil: 100, frange: 100}, poids={"Poil": 1, "Franges": 2}, s=s)
    g = a.m.courant  # type: ignore[attr-defined]
    lp = lot(s, s.get_one(Matiere, poil), "PB-L1")
    entree(s, lp, 1000, JOUR, g)
    lf = lot(s, s.get_one(Matiere, frange), "PB-F1")
    entree(s, lf, 90, JOUR, g)
    return q, poil, frange, lp, lf


def test_le_prevu_d_un_ordre_est_fige(s: Session) -> None:
    """Hérité : test_plan_besoins::test_le_prevu_d_un_ordre_est_fige_et_le_bilan_le_lit_comme_les_sorties
    (partie ordres ; le bilan est au lot D8) — prévu 10 × (1 + 0,02) × 1,02 ; figé {poil 10,
    franges 0,2 ; perte 0,02} ; doubler le poids du poil ne le change pas ; net 50."""  # noqa: E501
    a, qui = atelier(s), acteur(s, Role.alimentation)
    q, poil, frange, lp, lf = _frangee(s, a)
    o = valide(s, qui, saisie(a.m.courant.id, [(lp, 30), (lf, 20)], [(q, 10)]))
    s.flush()
    lus = select(OrdrePrevu.matiere_id, OrdrePrevu.kg_hors_perte).where(OrdrePrevu.ordre_id == o.id)
    fige = dict(s.execute(lus).all())
    assert fige == {poil: Decimal("10.000"), frange: Decimal("0.200")}
    assert o.prevu_fige and o.taux_perte_fige == Decimal("0.02")
    prevu = ordres.fiche(s, o.id).prevu
    assert prevu == pytest.approx(10 * (1 + 0.02) * 1.02)
    for p in s.scalars(select(QualitePoids).where(QualitePoids.qualite_id == q)):
        p.poids *= 2
    s.flush()
    lu = ordres.fiche(s, o.id)
    assert lu.prevu == pytest.approx(prevu) and lu.net == pytest.approx(50)


def test_d07_changer_le_taux_de_perte_ne_reecrit_pas_un_ordre(s: Session) -> None:
    """Hérité : test_defauts_d::test_d07_changer_le_taux_de_perte_ne_reecrit_pas_un_ordre_ancien
    — un ordre validé garde son taux figé ; un ordre repris sans prévu figé prend le taux en
    vigueur à sa validation, relu dans l'historique des réglages."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    o = valide(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 10)], [(a.e1, 10)]))
    ancien = valide(s, qui, saisie(a.m.courant.id, [(a.lot("E-L2"), 10)], [(a.e1, 10)]))
    ancien.prevu_fige, ancien.taux_perte_fige = False, None  # un ordre repris, non figé
    s.flush()
    avant = ordres.fiche(s, o.id).prevu, ordres.fiche(s, ancien.id).prevu
    taux = s.get_one(Parametre, "taux_perte")
    taux.valeur = "0.05"
    s.add(ParametreHistorique(cle="taux_perte", avant="0.02", apres="0.05",
                              quand=horloge.maintenant() + timedelta(hours=1)))  # fmt: skip
    s.flush()
    donnees_moteur.invalider()
    assert (ordres.fiche(s, o.id).prevu, ordres.fiche(s, ancien.id).prevu) == pytest.approx(avant)
    assert ordres.fiche(s, ancien.id).taux_perte == pytest.approx(0.02)
    assert ordres.fiche(s, o.id).taux_perte == pytest.approx(0.02)


def test_d03_renommer_une_matiere_garde_l_ecart_des_ordres(s: Session) -> None:
    """Hérité : test_defauts_d::test_d03_renommer_une_matiere_garde_l_ecart_des_ordres — le
    prévu figé désigne la matière par son id."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    o = valide(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 12)], [(a.e1, 10)]))
    avant = ordres.fiche(s, o.id)
    a.m.a2.reference = "TRAME RENOMMÉE"
    s.flush()
    apres = ordres.fiche(s, o.id)
    assert (apres.prevu, apres.ecart) == pytest.approx((avant.prevu, avant.ecart))
    assert not any(x.hors_recette for x in apres.par_matiere)
    assert "TRAME RENOMMÉE" in {x.reference for x in apres.par_matiere}


def test_d06_poids_bobine_ignore_une_sortie_annulee(s: Session) -> None:
    """Hérité : test_defauts_d::test_d06_poids_bobine_ignore_une_sortie_annulee — le poids d'une
    bobine montée est celui du dernier lot sorti **qui compte encore**."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    p1, p2 = a.lot("E-L1"), a.lot("E-L2")
    p1.poids_bobine, p2.poids_bobine = Decimal(2), Decimal(3)
    valide(s, qui, saisie(a.m.courant.id, [(p1, 4)]))
    annule = valide(s, qui, saisie(a.m.courant.id, [(p2, 6)]))
    ordres.annuler(s, qui, annule.id, annule.version)
    s.flush()
    assert donnees_moteur.poids_bobine_mesures(s)[a.m.a1.id] == (2.0, p1.numero, "sorti")


def test_un_ordre_annule_avec_son_retour_ne_compte_rien(s: Session) -> None:
    """Hérité : test_plan_besoins::test_un_ordre_annule_avec_son_retour_ne_compte_ni_sortie_ni_retour
    — consommé, retours, net : 0 ; absent de la consommation des ordres (P74)."""  # noqa: E501
    a, qui = atelier(s), acteur(s, Role.alimentation)
    o = valide(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 20)], [(a.e1, 10)]))
    retour(s, qui, o, [(a.lot("E-L1"), 5)])
    conso = {x.numero: x for x in ordres.consommation_des_ordres(s)}
    assert conso[o.numero or ""].net == pytest.approx(15)
    assert conso[o.numero or ""].retours == pytest.approx(5)
    ordres.annuler(s, qui, o.id, o.version)
    s.flush()
    x = consommation.consommations(s)[o.numero or ""]
    assert (x.consomme, x.retours, x.net) == (0, 0, 0)
    assert o.numero not in {y.numero for y in ordres.consommation_des_ordres(s)}
    assert s.get_one(Ordre, o.id).numero == o.numero  # le numéro reste


def test_annuler_refuse_un_brouillon_et_ne_touche_rien(s: Session) -> None:
    """PR20 : seul un ordre validé s'annule ; un brouillon se supprime."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    o = ordres.creer(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 1)]))
    with pytest.raises(Refus) as refus:
        ordres.annuler(s, qui, o.id, o.version)
    assert refus.value.detail == "Seul un ordre validé s'annule ; un brouillon se supprime."
