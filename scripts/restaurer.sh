#!/bin/bash
# Restaure une sauvegarde de Gestion MP PRO — tout ou rien (ARCHITECTURE § 13.3, lot D10) :
# relecture du fichier, refus d'une sauvegarde d'une autre base ou d'une version plus récente,
# sauvegarde « avant restauration », remplacement du schéma en une transaction, pièces jointes
# remises, migration à la révision de la version installée (head), journal écrit dans la base
# restaurée. Jamais sur la base gestion_mp (Gestion MP) : refusé avant toute connexion.
#
#   scripts/restaurer.sh gestion-mp-pro-2026-10-08-020000-quotidienne.dump
#   scripts/restaurer.sh FICHIER --confirmation RESTAURER [--motif "pourquoi"]   # sans question
#
# Le fichier est cherché dans le dossier de cette base (~/gestion-mp-pro-sauvegardes/<base>/),
# son archive de pièces à côté. Le serveur de cette base doit être arrêté (scripts/arreter.sh) ;
# serveur en marche, restaurer depuis l'écran : Administration › Sauvegardes.
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$ICI/commun.sh" ]; then . "$ICI/commun.sh"; else . "$ICI/../deploiement/mac/commun.sh"; fi
garder_la_base

FICHIER="" CONFIRMATION="" MOTIF="restauration depuis le poste (scripts/restaurer.sh)"
while [ $# -gt 0 ]; do
  case "$1" in
    --confirmation) CONFIRMATION="${2:-}"; shift 2 ;;
    --motif) MOTIF="${2:-}"; shift 2 ;;
    -*) echouer "option inconnue : $1" ;;
    *) [ -z "$FICHIER" ] || echouer "un seul fichier à la fois."; FICHIER="$1"; shift ;;
  esac
done
[ -n "$FICHIER" ] || echouer "quel fichier ? (scripts/restaurer.sh gestion-mp-pro-…dump)"

DOSSIER="${GESTIONMPPRO_SAUVEGARDES:-$HOME/gestion-mp-pro-sauvegardes}"
DOSSIER="${DOSSIER/#\~/$HOME}/$BASE_NOM"
case "$FICHIER" in
  */*)
    parent="$(cd "$(dirname "$FICHIER")" 2>/dev/null && pwd || true)"
    [ "$parent" = "$(cd "$DOSSIER" 2>/dev/null && pwd || true)" ] \
      || echouer "le fichier doit être dans $DOSSIER (y copier la sauvegarde et son .pieces.tar)."
    ;;
esac

if [ -n "$(pids_pro)" ]; then
  echouer "le serveur tourne sur le port $GESTIONMPPRO_PORT : l'arrêter d'abord (scripts/arreter.sh), ou restaurer depuis l'écran (Administration › Sauvegardes)."
fi

if [ -z "$CONFIRMATION" ]; then
  [ -t 0 ] || echouer "confirmation absente : ajouter --confirmation RESTAURER."
  dire "Toute la base $BASE_NOM va être remplacée par $(basename "$FICHIER")."
  dire "L'état actuel sera sauvegardé d'abord (« avant restauration »)."
  printf 'Pour confirmer, tapez RESTAURER : '
  read -r CONFIRMATION
fi
poste restaurer "$(basename "$FICHIER")" --confirmation "$CONFIRMATION" --motif "$MOTIF"
