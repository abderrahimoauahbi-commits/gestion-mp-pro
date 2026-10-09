#!/bin/bash
# Épreuve de scripts/sauvegarder.sh et scripts/restaurer.sh (lot X2) sur une base d'ESSAI :
# restauration tout ou rien, pièces jointes comprises, table née après la sauvegarde retirée,
# migration à head d'une sauvegarde plus ancienne (0003), refus (base gestion_mp, autre base,
# fichier abîmé, confirmation absente, serveur en marche) sans rien changer.
#
#   GESTIONMPPRO_BASE=postgresql+psycopg://gestion_mp_pro@localhost/gestion_mp_pro_x2_poste_essai \
#   GESTIONMPPRO_PORT=8150 GESTIONMPPRO_SAUVEGARDES=… GESTIONMPPRO_PIECES=… \
#   essais/sauvegarde_restauration.sh
#
# Prérequis : deploiement/mac/installer.sh lancé avec les mêmes variables ; serveur arrêté.
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
. "$ICI/../deploiement/mac/commun.sh"
case "$BASE_NOM" in *_essai) ;; *) echouer "épreuve réservée à une base *_essai (ici $BASE_NOM)." ;; esac
[ -n "${GESTIONMPPRO_SAUVEGARDES:-}" ] && [ -n "${GESTIONMPPRO_PIECES:-}" ] \
  || echouer "donner GESTIONMPPRO_SAUVEGARDES et GESTIONMPPRO_PIECES (dossiers d'essai)."
OUT="$OUTILS"
DOSSIER="$GESTIONMPPRO_SAUVEGARDES/$BASE_NOM"
PIECES="$GESTIONMPPRO_PIECES/$BASE_NOM"
URL="$(printf '%s' "$GESTIONMPPRO_BASE" | sed 's#^postgresql+psycopg#postgresql#')"
sql() { psql -X -q -At -v ON_ERROR_STOP=1 "$URL" -c "$1"; }
ok=0 ko=0
verifier() { if (eval "$2"); then ok=$((ok + 1)); dire "  ok  $1"; else ko=$((ko + 1)); dire "  KO  $1"; fi; }
dernier() { ls -t "$DOSSIER"/gestion-mp-pro-*-"$1".dump 2>/dev/null | head -n 1; }
ville() { sql "SELECT valeur FROM parametre WHERE cle = 'ville'"; }
SORTIE="$(mktemp)"
AUTRE_BASE="${BASE_NOM%_essai}_autre_essai"
nettoyer() { rm -f "$SORTIE"; dropdb --if-exists "$AUTRE_BASE" 2>/dev/null; rm -rf "$GESTIONMPPRO_SAUVEGARDES/$AUTRE_BASE" "$GESTIONMPPRO_PIECES/$AUTRE_BASE"; }
trap nettoyer EXIT
restaurer() { "$OUT/restaurer.sh" "$@" >"$SORTIE" 2>&1; r=$?; sed 's/^/      /' "$SORTIE"; return $r; }

dire "Sauvegarde et restauration : base $BASE_NOM ($DOSSIER)"
"$OUT/arreter.sh" >/dev/null
poste migrer >/dev/null
sql "UPDATE parametre SET valeur = 'Avant X2' WHERE cle = 'ville'"
mkdir -p "$PIECES/reception/1"
printf 'bon de réception %s\n' "$$" >"$PIECES/reception/1/bon.pdf"
"$OUT/sauvegarder.sh" >/dev/null
A="$(dernier manuelle)"
verifier "sauvegarde manuelle écrite et son archive de pièces à côté" "[ -f '$A' ] && [ -f '$A.pieces.tar' ]"
verifier "la sauvegarde manuelle est au journal de la base" "[ \"\$(sql \"SELECT count(*) FROM journal WHERE action = 'sauvegarde' AND detail = '$(basename "$A")'\")\" = 1 ]"

# Ce qui change après la sauvegarde : une valeur, une pièce perdue, une table née après.
sql "UPDATE parametre SET valeur = 'Après X2' WHERE cle = 'ville'"
rm -f "$PIECES/reception/1/bon.pdf"
sql "CREATE TABLE nee_apres_x2 (id int)"

