#!/bin/bash
# Arrête Gestion MP PRO sur ce poste (port 8050) — et lui seul : Gestion MP (8030) n'est
# jamais touché (seul un processus `gestion_mp_pro.main` sur le port de PRO est arrêté).
#
#   scripts/arreter.sh
#   scripts/arreter.sh --etiquette fr.usine.gestion-mp-pro.essai   # agent launchd d'essai
#
# Si le démarrage automatique est installé (agent launchd), l'agent est d'abord déchargé : sans
# cela, launchd le relancerait aussitôt. Il revient à la prochaine ouverture de session, ou au
# double-clic sur « Gestion MP PRO » du bureau.
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$ICI/commun.sh" ]; then . "$ICI/commun.sh"; else . "$ICI/../deploiement/mac/commun.sh"; fi

ETIQUETTE="$ETIQUETTE_DEFAUT"
while [ $# -gt 0 ]; do
  case "$1" in
    --etiquette) ETIQUETTE="${2:?--etiquette demande un nom}"; shift 2 ;;
    *) echouer "option inconnue : $1" ;;
  esac
done

DOMAINE="gui/$(id -u)"
PLIST="$HOME/Library/LaunchAgents/$ETIQUETTE.plist"
# L'agent n'est déchargé que s'il sert ce port-ci (un agent d'essai ne touche pas la production).
port_agent="$(plutil -extract EnvironmentVariables.GESTIONMPPRO_PORT raw "$PLIST" 2>/dev/null || true)"
if [ "$port_agent" = "$GESTIONMPPRO_PORT" ] && launchctl print "$DOMAINE/$ETIQUETTE" >/dev/null 2>&1; then
  launchctl bootout "$DOMAINE/$ETIQUETTE" 2>/dev/null || true
  dire "Démarrage automatique suspendu jusqu'à la prochaine ouverture de session ($ETIQUETTE)."
fi

pids="$(pids_pro)"
if [ -z "$pids" ]; then
  if [ -n "$(pids_sur_le_port)" ]; then
    dire "Le port $GESTIONMPPRO_PORT est tenu par un autre programme que Gestion MP PRO : rien n'est arrêté."
  else
    dire "Gestion MP PRO ne tourne pas sur le port $GESTIONMPPRO_PORT."
  fi
  exit 0
fi
# shellcheck disable=SC2086
kill $pids 2>/dev/null || true
# Arrêt propre (tâches de fond rendues, connexions fermées) : 20 s au plus, puis de force.
for _ in $(seq 1 40); do
  [ -n "$(pids_pro)" ] || break
  sleep 0.5
done
restants="$(pids_pro)"
# shellcheck disable=SC2086
[ -z "$restants" ] || kill -9 $restants 2>/dev/null || true
dire "Gestion MP PRO arrêté (port $GESTIONMPPRO_PORT)."
