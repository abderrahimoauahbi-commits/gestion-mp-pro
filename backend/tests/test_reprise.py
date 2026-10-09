"""Reprise rejouable depuis Gestion MP (lot R1 ; MODELE-DONNEES § 10, ARCHITECTURE § 14.2).

Une petite usine au schéma de Gestion MP corrigé (`fabriques/reprise.py`) est reprise dans une
base PRO neuve : contrôles tenus, traductions de § 10.3, journal rangé en tables, rejeu sans
changement (rien n'est créé), rejeu après des gestes (activité remplacée, référentiels mis à
jour), refus d'écraser une activité saisie dans PRO, lecture seule de la source.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fabriques.reprise import (
    CODE_DIRECTION,
    FICHIERS,
    PETITE_USINE,
    cible_migree,
    executer_sql,
    source_gestion_mp,
    supprimer_base,
)
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from gestion_mp_pro.modeles.enums import ModeReprise
from gestion_mp_pro.reprise import source as src
from gestion_mp_pro.reprise.activite import ActiviteRefusee
from gestion_mp_pro.reprise.contexte import Options
from gestion_mp_pro.reprise.etapes import ReferentielsAbsents
from gestion_mp_pro.reprise.execution import RepriseRefusee, Resultat, executer
from gestion_mp_pro.services import comptes

ESSAI = make_url(os.environ["GESTIONMPPRO_BASE"]).database or "gestion_mp_pro_essai"
SOURCE = f"postgresql+psycopg:///{ESSAI.removesuffix('_essai')}_rsource_essai"
CIBLE = f"postgresql+psycopg:///{ESSAI.removesuffix('_essai')}_rcible_essai"


@pytest.fixture(scope="module")
def dossiers(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Dossier des pièces de la source (fichiers de la petite usine) et de la cible."""
    racine = tmp_path_factory.mktemp("pieces")
    for chemin, contenu in FICHIERS.items():
        (racine / "source" / chemin).parent.mkdir(parents=True, exist_ok=True)
        (racine / "source" / chemin).write_bytes(contenu)
    return racine / "source", racine / "cible"


@pytest.fixture
def bases() -> Iterator[None]:
    """Une source neuve (petite usine) et une cible PRO neuve, supprimées après l'essai."""
    source_gestion_mp(SOURCE, PETITE_USINE)
    cible_migree(CIBLE)
    yield
    supprimer_base(SOURCE)
    supprimer_base(CIBLE)


def reprendre(dossiers: tuple[Path, Path], **options: Any) -> Resultat:
    """Lance la reprise de la petite usine (sans sauvegarde : pg_dump est essayé à part)."""
    o = Options(
        source=SOURCE,
        cible=CIBLE,
        mode=options.pop("mode", ModeReprise.tout),
        sauvegarder=False,
        pieces_source=str(dossiers[0]),
        pieces_cible=str(dossiers[1]),
        **options,
    )
    return executer(o)


def lire(sql: str, url: str = CIBLE) -> list[Any]:
    """Les lignes d'une requête sur la cible."""
    moteur = create_engine(url, poolclass=NullPool)
    with moteur.connect() as c:
        lignes = list(c.execute(text(sql)).all())
    moteur.dispose()
    return lignes


def un(sql: str, url: str = CIBLE) -> Any:
    """La première valeur d'une requête."""
    return lire(sql, url)[0][0]


def comptes_cible() -> dict[str, int]:
    """Nombre de lignes de chaque table de la cible (hors traces de la reprise elle-même)."""
    tables = [t for (t,) in lire("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")]
    gardees = {"reprise_execution", "journal", "reprise_correspondance", "alembic_version"}
    return {t: un(f"SELECT count(*) FROM {t}") for t in tables if t not in gardees}  # noqa: S608


def test_premiere_reprise_tous_les_controles_tenus(
    bases: None, dossiers: tuple[Path, Path]
) -> None:
    r = reprendre(dossiers)
    assert r.reussie, r.rapport
    assert "NON TENU" not in r.rapport
    assert "lecture seule vérifiée : oui" in r.rapport
    assert "(identique)" in r.rapport
    assert un("SELECT count(*) FROM mouvement") == 11
    assert un("SELECT statut FROM reprise_execution ORDER BY id DESC LIMIT 1") == "reussie"


def test_source_jamais_ecrite_et_lecture_seule_verifiee(
    bases: None, dossiers: tuple[Path, Path]
) -> None:
    avant = src.empreinte_actuelle(SOURCE)
    photo = src.photographier(SOURCE)
    assert photo.lecture_seule_verifiee and photo.empreinte == avant
    reprendre(dossiers)
    assert src.empreinte_actuelle(SOURCE) == avant
    for chemin, contenu in FICHIERS.items():
        assert (dossiers[0] / chemin).read_bytes() == contenu


def test_ecriture_refusee_par_la_source(bases: None) -> None:
    c = src._connexion(SOURCE)
    c.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
    src._verifier_lecture_seule(c)
    with pytest.raises(Exception, match="read-only|lecture seule"):
        c.execute(text("DELETE FROM journal"))
    c.close()


def test_rejouee_sans_changement_rien_n_est_cree(bases: None, dossiers: tuple[Path, Path]) -> None:
    reprendre(dossiers)
    avant = comptes_cible()
    journal = un("SELECT count(*) FROM journal")
    r = reprendre(dossiers)
    assert r.reussie, r.rapport
    assert comptes_cible() == avant
    assert un("SELECT count(*) FROM journal") == journal + 1  # la ligne « reprise » seule
    tables = r.comptes["tables"]
    assert sum(c["creees"] + c["mises_a_jour"] + c["supprimees"] for c in tables.values()) == 0


