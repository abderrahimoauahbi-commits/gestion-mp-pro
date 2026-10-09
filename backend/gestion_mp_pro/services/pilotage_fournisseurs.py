"""La note des fournisseurs (routes 215, 220) : OTIF des réceptions, retours, délai → score.

Sans période, la note du moteur (`calcul.fournisseurs.scorecard_fournisseurs`). Avec `du` /
`au`, la même formule sur la période : réceptions validées de la période (chacune notée sur son
bon, quelle que soit sa date), bons partis de la période, retours de la période. Les
classements se disent sans émoji (P8-23) ; chaque ligne porte l'id de sa fiche.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul.achats import montant_ligne_mad, pas_partie
from gestion_mp_pro.calcul.fournisseurs import (
    PerformanceReception,
    ScoreFournisseur,
    performance_receptions,
    points_score,
    scorecard_fournisseurs,
)
from gestion_mp_pro.calcul.modele import Donnees, Fournisseur
from gestion_mp_pro.calcul.outils import arrondi
from gestion_mp_pro.modeles import Reception
from gestion_mp_pro.services import donnees_moteur
from gestion_mp_pro.services.pilotage import ids_fournisseurs


def _dans(jour: date | None, du: date | None, au: date | None) -> bool:
    return jour is not None and (du is None or jour >= du) and (au is None or jour <= au)


def sans_emoji(classement: str) -> str:
    """« 🟢 Stratégique » → « Stratégique » (le nom de classement reste)."""
    tete, _, reste = classement.partition(" ")
    return reste if reste and not tete.isalnum() else classement


def _moyenne(lot: list[PerformanceReception], champ: str) -> float | None:
    notees = [getattr(x, champ) for x in lot if x.otif is not None]
    valeurs = [v for v in notees if v is not None]
    return float(sum(valeurs) / len(valeurs)) if valeurs else None


def _classement(d: Donnees, score: float | None) -> tuple[str, str]:
    p = d.parametres
    paliers = (
        (p.score_strategique, "Stratégique", "Fidéliser + négocier volume"),
        (p.score_standard, "Standard", "Maintenir relation"),
        (p.score_surveiller, "À surveiller", "Audit qualité + relance"),
    )
    if score is None:
        return "—", "—"
    return next(
        ((c, a) for seuil, c, a in paliers if score >= seuil),
        ("À challenger", "Chercher alternative"),
    )


def _score(
    d: Donnees,
    f: Fournisseur,
    lot: list[PerformanceReception],
    periode: tuple[date | None, date | None],
) -> ScoreFournisseur:
    du, au = periode
    bons = [
        c
        for c in d.commandes
        if c.fournisseur == f.nom
        and not pas_partie(c)
        and c.statut != "Annulée"
        and _dans(c.date_bc, du, au)
    ]
    flux: dict[str, float] = defaultdict(float)
    for m in d.mouvements:
        if m.fournisseur == f.nom and _dans(m.date, du, au):
            flux[m.type] += m.quantite
    recu = flux["ENTREE_RECEPTION"]
    retours = flux["RETOUR_FOURNISSEUR"] / recu if recu else 0.0
    otif = _moyenne(lot, "otif")
    score = None if otif is None else arrondi(points_score(otif, retours, f.delai_jours))
    classement, action = _classement(d, score)
    ecarts = [x.ecart_pesee for x in lot if x.ecart_pesee is not None]
    return ScoreFournisseur(
        fournisseur=f.nom,
        pays=f.pays,
        devise=f.devise,
        delai_jours=f.delai_jours,
        nb_commandes=len(bons),
        montant_mad=sum(
            montant_ligne_mad(x, x.quantite_commandee, d.parametres) for c in bons for x in c.lignes
        ),
        receptions=len(lot),
        on_time=_moyenne(lot, "on_time"),
        in_full=_moyenne(lot, "in_full"),
        in_spec=_moyenne(lot, "in_spec"),
        otif=otif,
        taux_retours=retours,
        ecart_pesee_moyen=sum(ecarts) / len(ecarts) if ecarts else None,
        score=score,
        classement=classement,
        action=action,
        sous_performant=otif is not None and otif < d.parametres.cible_otif,
    )


@dataclass
class PerformanceFournisseurs:
    """La note des fournisseurs et les réceptions notées une à une."""

    du: date | None
    au: date | None
    cible_otif: float
    seuils: dict[str, float]
    lignes: list[dict[str, Any]]
    receptions: list[dict[str, Any]]


def performance(
    s: Session, du: date | None = None, au: date | None = None
) -> PerformanceFournisseurs:
    """Route 215 : le classement des fournisseurs (période facultative)."""
    d = donnees_moteur.charger(s)
    notes = [
        x
        for x in performance_receptions(d)
        if du is None and au is None or _dans(x.date_reception, du, au)
    ]
    if du is None and au is None:
        scores = [
            replace(x, classement=sans_emoji(x.classement)) for x in scorecard_fournisseurs(d)
        ]
    else:
        par_nom: dict[str, list[PerformanceReception]] = defaultdict(list)
        for x in notes:
            par_nom[x.fournisseur].append(x)
        scores = [
            _score(d, f, par_nom[f.nom], (du, au))
            for f in sorted(d.fournisseurs, key=lambda f: f.nom)
        ]
    ids = ids_fournisseurs(s)
    receptions = dict(
        s.execute(select(Reception.numero, Reception.id).where(Reception.numero.is_not(None))).all()
    )
    p = d.parametres
    return PerformanceFournisseurs(
        du=du,
        au=au,
        cible_otif=p.cible_otif,
        seuils={
            "strategique": p.score_strategique,
            "standard": p.score_standard,
            "surveiller": p.score_surveiller,
        },
        lignes=[{**asdict(x), "fournisseur_id": ids.get(x.fournisseur)} for x in scores],
        receptions=[
            {
                **asdict(x),
                "reception_id": receptions.get(x.numero),
                "fournisseur_id": ids.get(x.fournisseur),
            }
            for x in notes
        ],
    )
