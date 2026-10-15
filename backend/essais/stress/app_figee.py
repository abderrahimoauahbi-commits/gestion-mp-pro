"""L'application réelle, l'horloge figée par `GESTIONMPPRO_STRESS_DATE` (épreuve d'écran).

Les bases du stress test « 10 ans » s'arrêtent en 2036 : pour que l'écran les lise au jour de
leur dernière activité (cockpit, plan glissant, période, « il y a 40 min »), le serveur jetable
part de ce module plutôt que de `gestion_mp_pro.main:app`. Rien d'autre ne change : mêmes routes,
mêmes refus, même en-tête `X-Heure-Serveur` (c'est lui qui donne « aujourd'hui » à l'écran).

    GESTIONMPPRO_STRESS_DATE=2036-10-14 uvicorn essais.stress.app_figee:app --port 8121

Sans la variable, l'horloge reste au temps réel. Réservé aux essais : jamais en service.
"""

from __future__ import annotations

import os
from datetime import date

from gestion_mp_pro.main import app
from gestion_mp_pro.services import horloge

__all__ = ["app"]

_FIGEE = os.environ.get("GESTIONMPPRO_STRESS_DATE", "").strip()
if _FIGEE:
    horloge.fixer(date.fromisoformat(_FIGEE))
