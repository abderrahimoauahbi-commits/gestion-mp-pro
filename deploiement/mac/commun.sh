# Gestion MP PRO — réglages et fonctions communs aux scripts du poste Mac (lot X2).
#
# Lu (`.`) par scripts/{demarrer,arreter,sauvegarder,restaurer}.sh, par installer.sh et par
# installer_demarrage_automatique.sh, depuis le dépôt ou depuis leur copie installée dans
# « ~/Library/Application Support/Gestion MP PRO/outils » (ARCHITECTURE § 13.2, § 14.1).
#
# Rien ici ne vise Gestion MP : port 8050, base gestion_mp_pro, dossiers « Gestion MP PRO »,
# variables GESTIONMPPRO_* seulement. Bash 3.2 (celui du Mac) : rien de plus récent.

# Lancé depuis le Finder ou launchd, le PATH ne contient pas les outils de Homebrew.
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin${PATH:+:$PATH}"
export PATH
export PYTHONUTF8=1 LANG="${LANG:-fr_FR.UTF-8}"
# Sauvegardes, pièces, journaux et copie : lisibles du seul compte du Mac (empreintes des codes).
umask 077

ETIQUETTE_DEFAUT="fr.usine.gestion-mp-pro"
_ici_commun="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Le dossier de l'application : celui qui contient ces outils une fois installés (fichier
# PROJET à côté) ; depuis le dépôt, GESTIONMPPRO_APPLI (essais) ou le dossier du poste.
if [ -f "$_ici_commun/PROJET" ]; then
  APPLI="$(dirname "$_ici_commun")"
else
  APPLI="${GESTIONMPPRO_APPLI:-$HOME/Library/Application Support/Gestion MP PRO}"
fi
OUTILS="$APPLI/outils"
JOURNAUX="$HOME/Library/Logs/Gestion MP PRO"
RACCOURCI="$HOME/Desktop/Gestion MP PRO.app"

# Réglages permanents du poste (SMTP, copie externe…) : « environnement » à côté des outils,
# lignes GESTIONMPPRO_NOM=valeur (valeur prise telle quelle) ; une variable déjà donnée par
# l'appelant (launchd, essai) l'emporte. Fichier 0600 : il peut porter le mot de passe SMTP.
if [ -f "$APPLI/environnement" ]; then
  while IFS= read -r _ligne || [ -n "$_ligne" ]; do
    case "$_ligne" in GESTIONMPPRO_[A-Z]*=*) ;; *) continue ;; esac
    _nom="${_ligne%%=*}"
    case "$_nom" in *[!A-Z_]*) continue ;; esac
    [ -n "$(eval "printf '%s' \"\${$_nom:-}\"")" ] || export "$_nom=${_ligne#*=}"
  done <"$APPLI/environnement"
fi
: "${GESTIONMPPRO_BASE:=postgresql+psycopg://gestion_mp_pro@localhost/gestion_mp_pro}"
: "${GESTIONMPPRO_PORT:=8050}"
: "${GESTIONMPPRO_ECOUTE:=127.0.0.1}"
export GESTIONMPPRO_BASE GESTIONMPPRO_PORT GESTIONMPPRO_ECOUTE
if [ -z "${GESTIONMPPRO_PG_BIN:-}" ] && [ -x /opt/homebrew/opt/postgresql@16/bin/pg_dump ]; then
  GESTIONMPPRO_PG_BIN=/opt/homebrew/opt/postgresql@16/bin
fi
[ -z "${GESTIONMPPRO_PG_BIN:-}" ] || export GESTIONMPPRO_PG_BIN

# Le nom de la base : dernier segment de l'adresse, sans paramètres.
BASE_NOM="$(printf '%s' "$GESTIONMPPRO_BASE" | sed 's#.*/##; s#?.*##')"
# Une copie figée par base : une base d'essai ne remplace jamais la copie en service.
SUFFIXE=""
[ "$BASE_NOM" = "gestion_mp_pro" ] || SUFFIXE="-$BASE_NOM"
VERSION_DIR="$APPLI/version$SUFFIXE"
: "${GESTIONMPPRO_JOURNAL_FICHIER:=$JOURNAUX/serveur$SUFFIXE.log}"
export GESTIONMPPRO_JOURNAL_FICHIER

# Le projet (dépôt git) d'où la version est tirée : la variable, sinon celui noté à
# l'installation, sinon le dépôt qui contient ce fichier.
if [ -n "${GESTIONMPPRO_PROJET:-}" ]; then
  PROJET="$GESTIONMPPRO_PROJET"
elif [ -f "$_ici_commun/PROJET" ]; then
  PROJET="$(cat "$_ici_commun/PROJET")"
else
  PROJET="$(cd "$_ici_commun/../.." && pwd)"
fi
# poste.py est à côté de ce fichier, au dépôt (deploiement/mac) comme une fois installé.
POSTE_PY="$_ici_commun/poste.py"

dire() { printf '%s\n' "$*"; }
echouer() { printf 'Gestion MP PRO : %s\n' "$*" >&2; exit 1; }

# Garde-fou : jamais la base de Gestion MP, ni une base qui n'est pas de Gestion MP PRO.
garder_la_base() {
  case "$BASE_NOM" in
    gestion_mp_pro | gestion_mp_pro_*) ;;
    *) echouer "base « $BASE_NOM » refusée : seules gestion_mp_pro et gestion_mp_pro_* sont de Gestion MP PRO (jamais gestion_mp, celle de Gestion MP)." ;;
  esac
}

# Les processus qui écoutent sur le port de PRO, puis ceux d'entre eux qui sont Gestion MP PRO.
pids_sur_le_port() { lsof -nP -tiTCP:"$GESTIONMPPRO_PORT" -sTCP:LISTEN 2>/dev/null || true; }
est_pro() { ps -o command= -p "$1" 2>/dev/null | grep -q 'gestion_mp_pro\.main:app'; }
pids_pro() {
  for _pid in $(pids_sur_le_port); do
    if est_pro "$_pid"; then printf '%s\n' "$_pid"; fi
  done
}

# L'environnement Python d'une copie (un par version de requirements.lock, partagé entre
# copies) ; `python_de <copie>`.
python_de() {
  _env="$(cat "$1/ENVIRONNEMENT" 2>/dev/null || true)"
  [ -n "$_env" ] && [ -f "$APPLI/python/$_env/.complet" ] || return 1
  printf '%s\n' "$APPLI/python/$_env/bin/python"
}

# Lance poste.py avec le code de la copie figée de cette base (sinon, pour le développement,
# celui du projet et son backend/.venv).
poste() {
  if _py="$(python_de "$VERSION_DIR")"; then
    _code="$VERSION_DIR/backend"
  elif [ -x "$PROJET/backend/.venv/bin/python" ]; then
    _py="$PROJET/backend/.venv/bin/python"
    _code="$PROJET/backend"
  else
    echouer "aucune version installée pour la base $BASE_NOM (lancer deploiement/mac/installer.sh)."
  fi
  (cd "$_code" && PYTHONPATH="$_code" "$_py" "$POSTE_PY" "$@")
}

# `/api/sante` du serveur PRO de ce port : le code HTTP (000 s'il ne répond pas).
etat_http() {
  curl -s -o /dev/null -w '%{http_code}' --max-time "${2:-2}" \
    "http://127.0.0.1:${1:-$GESTIONMPPRO_PORT}/api/sante" 2>/dev/null || true
}
