"""Le stock sous plusieurs postes à la fois (lot S4 ; I04, I10, I30 ; PLAN-DE-RECETTE A10) :
chaque essai valide ses transactions (des fils, des sessions à part) sur des fiches à son nom.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from fabriques.stock import JOUR, REPRISE, entree, magasin, matiere, s
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import Lot, Mouvement, Solde
from gestion_mp_pro.modeles.enums import TypeMouvement
from gestion_mp_pro.services import lots, stock

__all__ = ["s"]

REPETITIONS = 50


def _en_meme_temps(geste: Callable[[Session], object], postes: int = 2) -> list[str]:
    """Le même geste lancé par `postes` sessions au même instant ; « ok » ou le code du refus."""
    depart = threading.Barrier(postes)
    issues: list[str] = []

    def poste() -> None:
        with fabrique()() as session:
            depart.wait()
            try:
                geste(session)
                session.commit()
                issues.append("ok")
            except Refus as refus:
                session.rollback()
                issues.append(refus.code)

    fils = [threading.Thread(target=poste) for _ in range(postes)]
    for f in fils:
        f.start()
    for f in fils:
        f.join(timeout=30)
    return sorted(issues)


def _lot_garni(quantite: int) -> tuple[int, int]:
    """Un lot de `quantite` kg, validé en base : (lot, magasin)."""
    with fabrique()() as session:
        x = lots.lot_ou_creer(session, matiere(session).id, "PALETTE", JOUR)
        entree(session, x, quantite)
        g = magasin(session).id
        session.commit()
        return x.id, g


def _sortir(lot_id: int, magasin_id: int, quantite: int) -> Callable[[Session], object]:
    def geste(session: Session) -> object:
        x = session.get(Lot, lot_id)
        assert x is not None
        return stock.ecrire(
            session, type=TypeMouvement.SORTIE, lot=x, magasin_id=magasin_id,
            quantite=-quantite, jour=JOUR, piece=REPRISE, auteur_id=None,
        )  # fmt: skip

    return geste


def test_deux_sorties_de_70_pour_cent_jamais_sous_zero() -> None:
    """Deux postes sortent 70 % de la même palette au même instant, 50 fois : une passe,
    l'autre est refusée (elle attend le verrou, puis lit le solde à jour) ; jamais de solde
    négatif. Hérité : test_parcours::test_deux_sorties_simultanees_sur_la_meme_palette."""
    for _ in range(REPETITIONS):
        lot_id, g = _lot_garni(100)
        assert _en_meme_temps(_sortir(lot_id, g, 70)) == ["ok", "stock_insuffisant"]
        with fabrique()() as session:
            solde = session.scalar(select(Solde.quantite).where(Solde.lot_id == lot_id))
            journal = session.scalar(
                select(func.sum(Mouvement.quantite)).where(Mouvement.lot_id == lot_id)
            )
        assert solde == journal == Decimal("30.000")


def test_deux_annulations_simultanees_une_seule_passe() -> None:
    """I10 : deux postes annulent la même sortie au même instant : une contre-passation."""
    lot_id, g = _lot_garni(100)
    with fabrique()() as session:
        origine = _sortir(lot_id, g, 40)(session)
        assert isinstance(origine, Mouvement)
        ident = origine.id
        session.commit()

    def annuler(session: Session) -> object:
        x = session.get(Mouvement, ident)
        assert x is not None
        return stock.contrepasser_mouvements(session, [x], None)

    assert _en_meme_temps(annuler) == ["deja_annule", "ok"]
    with fabrique()() as session:
        assert session.scalar(select(Solde.quantite).where(Solde.lot_id == lot_id)) == 100


def test_deux_postes_creent_le_meme_lot_une_fois() -> None:
    """I30 : `lot_ou_creer` simultané sur (matière, numéro) : un seul lot."""
    with fabrique()() as session:
        m = matiere(session).id
        session.commit()
    assert _en_meme_temps(lambda x: lots.lot_ou_creer(x, m, "DOUBLE-1", JOUR)) == ["ok", "ok"]
    with fabrique()() as session:
        nombre = session.scalar(select(func.count()).select_from(Lot).where(Lot.matiere_id == m))
    assert nombre == 1


def test_le_numero_de_lot_interne_ne_se_troue_pas(s: Session) -> None:
    """M65, T7 : le numéro `LOT-AAAA-NNNN` est donné à la validation ; une validation refusée
    l'annule avec elle (le suivant reprend le même numéro)."""
    m = matiere(s)
    premier = lots.lot_interne(s, m.id, JOUR)
    s.commit()
    point = s.begin_nested()
    perdu = lots.numero_interne(s, JOUR)
    point.rollback()
    suivant = lots.lot_interne(s, m.id, date(2026, 10, 1))
    annee, rang = premier.numero.rsplit("-", 1)[0], int(premier.numero.rsplit("-", 1)[1])
    assert annee == "LOT-2026" and premier.interne
    assert suivant.numero == perdu == f"LOT-2026-{rang + 1:04d}"
