"""Le modèle de données (lot S1, MODELE-DONNEES) : tables, défauts, semences, déclencheurs,
index uniques partiels, verrou optimiste, texte de recherche, arrondi.

Les CHECK un par un et les FK composites : `test_modele_contraintes.py`.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal
from typing import Any

import base_connue
import pytest
from modele_monde import Ids, batir, inserer
from psycopg import errors
from sqlalchemy import Connection, Enum, String, text
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

from gestion_mp_pro import modeles
from gestion_mp_pro.db import moteur
from gestion_mp_pro.modeles.base import MAINTENANT
from gestion_mp_pro.modeles.enums import ENUMERATIONS
from gestion_mp_pro.services import horloge

TABLES_DU_DOCUMENT = """utilisateur, session, tentative, appareil, journal, parametre,
parametre_historique, compteur, notification, notification_lecture, courriel, tache_execution,
sauvegarde, devise, devise_cours, composition, type_fil, titrage, unite_titrage, couleur,
role_nomenclature, fournisseur, code_douanier, matiere, qualite, qualite_poids, qualite_saison,
recette, recette_version, recette_version_ligne, recette_version_poids, plan_version,
plan_version_saison,
magasin, metier, metier_etage, montage, montage_evenement, poste_frais, motif, lot, solde,
mouvement, commande, commande_ligne, commande_version, commande_version_ligne, commande_decision,
facture, reception, reception_ligne, ordre, ordre_qualite, ordre_ligne, ordre_prevu, operation,
operation_ligne, inventaire, inventaire_critere, inventaire_matiere, inventaire_ligne, dossier,
dossier_facture, dossier_ligne, dossier_frais, dossier_frais_part, reclamation, signalement,
piece_jointe, indicateur_jour, reprise_correspondance, reprise_execution, alembic_version"""
"""MODELE-DONNEES § 11 : les 73 tables (`dossier_facture` : révision 0007 ; `unite_titrage` :
révision 0008)."""


@pytest.fixture
def lien() -> Iterator[Connection]:
    """Une connexion sur une base neuve (`base_connue`), dans une transaction annulée à la fin
    de l'essai."""
    with moteur().connect() as c:
        transaction = c.begin()
        base_connue.remettre(c)
        yield c
        transaction.rollback()


@pytest.fixture
def monde(lien: Connection) -> tuple[Connection, Ids]:
    """Une ligne valide par table, dans la transaction de l'essai."""
    return lien, batir(lien)


def _un(c: Connection, sql: str, **parametres: Any) -> Any:
    return c.execute(text(sql), parametres).scalar()


def test_les_73_tables(lien: Connection) -> None:
    attendues = {t.strip() for t in TABLES_DU_DOCUMENT.split(",")}
    assert len(attendues) == 73
    assert set(modeles.metadata.tables) == attendues - {"alembic_version"}
    en_base = set(
        lien.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars()
    )
    assert en_base == attendues


def test_enumerations_fermees_et_assez_longues() -> None:
    assert len(ENUMERATIONS) == 36
    for classe in ENUMERATIONS:
        assert [m.value for m in classe] == [m.name for m in classe] or classe.__name__ in {
            "TypeMouvement",
            "SerieNumero",
        }
    for table in modeles.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, Enum):
                assert col.type.length >= max(len(v) for v in col.type.enums), col
                assert not col.type.native_enum


def test_les_textes_sont_bornes() -> None:
    for table in modeles.metadata.tables.values():
        for col in table.columns:
            if type(col.type) is String:
                assert col.type.length, f"{table.name}.{col.name} sans longueur"


def _defaut_serveur(c: Connection, table: str, colonne: str) -> str | None:
    return _un(
        c,
        "SELECT column_default FROM information_schema.columns WHERE table_schema = 'public'"
        " AND table_name = :t AND column_name = :col",
        t=table,
        col=colonne,
    )


