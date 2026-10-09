"""Concurrence : les courses de PLAN-DE-RECETTE-PRO § 11.3, rassemblées et complétées (lot V4).

Chaque domaine a déjà éprouvé ses propres courses (stock S4, réceptions D4, opérations D5,
ordres D6, importations D7, connexions et restauration) ; ce fichier **rassemble** la preuve
(`test_les_courses_du_plan_sont_toutes_eprouvees` : chaque course du § 11.3 cite le test qui la
tient) et **complète** les courses des bons de commande, que personne ne tenait encore :

- deux envois du même bon au même instant : un seul numéro (A10) ;
- vingt envois simultanés de la même série : vingt numéros qui se suivent, sans trou ni
  doublon (le compteur verrouillé de `services/numerotation`) ;
- deux approbations du même bon : une seule part ;
- deux enregistrements d'une même fiche : le verrou de version (409 pour le perdant).

Chaque course est rejouée 50 fois (`REPETITIONS`), postes à part (sessions distinctes),
départ synchronisé par une barrière, comme les autres fichiers de concurrence.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

import pytest
from fabrique import *  # noqa: F403
from fabrique import client_de
from fabriques.achats import Achat, bon, reglage
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.config import RACINE
from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Commande
from gestion_mp_pro.modeles.enums import StatutCommande

REPETITIONS = 50
SEUIL_HAUT = "100000000"
"""Un seuil d'approbation hors d'atteinte : l'envoi numérote tout de suite (pas d'approbation)."""


def _ensemble(appels: list[Callable[[], int]]) -> list[int]:
    """Lance les appels au même instant (barrière) ; rend leurs codes, triés."""
    depart = threading.Barrier(len(appels))
    codes: list[int] = [0] * len(appels)

    def courir(rang: int) -> None:
        depart.wait()
        codes[rang] = appels[rang]()

    fils = [threading.Thread(target=courir, args=(i,)) for i in range(len(appels))]
    for f in fils:
        f.start()
    for f in fils:
        f.join(timeout=60)
    return sorted(codes)


def _rang(numero: str) -> int:
    """Le rang d'un numéro `BC-AAAA-NNNN`."""
    return int(numero.rsplit("-", 1)[1])


def _envoyer(poste: TestClient, cid: int, version: int) -> int:
    return poste.post(f"/api/commandes/{cid}/envoyer", json={"version": version}).status_code


@pytest.mark.parametrize("tour", range(REPETITIONS))
def test_double_envoi_d_un_bon_donne_un_seul_numero(
    application: FastAPI, achats: TestClient, tour: int
) -> None:
    """Deux postes envoient le même brouillon au même instant : l'un part (200), l'autre lit
    une version périmée (409) ; le bon a un seul numéro. Le compteur est pris sous verrou de
    ligne dans la transaction de l'envoi : aucun numéro n'est gâché (A10)."""
    with reglage("seuil_approbation", SEUIL_HAUT):
        a = Achat.nouveau()
        b = bon(achats, a, {a.matiere(f"ENV-{tour}"): 100})
        version = b["version"]
        postes = [client_de(application, "achats"), client_de(application, "achats")]
        assert _ensemble([lambda p=p: _envoyer(p, b["id"], version) for p in postes]) == [200, 409]
    with sessions()() as s:
        c = s.get_one(Commande, b["id"])
        assert c.numero is not None and c.statut == StatutCommande.envoyee


def test_vingt_envois_simultanes_numerotent_sans_trou(
    application: FastAPI, achats: TestClient
) -> None:
    """Vingt bons de la même série envoyés au même instant : vingt numéros consécutifs, sans
    trou ni doublon (course de numérotation sous verrou, § 11.3). Hérité :
    test_audit2_achats::test_des_validations_simultanees_numerotent_sans_trou (porté à 20)."""
    with reglage("seuil_approbation", SEUIL_HAUT):
        a = Achat.nouveau()
        bons = [bon(achats, a, {a.matiere(f"N20-{i}"): 100}) for i in range(20)]
        postes = [client_de(application, "achats") for _ in range(20)]
        paires = zip(postes, bons, strict=True)
        codes = _ensemble([lambda p=p, b=b: _envoyer(p, b["id"], b["version"]) for p, b in paires])
    assert codes == [200] * 20
    with sessions()() as s:
        numeros = sorted(
            s.scalars(select(Commande.numero).where(Commande.id.in_([b["id"] for b in bons])))
        )
    rangs = [_rang(n) for n in numeros]
    assert len(set(rangs)) == 20
    assert rangs == list(range(rangs[0], rangs[0] + 20))


@pytest.mark.parametrize("tour", range(REPETITIONS))
def test_double_approbation_ne_vaut_qu_une_fois(
    application: FastAPI, achats: TestClient, direction: TestClient, tour: int
) -> None:
    """Un bon au-dessus du seuil attend la direction ; deux directeurs l'approuvent au même
    instant : un seul le fait partir (200), l'autre voit la version changée (409). Un seul
    numéro, un seul départ."""
    with reglage("seuil_approbation", "1"):
        a = Achat.nouveau()
        b = bon(achats, a, {a.matiere(f"APP-{tour}", prix="50"): 1000})
        envoye = achats.post(f"/api/commandes/{b['id']}/envoyer", json={"version": b["version"]})
        assert envoye.status_code == 200, envoye.text
        attente = envoye.json()
        assert attente["statut"] == StatutCommande.a_approuver
        version = attente["version"]
        postes = [client_de(application, "direction"), client_de(application, "direction")]
        codes = _ensemble(
            [
                lambda p=p: (
                    p.post(
                        f"/api/commandes/{b['id']}/approuver", json={"version": version}
                    ).status_code
                )
                for p in postes
            ]
        )
    assert codes == [200, 409]
    with sessions()() as s:
        c = s.get_one(Commande, b["id"])
        assert c.numero is not None and c.approuvee_par_id is not None


