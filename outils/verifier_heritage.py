#!/usr/bin/env python3
"""Vérifie que les preuves héritées de Gestion MP sont toutes reprises par PRO (lot V5).

`docs/heritage/ESSAIS.md` inventorie les essais automatiques de Gestion MP, chacun nommé
`fichier::fonction` dans une ligne de tableau (certaines lignes élident le fichier par « … » :
c'est le fichier de la ligne précédente). Le plan de recette (PLAN-DE-RECETTE-PRO § 3) exige que
**chaque** preuve soit portée par au moins un essai PRO, qui cite son origine dans sa docstring :
`Hérité : fichier::fonction`.

Ce script relève les identifiants de `ESSAIS.md`, relève les citations des essais PRO
(`backend/tests/`, `backend/essais/`), et vérifie que chaque preuve est couverte :

1. par une citation exacte `fichier::fonction` ; ou
2. par une citation du **même nom de fonction** sous un autre fichier (un essai PRO réunit ou
   déplace une preuve, ou « … » a été résolu vers un autre fichier) ; ou
3. par le relevé `COUVERTURE` ci-dessous, pour une preuve qu'un essai PRO prouve sous un **nom
   reformulé** — chaque entrée pointe un essai PRO réel, dont l'existence est vérifiée ici.

Sortie : le décompte et, s'il en manque, la liste. Code 1 si une preuve n'est pas couverte, 2 si
`ESSAIS.md` est introuvable ou vide.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
ESSAIS_MD = RACINE / "docs" / "heritage" / "ESSAIS.md"
SOURCES = (RACINE / "backend" / "tests", RACINE / "backend" / "essais")

# Preuves portées par un essai PRO au nom reformulé : identifiant hérité → essai PRO (relatif à
# backend/). L'essai visé doit exister (vérifié) ; sinon le relevé est périmé et le script échoue.
COUVERTURE: dict[str, str] = {
    "test_audit2_achats::test_le_courriel_du_lundi_compte_les_retards_comme_l_ecran": (
        "tests/moteur/test_suivi.py::test_commandes_en_retard_du_courriel"
    ),
    "test_audit2_pilotage::test_les_prix_payes_sont_au_kilo": (
        "tests/test_pilotage_prix.py::test_l_historique_des_prix_se_cherche_et_compte_ses_hausses"
    ),
    "test_exports::test_croissance_et_tolerance_de_livraison_bornees": (
        "tests/test_reglages.py::test_refus_de_saisie"
    ),
    "test_exports::test_le_journal_s_exporte_avec_ses_filtres": (
        "tests/test_exports.py::test_le_journal_s_exporte_avec_les_filtres_de_l_ecran"
    ),
    "test_exports::test_le_pilotage_s_exporte": (
        "tests/test_plan_achat.py::test_les_classeurs_du_plan_d_achat"
    ),
    "test_importations::test_un_fournisseur_marocain_se_confirme": (
        "tests/test_importations_attente.py::test_les_fournisseurs_marocains_n_ont_pas_de_dossier"
    ),
    "test_importations_second_audit::test_les_morceaux_d_un_ancien_eclatement_redeviennent_une_piece": (
        "tests/test_reprise_traductions.py::test_les_morceaux_d_un_ancien_eclatement_redeviennent_une_piece"
    ),
    "test_matieres_au_metre::test_bon_au_prix_au_metre": (
        "tests/test_bon_fournisseur.py::test_les_metres_d_un_cuir_sont_indicatifs"
    ),
    "test_matieres_au_metre::test_l_etape_14_convertit_les_metres_en_kilos": (
        "tests/test_reprise_reelle.py::test_reprise_reelle"
    ),
    "test_matieres_au_metre::test_proposition_de_sortie_en_kilos_avec_les_metres": (
        "tests/moteur/test_metre.py::test_consommation_d_un_ordre_en_kilos"
    ),
    "test_matieres_au_metre::test_reception_hors_commande_au_prix_du_kilo": (
        "tests/test_receptions.py::test_le_prix_paye_hors_commande_est_retenu"
    ),
    "test_matieres_au_metre::test_stock_et_valeur_en_kilos": (
        "tests/moteur/test_metre.py::test_stock_valeur_et_cmup_en_kilos"
    ),
    "test_parite::test_memes_resultats_que_l_erp_fil": (
        "tests/test_parite.py::test_parite_sur_l_annee_d_essai"
    ),
    "test_stock_atelier::test_export_des_sorties": (
        "tests/test_exports.py::test_titre_filtres_et_onglets"
    ),
    "test_stock_atelier::test_recette_les_seuils_de_couverture_restent_dans_l_ordre": (
        "tests/test_reglages.py::test_seuils_dans_l_ordre_sinon_rien"
    ),
    "test_valeur_et_dates::test_le_verificateur_voit_les_fautes_du_moteur_d_avant": (
        "tests/test_verification.py::test_ancien_moteur_g3_annulation_au_cout_moyen"
    ),
    "test_valorisation::test_api_l_inventaire_valorise_ses_ecarts_et_ne_se_date_pas_avant_ce_qu_il_fige": (
        "tests/moteur/test_inventaire.py::test_zero_kilo_net_et_4000_mad_de_perte"
    ),
    "test_valorisation::test_api_le_verificateur_voit_une_valeur_fausse": (
        "tests/test_verification.py::test_cmup_fois_1_1_dans_une_reponse"
    ),
    "test_zz_verificateur::test_les_ecrans_concordent_avec_la_base": (
        "tests/test_verification.py::test_sans_faute_aucun_ecart"
    ),
}

_LIGNE = re.compile(r"^\|\s*`(…|\.\.\.|[a-z0-9_]+)::(test_[a-z0-9_]+)`")
_PAIRE = re.compile(r"([a-z0-9_]+)::(test_[a-z0-9_]+)")
_DEF = re.compile(r"^\s*def (test_[a-z0-9_]+)\s*\(", re.MULTILINE)


def preuves_attendues() -> list[tuple[str, str]]:
    """Les preuves de ESSAIS.md : (fichier, fonction), « … » résolu au fichier précédent."""
    attendues: list[tuple[str, str]] = []
    dernier: str | None = None
    for ligne in ESSAIS_MD.read_text(encoding="utf-8").splitlines():
        m = _LIGNE.match(ligne.strip())
        if not m:
            continue
        fichier, fonction = m.group(1), m.group(2)
        if fichier in ("…", "..."):
            fichier = dernier or ""
        else:
            dernier = fichier
        if fichier:
            attendues.append((fichier, fonction))
    return sorted(set(attendues))


def _fichiers_py() -> list[Path]:
    """Tous les essais PRO (tests et essais)."""
    return sorted(p for racine in SOURCES for p in racine.rglob("*.py"))


def citations() -> tuple[set[tuple[str, str]], set[str]]:
    """Les paires `fichier::fonction` citées par les essais PRO, et les noms de fonction cités."""
    paires: set[tuple[str, str]] = set()
    for p in _fichiers_py():
        for m in _PAIRE.finditer(p.read_text(encoding="utf-8")):
            paires.add((m.group(1), m.group(2)))
    return paires, {fn for _, fn in paires}


def defs_pro() -> set[str]:
    """Les essais PRO réellement définis : « chemin/relatif::fonction » (relatif à backend/)."""
    back = RACINE / "backend"
    trouves: set[str] = set()
    for p in _fichiers_py():
        rel = p.relative_to(back).as_posix()
        for m in _DEF.finditer(p.read_text(encoding="utf-8")):
            trouves.add(f"{rel}::{m.group(1)}")
    return trouves


def verifier() -> tuple[list[str], dict[str, int]]:
    """Rend les preuves non couvertes et le décompte par mode de couverture."""
    attendues = preuves_attendues()
    paires, noms = citations()
    defs = defs_pro()
    cpt = {"exact": 0, "nom": 0, "supplement": 0, "manquant": 0}
    manquants: list[str] = []
    supplement_casse: list[str] = []
    for fichier, fonction in attendues:
        cle = f"{fichier}::{fonction}"
        if (fichier, fonction) in paires:
            cpt["exact"] += 1
        elif fonction in noms:
            cpt["nom"] += 1
        elif cle in COUVERTURE:
            if COUVERTURE[cle] in defs:
                cpt["supplement"] += 1
            else:
                supplement_casse.append(f"{cle} → {COUVERTURE[cle]} (essai PRO introuvable)")
        else:
            cpt["manquant"] += 1
            manquants.append(cle)
    return manquants + supplement_casse, cpt


def main() -> int:
    """Lance la vérification ; 0 si toutes les preuves sont couvertes, 1 sinon, 2 si lecture KO."""
    if not ESSAIS_MD.exists():
        sys.stderr.write(f"{ESSAIS_MD} introuvable.\n")
        return 2
    attendues = preuves_attendues()
    if not attendues:
        sys.stderr.write("Aucune preuve lue dans ESSAIS.md.\n")
        return 2
    manquants, cpt = verifier()
    total = len(attendues)
    sys.stdout.write(
        f"Preuves héritées (ESSAIS.md) : {total} citées "
        f"(exactes {cpt['exact']}, par le nom {cpt['nom']}, relevées {cpt['supplement']}).\n"
    )
    if manquants:
        sys.stdout.write(f"Non couvertes : {len(manquants)}\n")
        for x in manquants:
            sys.stdout.write(f"  MANQUE {x}\n")
        return 1
    sys.stdout.write("Toutes les preuves héritées sont reprises par un essai PRO.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
