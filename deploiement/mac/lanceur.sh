#!/bin/bash
# Lanceur de « Gestion MP PRO.app » (bureau) : démarre le serveur s'il ne tourne pas, puis ouvre
# http://localhost:8050 dans le navigateur par défaut. Recopié dans l'application par
# deploiement/mac/creer-raccourci.sh, qui écrit la ligne OUTILS juste au-dessous.
# Gestion MP (8030, « Gestion MP.app ») n'est jamais touché.
OUTILS="${OUTILS:-$HOME/Library/Application Support/Gestion MP PRO/outils}"
PORT=8050
ADRESSE="http://localhost:$PORT"
ETIQUETTE="fr.usine.gestion-mp-pro"
PLIST="$HOME/Library/LaunchAgents/$ETIQUETTE.plist"
JOURNAUX="$HOME/Library/Logs/Gestion MP PRO"
JOURNAL="$JOURNAUX/lanceur.log"
VERROU="${TMPDIR:-/tmp}/gestion-mp-pro-lanceur.verrou"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
# /api/sante répond 200 dès que Gestion MP PRO tourne (une base en défaut s'affiche dans l'écran).
etat() { /usr/bin/curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:$PORT/api/sante"; }
alerte() { /usr/bin/osascript -e "display alert \"Gestion MP PRO\" message \"$1\"" >/dev/null; }
signaler() { /usr/bin/osascript -e "display notification \"$1\" with title \"Gestion MP PRO\"" >/dev/null; }

[ "$(etat)" = 200 ] && { /usr/bin/open "$ADRESSE"; exit 0; }
# Un second double-clic pendant le démarrage n'en lance pas un second : il laisse faire le premier.
if ! /bin/mkdir "$VERROU" 2>/dev/null; then
  autre=$(cat "$VERROU/pid" 2>/dev/null)
  if [ -n "$autre" ] && kill -0 "$autre" 2>/dev/null; then
    signaler "Gestion MP PRO démarre déjà : le navigateur s'ouvrira dès qu'il sera prêt."
    exit 0
  fi
  rm -rf "$VERROU"
  /bin/mkdir "$VERROU" || exit 1
fi
echo $$ >"$VERROU/pid"
trap 'rm -rf "$VERROU"' EXIT

if [ ! -x "$OUTILS/demarrer.sh" ]; then
  alerte "Gestion MP PRO n'est pas installé sur ce Mac ($OUTILS) : lancer deploiement/mac/installer.sh."
  exit 1
fi
mkdir -p "$JOURNAUX"
serveur=""
if [ -f "$PLIST" ]; then
  # Démarrage automatique installé : c'est launchd qui porte le serveur (relance comprise).
  launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null \
    || launchctl kickstart "gui/$(id -u)/$ETIQUETTE" 2>/dev/null
else
  # Journal du lanceur tenu court : au-delà de 5 Mo, l'ancien est mis de côté (un seul gardé).
  if [ -f "$JOURNAL" ] && [ "$(stat -f %z "$JOURNAL")" -gt 5000000 ]; then
    mv -f "$JOURNAL" "$JOURNAL.1"
  fi
  nohup "$OUTILS/demarrer.sh" >>"$JOURNAL" 2>&1 &
  serveur=$!
fi
# Une nouvelle version construit d'abord sa copie figée et son écran : plusieurs minutes au
# besoin. On attend tant qu'il travaille (10 minutes au plus) ; on s'arrête aussitôt s'il a échoué.
for ((i = 0; i < 1200; i++)); do
  [ "$(etat)" = 200 ] && break
  [ -z "$serveur" ] || kill -0 "$serveur" 2>/dev/null || break
  [ "$i" = 20 ] && signaler "Démarrage en cours (nouvelle version : préparation de l'écran)…"
  sleep 0.5
done
[ "$(etat)" = 200 ] && { /usr/bin/open "$ADRESSE"; exit 0; }
alerte "Gestion MP PRO n'a pas démarré. Vérifiez que PostgreSQL tourne, puis consultez $JOURNAUX."
exit 1
