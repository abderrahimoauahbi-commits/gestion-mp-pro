"""Opérations et inventaires sous plusieurs postes à la fois (lot D5 ; PLAN-DE-RECETTE A10) :
chaque essai valide ses transactions (des fils, des sessions à part), sur des fiches à son nom,
et répète la course.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from decimal import Decimal

from fabriques.operations import (
    JOUR_DES_INVENTAIRES,
    acteur,
    ligne,
    monde,
    motif,
    ordre_valide,
    saisie,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import InventaireLigne, Lot, Mouvement
from gestion_mp_pro.modeles.enums import DocumentMouvement, Role, TypeMouvement
from gestion_mp_pro.services import inventaires as inv
from gestion_mp_pro.services import operations as ops
from gestion_mp_pro.services import stock
from gestion_mp_pro.services.inventaires import Criteres, Ouverture

REPETITIONS = 10


def _en_meme_temps(*gestes: Callable[[Session], object]) -> list[str]:
    """Les gestes lancés au même instant, chacun dans sa session ; « ok » ou le code du refus,
    dans l'ordre des gestes."""
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
        f.join(timeout=30)
    return issues


def _course_des_retours() -> None:
    with fabrique()() as s:
        m = monde(s)
        atelier = acteur(s, Role.alimentation)
        ordre = ordre_valide(s, [(m.lots["E-L1"], 100)])
        e = saisie(
            "retour_machine",
            ligne(m.a1.id, m.courant.id, 70, lot_id=m.lots["E-L1"].id),
            ordre_id=ordre.id,
            motif_id=motif(s, "retour_machine", "Reliquat de fin d'ordre"),
        )
        ids = [ops.creer(s, atelier, e).id for _ in range(2)]
        ordre_id = ordre.id
        s.commit()
    gestes = [lambda session, i=i: ops.valider(session, atelier, i, 1) for i in ids]
    assert sorted(_en_meme_temps(*gestes)) == ["ok", "stock_insuffisant"]
    with fabrique()() as s:
        net = s.scalar(select(func.sum(Mouvement.quantite)).where(Mouvement.ordre_id == ordre_id))
        assert net == Decimal(-30)


def test_deux_retours_simultanes_du_meme_ordre() -> None:
    """Hérité : test_parcours::test_deux_retours_simultanes_du_meme_ordre — deux retours de 70
    pour 100 partis, validés au même instant : un passe, l'autre est refusé (l'ordre est
    verrouillé, le second relit ce qui est déjà revenu) ; sorti net 30, jamais moins."""
    for _ in range(REPETITIONS):
        _course_des_retours()


def _course_des_deux_clics() -> None:
    with fabrique()() as s:
        m = monde(s)
        achats = acteur(s)
        e = saisie(
            "ajustement",
            ligne(m.a2.id, m.courant.id, 3, lot_id=m.lots["E-T1"].id),
            motif_id=motif(s, "ajustement", "Matière retrouvée"),
            commentaire="palette derrière",
        )
        ident = ops.creer(s, achats, e).id
        s.commit()

    def geste(session: Session) -> object:
        return ops.valider(session, achats, ident, 1)

    issues = sorted(_en_meme_temps(geste, geste))
    assert issues[1] == "ok" and issues[0] in {"deja_valide", "conflit_version"}
    with fabrique()() as s:
        n = s.scalar(select(func.count()).where(Mouvement.operation_id == ident))
        assert n == 1


def test_deux_clics_ne_valident_pas_deux_fois() -> None:
    """La même opération validée par deux postes au même instant : un seul numéro, un seul
    mouvement par ligne ; l'autre reçoit « déjà validée » (ou la version périmée)."""
    for _ in range(REPETITIONS):
        _course_des_deux_clics()


def _course_inventaire_contre_sortie() -> None:
    with fabrique()() as s:
        m = monde(s, le=JOUR_DES_INVENTAIRES)
        achats = acteur(s)
        lot_id, magasin_id, matiere_id = m.lots["E-T1"].id, m.courant.id, m.a2.id
        s.commit()

    def ouvrir(session: Session) -> object:
        criteres = Criteres(matieres=(matiere_id,))
        return inv.ouvrir(
            session, achats, Ouverture(JOUR_DES_INVENTAIRES, magasin_id, criteres=criteres)
        )

    def sortir(session: Session) -> object:
        lot = session.get_one(Lot, lot_id)
        return stock.ecrire(
            session,
            type=TypeMouvement.AJUSTEMENT,
            lot=lot,
            magasin_id=magasin_id,
            quantite=-50,
            jour=lot.entre_le,
            piece=stock.Piece(DocumentMouvement.reprise),
            auteur_id=None,
        )

    ouvert, sorti = _en_meme_temps(ouvrir, sortir)
    assert ouvert == "ok" and sorti in {"ok", "inventaire_en_cours"}
    with fabrique()() as s:
        ligne_figee = s.scalars(
            select(InventaireLigne).where(InventaireLigne.lot_id == lot_id)
        ).one()
        assert ligne_figee.theorique == (350 if sorti == "ok" else 400)
        inv.abandonner(s, achats, ligne_figee.inventaire_id, 1, "essai de course")
        s.commit()


def test_ouverture_d_inventaire_contre_sortie() -> None:
    """Un inventaire qui s'ouvre pendant qu'un lot de son périmètre sort : ou la sortie passe
    d'abord et le théorique la compte, ou elle voit l'inventaire et s'arrête (S14) ; jamais un
    théorique faux."""
    for _ in range(REPETITIONS):
        _course_inventaire_contre_sortie()