def test_defauts_serveur_egaux_aux_defauts_orm(lien: Connection) -> None:
    verifies = 0
    for table in modeles.metadata.tables.values():
        for col in table.columns:
            serveur = _defaut_serveur(lien, table.name, col.name)
            if col.identity is not None or col.computed is not None:
                continue
            if col.default is None:
                assert serveur is None, f"{table.name}.{col.name} : défaut serveur sans défaut ORM"
                continue
            assert serveur is not None, f"{table.name}.{col.name} : défaut ORM sans défaut serveur"
            orm = col.default.arg
            if callable(orm):
                assert orm.__name__ in {"maintenant", "<lambda>"}, col
                assert serveur == "now()", col
            else:
                assert _un(lien, f"SELECT {serveur}") == orm, f"{table.name}.{col.name}"  # noqa: S608
            verifies += 1
    assert verifies > 250


def test_un_defaut_instant_vaut_l_horloge_de_l_usine() -> None:
    from gestion_mp_pro.modeles.base import defauts

    orm, serveur = defauts(MAINTENANT)
    assert callable(orm)
    assert orm() == horloge.maintenant()
    assert str(serveur) == "now()"


ROLES = [
    ("Poil", False, 0), ("Chaîne", False, 1), ("Trame", False, 2), ("Colle", False, 3),
    ("Cuir", True, 4), ("Franges", True, 5), ("Ruban", True, 6), ("Plastique", False, 7),
]  # fmt: skip
POSTES = [
    ("DD", "droits", False, False, True), ("TPI", "tpi", False, False, True),
    ("TVA", "tva", True, False, True), ("PORT", "autre", False, False, False),
    ("FRET", "fret", False, True, True), ("ASSUR", "assurance", False, True, True),
    ("TRANSIT", "autre", False, False, False), ("TIMBRE", "autre", False, False, False),
    ("INT_OC", "autre", False, False, False), ("TMSA", "autre", False, False, False),
    ("AUTRE", "autre", False, False, False),
]  # fmt: skip
"""(code, nature, récupérable, valeur en douane, système), dans l'ordre (DONNEES § 5.2)."""


def test_semences_roles_postes_devises_magasins(lien: Connection) -> None:
    roles = lien.execute(
        text("SELECT code, lineaire, ordre FROM role_nomenclature WHERE de_base ORDER BY ordre")
    ).all()
    assert [tuple(r) for r in roles] == ROLES
    postes = lien.execute(
        text(
            "SELECT code, nature, recuperable, entre_valeur_douane, systeme FROM poste_frais"
            " ORDER BY ordre"
        )
    ).all()
    assert [tuple(p) for p in postes] == POSTES
    assert set(lien.execute(text("SELECT cle FROM poste_frais")).scalars()) == {"valeur"}
    devises = dict(lien.execute(text("SELECT code, cours FROM devise")).all())
    assert devises == {"MAD": Decimal(1), "USD": Decimal(10), "EUR": Decimal("10.8")}
    magasins = lien.execute(text("SELECT code, nom, type, actif FROM magasin ORDER BY id")).all()
    assert [tuple(m) for m in magasins] == [
        ("Magasin principal", "Magasin principal", "stock_courant", True),
        ("Quarantaine", "Quarantaine", "quarantaine", True),
    ]


def test_semences_motifs(lien: Connection) -> None:
    motifs = lien.execute(
        text("SELECT type_operation, libelle, code_r, impose_role FROM motif ORDER BY id")
    ).all()
    assert len(motifs) == 16
    codes = {m.libelle: m.code_r for m in motifs if m.code_r}
    assert codes == {
        "Reliquat de fin d'ordre": "R1",
        "Changement de série / arrêt machine": "R2",
        "Erreur de prélèvement": "R4",
        "Non-conformité qualité": "R3",
        "Excédent de réception": "R5",
        "Bobines endommagées": "R6",
        "Refus après quarantaine": "R3",
    }
    assert {m.libelle for m in motifs if m.impose_role} == {"Libération de quarantaine"}
    par_type = {t: sum(1 for m in motifs if m.type_operation == t) for t, *_ in motifs}
    assert par_type == {
        "retour_machine": 3,
        "retour_fournisseur": 4,
        "ajustement": 4,
        "transfert": 4,
        "inventaire": 1,
    }


