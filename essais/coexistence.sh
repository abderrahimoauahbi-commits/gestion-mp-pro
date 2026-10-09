#!/bin/bash
# Coexistence de Gestion MP PRO avec Gestion MP en service sur le même Mac (lot X2) : le
# tableau ARCHITECTURE § 14.1 vérifié point par point, PRO démarré puis arrêté pendant que
# Gestion MP est lu sans cesse (son /api/sante, toutes les 0,5 s : il doit toujours répondre,
# avec le même processus et la même version). Gestion MP n'est jamais démarré, arrêté, ni
# écrit : on lit son /api/sante, ses processus (lsof, ps) et quelques fichiers de son poste.
# Aucune connexion à la base gestion_mp : les catalogues partagés du serveur PostgreSQL
# (pg_database, pg_roles, pg_shdepend, pg_stat_activity, pg_locks) suffisent.
#
#   essais/coexistence.sh            # l'installation du poste : 127.0.0.1:8050, base gestion_mp_pro
#
# À la fin, PRO est remis dans l'état trouvé (arrêté, ou relancé s'il tournait).
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
. "$ICI/../deploiement/mac/commun.sh"
[ -x "$OUTILS/demarrer.sh" ] || echouer "Gestion MP PRO n'est pas installé ($OUTILS) : deploiement/mac/installer.sh."
PROJET="$(cat "$OUTILS/PROJET")"  # le projet de l'installation, pas ce dépôt-ci
GMP_PORT=8030
GMP_SANTE="http://127.0.0.1:$GMP_PORT/api/sante"
GMP_PROJET="$HOME/gestion-mp"
GMP_APPLI="$HOME/Library/Application Support/Gestion MP"
GMP_SAUVEGARDES="$HOME/gestion-mp-sauvegardes"
GMP_PIECES="$HOME/gestion-mp-pieces"
GMP_JOURNAL="$HOME/Library/Logs/Gestion MP.log"
GMP_RACCOURCI="$HOME/Desktop/Gestion MP.app"
TRAVAIL="$(mktemp -d "${TMPDIR:-/tmp}/coexistence.XXXXXX")"
ok=0 ko=0
verifier() { if (eval "$2"); then ok=$((ok + 1)); dire "  ok  $1"; else ko=$((ko + 1)); dire "  KO  $1"; fi; }
point() { printf '\n%s\n' "$*"; }
pg() { psql -X -q -At -d postgres -c "$1"; }
gmp_pid() { lsof -nP -tiTCP:"$GMP_PORT" -sTCP:LISTEN 2>/dev/null | sort | tr '\n' ' ' | sed 's/ $//'; }
gmp_version() { curl -s --max-time 3 "$GMP_SANTE" | sed -n 's/.*"version":"\([^"]*\)".*/\1/p'; }
pro_version() { curl -s --max-time 3 "http://127.0.0.1:$GESTIONMPPRO_PORT/api/sante" | sed -n 's/.*"version":"\([^"]*\)".*/\1/p'; }
# Pas d'imbrication entre deux dossiers (l'un dans l'autre ou égaux).
separes() { case "$1/" in "$2"/*) return 1 ;; esac; case "$2/" in "$1"/*) return 1 ;; esac; return 0; }
instantane() { ls -la "$@" 2>/dev/null | md5; }
fichiers_ouverts() { lsof -p "$1" -Fn 2>/dev/null | sed -n 's/^n//p'; }

# Gestion MP lu en continu pendant toute l'épreuve : une ligne par réponse.
guetter() { while :; do curl -s -o /dev/null -w '%{http_code}\n' --max-time 2 "$GMP_SANTE" >>"$TRAVAIL/guet"; sleep 0.5; done; }
ETAIT_EN_MARCHE=""
[ -z "$(pids_pro)" ] || ETAIT_EN_MARCHE=1
finir() {
  [ -z "${GUET:-}" ] || kill "$GUET" 2>/dev/null
  if [ -n "$ETAIT_EN_MARCHE" ] && [ -z "$(pids_pro)" ]; then (nohup "$OUTILS/demarrer.sh" >>"$JOURNAUX/lanceur.log" 2>&1 &); fi
  rm -rf "$TRAVAIL"
}
trap finir EXIT

dire "Coexistence Gestion MP ($GMP_PORT) / Gestion MP PRO ($GESTIONMPPRO_PORT, base $BASE_NOM) — $(date '+%Y-%m-%d %H:%M')"
point "0. Gestion MP en service avant l'épreuve"
GMP_PID="$(gmp_pid)"
GMP_VERSION="$(gmp_version)"
verifier "Gestion MP répond sur $GMP_PORT (processus $GMP_PID, version $GMP_VERSION)" "[ -n '$GMP_PID' ] && [ -n '$GMP_VERSION' ]"
AVANT_COPIE="$(instantane "$GMP_APPLI/version/VERSION" "$GMP_APPLI")"
AVANT_RACCOURCI="$(find "$GMP_RACCOURCI" -type f -exec md5 -q {} \; 2>/dev/null | md5)"
AVANT_PIECES="$(find "$GMP_PIECES" 2>/dev/null | grep -c 'gestion-mp-pro\|gestion_mp_pro')"
guetter &
GUET=$!

point "Démarrage de PRO par son raccourci (navigateur remplacé par un écho ; variables GESTION_MP_* hostiles)"
"$OUTILS/arreter.sh" >/dev/null
LANCEUR="$TRAVAIL/lanceur"
if [ -x "$RACCOURCI/Contents/MacOS/Gestion-MP-PRO" ] && [ "$GESTIONMPPRO_PORT" = 8050 ]; then
  sed -e 's|/usr/bin/open|printf "ouvrir %s\\n"|' -e 's|/usr/bin/osascript|printf "alerte %s\\n"|' \
    "$RACCOURCI/Contents/MacOS/Gestion-MP-PRO" >"$LANCEUR"
else
  printf '#!/bin/bash\nnohup "%s/demarrer.sh" >/dev/null 2>&1 &\nfor i in $(seq 1 1200); do [ "$(curl -s -o /dev/null -w %%{http_code} http://127.0.0.1:%s/api/sante)" = 200 ] && break; sleep 0.5; done\nprintf "ouvrir http://localhost:%s\\n"\n' "$OUTILS" "$GESTIONMPPRO_PORT" "$GESTIONMPPRO_PORT" >"$LANCEUR"
fi
GESTION_MP_PORT=8999 GESTION_MP_BASE=postgresql+psycopg:///gestion_mp GESTION_MP_ECOUTE=0.0.0.0 \
  bash "$LANCEUR" >"$TRAVAIL/lanceur.1" 2>&1
PRO_PID="$(pids_pro | tr '\n' ' ' | sed 's/ $//')"
verifier "le raccourci a démarré PRO (processus $PRO_PID) puis ouvert $(cat "$TRAVAIL/lanceur.1")" "[ \"\$(etat_http)\" = 200 ] && [ -n '$PRO_PID' ] && grep -qx 'ouvrir http://localhost:$GESTIONMPPRO_PORT' '$TRAVAIL/lanceur.1'"
bash "$LANCEUR" >"$TRAVAIL/lanceur.2" 2>&1
verifier "second double-clic : il ouvre seulement, même processus" "grep -qx 'ouvrir http://localhost:$GESTIONMPPRO_PORT' '$TRAVAIL/lanceur.2' && [ \"\$(pids_pro | tr '\n' ' ' | sed 's/ \$//')\" = '$PRO_PID' ]"

point "1. Dossier du projet : $GMP_PROJET / $PROJET"
verifier "dossiers distincts, aucun dans l'autre" "separes '$GMP_PROJET' '$PROJET'"
verifier "PRO n'a aucun fichier ouvert dans ~/gestion-mp" "! fichiers_ouverts $PRO_PID | grep -q '^$GMP_PROJET/'"

point "2. Port : $GMP_PORT / $GESTIONMPPRO_PORT"
verifier "ports différents" "[ '$GMP_PORT' != '$GESTIONMPPRO_PORT' ]"
verifier "les variables GESTION_MP_* n'ont pas déplacé PRO (rien sur 8999)" "[ -z \"\$(lsof -nP -tiTCP:8999 -sTCP:LISTEN)\" ]"
verifier "PRO n'écoute que sur 127.0.0.1:$GESTIONMPPRO_PORT" "[ \"\$(lsof -nP -a -p ${PRO_PID%% *} -iTCP -sTCP:LISTEN -Fn | sed -n 's/^n//p' | sort -u)\" = '127.0.0.1:$GESTIONMPPRO_PORT' ]"
verifier "processus disjoints : celui de $GMP_PORT n'est pas celui de $GESTIONMPPRO_PORT" "[ -z \"\$(comm -12 <(printf '%s\n' $GMP_PID | sort) <(printf '%s\n' $PRO_PID | sort))\" ]"
verifier "Gestion MP écoute toujours sur $GMP_PORT, même processus" "[ \"\$(gmp_pid)\" = '$GMP_PID' ]"

point "3. Base : gestion_mp / $BASE_NOM"
verifier "bases différentes" "[ '$BASE_NOM' != gestion_mp ]"
ETAT="$(poste etat)"
verifier "PRO travaille sur $BASE_NOM, connecté en gestion_mp_pro, à la révision attendue" "printf '%s' '$ETAT' | grep -q '\"base\": \"$BASE_NOM\".*\"utilisateur\": \"gestion_mp_pro\".*\"revision\": \"\\([0-9]*\\)\", \"attendue\": \"\\1\"'"
verifier "connexions à $BASE_NOM : rôle gestion_mp_pro seulement (hors administration)" "[ -z \"\$(pg \"SELECT DISTINCT usename FROM pg_stat_activity WHERE datname = '$BASE_NOM' AND usename NOT IN ('gestion_mp_pro', current_user) AND pid <> pg_backend_pid()\")\" ]"
verifier "aucune connexion du rôle gestion_mp_pro à gestion_mp" "[ \"\$(pg \"SELECT count(*) FROM pg_stat_activity WHERE datname = 'gestion_mp' AND usename = 'gestion_mp_pro'\")\" = 0 ]"
verifier "le serveur PRO tient des connexions à $BASE_NOM seulement" "[ \"\$(pg \"SELECT string_agg(DISTINCT datname, ',') FROM pg_stat_activity WHERE usename = 'gestion_mp_pro'\")\" = '$BASE_NOM' ]"

point "4. Rôle PostgreSQL : utilisateur du Mac / gestion_mp_pro"
verifier "gestion_mp_pro : ni superutilisateur, ni création de base ou de rôle" "[ \"\$(pg \"SELECT rolsuper OR rolcreatedb OR rolcreaterole FROM pg_roles WHERE rolname = 'gestion_mp_pro'\")\" = f ]"
verifier "gestion_mp_pro n'est propriétaire que de bases gestion_mp_pro*" "[ -z \"\$(pg \"SELECT datname FROM pg_database WHERE datdba = 'gestion_mp_pro'::regrole AND datname NOT LIKE 'gestion\\_mp\\_pro%'\")\" ]"
verifier "gestion_mp_pro ne possède rien et n'a reçu aucun droit dans gestion_mp (pg_shdepend)" "[ \"\$(pg \"SELECT count(*) FROM pg_shdepend s JOIN pg_database d ON d.oid = s.dbid WHERE d.datname = 'gestion_mp' AND s.refobjid = 'gestion_mp_pro'::regrole\")\" = 0 ]"
verifier "gestion_mp appartient toujours à l'utilisateur du Mac" "[ \"\$(pg \"SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = 'gestion_mp'\")\" != gestion_mp_pro ]"
verifier "$BASE_NOM fermée à PUBLIC (CONNECT retiré)" "[ \"\$(pg \"SELECT datacl IS NOT NULL AND NOT EXISTS (SELECT 1 FROM aclexplode(datacl) a WHERE a.grantee = 0 AND a.privilege_type = 'CONNECT') FROM pg_database WHERE datname = '$BASE_NOM'\")\" = t ]"

point "5. Copie figée : $GMP_APPLI/version / $VERSION_DIR"
verifier "dossiers distincts, aucun dans l'autre" "separes '$GMP_APPLI' '$VERSION_DIR'"
verifier "/api/sante de PRO dit le VERSION de sa copie figée ($(cat "$VERSION_DIR/VERSION"))" "[ \"\$(pro_version)\" = \"\$(cat '$VERSION_DIR/VERSION')\" ]"
verifier "le serveur tourne dans la copie (répertoire courant $VERSION_DIR/backend)" "[ \"\$(lsof -a -p ${PRO_PID%% *} -d cwd -Fn | sed -n 's/^n//p')\" = '$VERSION_DIR/backend' ]"
verifier "la copie de Gestion MP n'a pas bougé (VERSION $(cat "$GMP_APPLI/version/VERSION" 2>/dev/null))" "[ \"\$(instantane '$GMP_APPLI/version/VERSION' '$GMP_APPLI')\" = '$AVANT_COPIE' ]"

point "6. Sauvegardes : $GMP_SAUVEGARDES / ~/gestion-mp-pro-sauvegardes"
PRO_SAUVEGARDES="$(printf '%s' "$ETAT" | sed -n 's/.*"sauvegardes": "\([^"]*\)".*/\1/p')"
verifier "dossier de PRO : $PRO_SAUVEGARDES" "separes '$GMP_SAUVEGARDES' '$PRO_SAUVEGARDES' && separes '$GMP_SAUVEGARDES' '$(dirname "$PRO_SAUVEGARDES")'"
verifier "aucun fichier de PRO dans les sauvegardes de Gestion MP" "! ls '$GMP_SAUVEGARDES' 2>/dev/null | grep -q 'gestion-mp-pro'"
verifier "aucun fichier de Gestion MP dans celles de PRO" "! ls '$PRO_SAUVEGARDES' 2>/dev/null | grep -v '^gestion-mp-pro-' | grep -q ."

point "7. Pièces jointes : $GMP_PIECES / ~/gestion-mp-pro-pieces"
PRO_PIECES="$(printf '%s' "$ETAT" | sed -n 's/.*"pieces": "\([^"]*\)".*/\1/p')"
verifier "dossier de PRO : $PRO_PIECES" "separes '$GMP_PIECES' '$PRO_PIECES' && separes '$GMP_PIECES' '$(dirname "$PRO_PIECES")'"
verifier "rien de PRO dans les pièces de Gestion MP" "[ \"\$(find '$GMP_PIECES' 2>/dev/null | grep -c 'gestion-mp-pro\|gestion_mp_pro')\" = '$AVANT_PIECES' ]"

point "8. Journal du serveur : $GMP_JOURNAL / $JOURNAUX/"
verifier "PRO écrit son journal dans $GESTIONMPPRO_JOURNAL_FICHIER" "grep -q 'Gestion MP PRO .* prêt' '$GESTIONMPPRO_JOURNAL_FICHIER'"
verifier "PRO n'a ouvert aucun fichier du poste de Gestion MP (journal, sauvegardes, pièces, copie)" "! fichiers_ouverts ${PRO_PID%% *} | grep -q -e '$GMP_JOURNAL' -e '^$GMP_SAUVEGARDES/' -e '^$GMP_PIECES/' -e '^$GMP_APPLI/'"
verifier "Gestion MP n'a ouvert aucun fichier de PRO" "! { for p in $GMP_PID; do fichiers_ouverts \$p; done | grep -q -e 'Gestion MP PRO' -e 'gestion-mp-pro'; }"

point "9. Raccourci : $GMP_RACCOURCI / $RACCOURCI"
info() { plutil -extract "$2" raw "$1/Contents/Info.plist" 2>/dev/null; }
verifier "les deux raccourcis sont sur le bureau" "[ -d '$GMP_RACCOURCI' ] && [ -d '$RACCOURCI' ]"
verifier "noms différents ($(info "$GMP_RACCOURCI" CFBundleName) / $(info "$RACCOURCI" CFBundleName))" "[ \"\$(info '$RACCOURCI' CFBundleName)\" = 'Gestion MP PRO' ] && [ \"\$(info '$GMP_RACCOURCI' CFBundleName)\" != 'Gestion MP PRO' ]"
verifier "identifiants différents ($(info "$GMP_RACCOURCI" CFBundleIdentifier) / $(info "$RACCOURCI" CFBundleIdentifier))" "[ -n \"\$(info '$RACCOURCI' CFBundleIdentifier)\" ] && [ \"\$(info '$RACCOURCI' CFBundleIdentifier)\" != \"\$(info '$GMP_RACCOURCI' CFBundleIdentifier)\" ]"
verifier "icônes différentes" "a=\$(md5 -q '$RACCOURCI/Contents/Resources/'*.icns 2>/dev/null) && b=\$(md5 -q '$GMP_RACCOURCI/Contents/Resources/'*.icns) && [ \"\$a\" != \"\$b\" ]"
verifier "le raccourci de PRO ouvre le port 8050 ; hors commentaires, rien de Gestion MP (8030, ~/gestion-mp, GESTION_MP_*)" "grep -q '^PORT=8050\$' '$RACCOURCI/Contents/MacOS/'* && ! grep -v '^#' '$RACCOURCI/Contents/MacOS/'* | grep -q '8030\|gestion-mp/\|GESTION_MP_'"
verifier "le raccourci de Gestion MP n'a pas bougé" "[ \"\$(find '$GMP_RACCOURCI' -type f -exec md5 -q {} \\; | md5)\" = '$AVANT_RACCOURCI' ]"

point "10. Démarrage : double-clic / agent $ETIQUETTE_DEFAUT"
verifier "étiquette de PRO distincte de celle de Gestion MP (ma.gestion-mp)" "[ '$ETIQUETTE_DEFAUT' != ma.gestion-mp ]"
verifier "un agent de PRO éventuel ne cite rien de Gestion MP" "! grep -q -e 'gestion-mp/' -e ':8030' -e 'GESTION_MP_' \"\$HOME/Library/LaunchAgents/$ETIQUETTE_DEFAUT.plist\" 2>/dev/null"

point "11. Cookie de session : gestion_mp_session / gestion_mp_pro_session"
CONSTANTES="$(cd "$VERSION_DIR/backend" && PYTHONPATH=. "$(python_de "$VERSION_DIR")" -c 'from gestion_mp_pro import config as c, db; print(c.COOKIE_SESSION, c.COOKIE_APPAREIL, c.ENTETE_ANTI_FALSIFICATION, " ".join(str(int(v)) for v in db.VERROUS))')"
set -- $CONSTANTES
COOKIE_PRO="$1" APPAREIL_PRO="$2" ENTETE_PRO="$3"; shift 3; VERROUS_PRO="$*"
COOKIE_GMP="$(sed -n 's/^COOKIE = "\(.*\)"/\1/p' "$GMP_PROJET/gestion_mp/securite.py")"
verifier "noms différents ($COOKIE_GMP / $COOKIE_PRO, appareil $APPAREIL_PRO)" "[ -n '$COOKIE_GMP' ] && [ '$COOKIE_PRO' = gestion_mp_pro_session ] && [ '$COOKIE_PRO' != '$COOKIE_GMP' ] && [ '$APPAREIL_PRO' != '$COOKIE_GMP' ]"

point "12. En-tête anti-falsification : X-Gestion-MP / $ENTETE_PRO"
CODE="$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'X-Gestion-MP: 1' "http://127.0.0.1:$GESTIONMPPRO_PORT/api/sauvegardes")"
verifier "une écriture avec l'en-tête de Gestion MP est refusée par PRO ($CODE), rien n'est fait" "[ '$ENTETE_PRO' = X-Gestion-MP-PRO ] && [ '$CODE' = 403 ]"

point "13. Verrous consultatifs : 7426101–7426110 / 7426201–7426209"
VERROUS_GMP="$(grep -rhoE '74261[0-9]{2}' "$GMP_PROJET/gestion_mp" --include='*.py' | sort -u | tr '\n' ' ')"
verifier "numéros de PRO ($VERROUS_PRO) dans 7426201–7426209" "for v in $VERROUS_PRO; do [ \$v -ge 7426201 ] && [ \$v -le 7426209 ] || exit 1; done"
verifier "aucun numéro commun avec Gestion MP ($VERROUS_GMP)" "[ -z \"\$(comm -12 <(printf '%s\n' $VERROUS_PRO | sort) <(printf '%s\n' $VERROUS_GMP | sort))\" ]"
verifier "verrous tenus sur $BASE_NOM : tous dans la plage de PRO" "[ -z \"\$(pg \"SELECT objid FROM pg_locks l JOIN pg_database d ON d.oid = l.database WHERE l.locktype = 'advisory' AND d.datname = '$BASE_NOM' AND l.objid NOT BETWEEN 7426201 AND 7426209\")\" ]"
verifier "aucun verrou de la plage de PRO sur gestion_mp" "[ \"\$(pg \"SELECT count(*) FROM pg_locks l JOIN pg_database d ON d.oid = l.database WHERE l.locktype = 'advisory' AND d.datname = 'gestion_mp' AND l.objid BETWEEN 7426201 AND 7426209\")\" = 0 ]"

point "14. Variables : GESTION_MP_* / GESTIONMPPRO_*"
verifier "PRO lancé avec GESTION_MP_PORT=8999 et GESTION_MP_BASE=gestion_mp : toujours $GESTIONMPPRO_PORT et $BASE_NOM" "[ \"\$(etat_http)\" = 200 ] && [ -z \"\$(lsof -nP -tiTCP:8999 -sTCP:LISTEN)\" ] && [ \"\$(pg \"SELECT count(*) FROM pg_stat_activity WHERE datname = 'gestion_mp' AND usename = 'gestion_mp_pro'\")\" = 0 ]"
verifier "les scripts de PRO ne lisent aucune variable GESTION_MP_*" "! grep -q 'GESTION_MP_' '$OUTILS/'*.sh '$OUTILS/poste.py'"

point "15. Application au téléphone : « Gestion MP » / « Gestion MP PRO »"
NOM_PRO="$(curl -s --max-time 3 "http://127.0.0.1:$GESTIONMPPRO_PORT/manifest.webmanifest" | sed -n 's/.*"name": *"\([^"]*\)".*/\1/p')"
NOM_GMP="$(sed -n 's/.*"name": *"\([^"]*\)".*/\1/p' "$GMP_APPLI/version/ecran/manifest.webmanifest" 2>/dev/null | head -n 1)"
verifier "manifestes de noms différents (« $NOM_GMP » / « $NOM_PRO »), autre origine (port)" "case '$NOM_PRO' in 'Gestion MP PRO'*) [ '$NOM_PRO' != '$NOM_GMP' ] ;; *) false ;; esac"

point "16. Arrêter PRO n'arrête pas Gestion MP (et inversement)"
verifier "ce qu'arreter.sh de PRO arrêterait ($(pids_pro | tr '\n' ' ')) : ni le processus de Gestion MP, ni rien d'autre que gestion_mp_pro.main" "[ -z \"\$(comm -12 <(pids_pro | sort) <(printf '%s\n' $GMP_PID | sort))\" ] && for p in \$(pids_pro); do ps -o command= -p \$p | grep -q 'gestion_mp_pro.main:app' || exit 1; done"
"$OUTILS/arreter.sh" >/dev/null
verifier "PRO arrêté : port $GESTIONMPPRO_PORT rendu" "[ -z \"\$(pids_sur_le_port)\" ] && [ \"\$(etat_http)\" = 000 ]"
sleep 2
verifier "Gestion MP répond après l'arrêt de PRO, même processus, même version" "[ \"\$(curl -s -o /dev/null -w '%{http_code}' '$GMP_SANTE')\" = 200 ] && [ \"\$(gmp_pid)\" = '$GMP_PID' ] && [ \"\$(gmp_version)\" = '$GMP_VERSION' ]"
verifier "arreter.sh de Gestion MP vise son port (8030) seul : il ne peut atteindre PRO" "grep -q 'GESTION_MP_PORT:-8030' '$GMP_PROJET/scripts/arreter.sh' && ! grep -q '8050' '$GMP_PROJET/scripts/arreter.sh'"
kill "$GUET" 2>/dev/null; wait "$GUET" 2>/dev/null; GUET=""
LUES="$(wc -l <"$TRAVAIL/guet" | tr -d ' ')"
MANQUEES="$(grep -vc '^200$' "$TRAVAIL/guet")"
verifier "Gestion MP lu $LUES fois pendant le démarrage, le travail et l'arrêt de PRO : $MANQUEES sans réponse" "[ '$LUES' -ge 5 ] && [ '$MANQUEES' = 0 ]"

printf '\nCoexistence : %s vérification(s) tenue(s), %s en défaut.\n' "$ok" "$ko"
[ "$ko" = 0 ]
