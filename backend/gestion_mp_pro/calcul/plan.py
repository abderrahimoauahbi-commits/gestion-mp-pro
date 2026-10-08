"""Plan de production : m² du mois, plan glissant, plan de l'époque (CALCULS A § 3.4).

Portage de `moteur.m2_du_mois`, `plan_mensuel`, `plan_en_vigueur`, `m2_passe`. Le plan
glissant compte douze mois (M0 = mois de la date de référence) ; un mois passé se juge sur le
plan **de son époque**, au prorata des jours de chaque version.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from gestion_mp_pro.calcul.constantes import CROISSANCE_MINIMUM, MOIS
from gestion_mp_pro.calcul.modele import Donnees, PlanQualite, VersionPlan
from gestion_mp_pro.calcul.outils import arrondi, debut_de_mois, mois_du_plan, mois_entre


def m2_du_mois(
    donnees: Donnees, base: float, saisonnalite: list[float], fin: date, ancre: date
) -> float:
    """ARRONDI(base × saisonnalité[mois] × (1 + croissance)^(mois depuis l'ancre / 12) ; 0).

    L'ancre est le jour où la base a été saisie : un mois a la même prévision quel que soit
    le mois d'où on le regarde. La croissance est ramenée à −90 % au plus bas.
    """
    coefficient = saisonnalite[fin.month - 1] if saisonnalite else 1.0
    croissance = max(donnees.parametres.croissance_annuelle, CROISSANCE_MINIMUM)
    return arrondi(base * coefficient * (1 + croissance) ** (mois_entre(ancre, fin) / 12))


def plan_mensuel(donnees: Donnees, date_ref: date) -> dict[str, list[float]]:
    """m² par qualité et par mois du plan glissant (`Production_Plan!C26`) ; une qualité
    arrêtée ne compte plus pour les mois à venir."""
    mois = mois_du_plan(date_ref)
    resultat: dict[str, list[float]] = {}
    for ligne in donnees.plan:
        if not ligne.actif:
            resultat[ligne.qualite] = [0.0] * MOIS
            continue
        resultat[ligne.qualite] = [
            m2_du_mois(
                donnees, ligne.base_mensuelle, ligne.saisonnalite, fin, ligne.depuis or date_ref
            )
            for fin in mois
        ]
    return resultat


def plan_en_vigueur(donnees: Donnees, ligne: PlanQualite, fin: date) -> VersionPlan:
    """Le plan d'une qualité le dernier jour du mois `fin` : le dernier changement avant la
    fin du mois ; avant tout changement, le plan d'avant le premier ; sans histoire, le plan
    d'aujourd'hui (en service : le passé garde sa base)."""
    versions = donnees.versions_plan.get(ligne.qualite)
    if not versions:
        return VersionPlan(
            quand=None,
            base_mensuelle=ligne.base_mensuelle,
            saisonnalite=ligne.saisonnalite,
            actif=True,
            depuis=ligne.depuis,
        )
    limite = datetime.combine(fin, time.max)
    retenue = versions[0]
    for version in versions:
        if version.quand is not None and version.quand <= limite:
            retenue = version
    return retenue


def _m2_version(donnees: Donnees, version: VersionPlan, fin: date) -> float:
    return m2_du_mois(
        donnees, version.base_mensuelle, version.saisonnalite, fin, version.depuis or fin
    )


def m2_passe(donnees: Donnees, ligne: PlanQualite, fin: date, jusqu_a: date | None = None) -> float:
    """Les m² que le plan de l'époque prévoyait pour le mois `fin`, chaque version au prorata
    de sa durée en vigueur dans le mois ; `jusqu_a` : le mois vu à cette date (les jours qui
    suivent ne comptent pas)."""
    versions = donnees.versions_plan.get(ligne.qualite)
    if not versions:
        version = plan_en_vigueur(donnees, ligne, fin)
        return _m2_version(donnees, version, fin) if version.actif else 0.0
    debut = datetime.combine(debut_de_mois(fin), time.min)
    borne = min(fin, jusqu_a) if jusqu_a is not None else fin
    limite = datetime.combine(borne + timedelta(days=1), time.min)
    if limite <= debut:
        return 0.0
    en_vigueur, changements = versions[0], []
    for version in versions:
        if version.quand is None or version.quand <= debut:
            en_vigueur = version
        elif version.quand < limite:
            changements.append(version)
    instants = [debut, *(v.quand for v in changements if v.quand is not None), limite]
    duree = (limite - debut).total_seconds()
    total = 0.0
    for version, de, a in zip([en_vigueur, *changements], instants, instants[1:], strict=False):
        if version.actif and a > de:
            total += _m2_version(donnees, version, fin) * (a - de).total_seconds() / duree
    return total
