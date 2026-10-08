"""Contrôles des achats : commandes en retard, pesées, rupture projetée, poids des bobines
(C06, C08, C13, C30)."""

from __future__ import annotations

from datetime import date, timedelta

from gestion_mp_pro.calcul.achats import echeance_commande, pas_partie, reste_a_livrer
from gestion_mp_pro.calcul.constantes import POUSSIERE
from gestion_mp_pro.calcul.controles.base import Contexte, Ligne, colonne, controle
from gestion_mp_pro.calcul.modele import Commande, Donnees
from gestion_mp_pro.calcul.outils import pourcentage
from gestion_mp_pro.calcul.receptions import evolution_bobines

_REFERENCE = colonne("reference", "texte")


def echeance(donnees: Donnees, commande: Commande) -> date | None:
    """La livraison attendue d'un bon : la même échéance que la liste des commandes et le
    courriel du lundi (ETA, sinon date promise, sinon date du bon + délai du fournisseur)."""
    fournisseur = donnees.fournisseur(commande.fournisseur)
    delai = fournisseur.delai_jours if fournisseur else donnees.parametres.delai_defaut
    return echeance_commande(commande.eta, commande.date_livraison_prevue, commande.date_bc, delai)


def _retard(ctx: Contexte, commande: Commande) -> date | None:
    """L'échéance d'un bon en retard, None s'il ne l'est pas."""
    parametres = ctx.parametres
    if not commande.date_bc or pas_partie(commande):
        return None
    prevue = echeance(ctx.donnees, commande)
    tolere = timedelta(days=parametres.toler_retard_jours)
    if prevue is None or not ctx.date_ref > prevue + tolere:
        return None
    if any(reste_a_livrer(commande, ligne, parametres) > 0 for ligne in commande.lignes):
        return prevue
    return None


@controle(
    "C06",
    gravite="avertissement",
    lien="/commandes?filtre=retard",
    colonnes=(
        colonne("numero", "texte"),
        colonne("fournisseur", "texte"),
        colonne("date_bc", "date"),
        colonne("jours_commande", "j"),
        colonne("echeance", "date"),
        colonne("retard_jours", "j"),
    ),
)
def commande_en_retard(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un bon parti, pas livré, dont l'arrivée attendue est passée (au retard toléré près) ;
    un brouillon ne peut pas être en retard."""
    retards = [(prevue, c) for c in ctx.donnees.commandes if (prevue := _retard(ctx, c))]
    lignes: list[Ligne] = []
    for prevue, c in sorted(retards, key=lambda x: x[0]):
        lignes.append(
            {
                "numero": c.numero,
                "fournisseur": c.fournisseur,
                "date_bc": c.date_bc.isoformat() if c.date_bc else "",
                "jours_commande": (ctx.date_ref - c.date_bc).days if c.date_bc else 0,
                "echeance": prevue.isoformat(),
                "retard_jours": (ctx.date_ref - prevue).days,
            }
        )
    return (
        "Commande non livrée à sa date prévue (ETA, date promise, sinon délai du fournisseur)",
        lignes,
    )


@controle(
    "C08",
    gravite="avertissement",
    lien="/receptions?onglet=pesees",
    colonnes=(
        colonne("reception", "texte"),
        _REFERENCE,
        colonne("attendu", "kg"),
        colonne("pesee", "kg"),
        colonne("ecart", "%"),
    ),
)
def ecart_de_pesee(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """La pesée s'écarte de l'attendu au-delà de la tolérance. Une ligne pas encore pesée
    d'une réception en cours n'est pas un écart : elle attend."""
    tolerance = ctx.parametres.toler_ecart_pesee
    lignes: list[Ligne] = []
    for reception in ctx.donnees.receptions:
        for ligne in reception.lignes:
            if reception.statut != "Validée" and not ligne.quantite_pesee:
                continue
            relatif = ligne.ecart_relatif
            if relatif is not None and abs(relatif) > tolerance:
                lignes.append(
                    {
                        "reception": reception.numero,
                        "reference": ligne.reference,
                        "attendu": ligne.quantite_attendue,
                        "pesee": ligne.quantite_pesee,
                        "ecart": relatif,
                    }
                )
    return f"Écart de pesée supérieur à {pourcentage(tolerance)}", lignes


@controle(
    "C13",
    gravite="avertissement",
    lien="/plan-achat",
    colonnes=(
        _REFERENCE,
        colonne("stock_net", "kg"),
        colonne("stock_projete", "kg"),
        colonne("manque", "kg"),
    ),
)
def rupture_projetee(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Le stock projeté passe sous zéro pendant le délai : la rupture est déjà consommée. Une
    matière que le plan d'achat ne proposera pas (`sans_achat`) n'en est pas une ; les plus
    gros manques d'abord."""
    negatifs = [x for x in ctx.lignes_stock if x.stock_projete < -POUSSIERE and not x.sans_achat]
    negatifs.sort(key=lambda x: x.stock_projete)  # le manque (−projeté) décroissant
    lignes: list[Ligne] = [
        {
            "reference": x.reference,
            "stock_net": x.stock_net,
            "stock_projete": x.stock_projete,
            "manque": -x.stock_projete,
        }
        for x in negatifs
    ]
    return "Stock projeté négatif pendant le délai d'approvisionnement", lignes


@controle(
    "C30",
    gravite="information",
    lien="/receptions?onglet=bobines",
    colonnes=(
        _REFERENCE,
        colonne("fournisseur", "texte"),
        colonne("catalogue", "kg"),
        colonne("constate", "kg"),
        colonne("ecart", "%"),
        colonne("reception", "texte"),
    ),
)
def bobine_eloignee_du_catalogue(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Le poids d'une bobine à sa dernière réception s'écarte du catalogue (qui sert à compter
    le fil monté et à convertir les palettes) ; les plus grands écarts d'abord."""
    decalees = [x for x in evolution_bobines(ctx.donnees) if x.hors_tolerance]
    decalees.sort(key=lambda x: -abs(x.ecart_catalogue or 0.0))
    lignes: list[Ligne] = [
        {
            "reference": x.reference,
            "fournisseur": x.fournisseur,
            "catalogue": x.poids_catalogue,
            "constate": x.dernier,
            "ecart": x.ecart_catalogue,
            "reception": x.historique[-1].reception,
        }
        for x in decalees
    ]
    libelle = (
        "Poids de bobine reçu éloigné du catalogue de plus de "
        f"{pourcentage(ctx.parametres.toler_poids_bobine)}"
    )
    return libelle, lignes
