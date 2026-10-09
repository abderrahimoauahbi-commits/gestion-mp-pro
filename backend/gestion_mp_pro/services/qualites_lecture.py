"""Lectures des qualités : liste et fiche (82, 83), nomenclature (92), versions (88, 91).

Tout chiffre vient du moteur (`calcul.nomenclature`) nourri par le chargeur de S4 : kg/m²,
ml/m² d'un rôle au mètre, coût au m² (kg/m² × prix au kilo × cours × perte), contrôle des
100 % par rôle. Les prix sont rendus à tous ; le filtre générique des routes les met à `null`
pour qui ne les voit pas, et `voit_prix` faux retire en plus l'unité du prix (schéma réduit).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.nomenclature import (
    ControleRecette,
    LigneNomenclature,
    controle_recettes,
    nomenclature,
)
from gestion_mp_pro.modeles import (
    Devise,
    Matiere,
    OrdreQualite,
    PlanVersion,
    PlanVersionSaison,
    Qualite,
    QualitePoids,
    QualiteSaison,
    RecetteVersion,
    RecetteVersionLigne,
    RecetteVersionPoids,
    RoleNomenclature,
    Utilisateur,
)
from gestion_mp_pro.services import donnees_moteur

MOIS = 12


@dataclass
class Contexte:
    """Ce que toutes les lectures partagent : données du moteur, ids, rôles, auteurs."""

    donnees: c.Donnees
    matieres: dict[str, Matiere]
    roles: dict[str, RoleNomenclature]
    roles_par_id: dict[int, RoleNomenclature]
    codes: dict[str, int] = field(default_factory=dict)


def contexte(s: Session) -> Contexte:
    """Les données du moteur (sans journal) et les correspondances référence → id."""
    roles = list(s.scalars(select(RoleNomenclature).order_by(RoleNomenclature.ordre)))
    return Contexte(
        donnees=donnees_moteur.charger(s, avec_journal=False),
        matieres={m.reference: m for m in s.scalars(select(Matiere))},
        roles={r.code: r for r in roles},
        roles_par_id={r.id: r for r in roles},
        codes=dict(s.execute(select(Qualite.code, Qualite.id)).all()),
    )


def facteurs_cout(s: Session, d: c.Donnees) -> dict[str, Any]:
    """De quoi recalculer à la frappe le coût d'une recette, comme le serveur (A19 fondue)."""
    devises = s.scalars(select(Devise.code).order_by(Devise.code))
    return {
        "perte": 1 + d.parametres.taux_perte,
        "cours": {code: d.parametres.taux(code) for code in devises},
    }


def ligne_recette(x: LigneNomenclature, ctx: Contexte, voit_prix: bool) -> dict[str, Any]:
    """Une ligne de nomenclature, avec les identifiants et l'unité de saisie (ml/m²)."""
    m = ctx.matieres.get(x.reference)
    role = ctx.roles.get(x.role_bom)
    lineaire = bool(role and role.lineaire)
    return {
        "qualite_id": ctx.codes.get(x.qualite),
        "qualite": x.qualite,
        "matiere_id": m.id if m else None,
        "reference": x.reference,
        "role_id": role.id if role else None,
        "role": x.role_bom,
        "lineaire": lineaire,
        "nature": x.nature,
        "designation": x.designation,
        "fournisseur": x.fournisseur,
        "pourcentage": x.pourcentage,
        "kg_m2": x.kg_m2,
        "ml_m2": x.ml_m2 if lineaire else None,
        "densite": float(m.densite) if m else 0.0,
        "prix_kg": x.prix_kg,
        "prix": x.prix,
        "unite_prix": x.unite_prix if voit_prix else None,
        "devise_prix": x.devise,
        "cout_m2_mad": x.cout_m2_mad,
    }


def controle(x: ControleRecette | None) -> dict[str, Any]:
    """Le contrôle des 100 % d'une qualité (vide : aucune qualité de ce code au moteur)."""
    if x is None:
        return {"roles_utilises": 0, "roles_conformes": 0, "ecarts": [], "conforme": True}
    rendu = asdict(x)
    rendu.pop("qualite")
    return rendu


