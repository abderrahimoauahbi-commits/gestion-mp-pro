"""Ordres de fabrication, au niveau du service (lot D6) : saisie, unités, proposition FIFO à la
date, blocages, validation (numéros dans l'ordre des dates, prévu figé). Chaque essai travaille
dans une transaction annulée à la fin (`fabriques.stock.s`) ; ceux qui datent un ordre dans le
passé vident d'abord l'activité **dans** cette transaction (`vider`), pour ne pas dépendre des
ordres validés en base par les autres essais.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from fabriques import referentiels as ref
from fabriques import stock as fabriques_stock
from fabriques.ordres import JOUR, Atelier, acteur, atelier, brouillon, saisie, valide
from fabriques.stock import entree, inventaire_ouvert, lot, vider
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Journal, Lot, Matiere, OrdreQualite, Qualite, Solde
from gestion_mp_pro.modeles.enums import Role, StatutOrdre
from gestion_mp_pro.services import ordres
from gestion_mp_pro.services.conversions import Unite

s = fabriques_stock.s
"""La session de l'essai, annulée à la fin (fixture du lot S4)."""
HIER = JOUR - timedelta(days=1)


def _refus(fonction: object, *args: object, **kw: object) -> Refus:
    """Le refus d'un geste ; ce qu'il avait commencé est défait (comme la route le ferait)."""
    s = next(x for x in args if isinstance(x, Session))
    point = s.begin_nested()
    with pytest.raises(Refus) as e:
        fonction(*args, **kw)  # type: ignore[operator]
    point.rollback()
    return e.value


def _solde(s: Session, x: Lot, magasin_id: int) -> Decimal:
    return s.scalar(
        select(Solde.quantite).where(Solde.lot_id == x.id, Solde.magasin_id == magasin_id)
    ) or Decimal(0)


def _demande(a: Atelier, *qualites: tuple[int, float], le: object = None) -> ordres.Demande:
    return ordres.Demande(
        magasin_id=a.m.courant.id,
        qualites=tuple(ordres.SaisieQualite(q, Decimal(str(m2))) for q, m2 in qualites),
        date=le,  # type: ignore[arg-type]
    )


def test_sortie_plusieurs_qualites_et_unites(s: Session) -> None:
    """Hérité : test_stock_atelier::test_sortie_plusieurs_qualites_et_unites — une matière qui
    sert deux qualités apparaît une fois (`par_qualite`) ; une qualité une fois par ordre ;
    1 palette (50 × 2) = 100, 5 bobines = 10, 30 kg ; « ml » refusé ; bobines sans poids
    refusées ; brouillon modifiable, hors recette ; validé : `OF-`."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    p = ordres.proposer(s, _demande(a, (a.e1, 10), (a.e2, 10)))
    poil = next(x for x in p.lignes if x.matiere_id == a.m.a1.id)
    assert [q.qualite_id for q in poil.par_qualite] == sorted(
        [a.e1, a.e2], key=lambda i: s.get_one(Qualite, i).code
    )
    assert poil.bobines_palette == 50 and poil.poids_bobine == 2
    assert all(x.poids_bobine == 2 for x in poil.lots)
    double = saisie(a.m.courant.id, [(a.lot("E-L1"), 1)], [(a.e1, 5), (a.e1, 5)])
    assert "une fois" in _refus(brouillon, s, qui, double).detail
    e = saisie(
        a.m.courant.id,
        [(a.lot("E-L1"), 1, Unite.palette), (a.lot("E-L2"), 5, Unite.bobine), (a.lot("E-F1"), 30)],
        [(a.e1, 10), (a.e2, 10)], commentaire="équipe B",
    )  # fmt: skip
    o = brouillon(s, qui, e)
    assert [x.quantite for x in sorted(o.lignes, key=lambda y: y.id)] == [100, 10, 30]
    assert o.commentaire == "équipe B" and o.numero is None
    ml = saisie(a.m.courant.id, [(a.lot("E-F1"), 3, "ml")])
    assert "kilos" in _refus(ordres.modifier, s, qui, o.id, o.version, ml).detail
    bob = saisie(a.m.courant.id, [(a.lot("E-F1"), 3, Unite.bobine)])
    assert "bobine" in _refus(ordres.modifier, s, qui, o.id, o.version, bob).detail
    hors = saisie(a.m.courant.id, [(a.lot("E-T1"), 12)], commentaire="échantillons")
    o = ordres.modifier(s, qui, o.id, o.version, hors)
    lu = ordres.fiche(s, o.id)
    assert lu.qualites == [] and lu.total == 12 and lu.blocages == []
    assert lu.fabrication == "hors recette"
    o = ordres.valider(s, qui, o.id, o.version)
    assert o.numero is not None and o.numero.startswith("OF-2026-") and o.valide_le


def test_sortie_refuse_quarantaine_et_date_ancienne(s: Session) -> None:
    """Hérité : test_stock_atelier::test_sortie_refuse_quarantaine_et_date_ancienne."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    q = saisie(a.m.quarantaine.id, [(a.lot("E-Q1"), 1)])
    assert "quarantaine" in _refus(brouillon, s, qui, q).detail
    vieux = saisie(a.m.courant.id, [(a.lot("E-L1"), 1)], le=JOUR.replace(year=1999))
    assert "ancienne" in _refus(brouillon, s, qui, vieux).detail


