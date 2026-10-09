"""Tâche « sauvegarde » : la quotidienne relue si elle manque, puis la purge (ARCHITECTURE § 12).

Une quotidienne déjà faite dont la copie de sécurité manque (second disque débranché hier) est
recopiée : un échec de copie ne s'efface pas tant que la copie n'existe pas.
"""

from __future__ import annotations

from gestion_mp_pro.services import horloge
from gestion_mp_pro.services import sauvegarde as service
from gestion_mp_pro.services import sauvegarde_outils as o


def executer() -> None:
    """Un passage : quotidienne du jour (et purge), ou copie manquante refaite."""
    if service.du_jour() is not None:
        return
    copie = service.dossier_copie()
    if copie is None:
        return
    jour = horloge.aujourd_hui()
    for f in service.dossier().glob(f"{o.PREFIXE}*-quotidienne{o.EXTENSION}"):
        lu = o.lire_nom(f.name)
        if lu is not None and lu.jour == jour and not (copie / f.name).is_file():
            service.recopier(f)