def test_rejouee_apres_des_gestes_dans_gestion_mp(bases: None, dossiers: tuple[Path, Path]) -> None:
    reprendre(dossiers)
    executer_sql(
        SOURCE,
        """
        UPDATE article SET designation = 'Poil rouge vif' WHERE id = 1;
        DELETE FROM recette WHERE id = 2;
        INSERT INTO mouvement (id, date_effet, date_saisie, type, article_id, lot_id, magasin_id,
          quantite, document, document_id, document_numero, ordre_id, auteur)
          VALUES (12, '2026-09-15', '2026-09-15 08:00', 'SORTIE', 1, 1, 1, -10, 'sortie', 1,
                  'OF-2026-0001', 1, 'Youssef');
        UPDATE solde SET quantite = 800 WHERE lot_id = 1 AND magasin_id = 1;
        INSERT INTO journal (id, quand, utilisateur, role, action, objet, objet_id, detail)
          VALUES (10, '2026-10-01', 'Mohamed', 'direction', 'connexion', 'utilisateur', 1, '');
    """,
    )
    r = reprendre(dossiers)
    assert r.reussie, r.rapport
    assert un("SELECT designation FROM matiere WHERE id = 1") == "Poil rouge vif"
    assert un("SELECT count(*) FROM recette") == 1
    assert un("SELECT count(*) FROM mouvement") == 12
    assert un("SELECT quantite FROM solde WHERE lot_id = 1 AND magasin_id = 1") == Decimal(
        "800.000"
    )
    assert un("SELECT count(*) FROM journal WHERE action = 'connexion'") == 1


def test_refus_d_ecraser_une_activite_saisie_dans_pro(
    bases: None, dossiers: tuple[Path, Path]
) -> None:
    reprendre(dossiers)
    executer_sql(CIBLE, "UPDATE commande SET observations = 'saisi dans PRO' WHERE id = 1")
    with pytest.raises(ActiviteRefusee, match="--remplacer-activite"):
        reprendre(dossiers)
    assert un("SELECT observations FROM commande WHERE id = 1") == "saisi dans PRO"
    r = reprendre(dossiers, remplacer_activite=True)
    assert r.reussie, r.rapport
    assert un("SELECT observations FROM commande WHERE id = 1") == ""


def test_fiche_modifiee_dans_pro_et_dans_la_source(
    bases: None, dossiers: tuple[Path, Path]
) -> None:
    reprendre(dossiers)
    executer_sql(CIBLE, "UPDATE fournisseur SET contact = 'dans PRO' WHERE id = 1")
    executer_sql(SOURCE, "UPDATE fournisseur SET contact = 'dans GMP' WHERE id = 1")
    r = reprendre(dossiers)
    assert "modifiée dans PRO et dans la source" in r.rapport
    assert un("SELECT contact FROM fournisseur WHERE id = 1") == "dans PRO"
    reprendre(dossiers, mettre_a_jour=True)
    assert un("SELECT contact FROM fournisseur WHERE id = 1") == "dans GMP"


def test_essai_a_blanc_n_ecrit_rien(
    bases: None, dossiers: tuple[Path, Path], tmp_path: Path
) -> None:
    r = reprendre((dossiers[0], tmp_path / "cible"), essai=True)
    assert r.reussie and r.execution_id is None
    assert un("SELECT count(*) FROM matiere") == 0
    assert un("SELECT count(*) FROM reprise_execution") == 0
    assert not (tmp_path / "cible").exists()


def test_garde_fous(bases: None, dossiers: tuple[Path, Path]) -> None:
    with pytest.raises(RepriseRefusee, match="refusée"):
        executer(
            Options(source=SOURCE, cible="postgresql+psycopg:///gestion_mp", mode=ModeReprise.tout)
        )
    with pytest.raises(ReferentielsAbsents):
        reprendre(dossiers, mode=ModeReprise.activite)
    assert reprendre(dossiers, mode=ModeReprise.referentiels).reussie
    assert un("SELECT count(*) FROM mouvement") == 0
    assert reprendre(dossiers, mode=ModeReprise.activite).reussie
    assert un("SELECT count(*) FROM mouvement") == 11


def test_comptes_et_codes(bases: None, dossiers: tuple[Path, Path]) -> None:
    r = reprendre(dossiers)
    empreinte = un("SELECT empreinte_code FROM utilisateur WHERE identifiant = 'mohamed'")
    assert comptes.verifier(CODE_DIRECTION, empreinte)
    assert un("SELECT empreinte_code FROM utilisateur WHERE identifiant = 'atelier'") == ""
    assert "code à redonner" in r.rapport and "identifiant mis en minuscules" in r.rapport
    historiques = {n for (n,) in lire("SELECT nom FROM utilisateur WHERE historique")}
    assert {"Karim", "Youssef", "Démonstration", "Atelier"} - historiques == {"Atelier"}
    # « Mohamed » et « MOHAMED » répondent à l'identifiant du compte de la direction
    assert "graphies Mohamed, MOHAMED" in r.rapport
    assert un("SELECT utilisateur_id FROM journal WHERE action = 'renvoi aux achats'") == 1
    assert (
        un("SELECT count(*) FROM utilisateur WHERE historique AND (actif OR role IS NOT NULL)") == 0
    )
    assert un("SELECT count(*) FROM utilisateur WHERE nom IN ('système', 'ERP Fil', '')") == 0
