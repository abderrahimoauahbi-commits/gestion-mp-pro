"""Contrôles des importations : ce qui empêcherait le coût de revient d'être juste
(C28, C29, C34, C35, C36)."""

from __future__ import annotations

from gestion_mp_pro.calcul.controles.base import Contexte, Ligne, colonne, controle
from gestion_mp_pro.calcul.importations import (
    ecart_facture,
    lignes_aberrantes,
    lignes_de_la_facture,
    revient_dossier,
    tva_attendue,
)
from gestion_mp_pro.calcul.modele import DossierImport, FactureImport, Parametres
from gestion_mp_pro.calcul.outils import pourcentage

CENT = 100
"""Un seuil réglé en part, écrit en pour cent dans le libellé."""
DECIMALES_PART = 4
"""C36 : l'écart de la facture, en part arrondie à quatre décimales (0,035)."""

_IMPORTATIONS = "/importations"
_DOSSIER = colonne("dossier", "texte")


@controle(
    "C28",
    gravite="avertissement",
    lien=_IMPORTATIONS,
    colonnes=(
        _DOSSIER,
        colonne("arrivee", "date"),
        colonne("marchandises", "nombre"),
        colonne("jours_arrivee", "j"),
    ),
)
def dossier_sans_frais(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un dossier ouvert, avec des marchandises, arrivé depuis plus que le délai réglé et sans
    aucun frais hors TVA : son coût de revient n'est que le prix de la facture."""
    delai = ctx.parametres.delai_frais_import_jours
    lignes: list[Ligne] = [
        {
            "dossier": d.numero,
            "arrivee": d.date_arrivee.isoformat(),
            "marchandises": len(d.lignes),
            "jours_arrivee": (ctx.date_ref - d.date_arrivee).days,
        }
        for d in ctx.donnees.dossiers_import
        if d.ouvert
        and d.lignes
        and not [c for c in d.charges if not c.recuperable]
        and d.date_arrivee
        and (ctx.date_ref - d.date_arrivee).days > delai
    ]
    libelle = f"Dossier d'importation arrivé depuis plus de {delai:g} jours et sans frais hors TVA"
    return libelle, lignes


@controle(
    "C29",
    gravite="avertissement",
    lien=_IMPORTATIONS,
    colonnes=(
        _DOSSIER,
        colonne("tva_saisie", "MAD"),
        colonne("tva_attendue", "MAD"),
        colonne("ecart_mad", "MAD"),
    ),
)
def tva_douteuse(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """La TVA de la douane (les postes de nature `tva`) face à l'attendue : le taux réglé sur
    la valeur en douane augmentée des droits et de la TPI, à l'écart toléré près (réglage
    `toler_tva_import`, 5 % : Gestion MP 26459d4, E-10)."""
    parametres = ctx.parametres
    lignes: list[Ligne] = []
    for dossier in ctx.donnees.dossiers_import:
        tva = sum(c.montant for c in dossier.charges if c.est_tva)
        if not tva:
            continue
        attendue = tva_attendue(dossier, parametres)
        if attendue and abs(tva - attendue) > abs(attendue) * parametres.toler_tva_import:
            lignes.append(
                {
                    "dossier": dossier.numero,
                    "tva_saisie": tva,
                    "tva_attendue": attendue,
                    "ecart_mad": tva - attendue,
                }
            )
    libelle = (
        f"TVA d'importation à plus de {pourcentage(parametres.toler_tva_import)} "
        "de la TVA attendue "
        f"({pourcentage(parametres.taux_tva_import)} de la valeur en douane, droits et TPI "
        "compris)"
    )
    return libelle, lignes


@controle(
    "C34",
    gravite="avertissement",
    lien="/importations?onglet=rattacher",
    colonnes=(_DOSSIER, colonne("frais", "MAD"), colonne("tva", "MAD")),
)
def frais_sans_marchandise(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Des frais sur un dossier sans marchandise ne se répartissent sur rien ; la TVA à part."""
    lignes: list[Ligne] = [
        {
            "dossier": d.numero,
            "frais": sum(c.montant for c in d.charges if not c.recuperable),
            "tva": sum(c.montant for c in d.charges if c.recuperable),
        }
        for d in ctx.donnees.dossiers_import
        if d.charges and not d.lignes
    ]
    return "Dossier d'importation avec des frais mais sans marchandise", lignes


def _surcouts(dossier: DossierImport, parametres: Parametres) -> list[Ligne]:
    """Le dossier entier s'il dépasse le seuil, sinon ses marchandises aberrantes."""
    seuil = parametres.seuil_surcout_import
    repartis = revient_dossier(dossier, parametres)
    marchandise = sum(x.valeur_mad for x in repartis)
    frais = sum(x.charges_mad for x in repartis)
    if marchandise > 0 and frais > marchandise * seuil:
        return [
            {
                "dossier": dossier.numero,
                "reference": "(tout le dossier)",
                "marchandise_mad": round(marchandise, 2),
                "frais_mad": round(frais, 2),
                "surcout": frais / marchandise,
            }
        ]
    return [
        {
            "dossier": dossier.numero,
            "reference": x.reference,
            "marchandise_mad": round(x.valeur_mad, 2),
            "frais_mad": round(x.charges_mad, 2),
            "surcout": x.charges_mad / x.valeur_mad if x.valeur_mad > 0 else None,
        }
        for x in lignes_aberrantes(repartis, seuil)
    ]


@controle(
    "C35",
    gravite="avertissement",
    lien=_IMPORTATIONS,
    colonnes=(
        _DOSSIER,
        colonne("reference", "texte"),
        colonne("marchandise_mad", "MAD"),
        colonne("frais_mad", "MAD"),
        colonne("surcout", "%"),
    ),
)
def frais_aberrants(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Des frais sans commune mesure avec la marchandise (une faute de frappe, les frais d'un
    autre dossier) nourriraient le coût moyen du stock. `surcout` est la fraction frais /
    marchandise, non arrondie (échelle unique P8-3)."""
    seuil = ctx.parametres.seuil_surcout_import
    lignes: list[Ligne] = []
    for dossier in ctx.donnees.dossiers_import:
        lignes += _surcouts(dossier, ctx.parametres)
    libelle = (
        "Dossier d'importation (ou une de ses marchandises) dont les frais dépassent "
        f"{seuil * CENT:g} % de la marchandise"
    )
    return libelle, lignes


def _facture_ecartee(
    dossier: DossierImport, facture: FactureImport, parametres: Parametres
) -> Ligne | None:
    """La ligne de C36 pour une facture du dossier, ou None. Ce qui ne peut pas se rapprocher se
    dit, au lieu de passer pour conforme. Chaque facture se rapproche de **sa** marchandise
    (un dossier en porte plusieurs depuis le 12/10/2026)."""
    if facture.numero and dossier.lignes and not facture.montant:
        return {
            "dossier": dossier.numero,
            "facture": facture.numero,
            "motif": "montant de la facture non saisi",
        }
    lignes = lignes_de_la_facture(dossier, facture)
    if facture.numero and lignes:
        autres = sorted({x.devise or "MAD" for x in lignes} - {facture.devise or "MAD"})
        if autres:
            return {
                "dossier": dossier.numero,
                "facture": facture.numero,
                "devise": facture.devise or "MAD",
                "motif": f"marchandise en {', '.join(autres)} : ne se rapproche pas",
            }
    ecart = ecart_facture(dossier, facture, parametres)
    if ecart is None or not ecart.hors_tolerance:
        return None
    return {
        "dossier": dossier.numero,
        "facture": ecart.facture,
        "facture_montant": round(ecart.montant, 2),
        "recu": round(ecart.recu, 2),
        "devise": ecart.devise,
        "ecart": round(ecart.part, DECIMALES_PART),
    }


@controle(
    "C36",
    gravite="avertissement",
    lien=_IMPORTATIONS,
    colonnes=(
        _DOSSIER,
        colonne("facture", "texte"),
        colonne("facture_montant", "nombre"),
        colonne("recu", "nombre"),
        colonne("devise", "texte"),
        colonne("ecart", "%"),
        colonne("motif", "texte"),
    ),
)
def facture_eloignee(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Chaque facture rapprochée de la marchandise qu'elle a apportée (pesée × prix) : au-delà de
    la tolérance, un manque de poids, une facture mal saisie, un camion pas encore rattaché."""
    lignes: list[Ligne] = [
        ligne
        for dossier in ctx.donnees.dossiers_import
        for facture in dossier.factures
        if (ligne := _facture_ecartee(dossier, facture, ctx.parametres)) is not None
    ]
    libelle = (
        "Facture d'un dossier d'importation éloignée de plus de "
        f"{ctx.parametres.toler_facture_import * CENT:g} % de la marchandise reçue"
    )
    return libelle, lignes
