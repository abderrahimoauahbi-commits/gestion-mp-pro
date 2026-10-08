"""Qualités, recettes, plan et leurs versions, pour le moteur (CALCULS A § 4.5, § 4.6).

`plan_version` remplace le journal « plan de production » de Gestion MP : la **première**
version d'une qualité est le plan « d'avant » (en vigueur depuis toujours), chacune des
suivantes un changement daté. Une seule version, ou aucune, c'est un plan sans histoire. La
traduction passe par `calcul.chargement.versions_du_plan` et `arret_sans_histoire`, comme
Gestion MP : seule une nouvelle base déplace l'origine de la croissance.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.chargement import arret_sans_histoire, versions_du_plan
from gestion_mp_pro.modeles import (
    Mouvement,
    Ordre,
    OrdreQualite,
    PlanVersion,
    PlanVersionSaison,
    Qualite,
    QualitePoids,
    QualiteSaison,
    Recette,
    RecetteVersion,
    RecetteVersionLigne,
    RecetteVersionPoids,
)
from gestion_mp_pro.modeles.enums import StatutOrdre
from gestion_mp_pro.services.chargeur.contexte import Noms, heure_usine, nombre

MOIS = range(1, 13)

PlanBrut = dict[str, object]
"""Un plan comme le journal de Gestion MP l'écrivait : {b: base, c: 12 coefficients, a: actif}."""


@dataclass
class Qualites:
    """Ce que le chargeur rend pour les qualités."""

    qualites: list[c.Qualite]
    plan: list[c.PlanQualite]
    recettes: list[c.LigneRecette]
    versions_plan: dict[str, list[c.VersionPlan]]
    versions_recette: dict[str, list[c.VersionRecette]]


def _par_mois(lignes: list[tuple[int, int, float]]) -> dict[int, list[float]]:
    """{objet : douze coefficients} (1,0 pour un mois absent)."""
    mois: dict[int, dict[int, float]] = defaultdict(dict)
    for objet, m, coefficient in lignes:
        mois[objet][m] = coefficient
    return {objet: [valeurs.get(m, 1.0) for m in MOIS] for objet, valeurs in mois.items()}


def _plans_bruts(s: Session) -> dict[int, list[tuple[datetime, PlanBrut]]]:
    """Les versions du plan de chaque qualité, dans l'ordre : (depuis quand, plan)."""
    saisons = _par_mois(
        [
            (v, m, float(k))
            for v, m, k in s.execute(
                select(
                    PlanVersionSaison.version_id,
                    PlanVersionSaison.mois,
                    PlanVersionSaison.coefficient,
                )
            )
        ]
    )
    resultat: dict[int, list[tuple[datetime, PlanBrut]]] = defaultdict(list)
    requete = select(PlanVersion).order_by(
        PlanVersion.qualite_id, PlanVersion.valide_depuis, PlanVersion.id
    )
    for v in s.scalars(requete):
        plan: PlanBrut = {
            "b": float(v.base_mensuelle),
            "c": saisons.get(v.id, [1.0] * 12),
            "a": v.en_service,
        }
        resultat[v.qualite_id].append((heure_usine(v.valide_depuis), plan))
    return resultat


def _versions(brut: list[tuple[datetime, PlanBrut]], ouverture: date | None) -> list[c.VersionPlan]:
    """La première version est le plan d'avant ; chaque suivante, un changement."""
    changements = [(quand, brut[i - 1][1], plan) for i, (quand, plan) in enumerate(brut) if i > 0]
    return versions_du_plan(changements, ouverture)


def _derniers_tissages(s: Session) -> dict[int, date]:
    """Par qualité, la date du dernier ordre validé qui l'a fabriquée."""
    requete = (
        select(OrdreQualite.qualite_id, func.max(Ordre.date))
        .join(Ordre, Ordre.id == OrdreQualite.ordre_id)
        .where(Ordre.statut == StatutOrdre.valide)
        .group_by(OrdreQualite.qualite_id)
    )
    return dict(s.execute(requete).all())


