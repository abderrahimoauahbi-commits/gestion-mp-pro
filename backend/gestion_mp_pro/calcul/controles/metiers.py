"""Contrôles des métiers à tisser : laize, poids de bobine, étages (C22, C23, C24)."""

from __future__ import annotations

from gestion_mp_pro.calcul.constantes import EPSILON
from gestion_mp_pro.calcul.controles.base import Contexte, Ligne, colonne, controle
from gestion_mp_pro.calcul.controles.textes import GARANTI_C24

CENT = 100
"""Le pourcentage d'un fil sur ses mètres."""

_METIER = colonne("metier", "texte")
_ETAGE = colonne("etage", "nombre")
_REFERENCE = colonne("reference", "texte")


@controle(
    "C22",
    gravite="avertissement",
    lien="/metiers",
    colonnes=(
        _METIER,
        _ETAGE,
        colonne("laize", "m"),
        colonne("metres_montes", "m"),
        colonne("fils", "nombre"),
    ),
)
def etage_trop_large(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Ce qui est monté à un étage doit tenir dans la laize ; chaque fil pour sa part (deux
    fils à 60 et 40 % sur les mêmes mètres les occupent une fois)."""
    lignes: list[Ligne] = []
    for machine in ctx.donnees.metiers:
        if not machine.actif or machine.laize <= 0:
            continue
        for etage in sorted({f.etage for f in machine.fils}):
            fils_etage = [f for f in machine.fils if f.etage == etage]
            largeur = sum(f.metres * f.pourcentage / CENT for f in fils_etage)
            if largeur > machine.laize + EPSILON:
                lignes.append(
                    {
                        "metier": machine.code,
                        "etage": etage,
                        "laize": machine.laize,
                        "metres_montes": largeur,
                        "fils": len(fils_etage),
                    }
                )
    return "Étage monté plus large que la laize du métier", lignes


@controle(
    "C23",
    gravite="avertissement",
    lien="/catalogue?onglet=matieres",
    colonnes=(_METIER, _ETAGE, _REFERENCE, colonne("metres", "m")),
)
def fil_sans_poids_de_bobine(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un fil monté sans poids de bobine pèse zéro, donc échappe au stock et à la projection."""
    lignes: list[Ligne] = [
        {"metier": f.metier, "etage": f.etage, "reference": f.reference, "metres": f.metres}
        for f in ctx.fils
        if not f.poids_bobine
    ]
    return "Fil monté sans poids de bobine (ni pesé au lot, ni au catalogue)", lignes


@controle(
    "C24",
    gravite="avertissement",
    lien="/metiers",
    colonnes=(_METIER, _ETAGE, colonne("etages", "nombre"), _REFERENCE),
    garanti=GARANTI_C24,
)
def etage_inexistant(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un fil monté à un étage que le métier n'a pas (métiers en service)."""
    lignes: list[Ligne] = [
        {"metier": m.code, "etage": f.etage, "etages": m.etages, "reference": f.reference}
        for m in ctx.donnees.metiers
        if m.actif
        for f in m.fils
        if f.etage > m.etages
    ]
    return "Fil monté à un étage que le métier n'a pas", lignes
