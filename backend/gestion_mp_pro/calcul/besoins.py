"""Besoins (MRP) : le plan × les recettes, aujourd'hui et à l'époque (CALCULS A § 3.6-3.7).

Portage de `moteur.besoins_mensuels`, `versions_recette_pendant`, `kg_m2_version`,
`besoins_passes`, `besoin_sur_fenetre`, `fils_remplaces`, `sortis_des_recettes`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import date, datetime, time

from gestion_mp_pro.calcul.constantes import EGALITE_RELATIVE, JOURS_PAR_MOIS, MOIS
from gestion_mp_pro.calcul.modele import Donnees, Qualite, VersionRecette
from gestion_mp_pro.calcul.nomenclature import kg_par_m2
from gestion_mp_pro.calcul.outils import debut_de_mois
from gestion_mp_pro.calcul.plan import m2_passe, plan_mensuel

CacheRecette = dict[tuple[str, int], dict[str, float]]
"""(qualité, id de la version) → kg/m² par référence."""


def besoins_mensuels(donnees: Donnees, date_ref: date) -> dict[str, list[float]]:
    """Besoin en kg par référence et par mois du plan (`Production_Besoins!U6#`) :
    (1 + taux de perte) × Σ_recettes kg/m² × m²(qualité du mois)."""
    plan = plan_mensuel(donnees, date_ref)
    perte = 1 + donnees.parametres.taux_perte
    besoins: dict[str, list[float]] = defaultdict(lambda: [0.0] * MOIS)
    for recette in donnees.recettes:
        if not recette.reference:
            continue
        m2 = plan.get(recette.qualite)
        if m2 is None:
            besoins[recette.reference]  # la référence existe, sans besoin
            continue
        kg = kg_par_m2(donnees, recette.qualite, recette.reference, recette.pourcentage)
        if not kg:
            besoins[recette.reference]
            continue
        cumul = besoins[recette.reference]
        for i in range(MOIS):
            cumul[i] += kg * m2[i]
    return {ref: [v * perte for v in valeurs] for ref, valeurs in besoins.items()}


def versions_recette_pendant(
    donnees: Donnees, qualite: str, debut: datetime, fin: datetime
) -> list[VersionRecette | None]:
    """Les versions de la recette en vigueur entre `debut` et `fin`, dans l'ordre ; avant la
    première connue, c'est elle qui vaut ; `[None]` sans histoire (la recette d'aujourd'hui)."""
    versions = donnees.versions_recette.get(qualite)
    if not versions:
        return [None]
    en_vigueur: list[VersionRecette | None] = [versions[0]]
    for version in versions:
        if version.quand <= debut:
            en_vigueur = [version]
        elif version.quand <= fin:
            en_vigueur.append(version)
    return en_vigueur


def _poids_de_la_version(
    donnees: Donnees, qualite: str, version: VersionRecette
) -> dict[str, float]:
    """Les poids au m² de la version ; à défaut ceux de la version suivante qui les a, à
    défaut ceux d'aujourd'hui."""
    poids = version.poids
    if poids is None:
        suivantes = donnees.versions_recette.get(qualite, [])
        rang = next((i for i, v in enumerate(suivantes) if v is version), len(suivantes))
        poids = next((v.poids for v in suivantes[rang + 1 :] if v.poids is not None), None)
    if poids is None:
        fiche = donnees.qualite(qualite)
        poids = fiche.poids if fiche else {}
    return poids


def kg_m2_version(
    donnees: Donnees,
    qualite: str,
    version: VersionRecette | None,
    cache: CacheRecette | None = None,
) -> dict[str, float]:
    """Ce qu'un m² demande de chaque référence selon une version de la recette, en kilos."""
    cle = (qualite, id(version))
    if cache is not None and cle in cache:
        return cache[cle]
    kg: dict[str, float] = defaultdict(float)
    if version is None:
        for recette in donnees.recettes:
            if recette.qualite == qualite and recette.reference:
                kg[recette.reference] += kg_par_m2(
                    donnees, qualite, recette.reference, recette.pourcentage
                )
    else:
        poids = _poids_de_la_version(donnees, qualite, version)
        fiche = donnees.qualite(qualite)
        figee = replace(
            donnees,
            qualites=[Qualite(code=qualite, nom=fiche.nom if fiche else "", poids=dict(poids))],
        )
        for reference, pourcentage in version.lignes:
            if reference:
                kg[reference] += kg_par_m2(figee, qualite, reference, pourcentage)
    resultat = {ref: valeur for ref, valeur in kg.items() if valeur}
    if cache is not None:
        cache[cle] = resultat
    return resultat


