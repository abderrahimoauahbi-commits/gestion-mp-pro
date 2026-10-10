"""Lectures des métiers : liste et fiche (94, 95), historique des montages (101), matières
montables (102), classeur (238) (REGLES A § 1.11 : R-REF-80, R-REF-83, R-REF-84).

Le poids de chaque fil est celui que compte le stock « sur les métiers » (le même chiffre
partout, F18) ; sa valeur (poids × coût moyen pondéré) n'est calculée que pour qui voit les
prix. Les métiers sont rangés par nom puis code (le même ordre partout où l'on en choisit un).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul.valorisation import cmup_par_reference
from gestion_mp_pro.modeles import (
    Fournisseur,
    Matiere,
    Metier,
    MetierEtage,
    Montage,
    MontageEvenement,
    Ordre,
    RoleNomenclature,
    Utilisateur,
)
from gestion_mp_pro.services import donnees_moteur
from gestion_mp_pro.services import montage as mt
from gestion_mp_pro.services.montage import Bobine, Fil, Reglage


@dataclass
class Contexte:
    """Ce que la lecture de tous les métiers partage."""

    matieres: dict[int, Matiere]
    fournisseurs: dict[int, str]
    poids: dict[int, Bobine]
    tolerance: float
    couts: dict[str, float]
    ordres: dict[int, int]
    personnes: dict[int, str]


def contexte(s: Session, voit_prix: bool) -> Contexte:
    """Matières, poids de bobine retenus, tolérance, coûts moyens (pour qui voit les prix)."""
    matieres = {m.id: m for m in s.scalars(select(Matiere))}
    monte = s.scalar(select(func.count()).select_from(Montage))
    couts = cmup_par_reference(donnees_moteur.charger(s)) if voit_prix and monte else {}
    return Contexte(
        matieres=matieres,
        fournisseurs=dict(s.execute(select(Fournisseur.id, Fournisseur.nom)).all()),
        poids=mt.bobines(s, matieres.values()),
        tolerance=donnees_moteur.parametres(s).toler_poids_bobine,
        couts=couts,
        ordres={
            metier: n
            for metier, n in s.execute(
                select(Ordre.metier_id, func.count())
                .where(Ordre.metier_id.is_not(None))
                .group_by(Ordre.metier_id)
            )
            if metier is not None
        },
        personnes=dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).all()),
    )


def _fil(f: Fil, ident: int, r: Reglage, ctx: Contexte) -> dict[str, Any]:
    """Un fil monté : bobines, poids, poids de bobine (catalogue, retenu, source), écart."""
    m = ctx.matieres[f.matiere_id]
    bobine = ctx.poids[f.matiere_id]
    mesure = bobine.source not in {"catalogue", ""}
    ecart = (
        float(bobine.poids / m.poids_bobine - 1) if mesure and bobine.poids and m.poids_bobine
        else None
    )  # fmt: skip
    bobines = mt.bobines_du_fil(f, r)
    # Le remplissage des bobines (`pourcentage`) pèse sur le poids, pas sur le nombre de bobines.
    poids = float(bobines * bobine.poids * f.pourcentage / mt.CENT)
    return {
        "id": ident, "matiere_id": m.id, "reference": m.reference,
        "designation": m.designation,
        "fournisseur": ctx.fournisseurs.get(m.fournisseur_id or 0, ""),
        "etage": f.etage, "metres": f.metres, "pourcentage": f.pourcentage,
        "commentaire": f.commentaire, "bobines": float(bobines),
        "poids_bobine": m.poids_bobine, "poids_bobine_utilise": bobine.poids,
        "source_poids": bobine.source, "ecart_mesure": ecart,
        "ecart_hors_tolerance": ecart is not None and abs(ecart) > ctx.tolerance,
        "poids": poids, "valeur_mad": poids * ctx.couts.get(m.reference, 0.0),
    }  # fmt: skip


def _etage(
    n: int, fils: list[dict[str, Any]], r: Reglage, ligne: MetierEtage | None, ctx: Contexte
) -> dict[str, Any]:
    """Un étage : fils, largeur occupée (Σ mètres montés), bobines, poids, version."""
    metres = sum((Decimal(str(f["metres"]))
                  for f in fils), start=Decimal(0))  # fmt: skip
    return {
        "etage": n, "version": ligne.version if ligne else 1, "fils": len(fils),
        "metres": float(metres), "bobines": sum(f["bobines"] for f in fils),
        "poids": sum(f["poids"] for f in fils),
        "trop_large": bool(r.laize) and metres > r.laize,
        "monte_le": ligne.monte_le if ligne else None,
        "monte_par": ctx.personnes.get(ligne.monte_par_id) if ligne and ligne.monte_par_id
        else None,
    }  # fmt: skip


def _dernier(s: Session) -> dict[int, dict[str, Any]]:
    """Le dernier montage de chaque métier (historique des montages)."""
    derniers: dict[int, dict[str, Any]] = {}
    requete = select(MontageEvenement).order_by(MontageEvenement.id.desc())
    noms = dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).all())
    for e in s.scalars(requete):
        derniers.setdefault(
            e.metier_id,
            {"par": noms.get(e.par_id) if e.par_id else None, "quand": e.quand,
             "etage": e.etage, "effet_kg": e.effet_kg},
        )  # fmt: skip
    return derniers


def _metier(
    x: Metier, montes: list[Montage], etages: dict[int, MetierEtage], ctx: Contexte,
    dernier: dict[str, Any] | None,
) -> dict[str, Any]:  # fmt: skip
    """La fiche d'un métier."""
    r = Reglage.de(x)
    fils = [
        _fil(Fil(f.etage, f.matiere_id, f.metres, f.pourcentage, f.commentaire), f.id, r, ctx)
        for f in montes
    ]
    detail = [
        _etage(n, [f for f in fils if f["etage"] == n], r, etages.get(n), ctx)
        for n in range(1, x.etages + 1)
    ]
    return {
        "id": x.id, "code": x.code, "nom": x.nom, "laize": x.laize,
        "bobines_par_metre": x.bobines_par_metre, "etages": x.etages, "actif": x.actif,
        "commentaire": x.commentaire, "version": x.version, "fils": fils,
        "poids": sum(f["poids"] for f in fils),
        "sur_les_metiers": sum(f["poids"] for f in fils) if x.actif else 0.0,
        "valeur_mad": sum(f["valeur_mad"] for f in fils),
        "bobines": sum(f["bobines"] for f in fils),
        "metres": sum(e["metres"] for e in detail),
        "etages_detail": detail, "etages_garnis": sum(1 for e in detail if e["fils"]),
        "etages_trop_larges": [e["etage"] for e in detail if e["trop_large"]],
        "densite_a_saisir": not x.bobines_par_metre,
        "fils_sans_poids": sum(1 for f in fils if not f["poids_bobine_utilise"]),
        "ordres": ctx.ordres.get(x.id, 0), "tolerance_bobine": ctx.tolerance,
        "dernier_montage": dernier,
    }  # fmt: skip