def _poids(s: Session, ctx: Contexte) -> dict[int, list[dict[str, Any]]]:
    """Les poids au m² de chaque qualité, dans l'ordre des rôles."""
    rangs = {r.id: i for i, r in enumerate(ctx.roles_par_id.values())}
    resultat: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for p in s.scalars(select(QualitePoids)):
        r = ctx.roles_par_id[p.role_id]
        resultat[p.qualite_id].append(
            {"role_id": r.id, "role": r.code, "lineaire": r.lineaire, "poids": p.poids}
        )
    for liste in resultat.values():
        liste.sort(key=lambda x: rangs[x["role_id"]])
    return resultat


def _saisons(s: Session) -> dict[int, list[float]]:
    """Les douze coefficients de chaque qualité (1 pour un mois sans ligne)."""
    lus: dict[int, dict[int, float]] = defaultdict(dict)
    for q, m, k in s.execute(
        select(QualiteSaison.qualite_id, QualiteSaison.mois, QualiteSaison.coefficient)
    ):
        lus[q][m] = float(k)
    return {q: [mois.get(i, 1.0) for i in range(1, MOIS + 1)] for q, mois in lus.items()}


def lister(s: Session, voit_prix: bool, qualite_id: int | None = None) -> list[dict[str, Any]]:
    """Route 82 (et 83 pour une seule) : chaque qualité, triée par code, avec sa recette
    calculée, son contrôle, son coût au m², ses poids et ses fabrications."""
    ctx = contexte(s)
    lignes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for x in nomenclature(ctx.donnees):
        lignes[x.qualite].append(ligne_recette(x, ctx, voit_prix))
    controles = {x.qualite: x for x in controle_recettes(ctx.donnees)}
    fabrications = dict(
        s.execute(
            select(OrdreQualite.qualite_id, func.count()).group_by(OrdreQualite.qualite_id)
        ).all()
    )
    poids, saisons, facteurs = _poids(s, ctx), _saisons(s), facteurs_cout(s, ctx.donnees)
    requete = select(Qualite).order_by(Qualite.code)
    if qualite_id is not None:
        requete = requete.where(Qualite.id == qualite_id)
    resultat = []
    for q in s.scalars(requete):
        recette = lignes.get(q.code, [])
        resultat.append(
            {
                "id": q.id, "code": q.code, "nom": q.nom, "actif": q.actif,
                "version": q.version, "base_mensuelle": q.base_mensuelle,
                "saisonnalite": saisons.get(q.id, [1.0] * MOIS),
                "poids": poids.get(q.id, []), "recette": recette,
                "controle": controle(controles.get(q.code)),
                "kg_m2": sum(x["kg_m2"] for x in recette),
                "cout_m2_mad": sum(x["cout_m2_mad"] for x in recette),
                "fabrications": fabrications.get(q.id, 0),
                "facteurs_cout": facteurs,
            }
        )  # fmt: skip
    return resultat


def fiche(s: Session, qualite_id: int, voit_prix: bool) -> dict[str, Any]:
    """Route 83 : une qualité (404 « Qualité introuvable. »)."""
    trouvees = lister(s, voit_prix, qualite_id)
    if not trouvees:
        raise Refus.introuvable("Qualité introuvable.")
    return trouvees[0]


def lire_nomenclature(s: Session, voit_prix: bool) -> dict[str, Any]:
    """Route 92 : chaque ligne de chaque recette, et le contrôle des 100 % par qualité."""
    ctx = contexte(s)
    actives = dict(s.execute(select(Qualite.code, Qualite.actif)).all())
    controles = []
    for x in controle_recettes(ctx.donnees):
        controles.append(
            {"qualite_id": ctx.codes.get(x.qualite), "qualite": x.qualite,
             "actif": actives.get(x.qualite, True), **controle(x)}
        )  # fmt: skip
    return {
        "lignes": [ligne_recette(x, ctx, voit_prix) for x in nomenclature(ctx.donnees)],
        "controle": controles,
    }


