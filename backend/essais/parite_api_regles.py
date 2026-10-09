"""Parité par l'API : les règles d'explication directes (forme et ampleur vérifiées).

Les écarts des routes sont d'abord expliqués par un **recalcul** de Gestion MP (rejeu sur les
données traduites, chaîne en base, K7, K9). Restent les différences qu'aucun recalcul de
Gestion MP ne peut produire, parce qu'elles tiennent à ce que PRO garde et Gestion MP efface :

- **K3** (MODELE-DONNEES § 10.5) : un inventaire abandonné garde ses lignes dans PRO (statut
  `abandonne`, hors des calculs) ; Gestion MP corrigé garde l'inventaire et son numéro mais
  efface ses lignes. La règle exige : l'inventaire abandonné **des deux côtés**, aucune ligne
  chez Gestion MP, et l'écart limité aux lignes (en plus chez PRO) et à leur nombre.
"""

from __future__ import annotations

from parite_api import Ecart, Regle, Route
from parite_comparer import ABSENT


def k3_inventaire_abandonne(route: Route, e: Ecart) -> str | None:
    """Les lignes d'un inventaire abandonné, gardées par PRO, effacées par Gestion MP."""
    inv = e.element
    if not isinstance(inv, dict) or inv.get("statut") != "abandonne" or inv.get("nb_lignes"):
        return None
    if e.champ == "(élément)" and e.gmp is ABSENT and isinstance(e.pro, dict):
        return "K3"
    if e.champ == "nb_lignes" and e.gmp == 0 and isinstance(e.pro, int) and e.pro > 0:
        return "K3"
    return None


REGLES: list[Regle] = [k3_inventaire_abandonne]