def _plan_de(
    q: Qualite,
    saisons: list[float],
    versions: list[c.VersionPlan],
    dernier: date | None,
    ouverture: date | None,
) -> tuple[c.PlanQualite, list[c.VersionPlan]]:
    """Le plan courant d'une qualité et son histoire (une arrêtée garde sa base)."""
    if not versions and not q.actif:
        versions = [
            c.VersionPlan(
                quand=None,
                base_mensuelle=float(q.base_mensuelle),
                saisonnalite=saisons,
                actif=False,
                depuis=ouverture,
            )
        ]
    if versions and not versions[0].actif:
        versions = arret_sans_histoire(versions, dernier)
    plan = c.PlanQualite(
        qualite=q.code,
        base_mensuelle=float(q.base_mensuelle),
        saisonnalite=saisons,
        actif=q.actif,
        depuis=versions[-1].depuis if versions else ouverture,
    )
    return plan, versions


def _recettes_passees(
    s: Session, noms: Noms, codes: dict[int, str]
) -> dict[str, list[c.VersionRecette]]:
    """Les versions de recette, par qualité, dans l'ordre (poids `None` s'ils sont inconnus)."""
    lignes: dict[int, list[tuple[str, float]]] = defaultdict(list)
    for vid, m, p in s.execute(
        select(
            RecetteVersionLigne.version_id,
            RecetteVersionLigne.matiere_id,
            RecetteVersionLigne.pourcentage,
        ).order_by(RecetteVersionLigne.version_id, RecetteVersionLigne.matiere_id)
    ):
        lignes[vid].append((noms.references[m], float(p)))
    poids: dict[int, dict[str, float]] = defaultdict(dict)
    requete = select(
        RecetteVersionPoids.version_id, RecetteVersionPoids.role_id, RecetteVersionPoids.poids
    ).order_by(RecetteVersionPoids.version_id, RecetteVersionPoids.role_id)
    for vid, role, kg in s.execute(requete):
        poids[vid][noms.roles[role]] = float(kg)
    resultat: dict[str, list[c.VersionRecette]] = defaultdict(list)
    versions = select(RecetteVersion).order_by(RecetteVersion.valide_depuis, RecetteVersion.id)
    for v in s.scalars(versions):
        if v.qualite_id not in codes:
            continue
        resultat[codes[v.qualite_id]].append(
            c.VersionRecette(
                quand=heure_usine(v.valide_depuis),
                lignes=lignes.get(v.id, []),
                poids=dict(poids.get(v.id, {})) if v.poids_connus else None,
            )
        )
    return dict(resultat)


def qualites(s: Session, noms: Noms) -> Qualites:
    """Qualités (par code), plan courant et passé, recettes et leurs versions."""
    ouverture = s.scalar(select(func.min(Mouvement.date_effet)))
    poids: dict[int, dict[str, float]] = defaultdict(dict)
    for qid, role, kg in s.execute(
        select(QualitePoids.qualite_id, QualitePoids.role_id, QualitePoids.poids).order_by(
            QualitePoids.qualite_id, QualitePoids.role_id
        )
    ):
        poids[qid][noms.roles[role]] = float(kg)
    saisons = _par_mois(
        [
            (qid, m, float(k))
            for qid, m, k in s.execute(
                select(QualiteSaison.qualite_id, QualiteSaison.mois, QualiteSaison.coefficient)
            )
        ]
    )
    bruts, derniers = _plans_bruts(s), _derniers_tissages(s)
    resultat = Qualites([], [], [], {}, {})
    codes: dict[int, str] = {}
    for q in s.scalars(select(Qualite).order_by(Qualite.code)):
        codes[q.id] = q.code
        resultat.qualites.append(c.Qualite(code=q.code, nom=q.nom, poids=dict(poids.get(q.id, {}))))
        plan, versions = _plan_de(
            q,
            saisons.get(q.id, [1.0] * 12),
            _versions(bruts.get(q.id, []), ouverture),
            derniers.get(q.id),
            ouverture,
        )
        resultat.plan.append(plan)
        if versions:
            resultat.versions_plan[q.code] = versions
    resultat.versions_recette = _recettes_passees(s, noms, codes)
    resultat.recettes = [
        c.LigneRecette(
            qualite=codes[r.qualite_id],
            reference=noms.references[r.matiere_id],
            pourcentage=nombre(r.pourcentage),
        )
        for r in s.scalars(select(Recette).order_by(Recette.qualite_id, Recette.matiere_id))
    ]
    return resultat
