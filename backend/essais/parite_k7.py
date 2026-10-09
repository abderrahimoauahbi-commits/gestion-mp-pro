"""Parité : la correction déclarée K7, prouvée dans sa forme et son ampleur.

K7 (décision de Mohamed, U8 ; lot D8) : le fil monté sur les métiers est du stock **à toute
date** — PRO le compte dans la valorisation d'une date passée (montage de ce soir-là, rejoué
de `montage_evenement` ; un montage repris sans événement est monté depuis toujours) ; Gestion
MP ne le compte qu'au jour même. L'année d'essai n'a aucun fil monté : l'écart y est nul
partout (vérifié par la passe statique). Pour le prouver, une seconde copie reçoit deux fils
montés, est reprise dans PRO, et l'on compare **ce que le montage change** de chaque côté :

- Gestion MP tel quel : rien aux dates passées, le fil monté aujourd'hui ;
- PRO : le fil monté à toutes les dates ;
- Gestion MP rejoué avec K7 (`a_la_date` qui garde le montage connu) doit redonner, à chaque
  date et sur chaque valeur, exactement ce que PRO change. Sinon : à corriger.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import parite_bases as pb
import parite_comparer as pc
from parite_api_formes import aujourdhui
from parite_api_passe import rejouer
from parite_api_routes import pilotage
from parite_dynamique_outils import attendu_pro
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

METRES = 0.5
"""Un demi-mètre par étage : quelques centaines de kilos sur le métier (un montage réaliste ; un
montage démesuré grossirait le bruit de l'arrondi K1 du poids de bobine au-delà de 0,001 kg)."""


@dataclass
class PreuveK7:
    """Par date : écarts que le montage fait entre les deux, et ceux que K7 n'explique pas."""

    dates: list[str] = field(default_factory=list)
    comparees: int = 0
    expliques: int = 0
    a_corriger: list[tuple[str, pc.Chemin, Any, Any]] = field(default_factory=list)
    machine_aujourdhui_mad: float = 0.0


def monter(copie: str) -> str:
    """Deux fils montés (étages 1 et 2 du premier métier) dans la copie de Gestion MP."""
    moteur = create_engine(copie, poolclass=NullPool)
    with moteur.begin() as c:
        metier = c.execute(text("SELECT min(id) FROM metier")).scalar_one()
        article, reference = c.execute(text(
            "SELECT a.id, a.reference FROM article a JOIN lot l ON l.article_id = a.id "
            "JOIN solde s ON s.lot_id = l.id "
            "WHERE a.poids_bobine > 0 GROUP BY a.id, a.reference HAVING sum(s.quantite) > 1000 "
            "ORDER BY a.id LIMIT 1"
        )).one()  # fmt: skip
        for etage in (1, 2):
            c.execute(
                text("INSERT INTO fil_monte (metier_id, etage, article_id, metres, pourcentage, "
                     "commentaire) VALUES (:m, :e, :a, :q, 100, 'parité K7')"),
                {"m": metier, "e": etage, "a": article, "q": METRES},
            )  # fmt: skip
    moteur.dispose()
    return str(reference)


def valorisation_pro(adresse: str, jour: date) -> dict[str, Any]:
    """La valorisation de PRO (route 210, par ses services) au soir de `jour`."""
    from gestion_mp_pro.services import donnees_moteur, horloge
    from gestion_mp_pro.services import pilotage as pil

    donnees_moteur.invalider()  # deux bases, même signature : le cache serait faux
    moteur = create_engine(adresse, poolclass=NullPool)
    with horloge.figee(aujourdhui()), Session(moteur) as s:
        v = pil.valoriser_lecture(s, pil.lire(s, jour))
    moteur.dispose()
    donnees_moteur.invalider()
    return dataclasses.asdict(v)


def _vue(v: dict[str, Any], champs: set[str] | None = None) -> dict[str, Any]:
    """Totaux et lignes par référence (champs de Gestion MP seulement)."""
    tete = {k: x for k, x in v.items() if k not in ("lignes", "date_reference")}
    lignes = {x["reference"]: x for x in v["lignes"]}
    if champs is not None:
        tete = {k: x for k, x in tete.items() if k in champs}
        lignes = {r: {k: y for k, y in x.items() if k in champs} for r, x in lignes.items()}
    return tete | {"lignes": lignes}


def prouver(bases: pb.Bases, dossier: Path, dates: list[str]) -> PreuveK7:
    """La preuve de K7 sur une copie montée (supprimée ensuite)."""
    k7 = pb.Bases(prefixe=f"{bases.prefixe}k7")
    preuve = PreuveK7(dates=["", *dates])
    try:
        pb.copier(bases.copie.rsplit("/", 1)[-1], k7.copie)
        monter(k7.copie)
        pb.reprendre(k7.copie, k7.pro)
        routes = [pilotage(d)[1] for d in preuve.dates]
        sortie = dossier / "k7"
        rejouer(k7.copie, routes, ["monte=-", "monteK7=-+K7"], sortie)
        rejouer(bases.copie, routes, ["base=-"], sortie)
        for d, rm in zip(preuve.dates, routes, strict=True):
            _une_date(preuve, d, rm.route.nom, sortie, bases, k7)
    finally:
        pb.nettoyer(k7)
    return preuve


def _une_date(preuve: PreuveK7, d: str, nom: str, sortie: Path, bases: pb.Bases,  # noqa: PLR0917
              k7: pb.Bases) -> None:  # fmt: skip
    import json

    def lu(jeu: str) -> dict[str, Any]:
        return _vue(json.loads((sortie / jeu / f"{nom}.json").read_text(encoding="utf-8")))

    g_base, g_monte, g_k7 = lu("base"), lu("monte"), lu("monteK7")
    champs = set(g_base) | {k for x in g_base["lignes"].values() for k in x}
    jour = date.fromisoformat(d) if d else aujourdhui()
    p_base = _vue(valorisation_pro(bases.pro, jour), champs)
    p_monte = _vue(valorisation_pro(k7.pro, jour), champs)
    if not d:
        preuve.machine_aujourdhui_mad = float(p_monte["total_machine_mad"])
    sans = pc.comparer(attendu_pro(p_base, g_base, g_monte), p_monte)
    avec = {c for c, _, _ in pc.comparer(attendu_pro(p_base, g_base, g_k7), p_monte).ecarts}
    preuve.comparees += sans.comparees
    for chemin, x, y in sans.ecarts:
        if chemin in avec:
            preuve.a_corriger.append((d or "aujourd'hui", chemin, x, y))
        else:
            preuve.expliques += 1
    preuve.a_corriger += [
        (d or "aujourd'hui", c, None, None) for c in avec if c not in {e[0] for e in sans.ecarts}
    ]