restaurer "$A" && r=0 || r=$?
verifier "sans confirmation (pas de terminal) : refusé, rien changé" "[ $r != 0 ] && [ \"\$(ville)\" = 'Après X2' ]"
restaurer "$A" --confirmation NON && r=0 || r=$?
verifier "confirmation fausse : refusé, rien changé" "[ $r != 0 ] && [ \"\$(ville)\" = 'Après X2' ]"
GESTIONMPPRO_BASE=postgresql+psycopg:///gestion_mp restaurer "$A" --confirmation RESTAURER && r=0 || r=$?
verifier "sur la base gestion_mp (Gestion MP) : refusé avant toute connexion" "[ $r != 0 ]"
head -c 2000 "$A" >"$DOSSIER/gestion-mp-pro-2026-01-01-000000-manuelle.dump"
restaurer gestion-mp-pro-2026-01-01-000000-manuelle.dump --confirmation RESTAURER && r=0 || r=$?
verifier "fichier abîmé : refusé, rien changé" "[ $r != 0 ] && [ \"\$(ville)\" = 'Après X2' ]"
rm -f "$DOSSIER/gestion-mp-pro-2026-01-01-000000-manuelle.dump"
# La sauvegarde d'une autre base de Gestion MP PRO, posée dans le dossier de celle-ci.
createdb -O gestion_mp_pro "$AUTRE_BASE"
AUTRE_URL="${GESTIONMPPRO_BASE%/*}/$AUTRE_BASE"
GESTIONMPPRO_BASE="$AUTRE_URL" bash -c '. "$1"; poste migrer >/dev/null' _ "$ICI/../deploiement/mac/commun.sh"
AUTRE="$(GESTIONMPPRO_BASE="$AUTRE_URL" "$OUT/sauvegarder.sh")"
cp "$AUTRE" "$DOSSIER/gestion-mp-pro-2026-01-02-000000-manuelle.dump"
restaurer gestion-mp-pro-2026-01-02-000000-manuelle.dump --confirmation RESTAURER && r=0 || r=$?
verifier "sauvegarde d'une autre base ($AUTRE_BASE) : refusée, rien changé" "[ $r != 0 ] && [ \"\$(ville)\" = 'Après X2' ]"
rm -f "$DOSSIER/gestion-mp-pro-2026-01-02-000000-manuelle.dump"
restaurer "$DOSSIER/../ailleurs.dump" --confirmation RESTAURER && r=0 || r=$?
verifier "fichier hors du dossier de la base : refusé" "[ $r != 0 ]"

(nohup "$OUT/demarrer.sh" >/dev/null 2>&1 &)
for _ in $(seq 1 60); do [ "$(etat_http)" = 200 ] && break; sleep 0.5; done
restaurer "$A" --confirmation RESTAURER && r=0 || r=$?
verifier "serveur de cette base en marche : refusé, rien changé" "[ $r != 0 ] && [ \"\$(ville)\" = 'Après X2' ]"
"$OUT/arreter.sh" >/dev/null

restaurer "$A" --confirmation RESTAURER --motif "épreuve X2" && r=0 || r=$?
verifier "restauration acceptée" "[ $r = 0 ]"
verifier "la valeur sauvegardée est revenue" "[ \"\$(ville)\" = 'Avant X2' ]"
verifier "la pièce jointe perdue est revenue" "[ -f '$PIECES/reception/1/bon.pdf' ]"
verifier "la table née après la sauvegarde n'existe plus" "[ \"\$(sql \"SELECT to_regclass('nee_apres_x2') IS NULL\")\" = t ]"
verifier "sauvegarde « avant restauration » faite" "[ -n \"\$(dernier avant-restauration)\" ]"
verifier "journal « restauration » écrit dans la base restaurée" "[ \"\$(sql \"SELECT count(*) FROM journal WHERE action = 'restauration' AND detail LIKE '$(basename "$A") — épreuve X2%'\")\" = 1 ]"

# Une sauvegarde d'une version plus ancienne (schéma 0003) revient migrée à head.
PY="$(python_de "$VERSION_DIR")"
(cd "$VERSION_DIR/backend" && PYTHONPATH="$VERSION_DIR/backend" "$PY" -c \
  "from alembic import command; from gestion_mp_pro.services.installation import configuration; command.downgrade(configuration(), '0003')")
verifier "base descendue à 0003 pour l'épreuve" "[ \"\$(sql 'SELECT version_num FROM alembic_version')\" = 0003 ]"
"$OUT/sauvegarder.sh" >/dev/null
ANCIENNE="$(dernier manuelle)"
poste migrer >/dev/null
sql "UPDATE parametre SET valeur = 'Après 0003' WHERE cle = 'ville'"
restaurer "$ANCIENNE" --confirmation RESTAURER && r=0 || r=$?
verifier "sauvegarde à 0003 restaurée puis migrée à head (0004)" "[ $r = 0 ] && [ \"\$(sql 'SELECT version_num FROM alembic_version')\" = 0004 ] && [ \"\$(ville)\" = 'Avant X2' ]"

# Une autre version que celle en service : demarrer.sh refait la copie et sauvegarde d'abord.
COMMIT="$(cat "$VERSION_DIR/VERSION")"
printf '0000000\n' >"$VERSION_DIR/VERSION"
AVANT_MAJ="$(dernier avant-mise-a-jour)"
"$OUT/demarrer.sh" --preparer >/dev/null
verifier "nouvelle version : sauvegarde « avant mise à jour » faite, copie refaite ($COMMIT)" "[ -n \"\$(dernier avant-mise-a-jour)\" ] && [ \"\$(dernier avant-mise-a-jour)\" != '$AVANT_MAJ' ] && [ \"\$(cat '$VERSION_DIR/VERSION')\" = '$COMMIT' ]"
compter() { ls "$DOSSIER"/gestion-mp-pro-*-avant-mise-a-jour.dump 2>/dev/null | wc -l | tr -d ' '; }
N1="$(compter)"
"$OUT/demarrer.sh" --preparer >/dev/null
verifier "même version : rien n'est refait ni sauvegardé" "[ \"\$(compter)\" = '$N1' ]"

dire "Sauvegarde et restauration : $ok vérification(s) tenue(s), $ko en défaut."
[ "$ko" = 0 ]
