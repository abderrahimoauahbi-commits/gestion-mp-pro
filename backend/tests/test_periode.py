"""Dates permises et période close (lot S2) : messages mot pour mot (REGLES § 0.5, D1–D4).

Les données (réception, dossier, brouillons) viennent du « monde » de S1, inséré dans une
transaction annulée à la fin de chaque essai.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from modele_monde import batir
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.db import moteur
from gestion_mp_pro.modeles import Dossier, Journal, Parametre, ParametreHistorique
from gestion_mp_pro.services import periode

D3 = (
    "La période jusqu'au 30/09/2026 est close : rien ne s'y écrit plus. Dater après la "
    "clôture, ou demander à la direction de la rouvrir."
)


@dataclass(frozen=True)
class Qui:
    """Un auteur de geste pour le journal."""

    id: int
    nom: str = "Direction essai"
    role: str = "direction"
    requete: str = "0123456789abcdef"
    adresse: str = "127.0.0.1"


@pytest.fixture
def monde() -> Iterator[tuple[Session, dict[str, Any]]]:
    """Une session sur un monde complet (une ligne par table), annulé à la fin."""
    with moteur().connect() as c:
        transaction = c.begin()
        ids = batir(c)
        with Session(bind=c, join_transaction_mode="create_savepoint") as s:
            yield s, ids
        transaction.rollback()


def _clore_en_sql(s: Session, jour: str) -> None:
    s.execute(text("UPDATE parametre SET valeur = :v WHERE cle = 'date_cloture'"), {"v": jour})


def _refus(appel: Any) -> Refus:
    with pytest.raises(Refus) as refus:
        appel()
    return refus.value


def test_date_permise_d1_d2_d3(monde: tuple[Session, dict[str, Any]]) -> None:
    """Hérité : test_parcours::test_une_periode_close_ne_bouge_plus (un code, une étape)."""
    s, _ = monde
    r = _refus(lambda: periode.date_permise(s, date(1999, 12, 31)))
    assert (r.http, r.code) == (422, "date_trop_ancienne")
    assert r.detail == "Date trop ancienne (31/12/1999) : vérifier l'année."
    r = _refus(lambda: periode.date_permise(s, date(2026, 10, 9)))
    assert (r.http, r.code) == (422, "date_future")
    assert r.detail == (
        "Date dans le futur (09/10/2026) : un mouvement se saisit le jour où il a lieu."
    )
    periode.date_permise(s, date(2026, 10, 8))
    periode.date_permise(s, date(2000, 1, 1))
    _clore_en_sql(s, "2026-09-30")
    assert periode.fin_de_periode_close(s) == date(2026, 9, 30)
    r = _refus(lambda: periode.date_permise(s, date(2026, 9, 30)))
    assert (r.http, r.code, r.detail) == (409, "periode_close", D3)
    periode.date_permise(s, date(2026, 10, 1))


def test_cout_d_une_marchandise_entree_dans_un_mois_clos(
    monde: tuple[Session, dict[str, Any]],
) -> None:
    """Hérité : test_valeur_et_dates::test_un_mois_clos_ne_se_revalorise_pas (message D4)."""
    s, ids = monde
    dossier = s.get(Dossier, ids["dossier"])
    assert dossier is not None
    periode.cout_hors_periode_close(s, dossier, "frais")  # rien de clos
    _clore_en_sql(s, "2026-09-30")
    periode.cout_hors_periode_close(s, dossier, "frais")  # lot entré le 01/10 : hors période
    _clore_en_sql(s, "2026-10-05")
    r = _refus(lambda: periode.cout_hors_periode_close(s, dossier, "ajout de frais"))
    assert (r.http, r.code) == (409, "cout_periode_close")
    assert r.detail == (
        "La marchandise du dossier 1/26 est entrée le 01/10/2026, dans la période close "
        "jusqu'au 05/10/2026 : son coût a été rendu avec le mois et ne change plus (ajout "
        "de frais refusé). Pour corriger ce mois, la direction rouvre la période (Réglages "
        "› Période close jusqu'au — c'est tracé), on saisit, puis elle la referme."
    )
    r = _refus(lambda: periode.cout_hors_periode_close(s, None, "rattachement", [date(2026, 9, 2)]))
    assert r.detail.startswith("La marchandise rattachée est entrée le 02/09/2026, dans la")


def test_clore_refuse_sans_motif_ou_dans_le_futur(monde: tuple[Session, dict[str, Any]]) -> None:
    """Hérité : KR33 « On ne clôt qu'une période passée. » ; motif obligatoire (route 26)."""
    s, ids = monde
    qui = Qui(ids["utilisateur"])
    r = _refus(lambda: periode.clore(s, qui, date(2026, 9, 30), "ok"))
    assert (r.http, r.code) == (422, "motif_requis")
    for jour in (date(2026, 10, 8), date(2026, 10, 9)):
        r = _refus(lambda jour=jour: periode.clore(s, qui, jour, "Fin de mois"))
        assert (r.http, r.detail) == (422, "On ne clôt qu'une période passée.")


def test_clore_refuse_si_des_brouillons_restent(monde: tuple[Session, dict[str, Any]]) -> None:
    """Hérité : E-14 — un brouillon daté de la période ne pourrait plus se valider."""
    s, ids = monde
    r = _refus(lambda: periode.clore(s, Qui(ids["utilisateur"]), date(2026, 10, 5), "Mois"))
    assert r.http == 409
    assert r.detail == (
        "Des brouillons sont datés de la période à clore : 1 ordre de fabrication(s), "
        "1 opération(s), 1 inventaire(s). Les valider, les supprimer ou les redater d'abord : "
        "après la clôture, ils ne pourraient plus se valider."
    )


def test_clore_puis_rouvrir_est_trace(monde: tuple[Session, dict[str, Any]]) -> None:
    """Hérité : S171 « chaque changement est historisé et journalisé » ; avant/après."""
    s, ids = monde
    qui = Qui(ids["utilisateur"])
    vu: list[date] = []
    periode.APRES_CLOTURE.append(lambda _s, _q, jour: vu.append(jour))
    try:
        etat = periode.clore(s, qui, date(2026, 9, 30), "Clôture de septembre")
    finally:
        periode.APRES_CLOTURE.pop()
    assert vu == [date(2026, 9, 30)]
    assert (etat.date_cloture, etat.par) == (date(2026, 9, 30), "Essai")
    assert periode.clore(s, qui, None, "Réouverture pour corriger").date_cloture is None
    historique = s.scalars(
        select(ParametreHistorique)
        .where(ParametreHistorique.cle == "date_cloture")
        .order_by(ParametreHistorique.id)
    ).all()
    assert [(h.avant, h.apres, h.motif) for h in historique[-2:]] == [
        ("", "2026-09-30", "Clôture de septembre"),
        ("2026-09-30", "", "Réouverture pour corriger"),
    ]
    lignes = s.scalars(select(Journal).where(Journal.objet == "periode").order_by(Journal.id))
    derniere = list(lignes)[-1]
    assert derniere.avant == {"date_cloture": "2026-09-30"}
    assert derniere.apres == {"date_cloture": None}
    assert derniere.detail.startswith("Période close jusqu'au : 30/09/2026 → —")
    p = s.get(Parametre, "date_cloture")
    assert p is not None and p.modifie_par_id == ids["utilisateur"]
