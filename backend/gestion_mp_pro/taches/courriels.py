"""Tâche « courriel » : le lundi, le courriel de la semaine mis en file **une fois** ; à chaque
passage, la file envoyée (reprises espacées) — ARCHITECTURE § 12, défaut E-15.

Un passage qui écarte des adresses illisibles, ou dont un envoi échoue, se note en échec (la
tâche le dit à l'écran) sans empêcher les autres tâches.
"""

from __future__ import annotations

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.services import courriel
from gestion_mp_pro.services.courriel_contenu import courriel_du_lundi


class EchecCourriel(Exception):
    """Ce que le passage n'a pas pu faire (adresses écartées, envoi en échec)."""


def executer() -> None:
    """Un passage : mise en file du lundi, puis envoi de ce qui est dû."""
    with fabrique()() as s, s.begin():
        lundi = courriel_du_lundi(s)
    envoi = courriel.envoyer_la_file()
    fautes = []
    if lundi.illisibles:
        fautes.append("adresse(s) illisible(s) écartée(s) : " + ", ".join(lundi.illisibles))
    if envoi.echecs:
        fautes.append(f"{envoi.echecs} envoi(s) en échec : {envoi.derniere_erreur}")
    if fautes:
        raise EchecCourriel(" ; ".join(fautes))