def test_proposition_perte_comprise_et_un_seul_total(s: Session) -> None:
    """Hérité : test_stock_atelier::test_proposition_perte_comprise_et_un_seul_total — 100 m² ×
    1 kg × 1,02 = 102 ; 3 + 7 kg (trame, franges) : un seul total 10 ; densité des franges."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    p = ordres.proposer(s, _demande(a, (a.e1, 100)))
    poil = next(x for x in p.lignes if x.matiere_id == a.m.a1.id)
    assert poil.prevu == Decimal("102.000") and p.taux_perte == Decimal("0.02")
    o = brouillon(s, qui, saisie(a.m.courant.id, [(a.lot("E-T1"), 3), (a.lot("E-F1"), 7)]))
    lu = ordres.fiche(s, o.id)
    assert lu.total == 10 and [x.kg_par_ml for x in lu.lignes] == [0, Decimal("0.014")]


def _poil_seul(s: Session, a: Atelier) -> tuple[int, Lot, Lot]:
    """Une qualité de poil seul (1 kg/m²) : un vieux lot (50 kg, avant-hier) et un neuf (400 kg,
    aujourd'hui), dans le magasin du décor."""
    poil = ref.matiere(s=s)
    q = ref.qualite(recette={poil: 100}, poids={"Poil": 1}, s=s)
    fiche = s.get_one(Matiere, poil)
    vieux = lot(s, fiche, "VIEUX", entre_le=JOUR - timedelta(days=2))
    entree(s, vieux, 50, JOUR - timedelta(days=2), a.m.courant)
    neuf = lot(s, fiche, "NEUF", entre_le=JOUR)
    entree(s, neuf, 400, JOUR, a.m.courant)
    return q, vieux, neuf


def test_la_proposition_ne_prend_que_les_lots_presents_a_la_date(s: Session) -> None:
    """Hérité : test_audit2_atelier::test_la_proposition_ne_prend_que_les_lots_presents_a_la_date
    — aujourd'hui [VIEUX, NEUF] ; hier [VIEUX] et il manque 102 − 50 = 52."""
    a = atelier(s)
    q, vieux, neuf = _poil_seul(s, a)
    p = ordres.proposer(s, _demande(a, (q, 100)))
    assert [x.lot for x in p.lignes[0].lots] == ["VIEUX", "NEUF"]
    p = ordres.proposer(s, _demande(a, (q, 100), le=HIER))
    assert [x.lot for x in p.lignes[0].lots] == ["VIEUX"]
    assert p.lignes[0].manque == Decimal(52) and p.manques == p.lignes


def test_un_ordre_d_hier_ne_valide_pas_un_lot_arrive_aujourd_hui(s: Session) -> None:
    """Hérité : test_audit2_atelier::test_un_ordre_d_hier_ne_valide_pas_un_lot_arrive_aujourd_hui
    — blocage « après la date de l'ordre », 409 nommant le lot, lot intact (400)."""
    vider(s)
    a, qui = atelier(s), acteur(s, Role.alimentation)
    _q, _vieux, neuf = _poil_seul(s, a)
    o = brouillon(s, qui, saisie(a.m.courant.id, [(neuf, 10)], le=HIER))
    assert any(
        "NEUF" in x and "après la date de l'ordre" in x for x in ordres.fiche(s, o.id).blocages
    )
    refus = _refus(ordres.valider, s, qui, o.id, o.version)
    assert refus.http == 409 and "NEUF" in refus.detail
    assert _solde(s, neuf, a.m.courant.id) == 400


def test_une_qualite_arretee_ne_part_plus(s: Session) -> None:
    """Hérité : test_audit2_atelier::test_une_qualite_arretee_ne_part_plus — proposition 422
    « arrêtée », blocage du brouillon, validation 409."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    o = brouillon(s, qui, saisie(a.m.courant.id, [(a.lot("E-T1"), 5)], [(a.e1, 10)]))
    s.get_one(Qualite, a.e1).actif = False
    s.flush()
    refus = _refus(ordres.proposer, s, _demande(a, (a.e1, 10)))
    assert refus.http == 422 and "arrêtée" in refus.detail
    assert any("arrêtée" in x for x in ordres.fiche(s, o.id).blocages)
    refus = _refus(ordres.valider, s, qui, o.id, o.version)
    assert refus.http == 409 and "arrêtée" in refus.detail


def test_d08_une_bobine_se_compte_entiere(s: Session) -> None:
    """Hérité : test_defauts_d::test_d08_une_bobine_se_compte_entiere (U20) ; la palette peut
    être entamée."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    demi = saisie(a.m.courant.id, [(a.lot("E-L1"), "2.5", Unite.bobine)])
    refus = _refus(brouillon, s, qui, demi)
    assert refus.http == 422 and "entière" in refus.detail
    o = brouillon(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 3, Unite.bobine)]))
    assert o.lignes[0].quantite == 6
    o = brouillon(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), "0.5", Unite.palette)]))
    assert o.lignes[0].quantite == 50
    assert ordres.fiche(s, o.id).lignes[0].bobines == 25


