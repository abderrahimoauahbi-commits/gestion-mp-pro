"""Le fil monté sur les métiers à une date passée (décision de Mohamed : U8 ; DEFAUTS DM-07).

Le moteur ne connaît que le montage d'aujourd'hui (`a_la_date` le tient pour inconnu avant).
PRO garde l'histoire des montages (`montage_evenement` : les lignes d'avant et d'après de chaque
étage touché) : le montage d'un soir passé est celui d'aujourd'hui, **défait** événement par
événement, du plus récent au plus ancien, jusqu'à ce soir-là. Le fil monté est alors du stock
à toute date — dans la valeur, le disponible et le projeté, et dans le bilan du mois — comme
le veut la décision de Mohamed. Un montage repris sans événement est tenu pour monté depuis
toujours.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul.modele import Donnees, FilMonte, Metier
from gestion_mp_pro.modeles import Matiere, Montage, MontageEvenement
from gestion_mp_pro.modeles import Metier as MetierBase
from gestion_mp_pro.services import horloge

Etage = tuple[int, int]
"""(métier, étage) : la place d'un fil."""


def fin_de_journee(jour: date) -> datetime:
    """Minuit à la fin de `jour`, à l'heure de l'usine : ce qui est monté « ce soir-là »."""
    return datetime.combine(jour + timedelta(days=1), time.min, tzinfo=horloge.FUSEAU)


def _fils_d_aujourd_hui(s: Session) -> dict[Etage, list[dict[str, Any]]]:
    """Le montage en vigueur, étage par étage, comme les lignes de `montage_evenement`."""
    requete = select(Montage, Matiere.reference).join(Matiere, Matiere.id == Montage.matiere_id)
    etat: dict[Etage, list[dict[str, Any]]] = defaultdict(list)
    for m, reference in s.execute(requete.order_by(Montage.id)).all():
        etat[(m.metier_id, m.etage)].append(
            {
                "etage": m.etage,
                "reference": reference,
                "metres": float(m.metres),
                "pourcentage": float(m.pourcentage),
                "commentaire": m.commentaire,
            }
        )
    return etat


def _etages_touches(ev: MontageEvenement) -> set[int]:
    """Les étages qu'un événement a changés (ses lignes d'avant et d'après, et son étage)."""
    lignes: Iterable[Mapping[str, Any]] = [*(ev.avant or []), *(ev.apres or [])]
    etages = {int(x["etage"]) for x in lignes}
    return etages | ({ev.etage} if ev.etage is not None else set())


def montage_au_soir(s: Session, jour: date) -> dict[Etage, list[dict[str, Any]]]:
    """Le montage du soir de `jour` : celui d'aujourd'hui, défait des événements postérieurs."""
    etat = _fils_d_aujourd_hui(s)
    apres = (
        select(MontageEvenement)
        .where(MontageEvenement.quand >= fin_de_journee(jour))
        .order_by(MontageEvenement.quand.desc(), MontageEvenement.id.desc())
    )
    for ev in s.scalars(apres):
        for etage in _etages_touches(ev):
            etat[(ev.metier_id, etage)] = [
                dict(x) for x in (ev.avant or []) if int(x["etage"]) == etage
            ]
    return etat


def _metiers_au_soir(s: Session, d: Donnees, jour: date) -> list[Metier]:
    """Les métiers du moteur, leurs fils remplacés par ceux du soir de `jour` (poids de bobine
    retenu : celui d'aujourd'hui pour la même matière, sinon le catalogue)."""
    codes = dict(s.execute(select(MetierBase.id, MetierBase.code)).all())
    poids = {f.reference: f.poids_bobine for m in d.metiers for f in m.fils if f.poids_bobine}
    par_code: dict[str, list[FilMonte]] = defaultdict(list)
    for (metier_id, _etage), lignes in sorted(montage_au_soir(s, jour).items()):
        for x in lignes:
            par_code[codes.get(metier_id, "")].append(
                FilMonte(
                    reference=str(x["reference"]),
                    etage=int(x["etage"]),
                    metres=float(x["metres"]),
                    pourcentage=float(x["pourcentage"]),
                    commentaire=str(x.get("commentaire") or ""),
                    poids_bobine=poids.get(str(x["reference"]), 0.0),
                )
            )
    return [replace(m, fils=par_code.get(m.code, [])) for m in d.metiers]


def avec_montage(s: Session, d: Donnees, jour: date) -> Donnees:
    """Les données à `jour` avec le fil monté ce soir-là (aujourd'hui : rien à changer)."""
    if jour >= horloge.aujourd_hui() and d.montage_connu:
        return d
    return replace(d, metiers=_metiers_au_soir(s, d, jour), montage_connu=True)
