"""Routes du domaine « Reprise » (API-PRO § 1.24, routes 243–244) : le miroir de Gestion MP.

Lot C1 (ARCHITECTURE § 14.2). Routes minces : chemin, droits, schémas, `summary` ; un appel de
service (`services.miroir`). La route 244 répond 202 dès que la demande est acceptée (aucune
reprise en cours, activité propre remplacée seulement sur confirmation, source lisible) ; la
reprise suit en tâche de fond — sauvegarde « avant reprise » d'abord — et l'écran suit son
issue par la route 243.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import BackgroundTasks

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.reprise.schemas import (
    EtatMiroir,
    ExecutionMiroir,
    ExecutionReprise,
    RepriseDemandee,
)
from gestion_mp_pro.securite import D, QuiDep, T, droit
from gestion_mp_pro.services import miroir

routeur = nouveau_routeur("reprise")


def _execution(e: miroir.Execution, direction: bool) -> ExecutionMiroir:
    """Une exécution ; le rapport n'est rendu qu'à la direction."""
    valeurs = asdict(e)
    valeurs["rapport"] = e.rapport if direction else None
    return ExecutionMiroir.model_validate(valeurs)


@routeur.get(
    "/reprise",
    response_model=EtatMiroir,
    dependencies=[droit(D, T)],
    summary="L'état du miroir de Gestion MP : dernières reprises, signature, à jour, activité.",
    responses=reponses(401, 403),
)
def lire_miroir(qui: QuiDep) -> EtatMiroir:
    """Route 243."""
    e = miroir.etat()
    direction = str(qui.role) == "direction"
    return EtatMiroir(
        base=e.base,
        base_source=e.base_source,
        signature_source=e.signature_source,
        source_lisible=e.source_lisible,
        message_source=e.message_source,
        a_jour=e.a_jour,
        activite_propre=e.activite_propre,
        en_cours=e.en_cours,
        derniere_reussie=_execution(e.derniere_reussie, direction) if e.derniere_reussie else None,
        executions=[_execution(x, direction) for x in e.executions],
    )


@routeur.post(
    "/reprise",
    response_model=ExecutionReprise,
    status_code=202,
    dependencies=[droit(D)],
    summary="Rafraîchir le miroir : reprise de Gestion MP (sauvegarde « avant reprise » d'abord).",
    responses=reponses(401, 403, 409, 422, 503),
)
def rafraichir_miroir(
    corps: RepriseDemandee, qui: QuiDep, s: SessionDep, taches: BackgroundTasks
) -> ExecutionReprise:
    """Route 244 : 202, puis la reprise en tâche de fond (après le commit de la requête)."""
    demande = miroir.accepter(s, qui, corps.mode, corps.remplacer_activite, corps.confirmation)
    taches.add_task(miroir.lancer, demande)
    return ExecutionReprise(
        debut=demande.debut,
        mode=corps.mode.value,
        remplacer_activite=corps.remplacer_activite,
        message=(
            "La reprise de Gestion MP a commencé : une sauvegarde « avant reprise » de PRO est "
            "faite d'abord, puis tout est repris en une transaction. Suivre son issue ici."
        ),
    )