def lister(s: Session, voit_prix: bool, metier_id: int | None = None) -> list[dict[str, Any]]:
    """Route 94 (et 95 pour un seul) : chaque métier, ses fils étage par étage, leur poids."""
    ctx = contexte(s, voit_prix)
    requete = select(Metier).order_by(Metier.nom, Metier.code)
    if metier_id is not None:
        requete = requete.where(Metier.id == metier_id)
    metiers = list(s.scalars(requete))
    ids = [x.id for x in metiers]
    montes: dict[int, list[Montage]] = defaultdict(list)
    for f in s.scalars(
        select(Montage).where(Montage.metier_id.in_(ids)).order_by(Montage.etage, Montage.id)
    ):
        montes[f.metier_id].append(f)
    etages: dict[int, dict[int, MetierEtage]] = defaultdict(dict)
    for e in s.scalars(select(MetierEtage).where(MetierEtage.metier_id.in_(ids))):
        etages[e.metier_id][e.etage] = e
    derniers = _dernier(s)
    return [
        _metier(x, montes.get(x.id, []), etages.get(x.id, {}), ctx, derniers.get(x.id))
        for x in metiers
    ]


def fiche(s: Session, metier_id: int, voit_prix: bool) -> dict[str, Any]:
    """Route 95 : un métier (404 « Métier introuvable. »)."""
    trouves = lister(s, voit_prix, metier_id)
    if not trouves:
        raise Refus.introuvable("Métier introuvable.")
    return trouves[0]


def _kg(lignes: list[dict[str, Any]] | None) -> float:
    """Ce que pèsent les lignes d'un événement."""
    return sum(float(x.get("kg", 0.0)) for x in lignes or [])


def montages(s: Session, metier_id: int) -> list[dict[str, Any]]:
    """Route 101 : l'historique des montages d'un métier, le plus récent d'abord ; « téléphone »
    pour le montage d'un étage (route 100), « bureau » pour plusieurs étages (99, 97)."""
    if s.get(Metier, metier_id) is None:
        raise Refus.introuvable("Métier introuvable.")
    noms = dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).all())
    requete = (
        select(MontageEvenement)
        .where(MontageEvenement.metier_id == metier_id)
        .order_by(MontageEvenement.quand.desc(), MontageEvenement.id.desc())
    )
    return [
        {
            "id": e.id, "quand": e.quand, "par": noms.get(e.par_id) if e.par_id else None,
            "etage": e.etage, "origine": "téléphone" if e.etage is not None else "bureau",
            "avant": e.avant or [], "apres": e.apres or [],
            "avant_kg": _kg(e.avant), "apres_kg": _kg(e.apres), "effet_kg": e.effet_kg,
            "alerte": e.alerte,
        }
        for e in s.scalars(requete)
    ]  # fmt: skip


def matieres_montables(s: Session) -> list[dict[str, Any]]:
    """Route 102 : pour chaque matière au poids, le poids de bobine que le montage comptera,
    ce qui est parti aux machines en 30 jours et ce qui est déjà monté (métiers en service)."""
    lineaires = set(s.scalars(select(RoleNomenclature.id).where(RoleNomenclature.lineaire)))
    matieres = [
        m for m in s.scalars(select(Matiere).order_by(Matiere.reference))
        if m.role_id not in lineaires
    ]  # fmt: skip
    poids = mt.bobines(s, matieres)
    sorti = mt.sorties_recentes(s)
    reglages = {x.id: Reglage.de(x) for x in s.scalars(select(Metier))}
    monte: dict[int, Decimal] = defaultdict(Decimal)
    for f in s.scalars(select(Montage)):
        if f.matiere_id in poids:
            fil = Fil(f.etage, f.matiere_id, f.metres, f.pourcentage)
            monte[f.matiere_id] += mt.peser([fil], reglages[f.metier_id], poids)
    return [
        {
            "matiere_id": m.id, "reference": m.reference, "designation": m.designation,
            "actif": m.actif, "poids_bobine_catalogue": m.poids_bobine,
            "poids_bobine_compte": poids[m.id].poids, "origine_poids": poids[m.id].source,
            "sorti_30_j": sorti.get(m.id, Decimal(0)), "deja_monte": monte[m.id],
            "jours": mt.JOURS_SORTIES,
        }
        for m in matieres
    ]  # fmt: skip