def test_semences_reglages(lien: Connection) -> None:
    valeurs = dict(lien.execute(text("SELECT cle, valeur FROM parametre")).all())
    assert len(valeurs) == 57
    assert set(valeurs) == set(modeles.CLES_REGLAGES)
    assert valeurs["seuil_critique"] == "60"
    assert valeurs["marge_securite"] == "0.2"
    assert valeurs["taux_tpi_import"] == "0.0025"
    assert valeurs["croissance_annuelle"] == "0"
    assert valeurs["seuil_surcout_import"] == "1"
    assert valeurs["delai_frais_import_jours"] == "30"
    assert valeurs["toler_tva_import"] == "0.05"
    assert valeurs["seuil_bc_urgent"] == "300000"
    assert valeurs["secteur"] == "Fabrication de tapis mécaniques"
    assert valeurs["date_cloture"] == ""
    assert _un(lien, "SELECT count(*) FROM parametre WHERE modifie_par_id IS NOT NULL") == 0


def test_mouvement_immuable(monde: tuple[Connection, Ids]) -> None:
    c, ids = monde
    for sql in ("UPDATE mouvement SET commentaire = 'x'", "DELETE FROM mouvement"):
        point = c.begin_nested()
        with pytest.raises((IntegrityError, ProgrammingError)) as refus:
            c.execute(text(sql))
        point.rollback()
        assert isinstance(refus.value.orig, errors.RestrictViolation)
        assert refus.value.orig.diag.constraint_name == "tr_mouvement_immuable"
        assert "contre-passation" in str(refus.value.orig)
    point = c.begin_nested()
    c.execute(text("ALTER TABLE mouvement DISABLE TRIGGER tr_mouvement_immuable"))
    assert c.execute(text("DELETE FROM mouvement")).rowcount == 1
    point.rollback()
    assert _un(c, "SELECT count(*) FROM mouvement WHERE id = :i", i=ids["mouvement"]) == 1


def test_type_d_operation_fige(monde: tuple[Connection, Ids]) -> None:
    c, ids = monde
    c.execute(text("UPDATE operation SET commentaire = 'écart'"))
    with pytest.raises((IntegrityError, ProgrammingError)) as refus:
        c.execute(
            text("UPDATE operation SET type = 'transfert' WHERE id = :i"), {"i": ids["operation"]}
        )
    assert refus.value.orig.diag.constraint_name == "tr_operation_type_fige"  # type: ignore[union-attr]


def test_matiere_lineaire_sans_densite_refusee_a_la_validation(
    monde: tuple[Connection, Ids],
) -> None:
    c, ids = monde
    point = c.begin_nested()
    inserer(c, "matiere", {"reference": "Cuir sans densité", "role_id": ids["cuir"]})
    with pytest.raises(IntegrityError) as refus:
        c.execute(text("SET CONSTRAINTS tr_matiere_lineaire_densite IMMEDIATE"))
    point.rollback()
    assert refus.value.orig.diag.constraint_name == "tr_matiere_lineaire_densite"  # type: ignore[union-attr]
    point = c.begin_nested()
    nouvelle = inserer(c, "matiere", {"reference": "Cuir mesuré", "role_id": ids["cuir"]})
    c.execute(text("UPDATE matiere SET densite = 0.074 WHERE id = :i"), {"i": nouvelle})
    c.execute(text("SET CONSTRAINTS tr_matiere_lineaire_densite IMMEDIATE"))
    point.rollback()


def _refus(c: Connection, table: str, valeurs: dict[str, Any]) -> BaseException | None:
    point = c.begin_nested()
    try:
        inserer(c, table, valeurs)
    except (IntegrityError, OperationalError) as exc:
        return exc.orig
    finally:
        point.rollback()
    return None


