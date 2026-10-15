"""La fiche d'un ordre se calcule sur **son** journal, pas sur le moteur entier (stress « 3 ans »,
A4 : à 38 000 écritures, la réponse de `POST /ordres/{id}/valider` rechargeait tout le moteur,
1,2 s ; `GET /ordres` de même).

- `consommations_de(s, ordres)` rend, pour ces ordres, exactement ce que `consommations(s)`
  rend pour eux : validés avec prévu figé, repris sans prévu figé (taux de perte à la
  validation), avec retours (opération et reprise), annulés (rien), partagés par paquets.
- La fiche d'un ordre fraîchement validé, et une page de liste, ne relisent pas le moteur
  entier (`donnees_moteur.lire` n'est pas appelé) ; une liste de plus de `CIBLES_MAX` ordres
  numérotés repasse par le moteur entier (en cache).
- `charger_ordres` : le journal réduit est le sous-ensemble exact du journal entier portant
  ces ordres, dans le même ordre ; les ordres réduits sont ceux du moteur entier.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta

import pytest
from fabriques import stock as fabriques_stock
from fabriques.ordres import JOUR, Atelier, acteur, atelier, retour, retour_repris, saisie, valide
from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import Ordre
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.services import donnees_moteur, ordres
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.ordres import consommation, lecture, liste

s = fabriques_stock.s
"""La session de l'essai, annulée à la fin (fixture du lot S4)."""


def _decor(s: Session) -> tuple[Atelier, Acteur, list[Ordre]]:
    """Quatre ordres : validé avec retour d'opération, validé avec retour repris, hors recette,
    annulé ; et un brouillon qui ne compte pas."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    poil, trame = a.lot("E-L1"), a.lot("E-T1")
    o1 = valide(s, qui, saisie(a.m.courant.id, [(poil, 12), (trame, 6)], [(a.e1, 10)]))
    retour(s, qui, o1, [(poil, 2)])
    o2 = valide(s, qui, saisie(a.m.courant.id, [(poil, 21), (trame, 5)], [(a.e2, 10)]))
    retour_repris(s, o2, trame, "0.5")
    o3 = valide(s, qui, saisie(a.m.courant.id, [(trame, 3)]))
    o4 = valide(s, qui, saisie(a.m.courant.id, [(poil, 4)], [(a.e1, 3)]))
    retour(s, qui, o4, [(poil, 1)])
    o4, _ = ordres.annuler(s, qui, o4.id, o4.version, "essai")
    ordres.creer(s, qui, saisie(a.m.courant.id, [(poil, 1)], [(a.e1, 1)]))
    s.flush()
    return a, qui, [o1, o2, o3, o4]


def _memes(a: object, b: object) -> bool:
    return asdict(a) == asdict(b)  # type: ignore[call-overload]


def test_la_consommation_ciblee_est_celle_du_moteur_entier(s: Session) -> None:
    """Un à un et par paquet : mêmes prévu, net, écart, retours, lots, taux, références."""
    _, _, faits = _decor(s)
    entier = consommation.consommations(s)
    for o in faits:
        cible = consommation.consommations_de(s, [o])
        assert set(cible) == {o.numero}
        assert _memes(cible[o.numero or ""], entier[o.numero or ""])
    paquet = consommation.consommations_de(s, faits)
    assert set(paquet) == {o.numero for o in faits}
    assert all(_memes(paquet[o.numero or ""], entier[o.numero or ""]) for o in faits)
    assert paquet[faits[0].numero or ""].retours == pytest.approx(2.0)
    assert paquet[faits[1].numero or ""].retours == pytest.approx(0.5)
    assert paquet[faits[3].numero or ""].net == 0.0
    assert consommation.consommations_de(s, []) == {}


def test_la_fiche_et_la_page_ne_rechargent_pas_le_moteur_entier(
    s: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Après une validation (cache périmé), la fiche et une page de liste lisent le journal de
    leurs ordres seuls ; les chiffres sont ceux du moteur entier."""
    _, _, faits = _decor(s)
    attendu = {o.id: ordres.fiche(s, o.id) for o in faits}
    donnees_moteur.invalider()

    def interdit(*_a: object, **_k: object) -> None:
        raise AssertionError("le moteur entier a été relu pour une fiche")

    monkeypatch.setattr(donnees_moteur, "lire", interdit)
    for o in faits:
        lu = ordres.fiche(s, o.id)
        assert _memes(lu, attendu[o.id])
    page = liste.lister(s, liste.FiltresOrdres(), None, 50)
    lus = {x.id: x for x in page.elements}
    assert all(_memes(lus[o.id], attendu[o.id]) for o in faits)


def test_au_dela_du_seuil_le_moteur_entier_reprend(
    s: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plus de `CIBLES_MAX` ordres numérotés : la lecture ciblée n'est pas tentée."""
    _, _, faits = _decor(s)
    monkeypatch.setattr(lecture, "CIBLES_MAX", len(faits) - 1)

    def interdit(*_a: object, **_k: object) -> None:
        raise AssertionError("lecture ciblée au-delà du seuil")

    monkeypatch.setattr(consommation, "consommations_de", interdit)
    ctx = lecture.contexte(s, faits)
    assert {o.numero for o in faits} <= set(ctx.conso)


def test_charger_ordres_est_le_sous_ensemble_exact_du_moteur(s: Session) -> None:
    """Journal réduit = écritures du moteur entier portant ces ordres, dans le même ordre ;
    ordres réduits = les ordres validés du moteur entier parmi eux (l'annulé n'y est pas)."""
    _, _, faits = _decor(s)
    numeros = {o.numero for o in faits}
    d = donnees_moteur.charger(s)
    reduit = donnees_moteur.charger_ordres(s, [o.id for o in faits])
    attendu = [m for m in d.mouvements if m.numero_of in numeros]
    assert len(attendu) > len(faits)  # sorties, retours, contre-passations de l'annulé
    assert [asdict(m) for m in attendu] == [asdict(m) for m in reduit.mouvements]
    valides = [x for x in d.ordres if x.numero in numeros]
    assert [asdict(x) for x in valides] == [asdict(x) for x in reduit.ordres]
    assert {x.numero for x in reduit.ordres} == numeros - {faits[3].numero}
    assert reduit.commandes == [] and reduit.receptions == [] and reduit.soldes is None


def test_un_ordre_d_hier_repris_sans_prevu_fige_prend_le_taux_de_sa_validation(
    s: Session,
) -> None:
    """Le taux de perte d'un ordre sans prévu figé se lit à sa validation (D-07) : ciblé comme
    entier."""
    a, qui = atelier(s), acteur(s, Role.alimentation)
    o = valide(s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 5)], [(a.e1, 4)], le=JOUR))
    o.prevu_fige, o.taux_perte_fige = False, None
    o.valide_le = o.valide_le - timedelta(days=1) if o.valide_le else None
    s.flush()
    numero = o.numero or ""
    entier = consommation.consommations(s)[numero]
    cible = consommation.consommations_de(s, [s.get_one(Ordre, o.id)])[numero]
    assert _memes(cible, entier) and cible.taux_perte == entier.taux_perte
    assert s.scalar(select(Ordre.id).where(Ordre.id == o.id)) == o.id
