#!/bin/bash
# Sauvegarde la base de Gestion MP PRO (ARCHITECTURE § 13.3), serveur en marche ou non :
# `pg_dump -Fc` relu, pièces jointes dans l'archive voisine (.pieces.tar), copie de sécurité si
# GESTIONMPPRO_SAUVEGARDES_COPIE est réglé. Même service, mêmes noms que l'écran.
#
#   scripts/sauvegarder.sh                          # sauvegarde manuelle (écrite au journal)
#   scripts/sauvegarder.sh --genre reference-vide   # ou avant-mise-a-jour, avant-vidage
#
# Dossier : ~/gestion-mp-pro-sauvegardes/<base>/ (jamais celui de Gestion MP).
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$ICI/commun.sh" ]; then . "$ICI/commun.sh"; else . "$ICI/../deploiement/mac/commun.sh"; fi
garder_la_base
poste sauvegarder "$@"