@pytest.mark.parametrize("tour", range(REPETITIONS))
def test_deux_enregistrements_d_une_fiche_verrou_de_version(
    application: FastAPI, achats: TestClient, tour: int
) -> None:
    """Deux postes enregistrent le même brouillon au même instant, partis de la même version :
    l'un écrit (200), l'autre est refusé (409 `conflit_version`) et doit rouvrir la fiche. La
    version n'avance que d'un cran."""
    a = Achat.nouveau()
    m = a.matiere(f"FIC-{tour}")
    b = bon(achats, a, {m: 100})
    version = b["version"]

    def enregistrer(poste: TestClient, quantite: int) -> int:
        corps = {"version": version, "lignes": [{"matiere_id": m, "quantite": quantite}]}
        return poste.put(f"/api/commandes/{b['id']}", json=corps).status_code

    postes = [client_de(application, "achats"), client_de(application, "achats")]
    assert _ensemble(
        [lambda p=p, q=q: enregistrer(p, q) for p, q in ((postes[0], 110), (postes[1], 120))]
    ) == [
        200,
        409,
    ]
    with sessions()() as s:
        assert s.get_one(Commande, b["id"]).version == version + 1


# ── Rassemblement : chaque course du § 11.3 est tenue quelque part ───────────────────


COURSES_DU_PLAN = {
    "deux sorties de 70 % d'un même lot": (
        "test_stock_concurrence.py",
        "test_deux_sorties_de_70_pour_cent_jamais_sous_zero",
    ),
    "deux retours d'un même ordre": (
        "test_operations_concurrence.py",
        "test_deux_retours_simultanes_du_meme_ordre",
    ),
    "deux réceptions franchissent l'excédent": (
        "test_receptions_concurrence.py",
        "test_deux_postes_ne_franchissent_pas_l_excedent_a_deux",
    ),
    "deux clics ne valident pas deux fois": (
        "test_receptions_concurrence.py",
        "test_deux_clics_ne_valident_pas_deux_fois",
    ),
    "trois créations d'un même dossier": (
        "test_importations_concurrence.py",
        "test_trois_creations_simultanees_un_seul_dossier",
    ),
    "ouverture de dossier contre annulation de réception": (
        "test_importations_concurrence.py",
        "test_ouvrir_pendant_qu_on_annule_la_reception",
    ),
    "correction de facture contre ouverture": (
        "test_importations_concurrence.py",
        "test_corriger_la_facture_pendant_qu_on_ouvre_le_dossier",
    ),
    "clôture de dossier contre ajout d'un frais": (
        "test_importations_concurrence.py",
        "test_la_cloture_contre_l_ajout_d_un_frais",
    ),
    "validations d'ordres sous verrou": (
        "test_ordres_concurrence.py",
        "test_deux_validations_d_ordre_se_suivent_sous_verrou",
    ),
    "validation d'inventaire contre sortie": (
        "test_operations_concurrence.py",
        "test_ouverture_d_inventaire_contre_sortie",
    ),
    "connexions ratées simultanées": (
        "test_connexion.py",
        "test_des_echecs_simultanes_ne_font_pas_d_erreur",
    ),
    "restauration pendant l'activité (sessions ouvertes)": (
        "test_restauration.py",
        "test_restauration_reelle_identique_rapide_sessions_coupees_pieces",
    ),
    "cache du moteur à deux processus": (
        "test_donnees_moteur_cache.py",
        "test_une_ecriture_d_un_autre_processus_se_voit_aussitot",
    ),
    "double envoi d'un bon : un seul numéro": (
        "test_concurrence.py",
        "test_double_envoi_d_un_bon_donne_un_seul_numero",
    ),
    "numérotation sous vingt validations simultanées": (
        "test_concurrence.py",
        "test_vingt_envois_simultanes_numerotent_sans_trou",
    ),
    "double approbation": (
        "test_concurrence.py",
        "test_double_approbation_ne_vaut_qu_une_fois",
    ),
    "deux enregistrements d'une fiche (verrou de version)": (
        "test_concurrence.py",
        "test_deux_enregistrements_d_une_fiche_verrou_de_version",
    ),
}
"""Chaque course du plan → (fichier d'essais, fonction) qui la tient."""


def test_les_courses_du_plan_sont_toutes_eprouvees() -> None:
    """PLAN-DE-RECETTE-PRO § 11.3 : chaque course citée a bien un essai qui la tient (le nom de
    la fonction est présent dans son fichier). Garde-fou contre un renommage silencieux."""
    dossier = RACINE / "backend" / "tests"
    manquants = []
    for course, (fichier, fonction) in COURSES_DU_PLAN.items():
        chemin = dossier / fichier
        if not chemin.exists() or f"def {fonction}" not in chemin.read_text(encoding="utf-8"):
            manquants.append(f"{course} → {fichier}::{fonction}")
    assert not manquants, "Courses du § 11.3 sans essai : " + " ; ".join(manquants)
    assert Path(RACINE / "backend" / "essais" / "concurrence.py").exists()
