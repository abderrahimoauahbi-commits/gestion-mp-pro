"""Contrôles du catalogue : fournisseurs, prix, devises, stock minimum, sourcing
(C05, C07, C09, C10, C15, C17, C19, C21, C33, C38)."""

from __future__ import annotations

import math
from datetime import date

from gestion_mp_pro.calcul.constantes import (
    MONO_SOURCE,
    POUSSIERE,
    RAPPORT_PRIX_ELOIGNE,
    STATUTS_EN_ALERTE,
)
from gestion_mp_pro.calcul.controles.base import Contexte, Ligne, colonne, controle
from gestion_mp_pro.calcul.controles.textes import GARANTI_C09, GARANTI_C10, GARANTI_C21
from gestion_mp_pro.calcul.fournisseurs import devises_pratiquees
from gestion_mp_pro.calcul.modele import Donnees, LignePrix

_MATIERES = "/catalogue?onglet=matieres"
_REFERENCE = colonne("reference", "texte")
_FOURNISSEUR = colonne("fournisseur", "texte")


@controle("C05", gravite="bloquant", lien=_MATIERES, colonnes=(_REFERENCE,))
def matiere_sans_fournisseur(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Une matière en service sans fournisseur ne peut pas être commandée (T07) ; une matière
    désactivée ne se commande plus."""
    lignes: list[Ligne] = [
        {"reference": a.reference} for a in ctx.donnees.articles if a.actif and not a.fournisseur
    ]
    return "Matière sans fournisseur", lignes


@controle("C07", gravite="information", lien=_MATIERES, colonnes=(_REFERENCE,))
def matiere_jamais_utilisee(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Une matière en service ni dans une recette, ni dans le journal (T09)."""
    d = ctx.donnees
    utilisees = {r.reference for r in d.recettes} | {m.reference for m in d.mouvements}
    actives = {a.reference for a in d.articles if a.actif}
    lignes: list[Ligne] = [{"reference": r} for r in sorted(actives - utilisees)]
    return "Matière jamais utilisée (ni recette, ni mouvement)", lignes


@controle(
    "C09",
    gravite="bloquant",
    lien=_MATIERES,
    colonnes=(_REFERENCE, colonne("prix", "nombre")),
    garanti=GARANTI_C09,
)
def prix_negatif(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un prix négatif au catalogue (T11)."""
    lignes: list[Ligne] = [
        {"reference": a.reference, "prix": a.prix_unite}
        for a in ctx.donnees.articles
        if a.prix_unite < 0
    ]
    return "Prix négatif au catalogue", lignes


@controle(
    "C10",
    gravite="bloquant",
    lien="/catalogue?onglet=fournisseurs",
    colonnes=(_FOURNISSEUR, colonne("delai", "j")),
    garanti=GARANTI_C10,
)
def delai_invalide(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un délai fournisseur nul ou négatif (T12)."""
    lignes: list[Ligne] = [
        {"fournisseur": f.nom, "delai": f.delai_jours}
        for f in ctx.donnees.fournisseurs
        if f.delai_jours <= 0
    ]
    return "Délai fournisseur nul ou négatif", lignes


@controle(
    "C15",
    gravite="avertissement",
    lien=_MATIERES,
    colonnes=(colonne("qualite", "texte"), _REFERENCE, colonne("motif", "texte")),
)
def recette_sans_prix(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Une matière d'une recette sans prix d'achat, ou désactivée (C14 de l'audit)."""
    d = ctx.donnees
    lignes: list[Ligne] = [
        {
            "qualite": r.qualite,
            "reference": r.reference,
            "motif": (
                "matière désactivée encore dans la recette"
                if not article.actif
                else "sans prix d'achat"
            ),
        }
        for r in d.recettes
        if r.pourcentage > 0
        and (article := d.article(r.reference)) is not None
        and (not article.prix_kg or not article.actif)
    ]
    return "Matière d'une recette sans prix d'achat, ou désactivée", lignes


@controle(
    "C17",
    gravite="information",
    lien=_MATIERES,
    colonnes=(_REFERENCE, _FOURNISSEUR, colonne("montant_a_commander_mad", "MAD")),
)
def alerte_mono_source(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Une matière en alerte qui ne dépend que d'un fournisseur : mono-source, ou sans groupe
    d'équivalence (aucun fil de rechange connu) ; les plus gros montants d'abord."""
    mono = [
        x
        for x in ctx.lignes_stock
        if (x.sourcing == MONO_SOURCE or not x.groupe_equiv) and x.statut in STATUTS_EN_ALERTE
    ]
    mono.sort(key=lambda x: -x.montant_a_commander_mad)
    lignes: list[Ligne] = [
        {
            "reference": x.reference,
            "fournisseur": x.fournisseur,
            "montant_a_commander_mad": x.montant_a_commander_mad,
        }
        for x in mono
    ]
    return "Matière en alerte sans second fournisseur", lignes


@controle(
    "C19",
    gravite="information",
    lien="/catalogue?onglet=fournisseurs",
    colonnes=(_FOURNISSEUR, colonne("devises", "texte"), colonne("devise_par_defaut", "texte")),
)
def fournisseur_multi_devises(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un fournisseur qui facture en plusieurs monnaies : un fait commercial, pas une faute.
    Seules les matières en service comptent."""
    d = ctx.donnees
    pratiquees = devises_pratiquees(Donnees(articles=[a for a in d.articles if a.actif]))
    lignes: list[Ligne] = [
        {
            "fournisseur": nom,
            "devises": " · ".join(
                f"{devise} ({nombre} matière(s))" for devise, nombre in sorted(devises.items())
            ),
            "devise_par_defaut": (f.devise if (f := d.fournisseur(nom)) else ""),
        }
        for nom, devises in sorted(pratiquees.items())
        if len(devises) > 1
    ]
    return "Fournisseur qui facture en plusieurs devises", lignes


@controle(
    "C21",
    gravite="bloquant",
    lien=_MATIERES,
    colonnes=(_REFERENCE, colonne("prix", "nombre"), _FOURNISSEUR),
    garanti=GARANTI_C21,
)
def prix_sans_devise(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un prix au catalogue sans devise."""
    lignes: list[Ligne] = [
        {"reference": a.reference, "prix": a.prix_unite, "fournisseur": a.fournisseur}
        for a in ctx.donnees.articles
        if a.prix_unite and not a.devise
    ]
    return "Prix au catalogue sans devise", lignes


@controle(
    "C33",
    gravite="information",
    lien=_MATIERES,
    colonnes=(
        _REFERENCE,
        colonne("stock_min_catalogue", "kg"),
        colonne("conso_mensuelle", "kg"),
        colonne("mois", "nombre"),
        colonne("retenu", "kg"),
    ),
)
def stock_minimum_excessif(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Le stock minimum du catalogue au-delà du plafond en mois de la consommation qui vient
    (celle du calcul) : ce que le calcul plafonne, et de combien ; les plus longs d'abord."""
    plafond = ctx.parametres.plafond_stock_min_mois
    lignes: list[Ligne] = []
    cles: list[float] = []
    for x in ctx.lignes_stock:
        if (
            plafond > 0
            and x.conso_mensuelle > 0
            and x.conso_horizon > 0
            and x.stock_min_plafonne < x.stock_min - POUSSIERE
        ):
            mois = round(x.stock_min / x.conso_horizon, 1)
            cles.append(-mois)
            lignes.append(
                {
                    "reference": x.reference,
                    "stock_min_catalogue": x.stock_min,
                    "conso_mensuelle": round(x.conso_horizon, 1),
                    "mois": mois,
                    "retenu": round(x.stock_min_plafonne),
                }
            )
    ordre = sorted(range(len(lignes)), key=lambda i: cles[i])
    libelle = f"Stock minimum du catalogue supérieur à {plafond:g} mois de consommation"
    return libelle, [lignes[i] for i in ordre]


def _derniers_prix(ctx: Contexte) -> dict[str, tuple[date, LignePrix]]:
    """Le dernier prix payé de chaque matière à la date (à date égale, le dernier lu)."""
    derniers: dict[str, tuple[date, LignePrix]] = {}
    for p in ctx.donnees.historique_prix:
        if p.prix_achat > 0 and p.date_bc is not None and p.date_bc <= ctx.date_ref:
            if p.reference not in derniers or p.date_bc >= derniers[p.reference][0]:
                derniers[p.reference] = (p.date_bc, p)
    return derniers


@controle(
    "C38",
    gravite="avertissement",
    lien=_MATIERES,
    colonnes=(
        _REFERENCE,
        _FOURNISSEUR,
        colonne("prix_catalogue", "texte"),
        colonne("prix_paye", "texte"),
        colonne("date", "date"),
        colonne("rapport", "nombre"),
    ),
)
def prix_eloigne_du_paye(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Le prix du catalogue face au dernier prix payé, tous deux en MAD au cours du jour et au
    kilo : au-delà d'un rapport de 3, une unité ou une devise confondue, une virgule déplacée."""
    parametres = ctx.parametres
    derniers = _derniers_prix(ctx)
    lignes: list[Ligne] = []
    cles: list[float] = []
    for a in ctx.donnees.articles:
        dernier = derniers.get(a.reference)
        if not a.actif or a.prix_kg <= 0 or dernier is None:
            continue
        jour, p = dernier
        paye = p.prix_achat * parametres.taux(p.devise)
        rapport = a.prix_kg * parametres.taux(a.devise) / paye if paye else 0.0
        if rapport > RAPPORT_PRIX_ELOIGNE or (rapport and rapport < 1 / RAPPORT_PRIX_ELOIGNE):
            au_metre = f" ({a.prix_unite:g} {a.devise} / ml)" if a.unite_prix == "ml" else ""
            arrondi = round(rapport, 3)
            cles.append(-max(arrondi, 1 / arrondi) if arrondi else -math.inf)
            lignes.append(
                {
                    "reference": a.reference,
                    "fournisseur": p.fournisseur or a.fournisseur,
                    "prix_catalogue": f"{a.prix_kg:.6g} {a.devise} / kg{au_metre}",
                    "prix_paye": f"{p.prix_achat:g} {p.devise} / kg",
                    "date": jour.isoformat(),
                    "rapport": arrondi,
                }
            )
    ordre = sorted(range(len(lignes)), key=lambda i: cles[i])
    libelle = (
        f"Prix du catalogue à plus de {RAPPORT_PRIX_ELOIGNE:g} fois (ou moins d'un "
        f"{RAPPORT_PRIX_ELOIGNE:g}e) du dernier prix payé"
    )
    return libelle, [lignes[i] for i in ordre]
