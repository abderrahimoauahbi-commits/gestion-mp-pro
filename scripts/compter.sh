#!/bin/bash
# Compte les lignes de chaque table de la base de Gestion MP PRO, en JSON (avec la révision du
# schéma) : la preuve d'un transfert vers un autre serveur (docs/INSTALLATION-WINDOWS.md § 9).
# Lecture seule. À lancer serveur arrêté, juste après la sauvegarde à transférer :
#
#   scripts/arreter.sh && scripts/sauvegarder.sh && scripts/compter.sh > comptes-mac.json
#
# Le serveur Windows compare ensuite sa base restaurée à ce fichier (restaurer.ps1 -Comptes).
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$ICI/commun.sh" ]; then . "$ICI/commun.sh"; else . "$ICI/../deploiement/mac/commun.sh"; fi
garder_la_base
poste comptes
