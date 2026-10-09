"""Le routeur du domaine « Commandes », partagé par `routes.py` et `routes_documents.py`."""

from __future__ import annotations

from gestion_mp_pro.api.communs import nouveau_routeur

routeur = nouveau_routeur("commandes")
