"""Chaque CHECK refuse sa valeur interdite, un cas par contrainte ; FK composites (lot S1).

Pour isoler une contrainte, l'essai retire **les autres** CHECK de la table dans un point de
sauvegarde (le DDL de PostgreSQL est transactionnel), vérifie que la ligne valide passe la
contrainte, puis que la ligne modifiée est refusée par elle et par elle seule (nom exact).
Tout est annulé à la fin : la base d'essai n'en garde rien.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from modele_cas import CAS, Mutation, cas_generique
from modele_monde import LIGNES, Ids, batir, inserer
from psycopg import errors
from sqlalchemy import CheckConstraint, Connection, ForeignKeyConstraint, text
from sqlalchemy.exc import IntegrityError

from gestion_mp_pro import modeles
from gestion_mp_pro.db import moteur


def _nom_du_check(table: str, contrainte: CheckConstraint) -> str:
    """Le nom en base d'un CHECK (convention `ck_<table>_<nom>`)."""
    nom = str(contrainte.name)
    return nom if nom.startswith("ck_") else f"ck_{table}_{nom}"


CHECKS: dict[str, str] = {
    _nom_du_check(t.name, c): t.name
    for t in modeles.metadata.tables.values()
    for c in t.constraints
    if isinstance(c, CheckConstraint)
}
"""Tous les CHECK du modèle → leur table."""


def _cas(nom: str) -> tuple[str, Mutation]:
    """Le cas d'un CHECK : écrit à la main, sinon générique."""
    return CAS.get(nom) or cas_generique(nom, CHECKS[nom]) or (CHECKS[nom], {})


@pytest.fixture(scope="module")
def monde() -> Iterator[tuple[Connection, Ids]]:
    """Le monde valide, plus de quoi croiser les FK composites ; tout est annulé à la fin."""
    with moteur().connect() as c:
        transaction = c.begin()
        ids = batir(c)
        ids["matiere2"] = inserer(c, "matiere", {"reference": "Autre fil", "role_id": ids["poil"]})
        ids["dossier2"] = inserer(c, "dossier", {"numero": "2/26", "annee": 2026, "rang": 2})
        ids["reception2"] = inserer(
            c,
            "reception",
            {"date": "2026-10-01", "fournisseur_id": ids["fournisseur"], "devise": "USD"},
        )
        c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        yield c, ids
        transaction.rollback()


def _valeurs(ids: Ids, table: str, mutation: Mutation) -> dict[str, Any]:
    """La ligne valide de la table, modifiée par la mutation."""
    changement = mutation(ids) if callable(mutation) else mutation
    return {**LIGNES[table](ids), **changement}


def _seul_check(c: Connection, table: str, garde: str) -> None:
    """Retire de la table tous les CHECK sauf `garde` (dans la transaction en cours)."""
    autres = c.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE conrelid = CAST(:t AS regclass)"
            " AND contype = 'c' AND conname <> :g"
        ),
        {"t": table, "g": garde},
    ).scalars()
    for nom in list(autres):
        c.execute(text(f'ALTER TABLE {table} DROP CONSTRAINT "{nom}"'))


def _erreur(c: Connection, faire: Callable[[], object]) -> BaseException | None:
    """L'erreur d'intégrité levée par `faire`, dans un point de sauvegarde annulé."""
    point = c.begin_nested()
    try:
        faire()
    except IntegrityError as exc:
        return exc.orig
    finally:
        point.rollback()
    return None


def test_tous_les_checks_de_la_base_sont_ceux_du_modele(monde: tuple[Connection, Ids]) -> None:
    c, _ = monde
    en_base = set(
        c.execute(
            text(
                "SELECT conname FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace"
                " WHERE n.nspname = 'public' AND c.contype = 'c'"
            )
        ).scalars()
    )
    assert en_base == set(CHECKS)


def test_chaque_check_a_son_cas() -> None:
    sans_cas = [n for n in CHECKS if n not in CAS and cas_generique(n, CHECKS[n]) is None]
    assert sans_cas == []
    assert set(CAS) <= set(CHECKS)


@pytest.mark.parametrize("nom", sorted(CHECKS))
def test_le_check_refuse_sa_valeur_interdite(monde: tuple[Connection, Ids], nom: str) -> None:
    c, ids = monde
    table, mutation = _cas(nom)
    point = c.begin_nested()
    try:
        c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        _seul_check(c, table, nom)
        valide = _erreur(c, lambda: inserer(c, table, _valeurs(ids, table, {})))
        assert not isinstance(valide, errors.CheckViolation), valide
        refus = _erreur(c, lambda: inserer(c, table, _valeurs(ids, table, mutation)))
        assert isinstance(refus, errors.CheckViolation), refus
        assert refus.diag.constraint_name == nom
    finally:
        point.rollback()


COMPOSITES = {
    "fk_mouvement_lot_id_lot": ("mouvement", lambda i: {"matiere_id": i["matiere2"]}),
    "fk_reception_ligne_lot_id_lot": ("reception_ligne", lambda i: {"matiere_id": i["matiere2"]}),
    "fk_ordre_ligne_lot_id_lot": ("ordre_ligne", lambda i: {"matiere_id": i["matiere2"]}),
    "fk_operation_ligne_lot_id_lot": ("operation_ligne", lambda i: {"matiere_id": i["matiere2"]}),
    "fk_inventaire_ligne_lot_id_lot": (
        "inventaire_ligne",
        lambda i: {"matiere_id": i["matiere2"], "magasin_id": i["quarantaine"]},
    ),
    "fk_dossier_ligne_lot_id_lot": ("dossier_ligne", lambda i: {"matiere_id": i["matiere2"]}),
    "fk_montage_metier_id_metier_etage": ("montage", {"etage": 2}),
    "fk_dossier_frais_ligne_id_dossier_ligne": (
        "dossier_frais",
        lambda i: {"dossier_id": i["dossier2"]},
    ),
    "fk_reclamation_reception_ligne_id_reception_ligne": (
        "reclamation",
        lambda i: {"reception_id": i["reception2"], "numero": "RCL-2026-0002"},
    ),
}
"""Chaque FK composite → la ligne valide qui la croise (matière ≠ celle du lot, étage absent,
marchandise d'un autre dossier, ligne d'une autre réception)."""


def test_toutes_les_fk_composites_ont_leur_cas() -> None:
    composites = {
        f"fk_{t.name}_{c.columns[0].name}_{c.referred_table.name}"
        for t in modeles.metadata.tables.values()
        for c in t.constraints
        if isinstance(c, ForeignKeyConstraint) and len(c.columns) > 1
    }
    assert composites == set(COMPOSITES)


@pytest.mark.parametrize("nom", sorted(COMPOSITES))
def test_la_fk_composite_refuse_un_croisement(monde: tuple[Connection, Ids], nom: str) -> None:
    c, ids = monde
    table, mutation = COMPOSITES[nom]
    refus = _erreur(c, lambda: inserer(c, table, _valeurs(ids, table, mutation)))
    assert isinstance(refus, errors.ForeignKeyViolation), refus
    assert refus.diag.constraint_name == nom
