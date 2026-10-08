"""Le réel corrige le plan : coefficient de réalisation fil par fil (CALCULS A § 3.10).

Portage de la partie « fenêtre de réalisation » de `moteur.etat_stock` : sur les derniers
mois **clos** (réglage `fenetre_realisation_jours`, en mois entiers), le rapport de ce qui est
sorti à ce que le plan et les recettes **de l'époque** prévoyaient, borné à [0,5 ; 1,5] ; un
fil en rupture ne baisse pas sa prévision ; un fil hors recette mais consommé se prévoit à ce
qui sort ; un fil entré dans une recette à la place d'un autre hérite de son coefficient.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from gestion_mp_pro.calcul.besoins import (
    besoins_passes,
    fils_remplaces,
    sortis_des_recettes,
)
from gestion_mp_pro.calcul.constantes import (
    EPSILON,
    JOURS_PAR_MOIS,
    MOIS,
    POUSSIERE,
    REALISATION_MAXI,
    REALISATION_MINI,
    RECUL_DEBUT_JOURS,
)
from gestion_mp_pro.calcul.modele import Article, Donnees
from gestion_mp_pro.calcul.nomenclature import kg_par_m2
from gestion_mp_pro.calcul.outils import arrondi, debut_de_mois, fin_de_mois
from gestion_mp_pro.calcul.plan import plan_mensuel
from gestion_mp_pro.calcul.stock.journal import Agregat, CleMois, stock_net_de

Realisation = tuple[float | None, float | None, bool]
"""(coefficient, consommation réelle mensuelle, prévision « hors recette »)."""


@dataclass
class Fenetre:
    """Les mois clos qui jugent le plan (aucun : `mois` = 0)."""

    mois: int = 0
    debut: date | None = None
    fins: list[date] = field(default_factory=list)
    rangs: dict[CleMois, int] = field(default_factory=dict)
    prevus: dict[str, list[float]] = field(default_factory=dict)
    stables: dict[str, list[bool]] = field(default_factory=dict)


def fenetre_de_realisation(donnees: Donnees, date_ref: date) -> Fenetre:
    """La fenêtre en mois entiers clos (au demi supérieur : 75 jours font 3 mois) ; un mois
    où l'atelier n'avait pas commencé à sortir dans sa première semaine ne compte pas."""
    jours = int(donnees.parametres.fenetre_realisation_jours)
    if not jours:
        return Fenetre()
    mois = max(1, int(arrondi(jours / JOURS_PAR_MOIS)))
    debut = debut_de_mois(date_ref, -mois)
    premiere = min(
        (m.date for m in donnees.mouvements if m.type == "SORTIE_PROD" and m.date <= date_ref),
        default=None,
    )
    while mois and (premiere is None or premiere > debut + timedelta(days=RECUL_DEBUT_JOURS)):
        mois -= 1
        debut = debut_de_mois(date_ref, -mois)
    if not mois:
        return Fenetre()
    fins = [fin_de_mois(date_ref, -k) for k in range(mois, 0, -1)]
    prevus, stables = besoins_passes(donnees, fins)
    return Fenetre(
        mois=mois,
        debut=debut,
        fins=fins,
        rangs={(f.year, f.month): i for i, f in enumerate(fins)},
        prevus=prevus,
        stables=stables,
    )


@dataclass
class Lecture:
    """Ce que la réalisation lit du reste du calcul."""

    donnees: Donnees
    fenetre: Fenetre
    agregats: dict[str, Agregat]
    besoins: dict[str, list[float]]
    monte: dict[str, float]
    quarantaines: list[str]


def _realisation(lecture: Lecture, article: Article, sortis: set[str]) -> Realisation:
    fenetre = lecture.fenetre
    agregat = lecture.agregats.get(article.reference)
    besoin = lecture.besoins.get(article.reference, [0.0] * MOIS)
    conso_plan = sum(besoin) / MOIS
    prevus = fenetre.prevus.get(article.reference, [0.0] * fenetre.mois)
    stables = fenetre.stables.get(article.reference, [True] * fenetre.mois)
    retenus = [i for i in range(fenetre.mois) if stables[i]]
    if not retenus:
        return None, None, False
    serie = agregat.reel_par_mois if agregat else {}
    reel = max(0.0, sum(serie.get(i, 0.0) for i in retenus))
    conso_reelle = reel / len(retenus)
    prevu = sum(prevus[i] for i in retenus)
    if prevu > 0:
        coefficient = min(REALISATION_MAXI, max(REALISATION_MINI, reel / prevu))
        # Le stock qui pouvait servir : les magasins hors quarantaine et le fil monté.
        detenu = (
            stock_net_de(agregat)
            + lecture.monte.get(article.reference, 0.0)
            - (agregat.en_magasins(lecture.quarantaines) if agregat else 0.0)
        )
        if coefficient < 1 and detenu <= POUSSIERE:
            coefficient = 1.0  # un fil en rupture n'a pas pu sortir
        return coefficient, conso_reelle, False
    hors_recette = (
        reel > 0 and conso_plan == 0 and not any(prevus) and article.reference not in sortis
    )
    return None, conso_reelle, hors_recette


Morceau = tuple[float, float | None, list[str]]
"""(poids de la qualité dans le fil, coefficient hérité, fils remplacés)."""


def _morceaux(
    lecture: Lecture, realisations: dict[str, Realisation], date_ref: date
) -> dict[str, list[Morceau]]:
    donnees = lecture.donnees
    debut = datetime.combine(lecture.fenetre.debut or date_ref, time.min)
    remplaces = fils_remplaces(donnees, debut, datetime.combine(date_ref, time.max))
    plan = plan_mensuel(donnees, date_ref)
    parts: dict[str, list[Morceau]] = defaultdict(list)
    for recette in donnees.recettes:
        ref = recette.reference
        if not ref or realisations.get(ref, (None, None, False))[0] is not None:
            continue
        poids = kg_par_m2(donnees, recette.qualite, ref, recette.pourcentage) * sum(
            plan.get(recette.qualite, [0.0])
        )
        if poids <= 0:
            continue
        anciens = [
            x
            for x in remplaces.get((recette.qualite, ref), [])
            if realisations.get(x, (None, None, False))[0] is not None
        ]
        if anciens:
            prevus = [max(sum(lecture.fenetre.prevus.get(x, [])), EPSILON) for x in anciens]
            herite = sum(
                (realisations[x][0] or 0.0) * w for x, w in zip(anciens, prevus, strict=True)
            ) / sum(prevus)
            parts[ref].append((poids, herite, anciens))
        else:
            parts[ref].append((poids, None, []))
    return parts


def realisations(
    lecture: Lecture, date_ref: date
) -> tuple[dict[str, Realisation], dict[str, list[str]]]:
    """Le coefficient de chaque fil, et les fils dont chacun hérite."""
    donnees = lecture.donnees
    fin = datetime.combine(date_ref, time.max)
    sortis = sortis_des_recettes(
        donnees, datetime.combine(debut_de_mois(date_ref, -MOIS), time.min), fin
    )
    resultat = {a.reference: _realisation(lecture, a, sortis) for a in donnees.articles}
    heritages: dict[str, list[str]] = {}
    for ref, morceaux in _morceaux(lecture, resultat, date_ref).items():
        if not any(c is not None for _, c, _ in morceaux):
            continue
        total = sum(w for w, _, _ in morceaux)
        coefficient = sum(w * (1.0 if c is None else c) for w, c, _ in morceaux) / total
        _, conso_reelle, _ = resultat.get(ref, (None, None, False))
        resultat[ref] = (coefficient, conso_reelle, False)
        heritages[ref] = sorted({x for _, _, noms in morceaux for x in noms})
    return resultat, heritages
