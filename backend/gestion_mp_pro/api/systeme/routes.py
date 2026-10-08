"""Routes du domaine « Système ».

Squelette du lot S0, rempli par le lot S2 (et D10 pour /sante). Routes minces : chemin, droits,
schémas, `summary` ; un appel de service ; aucune règle métier (ARCHITECTURE § 3.1).
"""

from __future__ import annotations

from gestion_mp_pro.api.communs import nouveau_routeur

routeur = nouveau_routeur("systeme")