def besoins_passes(
    donnees: Donnees, fins: list[date]
) -> tuple[dict[str, list[float]], dict[str, list[bool]]]:
    """Ce que le plan et les recettes de l'époque demandaient, mois clos par mois clos (perte
    comprise), et les mois où la recette de chaque fil n'a pas changé (seuls à le juger)."""
    perte = 1 + donnees.parametres.taux_perte
    n = len(fins)
    prevus: dict[str, list[float]] = defaultdict(lambda: [0.0] * n)
    stables: dict[str, list[bool]] = defaultdict(lambda: [True] * n)
    cache: CacheRecette = {}
    for ligne in donnees.plan:
        for i, fin in enumerate(fins):
            debut = datetime.combine(debut_de_mois(fin), time.min)
            versions = versions_recette_pendant(
                donnees, ligne.qualite, debut, datetime.combine(fin, time.max)
            )
            kgs = [kg_m2_version(donnees, ligne.qualite, v, cache) for v in versions]
            m2 = m2_passe(donnees, ligne, fin)
            for reference in set[str]().union(*kgs):
                valeurs = [k.get(reference, 0.0) for k in kgs]
                if max(valeurs) - min(valeurs) > EGALITE_RELATIVE * max(1.0, *valeurs):
                    stables[reference][i] = False
                prevus[reference][i] += valeurs[-1] * m2 * perte
    return dict(prevus), dict(stables)


def _segments(
    besoins: list[float],
    fin_jours: float,
    jours_restants_du_mois: float | None,
    jours_du_mois: float | None,
    prolonger: bool,
) -> list[tuple[float, float]]:
    """La courbe de demande en segments (durée en jours, quantité sur le segment)."""
    segments: list[tuple[float, float]] = []
    for rang, besoin in enumerate(besoins, start=1):
        if rang == 1 and jours_restants_du_mois is not None:
            longueur = jours_du_mois or JOURS_PAR_MOIS
            duree = max(0.0, min(longueur, jours_restants_du_mois))
            segments.append((duree, besoin * duree / longueur))
        else:
            segments.append((float(JOURS_PAR_MOIS), besoin))
    if prolonger and besoins:
        couvert = sum(duree for duree, _ in segments)
        rang = 0
        while couvert < fin_jours:
            segments.append((float(JOURS_PAR_MOIS), besoins[rang % len(besoins)]))
            couvert += JOURS_PAR_MOIS
            rang += 1
    return segments


def besoin_sur_fenetre(
    besoins: list[float],
    debut_jours: float,
    fin_jours: float,
    jours_restants_du_mois: float | None = None,
    *,
    jours_du_mois: float | None = None,
    prolonger: bool = False,
) -> float:
    """Demande sur la fenêtre [début ; fin] en jours, mois de 30 jours (`Stock!G10`, `H10`).

    `jours_restants_du_mois` proratise le mois en cours sur sa vraie longueur
    (`jours_du_mois`) ; `prolonger` voit au-delà des douze mois l'année suivante comme
    celle-ci (D-14).
    """
    total = 0.0
    curseur = 0.0
    for duree, quantite in _segments(
        besoins, fin_jours, jours_restants_du_mois, jours_du_mois, prolonger
    ):
        if duree <= 0:
            continue
        bas = max(curseur, debut_jours)
        haut = min(curseur + duree, fin_jours)
        if haut > bas:
            total += quantite * (haut - bas) / duree
        curseur += duree
    return total


def fils_remplaces(
    donnees: Donnees, debut: datetime, fin: datetime
) -> dict[tuple[str, str], list[str]]:
    """Qui remplace qui dans les recettes entre `debut` et `fin` : {(qualité, entrant):
    sortants du même rôle}."""
    roles = {a.reference: a.role_bom for a in donnees.articles}
    actuelles: dict[str, set[str]] = defaultdict(set)
    for recette in donnees.recettes:
        if recette.reference and recette.pourcentage > 0:
            actuelles[recette.qualite].add(recette.reference)
    resultat: dict[tuple[str, str], list[str]] = {}
    for qualite, aujourd_hui in actuelles.items():
        versions = [v for v in versions_recette_pendant(donnees, qualite, debut, fin) if v]
        if not versions:
            continue
        au_debut = {ref for ref, part in versions[0].lignes if ref and part > 0}
        vus = {ref for v in versions for ref, part in v.lignes if ref and part > 0}
        sortants = vus - aujourd_hui
        for entrant in aujourd_hui - au_debut:
            memes = sorted(x for x in sortants if roles.get(x) == roles.get(entrant))
            if memes:
                resultat[(qualite, entrant)] = memes
    return resultat


def sortis_des_recettes(donnees: Donnees, debut: datetime, fin: datetime) -> set[str]:
    """Les fils qu'une recette contenait entre `debut` et `fin` et qu'aucune ne contient plus."""
    vus: set[str] = set()
    for qualite in donnees.versions_recette:
        for version in versions_recette_pendant(donnees, qualite, debut, fin):
            if version:
                vus |= {ref for ref, part in version.lignes if ref and part > 0}
    return vus - {r.reference for r in donnees.recettes if r.reference and r.pourcentage > 0}
