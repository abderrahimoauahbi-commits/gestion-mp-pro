#!/bin/bash
# Épreuve du démarrage automatique (lot X2) sous une étiquette et une base d'ESSAI : l'agent
# launchd démarre le serveur, le relance après `kill` (deux fois : TERM puis KILL), arreter.sh le
# suspend sans relance, --retirer le retire proprement. Gestion MP (8030) est lu avant, pendant
# et après : il doit répondre et garder le même processus. À la fin, aucun agent ne reste.
#
#   GESTIONMPPRO_BASE=postgresql+psycopg://gestion_mp_pro@localhost/gestion_mp_pro_x2_poste_essai \
#   GESTIONMPPRO_PORT=8150 essais/demarrage_automatique.sh
#
# Prérequis : deploiement/mac/installer.sh lancé avec les mêmes variables (copie de cette base).
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
. "$ICI/../deploiement/mac/commun.sh"
ETIQUETTE="$ETIQUETTE_DEFAUT.essai"
DOMAINE="gui/$(id -u)"
PLIST="$HOME/Library/LaunchAgents/$ETIQUETTE.plist"
GMP="http://127.0.0.1:8030/api/sante"
ok=0 ko=0
verifier() { if (eval "$2"); then ok=$((ok + 1)); dire "  ok  $1"; else ko=$((ko + 1)); dire "  KO  $1"; fi; }
gmp_repond() { [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$GMP")" = 200 ]; }
gmp_pid() { lsof -nP -tiTCP:8030 -sTCP:LISTEN 2>/dev/null | head -n 1; }
pid_agent() { launchctl print "$DOMAINE/$ETIQUETTE" 2>/dev/null | awk '$1 == "pid" { print $3; exit }'; }
# Attend qu'un serveur PRO réponde avec un autre processus que $1 (60 s au plus) ; rend son pid.
attendre_nouveau() {
  for _ in $(seq 1 120); do
    p="$(pids_pro | head -n 1)"
    if [ -n "$p" ] && [ "$p" != "$1" ] && [ "$(etat_http)" = 200 ]; then printf '%s' "$p"; return 0; fi
    sleep 0.5
  done
  return 1
}

case "$BASE_NOM:$GESTIONMPPRO_PORT" in
  gestion_mp_pro:* | *:8050 | *:8030) echouer "épreuve réservée à une base d'essai sur un port d'essai (pas gestion_mp_pro, ni 8050, ni 8030)." ;;
esac
[ -x "$OUTILS/installer_demarrage_automatique.sh" ] || echouer "outils absents : lancer deploiement/mac/installer.sh avec ces variables."
trap '"$OUTILS/installer_demarrage_automatique.sh" --etiquette "$ETIQUETTE" --retirer >/dev/null 2>&1' EXIT

dire "Démarrage automatique : étiquette $ETIQUETTE, base $BASE_NOM, port $GESTIONMPPRO_PORT"
GMP_PID="$(gmp_pid)"
verifier "Gestion MP répond avant l'épreuve (8030, processus $GMP_PID)" "gmp_repond"
verifier "aucun agent d'essai ni serveur sur $GESTIONMPPRO_PORT avant" "[ ! -f '$PLIST' ] && [ -z \"\$(pids_sur_le_port)\" ]"

"$OUTILS/installer_demarrage_automatique.sh" --etiquette "$ETIQUETTE"
P1="$(pid_agent)"
verifier "l'agent a démarré le serveur (RunAtLoad), /api/sante 200" "[ \"\$(etat_http)\" = 200 ]"
verifier "le serveur qui répond est celui de l'agent (processus $P1)" "pids_pro | grep -qx '$P1'"
verifier "l'agent porte KeepAlive et RunAtLoad" "[ \"\$(plutil -extract KeepAlive raw '$PLIST')\" = true ] && [ \"\$(plutil -extract RunAtLoad raw '$PLIST')\" = true ]"

kill -TERM "$P1"
P2="$(attendre_nouveau "$P1")"
verifier "relancé après kill -TERM ($P1 → ${P2:-rien})" "[ -n '$P2' ]"
kill -KILL "$P2" 2>/dev/null
P3="$(attendre_nouveau "$P2")"
verifier "relancé après kill -KILL ($P2 → ${P3:-rien})" "[ -n '$P3' ]"
verifier "Gestion MP a répondu pendant les relances, même processus" "gmp_repond && [ \"\$(gmp_pid)\" = '$GMP_PID' ]"

"$OUTILS/arreter.sh" --etiquette "$ETIQUETTE"
sleep 15
verifier "arreter.sh : arrêté et pas relancé (15 s)" "[ -z \"\$(pids_sur_le_port)\" ] && ! launchctl print '$DOMAINE/$ETIQUETTE' >/dev/null 2>&1"

"$OUTILS/installer_demarrage_automatique.sh" --etiquette "$ETIQUETTE" >/dev/null
verifier "réinstallé (idempotent) : il répond de nouveau" "[ \"\$(etat_http)\" = 200 ]"
"$OUTILS/installer_demarrage_automatique.sh" --etiquette "$ETIQUETTE" --retirer
sleep 12
verifier "--retirer : agent déchargé, fichier retiré, port rendu, pas de relance" "[ ! -f '$PLIST' ] && ! launchctl print '$DOMAINE/$ETIQUETTE' >/dev/null 2>&1 && [ -z \"\$(pids_sur_le_port)\" ]"
verifier "Gestion MP répond après l'épreuve, même processus ($GMP_PID)" "gmp_repond && [ \"\$(gmp_pid)\" = '$GMP_PID' ]"

dire "Démarrage automatique : $ok vérification(s) tenue(s), $ko en défaut."
[ "$ko" = 0 ]