def test_d09_messages_d_un_ordre(s: Session) -> None:
    """Hérité : test_defauts_d::test_d09_messages_d_un_ordre — « 1 234,5 kg » au journal ; un
    ordre annulé ne « se valide plus » ; « déjà annulé » ; « Ordre introuvable. »."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    o = valide(s, qui, saisie(a.m.courant.id, [(a.lot("E-F1"), "934.5"), (a.lot("E-L1"), 300)]))
    s.flush()
    detail = s.scalar(
        select(Journal.detail).where(Journal.action == "validation ordre", Journal.objet_id == o.id)
    )
    assert detail is not None and "1 234,5 kg" in detail and o.numero in detail
    o, _ = ordres.annuler(s, qui, o.id, o.version)
    refus = _refus(ordres.valider, s, qui, o.id, o.version)
    assert refus.http == 409 and "annulé" in refus.detail and "valide plus" in refus.detail
    refus = _refus(ordres.annuler, s, qui, o.id, o.version)
    assert refus.http == 409 and "déjà annulé" in refus.detail
    assert _refus(ordres.fiche, s, 999_999).detail == "Ordre introuvable."


def test_d11_la_proposition_controle_magasin_et_date(s: Session) -> None:
    """Hérité : test_defauts_d::test_d11_la_proposition_controle_magasin_et_date — quarantaine
    422, magasin inconnu 404, date future 422."""
    a = atelier(s)
    q = ordres.Demande(a.m.quarantaine.id, (ordres.SaisieQualite(a.e1, Decimal(10)),))
    refus = _refus(ordres.proposer, s, q)
    assert refus.http == 422 and "quarantaine" in refus.detail
    inconnu = ordres.Demande(0, (ordres.SaisieQualite(a.e1, Decimal(10)),))
    assert _refus(ordres.proposer, s, inconnu).http == 404
    refus = _refus(ordres.proposer, s, _demande(a, (a.e1, 10), le=JOUR + timedelta(days=1)))
    assert refus.http == 422 and "futur" in refus.detail


def test_d21_une_qualite_une_fois_par_ordre_en_base(s: Session) -> None:
    """Hérité : test_defauts_d::test_d21_une_qualite_une_fois_par_ordre_en_base."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    o = brouillon(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 1)], [(a.e1, 5)]))
    point = s.begin_nested()
    with pytest.raises(IntegrityError):
        s.add(OrdreQualite(ordre_id=o.id, qualite_id=a.e1, m2=Decimal(5)))
        s.flush()
    point.rollback()


