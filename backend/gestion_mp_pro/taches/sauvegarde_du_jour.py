"""Tâche « sauvegarde » : les automatiques dues (quotidienne, hebdomadaire, mensuelle, à 22 h,
rattrapées), puis la purge (ARCHITECTURE § 12 ; décision X7).

Une automatique déjà faite dont la copie de sécurité manque (second disque débranché hier) est
recopiée : un échec de copie ne s'efface pas tant que la copie n'existe pas.
"""

from __future__ import annotations

from gestion_mp_pro.services import sauvegarde as service


def executer() -> None:
    """Un passage : les automatiques dues (et la purge), ou les copies manquantes refaites."""
    if service.automatiques():
        return
    copie = service.dossier_copie()
    if copie is None:
        return
    for f in service.dernieres_automatiques():
        if not (copie / f.name).is_file():
            service.recopier(f)
