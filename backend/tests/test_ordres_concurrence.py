"""Ordres de fabrication sous plusieurs postes à la fois (lot D6 ; PLAN-DE-RECETTE A10) : chaque
essai valide ses transactions (des fils, des sessions à part), sur des données à lui, et répète
la course. Les ordres sont datés d'aujourd'hui (le jour le plus récent : aucun ordre laissé par
un autre essai ne les refuse).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from decimal import Decimal

from fabriques import referentiels as ref
from fabriques.ordres import Atelier, acteur, atelier, retour, saisie, valide
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.db import Verrou, fabrique, moteur
from gestion_mp_pro.modeles import Lot, Mouvement, Ordre, Solde
from gestion_mp_pro.modeles.enums import Role, StatutOrdre
from gestion_mp_pro.services import ordres
from gestion_mp_pro.services.comptes import Acteur

REPETITIONS = 10


def _en_meme_temps(*gestes: Callable[[Session], object]) -> list[str]:
    """Les gestes lancés au même instant, chacun dans sa session ; « ok » ou le code du refus."""
    depart = threading.Barrier(len(gestes))
    issues: list[str] = [""] * len(gestes)

    def poste(rang: int) -> None:
        with fabrique()() as session:
            depart.wait()
            try:
                gestes[rang](session)
                session.commit()
                issues[rang] = "ok"
            except Refus as refus:
                session.rollback()
                issues[rang] = refus.code

    fils = [threading.Thread(target=poste, args=(i,)) for i in range(len(gestes))]
    for f in fils:
        f.start()
    for f in fils:
        f.join(timeout=60)
    return issues


def _decor() -> tuple[Atelier, Acteur]:
    """Un atelier à soi et un compte de l'alimentation, validés en base."""
    with fabrique()() as s:
        a, qui = atelier(s), acteur(s, Role.alimentation)
        s.commit()
    return a, qui


def _solde(lot_id: int) -> Decimal:
    with fabrique()() as s:
        return s.scalar(select(func.sum(Solde.quantite)).where(Solde.lot_id == lot_id)) or Decimal(
            0
        )


def _brouillons(qui: Acteur, magasin_id: int, lot: Lot, kg: float, n: int) -> list[int]:
    with fabrique()() as s:
        ids = [ordres.creer(s, qui, saisie(magasin_id, [(lot, kg)])).id for _ in range(n)]
        s.commit()
    return ids


def test_deux_sorties_simultanees_sur_la_meme_palette() -> None:
    """Hérité : test_parcours::test_deux_sorties_simultanees_sur_la_meme_palette — deux ordres de
    70 % du même lot validés au même instant : un seul passe, le lot ne passe jamais sous zéro
    (10 fois)."""
    a, qui = _decor()
    for _ in range(REPETITIONS):
        with fabrique()() as s:
            x = ref.stock_initial(a.m.a2.id, 100, magasin_id=a.m.courant.id, s=s)
            s.commit()
        lot = Lot(id=x)
        ids = _brouillons(qui, a.m.courant.id, lot, 70, 2)
        gestes = [lambda session, i=i: ordres.valider(session, qui, i, 1) for i in ids]
        assert sorted(_en_meme_temps(*gestes)) == ["ok", "stock_insuffisant"]
        assert _solde(x) == 30


def test_deux_validations_d_ordre_se_suivent_sous_verrou() -> None:
    """Hérité : test_audit2_atelier::test_deux_validations_d_ordre_se_suivent_sous_verrou — tant
    qu'un autre poste tient le verrou des ordres, la validation attend ; libéré, elle passe."""
    a, qui = _decor()
    [ident] = _brouillons(qui, a.m.courant.id, a.lot("E-T1"), 1, 1)
    issues: list[str] = []
    with moteur().connect() as autre:
        autre.execute(text("SELECT pg_advisory_lock(:c)"), {"c": int(Verrou.ORDRES)})
        fil = threading.Thread(
            target=lambda: issues.extend(_en_meme_temps(lambda s: ordres.valider(s, qui, ident, 1)))
        )
        fil.start()
        time.sleep(0.5)
        assert fil.is_alive() and not issues
        autre.execute(text("SELECT pg_advisory_unlock(:c)"), {"c": int(Verrou.ORDRES)})
        autre.commit()
        fil.join(10)
    assert issues == ["ok"]


def test_des_validations_simultanees_numerotent_sans_trou() -> None:
    """Huit ordres validés au même instant : huit numéros qui se suivent, aucun perdu."""
    a, qui = _decor()
    ids = _brouillons(qui, a.m.courant.id, a.lot("E-L1"), 1, 8)
    gestes = [lambda session, i=i: ordres.valider(session, qui, i, 1) for i in ids]
    assert _en_meme_temps(*gestes) == ["ok"] * 8
    with fabrique()() as s:
        numeros = sorted(s.scalars(select(Ordre.numero).where(Ordre.id.in_(ids))))
    rangs = [int(str(n).rsplit("-", 1)[1]) for n in numeros]
    assert rangs == list(range(rangs[0], rangs[0] + 8))


def test_deux_annulations_simultanees_ne_rendent_la_matiere_qu_une_fois() -> None:
    """Deux postes annulent le même ordre : un seul passe ; la matière revient une fois
    (10 fois)."""
    a, qui = _decor()
    trame = a.lot("E-T1")
    for _ in range(REPETITIONS):
        avant = _solde(trame.id)
        with fabrique()() as s:
            o = valide(s, qui, saisie(a.m.courant.id, [(trame, 10)]))
            ident, version = o.id, o.version
            s.commit()
        gestes = [lambda session, i=ident, v=version: ordres.annuler(session, qui, i, v)] * 2
        issues = sorted(_en_meme_temps(*gestes))
        assert issues[1] == "ok" and issues[0] in {"conflit_version", "deja_annule"}
        assert _solde(trame.id) == avant


def test_annuler_un_ordre_pendant_qu_un_retour_se_valide() -> None:
    """L'annulation d'un ordre et la validation d'un de ses retours au même instant : jamais
    d'interblocage ; l'ordre est annulé, le retour annulé avec lui ou supprimé, et le lot
    retrouve son stock d'avant l'ordre (10 fois)."""
    from gestion_mp_pro.services import operations as ops

    a, qui = _decor()
    trame = a.lot("E-T1")
    for _ in range(REPETITIONS):
        avant = _solde(trame.id)
        with fabrique()() as s:
            o = valide(s, qui, saisie(a.m.courant.id, [(trame, 10)]))
            r = retour(s, qui, o, [(trame, 3)], valider=False)
            ids = (o.id, o.version, r.id, r.version)
            s.commit()
        issues = _en_meme_temps(
            lambda session, x=ids: ordres.annuler(session, qui, x[0], x[1]),
            lambda session, x=ids: ops.valider(session, qui, x[2], x[3]),
        )
        assert issues[0] == "ok" and issues[1] in {"ok", "introuvable", "stock_insuffisant"}
        assert _solde(trame.id) == avant
        with fabrique()() as s:
            assert s.get_one(Ordre, ids[0]).statut == StatutOrdre.annule
            net = s.scalar(select(func.sum(Mouvement.quantite)).where(Mouvement.ordre_id == ids[0]))
            assert net == 0
