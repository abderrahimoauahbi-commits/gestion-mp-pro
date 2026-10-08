"""Numérotation des pièces (lot S2) : format, année de la pièce, aucun trou ni doublon.

Héritage REGLES § 0.4, B.6.5 (X40) ; M65 « numéros à la validation » : un refus annule
l'incrément ; 20 validations parallèles donnent 1…N sans trou.
Les essais prennent des années à eux (2090…) pour ne gêner aucun autre lot.
"""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import Compteur
from gestion_mp_pro.modeles.enums import SerieNumero
from gestion_mp_pro.services import numerotation


@pytest.fixture
def s() -> Iterator[Session]:
    """Une session dont la transaction est annulée à la fin."""
    with fabrique()() as session:
        yield session
        session.rollback()


def _vider(annee: int) -> None:
    with fabrique()() as session, session.begin():
        session.execute(delete(Compteur).where(Compteur.annee == annee))


def test_format_des_series() -> None:
    assert numerotation.formater(SerieNumero.BC, 2026, 1) == "BC-2026-0001"
    assert numerotation.formater("REC", 2026, 318) == "REC-2026-0318"
    assert numerotation.formater(SerieNumero.LOT, 2026, 12345) == "LOT-2026-12345"
    assert numerotation.formater(SerieNumero.DOS, 2026, 1) == "01/26"
    assert numerotation.formater(SerieNumero.DOS, 2026, 112) == "112/26"
    assert numerotation.libelle_brouillon(12) == "brouillon n° 12"


def test_annee_de_la_piece_et_suite(s: Session) -> None:
    """Hérité : l'année est celle de la date de la pièce, pas d'aujourd'hui (B.6.5)."""
    assert numerotation.numero(s, SerieNumero.BC, date(2090, 12, 31)) == "BC-2090-0001"
    assert numerotation.numero(s, SerieNumero.BC, date(2090, 1, 2)) == "BC-2090-0002"
    assert numerotation.numero(s, SerieNumero.BC, date(2091, 1, 1)) == "BC-2091-0001"
    assert numerotation.numero(s, SerieNumero.REC, 2090) == "REC-2090-0001"
    assert numerotation.dernier(s, SerieNumero.BC, 2090) == 2
    assert numerotation.dernier(s, SerieNumero.OF, 2090) == 0


def test_dossier_saute_les_numeros_pris(s: Session) -> None:
    pris = {"01/92", "02/92"}
    assert numerotation.numero(s, "DOS", date(2092, 3, 1), deja_pris=pris.__contains__) == "03/92"
    assert numerotation.rattraper(s, "LOT", 2092, 40) == 40
    assert numerotation.rattraper(s, "LOT", 2092, 10) == 40
    assert numerotation.numero(s, "LOT", 2092) == "LOT-2092-0041"


def test_un_refus_ne_laisse_pas_de_trou() -> None:
    """Hérité : X40 — le numéro est pris dans la transaction du geste ; refusé, il revient."""
    _vider(2093)
    with fabrique()() as session:
        assert numerotation.numero(session, "OUV", 2093) == "OUV-2093-0001"
        session.rollback()
    with fabrique()() as session, session.begin():
        assert numerotation.numero(session, "OUV", 2093) == "OUV-2093-0001"
    with fabrique()() as session, session.begin():
        assert numerotation.numero(session, "OUV", 2093) == "OUV-2093-0002"


def test_vingt_validations_paralleles_sans_trou_ni_doublon() -> None:
    """Hérité : SEC:179-207 « deux validations simultanées obtiennent N et N+1 » (×20, M65)."""
    _vider(2094)
    depart = threading.Barrier(20)
    hasard = random.Random(8)
    refus = {i for i in range(20) if hasard.random() < 0.3}

    def valider(i: int) -> str | None:
        with fabrique()() as session:
            depart.wait()
            texte = numerotation.numero(session, SerieNumero.REC, date(2094, 5, 1))
            time.sleep(0.005)
            if i in refus:
                session.rollback()
                return None
            session.commit()
            return texte

    with ThreadPoolExecutor(20) as pool:
        obtenus = [x for x in pool.map(valider, range(20)) if x is not None]
    assert len(obtenus) == 20 - len(refus)
    assert sorted(obtenus) == [f"REC-2094-{n:04d}" for n in range(1, len(obtenus) + 1)]
    with fabrique()() as session:
        assert numerotation.dernier(session, SerieNumero.REC, 2094) == len(obtenus)