def test_une_recette_qui_oublie_un_role_bloque_l_ordre(s: Session) -> None:
    """Une qualité dont la recette oublie un rôle pesant (`recettes.oublies`, D2) : la
    proposition le dit (P14, mot pour mot), le brouillon l'annonce, la validation le refuse —
    le prévu figé serait faux pour toujours."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    q = ref.qualite(recette={a.m.a1.id: 100}, poids={"Poil": 1, "Trame": "0.5"}, s=s)
    code = s.get_one(Qualite, q).code
    p = ordres.proposer(s, _demande(a, (q, 10)))
    assert p.recettes_incompletes == [
        f"{code} : le rôle Trame pèse 0.5 au m², mais la recette ne nomme aucune matière pour "
        "lui : rien ne lui est proposé. La direction doit compléter la recette."
    ]
    o = brouillon(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 10)], [(q, 10)]))
    assert f"{code} : La recette oublie le rôle Trame (0,5 au m²)" in " ".join(
        ordres.fiche(s, o.id).blocages
    )
    refus = _refus(ordres.valider, s, qui, o.id, o.version)
    assert refus.code == "validation_bloquee" and "Trame" in refus.detail


def test_un_inventaire_ne_bloque_que_son_perimetre(s: Session) -> None:
    """K2 : un inventaire ouvert sur le magasin ne bloque que les matières qu'il compte ;
    la proposition l'annonce avec le texte de l'écran."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    i = inventaire_ouvert(s, a.m.courant, [a.m.a2])
    trame = brouillon(s, qui, saisie(a.m.courant.id, [(a.lot("E-T1"), 5)]))
    poil = brouillon(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 5)]))
    assert (
        f"l'inventaire {i.numero} est en cours sur « {a.m.courant.code} »"
        in ordres.fiche(s, trame.id).blocages
    )
    assert ordres.fiche(s, poil.id).blocages == []
    assert _refus(ordres.valider, s, qui, trame.id, trame.version).code == "inventaire_en_cours"
    ordres.valider(s, qui, poil.id, poil.version)
    p = ordres.proposer(s, _demande(a, (a.e1, 10)))
    assert any(
        x.startswith(f"L'inventaire {i.numero} ({a.m.courant.code}, du ") for x in p.blocages
    )


def test_les_numeros_suivent_les_dates(s: Session) -> None:
    """M67, O1 (P52) : un ordre ne se valide pas à une date antérieure au dernier ordre validé
    **ou annulé** ; la même date passe ; un brouillon d'hier l'annonce ; numéros sans trou."""
    vider(s)
    a, qui = atelier(s, le=HIER), acteur(s, Role.alimentation)
    hier = brouillon(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 1)], le=HIER))
    o1 = valide(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 1)]))
    ordres.annuler(s, qui, o1.id, o1.version)
    attendu = (
        f"un ordre daté du {JOUR:%d/%m/%Y} est déjà validé : dater cet ordre au moins de ce jour"
    )
    assert attendu in ordres.fiche(s, hier.id).blocages
    refus = _refus(ordres.valider, s, qui, hier.id, hier.version)
    assert refus.code == "ordre_des_dates" and "date antérieure" in refus.detail
    o2 = valide(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 1)]))
    rang = int(o1.numero.rsplit("-", 1)[1])  # type: ignore[union-attr]
    assert o2.numero == f"OF-2026-{rang + 1:04d}"
    assert ordres.fiche(s, hier.id).statut == StatutOrdre.brouillon
