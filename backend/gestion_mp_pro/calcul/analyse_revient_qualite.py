"""Le coût matière d'une qualité, pondéré par sa recette, au coût de revient réel (CALCULS B
§ 9.13).

Portage de la partie calcul de `gestion_mp/api/analyse_import.py` (`analyse_qualite`) : la
recette dit quels fils entrent dans la qualité et dans quelle proportion ; les dossiers
d'importation disent ce que ces fils ont coûté rendus usine (hors TVA, au kilo, sur la
période). On croise les deux, rôle par rôle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from gestion_mp_pro.calcul.analyse_revient import (
    AnalyseRevient,
    FiltresRevient,
    QualiteInconnue,
    analyse_revient,
)
from gestion_mp_pro.calcul.analyse_revient_lignes import GroupeRevient
from gestion_mp_pro.calcul.constantes import ROLES_LINEAIRES
from gestion_mp_pro.calcul.modele import Donnees, LigneRecette
from gestion_mp_pro.calcul.nomenclature import kg_par_m2

CENT = 100
"""Les parts de la recette sont en pourcents."""


@dataclass
class RoleQualite:
    """Un rôle de la recette : son poids au m² (kg, ou ml pour un rôle au mètre), la part
    dont le coût est connu, et ce qu'elle coûte au m²."""

    role: str
    poids_m2: float
    lineaire: bool
    connu_m2: float = 0.0
    cout_m2: float = 0.0
    fils: int = 0
    importes: int = 0


@dataclass
class AnalyseQualite(AnalyseRevient):
    """L'analyse par référence des fils de la recette, et la synthèse de la qualité (mêmes
    clés que la route `GET /importations/analyse/qualite/{code}`)."""

    qualite: str = ""
    nom: str = ""
    references_de_la_recette: int = 0
    references_importees: int = 0
    roles: list[RoleQualite] = field(default_factory=list)
    poids_m2: float = 0.0
    couverture: float = 0.0
    cout_m2: float = 0.0
    cout_m2_estime: float = 0.0
    cout_kg_tapis: float = 0.0
    roles_sans_cout: list[str] = field(default_factory=list)


def _roles(
    donnees: Donnees, code: str, recettes: list[LigneRecette], couts: dict[str, float]
) -> dict[str, RoleQualite]:
    """Pour chaque rôle, son poids au m² réparti entre ses fils selon la recette, au coût
    hors TVA de chaque fil (kg/m² — ml/m² × densité pour un rôle au mètre — × MAD/kg)."""
    qualite = donnees.qualite(code)
    poids_roles = qualite.poids if qualite else {}
    roles: dict[str, RoleQualite] = {}
    for r in recettes:
        a = donnees.article(r.reference)
        role = a.role_bom if a else ""
        poids_m2 = poids_roles.get(role, 0.0) * r.pourcentage / CENT
        bloc = roles.setdefault(
            role, RoleQualite(role, poids_roles.get(role, 0.0), role in ROLES_LINEAIRES)
        )
        bloc.fils += 1
        if r.reference in couts:
            bloc.importes += 1
            bloc.connu_m2 += poids_m2
            bloc.cout_m2 += (
                kg_par_m2(donnees, code, r.reference, r.pourcentage) * couts[r.reference]
            )
    return roles


def _completer(
    donnees: Donnees, code: str, recettes: list[LigneRecette], ligne: GroupeRevient
) -> None:
    """Une ligne d'analyse reçoit son rôle, sa part de recette, son poids et son coût au m²."""
    qualite = donnees.qualite(code)
    poids_roles = qualite.poids if qualite else {}
    recette = next((r for r in recettes if r.reference == ligne.valeur), None)
    a = donnees.article(ligne.valeur)
    role = a.role_bom if a else ""
    ligne.role = role
    ligne.part_recette = recette.pourcentage if recette else 0.0
    ligne.poids_m2 = poids_roles.get(role, 0.0) * ligne.part_recette / CENT
    ligne.cout_m2 = kg_par_m2(donnees, code, ligne.valeur, ligne.part_recette) * ligne.revient_kg


def analyse_qualite(
    donnees: Donnees,
    code: str,
    *,
    debut: date | None = None,
    fin: date | None = None,
    ids_dossiers: dict[str, int] | None = None,
) -> AnalyseQualite:
    """Ce qu'une qualité a coûté en matière (`analyse_qualite`) ; `QualiteInconnue` pour une
    qualité inconnue ou sans recette.

    Au m² : Σ des coûts connus ; estimé : chaque rôle extrapolé de sa part connue à son poids
    entier ; au kilo de tapis : sur les seuls rôles pesés en kilos dont un fil au moins a été
    importé (les rôles au mètre se comptent au m²).
    """
    recettes = [r for r in donnees.recettes if r.qualite == code]
    if not recettes:
        raise QualiteInconnue(f"qualité inconnue ou sans recette : « {code} »")
    references = {r.reference for r in recettes}
    filtres = FiltresRevient(
        axe="reference", debut=debut, fin=fin, references=";".join(sorted(references))
    )
    analyse = analyse_revient(donnees, filtres, ids_dossiers=ids_dossiers)
    couts = {g.valeur: g.revient_kg for g in analyse.lignes}
    roles = _roles(donnees, code, recettes, couts)
    for ligne in analyse.lignes:
        _completer(donnees, code, recettes, ligne)
    en_kg = [b for b in roles.values() if not b.lineaire]
    poids_total = sum(b.poids_m2 for b in en_kg)
    connu = sum(b.connu_m2 for b in en_kg)
    poids_estime = sum(b.poids_m2 for b in en_kg if b.connu_m2)
    cout_en_kg = sum(b.cout_m2 / b.connu_m2 * b.poids_m2 for b in en_kg if b.connu_m2)
    qualite = donnees.qualite(code)
    return AnalyseQualite(
        **vars(analyse),
        qualite=code,
        nom=qualite.nom if qualite else "",
        references_de_la_recette=len(references),
        references_importees=len(analyse.lignes),
        roles=sorted(roles.values(), key=lambda b: -b.poids_m2),
        poids_m2=poids_total,
        couverture=connu / poids_total if poids_total else 0.0,
        cout_m2=sum(b.cout_m2 for b in roles.values()),
        cout_m2_estime=sum(
            b.cout_m2 / b.connu_m2 * b.poids_m2 for b in roles.values() if b.connu_m2
        ),
        cout_kg_tapis=cout_en_kg / poids_estime if poids_estime else 0.0,
        roles_sans_cout=[b.role for b in roles.values() if not b.connu_m2],
    )