def test_un_inventaire_ouvert_par_magasin(monde: tuple[Connection, Ids]) -> None:
    c, ids = monde
    meme = {"numero": "INV-2026-0002", "date": "2026-10-02", "magasin_id": ids["courant"]}
    refus = _refus(c, "inventaire", meme)
    assert isinstance(refus, errors.UniqueViolation)
    assert refus.diag.constraint_name == "uq_inventaire_ouvert_magasin"
    autre = {**meme, "magasin_id": ids["quarantaine"]}
    assert _refus(c, "inventaire", autre) is None
    inserer(c, "inventaire", {"numero": "INV-2026-0003", "date": "2026-10-02"})
    global_bis = _refus(c, "inventaire", {"numero": "INV-2026-0004", "date": "2026-10-02"})
    assert isinstance(global_bis, errors.UniqueViolation)
    c.execute(text("UPDATE inventaire SET statut = 'abandonne', abandonne_le = now()"))
    assert _refus(c, "inventaire", meme) is None


def test_une_facture_dans_un_seul_dossier_sauf_liberee(monde: tuple[Connection, Ids]) -> None:
    """Lot PLUSIEURS-FACTURES (révision 0007) : un dossier porte plusieurs factures, une facture
    n'est que dans un seul dossier tant qu'elle n'est pas libérée (dossier annulé)."""
    c, ids = monde
    autre = inserer(c, "dossier", {"numero": "2/26", "annee": 2026, "rang": 2})
    second = {"dossier_id": autre, "facture_id": ids["facture"]}
    refus = _refus(c, "dossier_facture", second)
    assert isinstance(refus, errors.UniqueViolation)
    assert refus.diag.constraint_name == "uq_dossier_facture"
    c.execute(text("UPDATE dossier_facture SET liberee_le = now()"))
    assert _refus(c, "dossier_facture", second) is None


def test_une_qualite_une_fois_par_ordre(monde: tuple[Connection, Ids]) -> None:
    c, ids = monde
    refus = _refus(
        c, "ordre_qualite", {"ordre_id": ids["ordre"], "qualite_id": ids["qualite"], "m2": 1}
    )
    assert isinstance(refus, errors.UniqueViolation)
    assert refus.diag.constraint_name == "uq_ordre_qualite_ordre_id_qualite_id"


def test_lot_trouve_a_creer_unique_dans_l_inventaire(monde: tuple[Connection, Ids]) -> None:
    c, ids = monde
    trouve = {
        "inventaire_id": ids["inventaire"],
        "matiere_id": ids["matiere"],
        "lot_numero": "L-TROUVE",
        "magasin_id": ids["courant"],
        "lot_trouve": True,
    }
    inserer(c, "inventaire_ligne", trouve)
    refus = _refus(c, "inventaire_ligne", trouve)
    assert isinstance(refus, errors.UniqueViolation)
    assert refus.diag.constraint_name == "uq_inventaire_ligne_lot_a_creer"
    interne = {**trouve, "lot_numero": "", "lot_interne": True}
    inserer(c, "inventaire_ligne", interne)
    assert _refus(c, "inventaire_ligne", interne) is None


def test_la_colonne_parti_suit_le_numero(monde: tuple[Connection, Ids]) -> None:
    c, ids = monde
    assert _un(c, "SELECT parti FROM commande WHERE id = :i", i=ids["commande"]) is False
    c.execute(
        text("UPDATE commande SET numero = 'BC-2026-0001', statut = 'a_approuver' WHERE id = :i"),
        {"i": ids["commande"]},
    )
    assert _un(c, "SELECT parti FROM commande WHERE id = :i", i=ids["commande"]) is True


def test_identifiants_repris_puis_suite(lien: Connection) -> None:
    gardee = inserer(lien, "couleur", {"id": 500, "code": "Reprise"})
    assert gardee == 500
    lien.execute(text("SELECT setval(pg_get_serial_sequence('couleur', 'id'), 500)"))
    assert inserer(lien, "couleur", {"code": "Suivante"}) == 501


def test_instants_en_fuseau(lien: Connection) -> None:
    quand = _un(lien, "SELECT now()")
    assert isinstance(quand, datetime)
    assert quand.tzinfo is not None
