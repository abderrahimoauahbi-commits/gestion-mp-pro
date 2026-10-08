"""Contrôle des devises : C11, une devise employée sans cours."""

from __future__ import annotations

from gestion_mp_pro.calcul.controles.base import Contexte, Ligne, colonne, controle
from gestion_mp_pro.calcul.controles.textes import GARANTI_C11
from gestion_mp_pro.calcul.modele import Donnees, Parametres


def devises_employees(donnees: Donnees) -> dict[str, str]:
    """Chaque devise employée et où elle l'est d'abord : matières en service, lignes de bons,
    marchandises et factures des dossiers d'importation."""
    employees: dict[str, str] = {}
    for a in donnees.articles:
        if a.actif and a.devise:
            employees.setdefault(a.devise, f"matière {a.reference}")
    for commande in donnees.commandes:
        for ligne in commande.lignes:
            if ligne.devise:
                employees.setdefault(ligne.devise, f"commande {commande.numero}")
    for dossier in donnees.dossiers_import:
        for marchandise in dossier.lignes:
            if marchandise.devise:
                employees.setdefault(marchandise.devise, f"dossier {dossier.numero}")
        if dossier.facture_devise:
            employees.setdefault(dossier.facture_devise, f"dossier {dossier.numero}")
    return employees


def _taux_du_classeur(parametres: Parametres) -> list[Ligne]:
    """Sans table des devises : les deux taux des réglages."""
    lignes: list[Ligne] = []
    if parametres.taux_eur_mad <= 0:
        lignes.append({"taux": "EUR → MAD", "valeur": parametres.taux_eur_mad})
    if parametres.taux_usd_mad <= 0:
        lignes.append({"taux": "USD → MAD", "valeur": parametres.taux_usd_mad})
    return lignes


@controle(
    "C11",
    gravite="bloquant",
    lien="/reglages?onglet=devises",
    colonnes=(colonne("taux", "texte"), colonne("valeur", "MAD"), colonne("type", "texte")),
    garanti=GARANTI_C11,
)
def devise_sans_cours(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Une devise employée sans cours tenu se lirait comme des dirhams (`Parametres.taux`
    rend 1) : elle se signale, comme un cours nul."""
    parametres = ctx.parametres
    libelle = "Devise employée (catalogue, bons, dossiers) sans cours"
    if not parametres.cours:
        return libelle, _taux_du_classeur(parametres)
    lignes: list[Ligne] = []
    for devise, ou in sorted(devises_employees(ctx.donnees).items()):
        cours = parametres.cours.get(devise)
        if devise != "MAD" and (cours is None or cours <= 0):
            lignes.append({"taux": devise, "valeur": cours or 0.0, "type": f"employée par : {ou}"})
    return libelle, lignes