def _personnes(s: Session, ids: set[int | None]) -> dict[int, dict[str, Any]]:
    """Les auteurs cités : {id : {id, nom, role}}."""
    voulus = [i for i in ids if i is not None]
    if not voulus:
        return {}
    requete = select(Utilisateur).where(Utilisateur.id.in_(voulus))
    return {u.id: {"id": u.id, "nom": u.nom, "role": u.role} for u in s.scalars(requete)}


def _existe(s: Session, qualite_id: int) -> None:
    """404 si la qualité n'existe pas."""
    if s.get(Qualite, qualite_id) is None:
        raise Refus.introuvable("Qualité introuvable.")


def versions_recette(s: Session, qualite_id: int) -> list[dict[str, Any]]:
    """Route 88 : les versions de la recette, de la plus récente à la plus ancienne."""
    _existe(s, qualite_id)
    versions = list(
        s.scalars(
            select(RecetteVersion)
            .where(RecetteVersion.qualite_id == qualite_id)
            .order_by(RecetteVersion.numero.desc())
        )
    )
    ids = [v.id for v in versions]
    roles = {r.id: r.code for r in s.scalars(select(RoleNomenclature))}
    references = dict(s.execute(select(Matiere.id, Matiere.reference)).all())
    lignes: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for x in s.scalars(select(RecetteVersionLigne).where(RecetteVersionLigne.version_id.in_(ids))):
        lignes[x.version_id].append(
            {"matiere_id": x.matiere_id, "reference": references[x.matiere_id],
             "role_id": x.role_id, "role": roles[x.role_id], "pourcentage": x.pourcentage}
        )  # fmt: skip
    poids: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for p in s.scalars(select(RecetteVersionPoids).where(RecetteVersionPoids.version_id.in_(ids))):
        poids[p.version_id].append(
            {"role_id": p.role_id, "role": roles[p.role_id], "poids": p.poids}
        )
    numeros = {v.id: v.numero for v in versions}
    auteurs = _personnes(s, {v.par_id for v in versions})
    return [
        {
            "id": v.id, "numero": v.numero, "valide_depuis": v.valide_depuis,
            "par": auteurs.get(v.par_id) if v.par_id else None,
            "origine": v.origine, "motif": v.motif,
            "restauree_de": numeros.get(v.restauree_de_id) if v.restauree_de_id else None,
            "en_vigueur": i == 0,
            "lignes": sorted(lignes.get(v.id, []), key=lambda x: (x["role"], x["reference"])),
            "poids": sorted(poids.get(v.id, []), key=lambda x: x["role"]) if v.poids_connus
            else None,
        }
        for i, v in enumerate(versions)
    ]  # fmt: skip


def versions_plan(s: Session, qualite_id: int) -> list[dict[str, Any]]:
    """Route 91 : les versions du plan, de la plus récente à la plus ancienne (la plus
    ancienne est le plan « d'avant », en vigueur depuis toujours)."""
    _existe(s, qualite_id)
    versions = list(
        s.scalars(
            select(PlanVersion)
            .where(PlanVersion.qualite_id == qualite_id)
            .order_by(PlanVersion.valide_depuis.desc(), PlanVersion.id.desc())
        )
    )
    coefficients: dict[int, dict[int, float]] = defaultdict(dict)
    for x in s.scalars(
        select(PlanVersionSaison).where(PlanVersionSaison.version_id.in_([v.id for v in versions]))
    ):
        coefficients[x.version_id][x.mois] = float(x.coefficient)
    auteurs = _personnes(s, {v.par_id for v in versions})
    return [
        {
            "id": v.id, "valide_depuis": v.valide_depuis, "base_mensuelle": v.base_mensuelle,
            "saisonnalite": [coefficients[v.id].get(m, 1.0) for m in range(1, MOIS + 1)],
            "en_service": v.en_service, "par": auteurs.get(v.par_id) if v.par_id else None,
            "origine": v.origine, "motif": v.motif, "en_vigueur": i == 0,
            "depuis_toujours": i == len(versions) - 1,
        }
        for i, v in enumerate(versions)
    ]  # fmt: skip
