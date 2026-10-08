"""Nomenclature : ce qu'un m² de chaque qualité demande de chaque matière (CALCULS § 3.5).

Portage de `moteur.metres_du_role`, `poids_du_role`, `kg_par_m2`, `nomenclature`,
`controle_recettes`. Le poids d'un rôle au mètre (cuir, franges, ruban) est saisi en ml/m²
et ramené en kg/m² par la densité de la matière (kg/ml).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gestion_mp_pro.calcul.constantes import ROLES_LINEAIRES, TOLERANCE_RECETTE
from gestion_mp_pro.calcul.modele import Article, Donnees, LigneRecette

CENT = 100


def metres_du_role(donnees: Donnees, qualite: str, article: Article) -> float:
    """Les ml qu'un m² de la qualité demande au rôle de l'article (0 pour un rôle au poids)."""
    if article.role_bom not in ROLES_LINEAIRES:
        return 0.0
    fiche = donnees.qualite(qualite)
    return (fiche.poids.get(article.role_bom, 0.0) or 0.0) if fiche else 0.0


def poids_du_role(donnees: Donnees, qualite: str, article: Article) -> float:
    """Poids du rôle de l'article pour un m² de la qualité, en kg (`Recettes!M5`)."""
    fiche = donnees.qualite(qualite)
    if fiche is None:
        return 0.0
    valeur = fiche.poids.get(article.role_bom, 0.0) or 0.0
    if article.role_bom in ROLES_LINEAIRES:
        valeur *= article.densite or 0.0
    return valeur


def kg_par_m2(donnees: Donnees, qualite: str, reference: str, pourcentage: float) -> float:
    """`Recettes!F5` : % composition / 100 × poids du rôle, en kilos."""
    article = donnees.article(reference)
    if article is None:
        return 0.0
    return pourcentage / CENT * poids_du_role(donnees, qualite, article)


@dataclass
class LigneNomenclature:
    """Une ligne de la feuille 🧵 Recettes, colonnes calculées comprises."""

    qualite: str
    reference: str
    pourcentage: float
    role_bom: str
    nature: str
    designation: str
    fournisseur: str
    kg_m2: float
    prix_kg: float
    devise: str
    cout_m2_mad: float
    poids_categorie: float
    ml_m2: float = 0.0
    prix: float = 0.0
    unite_prix: str = "kg"


def _ligne_sans_article(recette: LigneRecette) -> LigneNomenclature:
    return LigneNomenclature(
        qualite=recette.qualite,
        reference=recette.reference,
        pourcentage=recette.pourcentage,
        role_bom="",
        nature="",
        designation="",
        fournisseur="",
        kg_m2=0.0,
        prix_kg=0.0,
        devise="",
        cout_m2_mad=0.0,
        poids_categorie=0.0,
    )


def _ligne(donnees: Donnees, recette: LigneRecette, article: Article) -> LigneNomenclature:
    perte = 1 + donnees.parametres.taux_perte
    devise = donnees.devise_article(article)
    poids = poids_du_role(donnees, recette.qualite, article)
    kg = recette.pourcentage / CENT * poids
    prix = article.prix_kg
    return LigneNomenclature(
        qualite=recette.qualite,
        reference=recette.reference,
        pourcentage=recette.pourcentage,
        role_bom=article.role_bom,
        nature=article.nature,
        designation=article.designation,
        fournisseur=article.fournisseur,
        kg_m2=kg,
        prix_kg=prix,
        devise=devise,
        # Les quantités achetées sont majorées du taux de perte : le coût aussi.
        cout_m2_mad=kg * prix * donnees.parametres.taux(devise) * perte,
        poids_categorie=poids,
        ml_m2=recette.pourcentage / CENT * metres_du_role(donnees, recette.qualite, article),
        prix=article.prix_unite,
        unite_prix=article.unite_prix,
    )


def nomenclature(donnees: Donnees) -> list[LigneNomenclature]:
    """La feuille 🧵 Recettes, une ligne par ligne de recette."""
    lignes: list[LigneNomenclature] = []
    for recette in donnees.recettes:
        article = donnees.article(recette.reference)
        if article is None:
            lignes.append(_ligne_sans_article(recette))
        else:
            lignes.append(_ligne(donnees, recette, article))
    return lignes


@dataclass
class EcartRole:
    """Un rôle de la recette dont les parts ne font pas 100 %."""

    role: str
    somme: float


@dataclass
class ControleRecette:
    """Le contrôle d'une qualité : rôles utilisés, conformes, et les écarts."""

    qualite: str
    roles_utilises: int
    roles_conformes: int
    ecarts: list[EcartRole] = field(default_factory=list)
    conforme: bool = True


def _somme_du_role(donnees: Donnees, qualite: str, role: str) -> float:
    return sum(
        r.pourcentage
        for r in donnees.recettes
        if r.qualite == qualite
        and (a := donnees.article(r.reference)) is not None
        and a.role_bom == role
    )


def controle_recettes(donnees: Donnees) -> list[ControleRecette]:
    """`Recettes!O6:R26` : la somme des % vaut 100 (à 0,01 point) dans chaque rôle utilisé."""
    resultats = []
    for qualite in donnees.qualites:
        ecarts = []
        total_roles = 0
        for role, poids in qualite.poids.items():
            if not poids:
                continue
            total_roles += 1
            somme = _somme_du_role(donnees, qualite.code, role)
            if abs(somme - CENT) > TOLERANCE_RECETTE:
                ecarts.append(EcartRole(role=role, somme=somme))
        resultats.append(
            ControleRecette(
                qualite=qualite.code,
                roles_utilises=total_roles,
                roles_conformes=total_roles - len(ecarts),
                ecarts=ecarts,
                conforme=not ecarts,
            )
        )
    return resultats
