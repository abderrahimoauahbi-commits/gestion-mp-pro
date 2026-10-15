"""Simulateur « 10 ans d'exploitation » de Gestion MP PRO (épreuve demandée le 15/10/2026).

Dix ans d'activité d'usine rejoués **par les routes de l'application**, en mémoire (`TestClient`
sur l'application réelle), jour après jour (horloge de l'usine fixée), avec trois comptes
(direction, achats, alimentation) qui font chacun ce que leur rôle fait à l'usine, erreurs
humaines comprises. Chaque appel est consigné (route, rôle, statut, durée) ; chaque anomalie
(500, refus inattendu, lenteur, invariant faux aux fins de mois) est classée dans
`anomalies.jsonl` ; le fil des mois est dans `journal-10-ans.md`.

Règle de Mohamed (15/10) : tout se passe sur une copie `gestion_mp_pro_stress*_essai` de la
base ; ses référentiels ne sont **jamais** modifiés ni désactivés — les besoins du scénario
ajoutent des éléments d'essai dont le nom finit par « (stress) ».

    cd backend
    .venv/bin/python -m essais.stress.simulateur --dump <référentiels.dump> --annees 1

Voir `simulateur.py` pour les options (graine, reprise depuis une année, dossiers des dumps).
"""
