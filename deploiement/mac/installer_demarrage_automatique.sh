#!/bin/bash
# Démarrage automatique de Gestion MP PRO sur le Mac de l'usine : le serveur part à l'ouverture
# de la session et repart seul s'il tombe ou s'il est tué (agent launchd
# « fr.usine.gestion-mp-pro », ARCHITECTURE § 13.2). C'est un réglage du Mac : rien n'est fait
# tant que l'utilisateur du Mac ne lance pas ce script lui-même.
#
#   deploiement/mac/installer_demarrage_automatique.sh             # installer (ou mettre à jour)
#   deploiement/mac/installer_demarrage_automatique.sh --retirer   # revenir au raccourci seul
#   … --etiquette fr.usine.gestion-mp-pro.essai                     # agent d'essai (avec
#     GESTIONMPPRO_BASE et GESTIONMPPRO_PORT d'une base d'essai)
#
# Le serveur est scripts/demarrer.sh dans sa copie installée (installer.sh d'abord). Pour
# servir une nouvelle version : launchctl kickstart -k gui/$(id -u)/fr.usine.gestion-mp-pro.
# Gestion MP (agent « ma.gestion-mp », port 8030) n'est jamais touché.
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
. "$ICI/commun.sh"
garder_la_base

ETIQUETTE="$ETIQUETTE_DEFAUT" RETIRER=0
while [ $# -gt 0 ]; do
  case "$1" in
    --retirer) RETIRER=1; shift ;;
    --etiquette) ETIQUETTE="${2:?--etiquette demande un nom}"; shift 2 ;;
    *) echouer "option inconnue : $1" ;;
  esac
done
case "$ETIQUETTE" in
  fr.usine.gestion-mp-pro | fr.usine.gestion-mp-pro.*) ;;
  *) echouer "étiquette « $ETIQUETTE » refusée : fr.usine.gestion-mp-pro[.…] seulement." ;;
esac
DOMAINE="gui/$(id -u)"
PLIST="$HOME/Library/LaunchAgents/$ETIQUETTE.plist"

if [ "$RETIRER" = 1 ]; then
  launchctl bootout "$DOMAINE/$ETIQUETTE" 2>/dev/null || true
  rm -f "$PLIST"
  # launchd arrête le serveur avec l'agent ; on attend que le port soit rendu.
  for _ in $(seq 1 40); do [ -n "$(pids_pro)" ] || break; sleep 0.5; done
  dire "Démarrage automatique retiré ($ETIQUETTE) : lancer Gestion MP PRO par le raccourci du bureau."
  exit 0
fi

DEMARRER="$OUTILS/demarrer.sh"
[ -x "$DEMARRER" ] || echouer "pas installé sur ce Mac ($DEMARRER absent) : lancer d'abord deploiement/mac/installer.sh."
# Un serveur lancé à la main tiendrait le port : launchd le reprend.
if [ -n "$(pids_pro)" ] && ! launchctl print "$DOMAINE/$ETIQUETTE" >/dev/null 2>&1; then
  "$OUTILS/arreter.sh" >/dev/null
fi

# Les valeurs vont dans du XML puis dans sed : & < > échappés pour l'un, | & \ pour l'autre.
xml() { printf '%s' "$1" | sed -e 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'; }
valeur() { xml "$1" | sed -e 's/[|&\\]/\\&/g'; }
mkdir -p "$HOME/Library/LaunchAgents" "$JOURNAUX"
# L'agent porte la base et le port de cette instance, et les réglages donnés à l'appel ; jamais de
# secret ici (le mot de passe SMTP va dans le fichier « environnement » du poste, 0600).
VARIABLES="$(mktemp)"
trap 'rm -f "$VARIABLES" "$PLIST.nouveau"' EXIT
for nom in BASE PORT ECOUTE JOURNAL_FICHIER SAUVEGARDES SAUVEGARDES_COPIE PIECES PG_BIN HTTPS ADRESSE; do
  case "$nom:$_GMPPRO_DONNEES" in BASE:* | PORT:* | *" GESTIONMPPRO_$nom "*) ;; *) continue ;; esac
  v="$(eval "printf '%s' \"\${GESTIONMPPRO_$nom:-}\"")"
  [ -z "$v" ] || printf '    <key>GESTIONMPPRO_%s</key><string>%s</string>\n' "$nom" "$(xml "$v")" >>"$VARIABLES"
done
sed -e "s|@@ETIQUETTE@@|$(valeur "$ETIQUETTE")|" \
  -e "s|@@DEMARRER@@|$(valeur "$DEMARRER")|" \
  -e "s|@@APPLI@@|$(valeur "$APPLI")|" \
  -e "s|@@SORTIE@@|$(valeur "$JOURNAUX/launchd$SUFFIXE.log")|" \
  "$ICI/fr.usine.gestion-mp-pro.plist" \
  | awk -v f="$VARIABLES" '/@@VARIABLES@@/ { while ((getline l < f) > 0) print l; next } { print }' \
    >"$PLIST.nouveau"
plutil -lint -s "$PLIST.nouveau" || { rm -f "$PLIST.nouveau"; echouer "agent launchd mal formé."; }
mv "$PLIST.nouveau" "$PLIST"
launchctl bootout "$DOMAINE/$ETIQUETTE" 2>/dev/null || true
launchctl bootstrap "$DOMAINE" "$PLIST"
# Après une mise à jour, la première copie figée construit l'écran : plusieurs minutes au besoin.
for _ in $(seq 1 600); do
  [ "$(etat_http)" = 200 ] && break
  sleep 0.5
done
if [ "$(etat_http)" = 200 ]; then
  dire "Démarrage automatique installé ($PLIST) : Gestion MP PRO répond sur le port $GESTIONMPPRO_PORT."
else
  dire "Agent installé ($PLIST), mais Gestion MP PRO ne répond pas encore : voir $JOURNAUX." >&2
  exit 1
fi
