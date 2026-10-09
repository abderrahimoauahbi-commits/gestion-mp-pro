#!/bin/bash
# Installe Gestion MP PRO sur le Mac de l'usine, à côté de Gestion MP (ARCHITECTURE § 13.2,
# § 14.1). Idempotent : relancé, il ne refait que ce qui manque ou a changé, et ne supprime
# jamais rien (ni rôle, ni base, ni sauvegarde).
#
#   deploiement/mac/installer.sh                         # le poste de l'usine
#   deploiement/mac/installer.sh --projet ~/gestion-mp-pro
#   deploiement/mac/installer.sh --demarrage-automatique # en plus : agent launchd (réglage du Mac)
#   deploiement/mac/installer.sh --sans-raccourci
#
# Fait, dans l'ordre :
#  1. vérifie les outils (PostgreSQL 16 en marche, Python 3.12, Node, git) ;
#  2. installe les scripts du poste dans « ~/Library/Application Support/Gestion MP PRO/outils »
#     (le raccourci et launchd les appellent ; le projet peut changer sans toucher au poste) ;
#  3. crée le rôle PostgreSQL `gestion_mp_pro` et sa base `gestion_mp_pro` s'ils manquent
#     (propriétaire de sa base seulement ; connexion à cette base retirée à PUBLIC) ;
#  4. prépare la copie figée du dernier commit (code, écran construit, environnement Python) ;
#  5. met la base à la révision attendue (schéma et semences ; aucune donnée métier, aucune
#     reprise : `make miroir` la remplit depuis Gestion MP, voir docs/lots/R1.md) ;
#  6. crée les dossiers de sauvegardes et de pièces (lisibles du seul compte du Mac) ;
#  7. pose « Gestion MP PRO.app » sur le bureau ;
#  8. avec --demarrage-automatique seulement : l'agent launchd fr.usine.gestion-mp-pro.
# Le serveur n'est pas démarré : double-clic sur le raccourci (ou scripts/demarrer.sh).
# Rien de Gestion MP n'est lu ni écrit (port 8030, base gestion_mp, ~/gestion-mp…).
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
DEPOT="$(cd "$ICI/../.." && pwd)"
# Le projet par défaut : le dépôt principal (celui d'un worktree est son dépôt commun).
commun_git="$(git -C "$DEPOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
PROJET_DEFAUT="$DEPOT"
[ -z "$commun_git" ] || PROJET_DEFAUT="$(dirname "$commun_git")"

AUTO=0 RACCOURCI_OUI=1 PROJET_CHOISI=""
while [ $# -gt 0 ]; do
  case "$1" in
    --projet) PROJET_CHOISI="$(cd "${2:?--projet demande un dossier}" && pwd)"; shift 2 ;;
    --demarrage-automatique) AUTO=1; shift ;;
    --sans-raccourci) RACCOURCI_OUI=0; shift ;;
    *) echo "Option inconnue : $1" >&2; exit 1 ;;
  esac
done
GESTIONMPPRO_PROJET="${PROJET_CHOISI:-${GESTIONMPPRO_PROJET:-$PROJET_DEFAUT}}"
export GESTIONMPPRO_PROJET
. "$ICI/commun.sh"
garder_la_base
etape() { printf '\n== %s\n' "$*"; }

etape "1. Outils"
[ "$(uname -s)" = Darwin ] || echouer "ce script est celui du poste Mac (serveur Linux : deploiement/)."
for outil in git python3.12 node npm psql pg_isready createdb; do
  command -v "$outil" >/dev/null || echouer "$outil introuvable (Homebrew : brew install postgresql@16 python@3.12 node git)."
done
pg_isready -q || echouer "PostgreSQL ne répond pas (brew services start postgresql@16)."
version_pg="$(psql -X -d postgres -Atc 'SHOW server_version_num')"
[ "$version_pg" -ge 160000 ] || echouer "PostgreSQL 16 au moins est attendu (trouvé $version_pg)."
git -C "$PROJET" rev-parse --verify -q HEAD >/dev/null || echouer "projet sans commit : $PROJET"
dire "Projet : $PROJET (commit $(git -C "$PROJET" rev-parse --short=7 HEAD)) ; base : $BASE_NOM ; port : $GESTIONMPPRO_PORT."

etape "2. Scripts du poste"
rm -rf "$OUTILS.nouveau"
mkdir -p "$OUTILS.nouveau"
cp "$ICI/commun.sh" "$ICI/poste.py" "$ICI/installer_demarrage_automatique.sh" \
  "$ICI/fr.usine.gestion-mp-pro.plist" "$DEPOT/scripts/demarrer.sh" "$DEPOT/scripts/arreter.sh" \
  "$DEPOT/scripts/sauvegarder.sh" "$DEPOT/scripts/restaurer.sh" "$OUTILS.nouveau/"
printf '%s\n' "$PROJET" >"$OUTILS.nouveau/PROJET"
chmod 755 "$OUTILS.nouveau"/*.sh
chmod 644 "$OUTILS.nouveau/commun.sh"
rm -rf "$OUTILS"
mv "$OUTILS.nouveau" "$OUTILS"
dire "$OUTILS (projet noté : $PROJET)."

etape "3. Rôle et base PostgreSQL"
# Le rôle est celui de l'adresse (gestion_mp_pro) ; sans utilisateur, celui du Mac.
ROLE="$(printf '%s' "$GESTIONMPPRO_BASE" | sed -n 's#^[^:]*://\([^:@/]*\)[:@].*#\1#p')"
admin() { psql -X -q -v ON_ERROR_STOP=1 -d postgres "$@"; }
if [ -n "$ROLE" ]; then
  if [ "$(admin -Atc "SELECT 1 FROM pg_roles WHERE rolname = '$ROLE'")" = 1 ]; then
    dire "Rôle $ROLE : déjà là."
  else
    admin -c "CREATE ROLE \"$ROLE\" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE"
    dire "Rôle $ROLE : créé."
  fi
fi
proprietaire="$(admin -Atc "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = '$BASE_NOM'")"
if [ -z "$proprietaire" ]; then
  createdb -E UTF8 -T template0 ${ROLE:+-O "$ROLE"} "$BASE_NOM"
  dire "Base $BASE_NOM : créée${ROLE:+ (propriétaire $ROLE)}."
elif [ -n "$ROLE" ] && [ "$proprietaire" != "$ROLE" ]; then
  echouer "la base $BASE_NOM existe mais appartient à $proprietaire (et non $ROLE) : rien n'est changé, voir docs/lots/X2.md."
else
  dire "Base $BASE_NOM : déjà là (propriétaire $proprietaire)."
fi
# Seul son propriétaire (et l'administrateur du serveur) s'y connecte.
admin -c "REVOKE CONNECT, TEMPORARY ON DATABASE \"$BASE_NOM\" FROM PUBLIC"

etape "4. Copie figée de la version"
"$OUTILS/demarrer.sh" --preparer

etape "5. Schéma de la base"
poste migrer
poste etat

etape "6. Dossiers de sauvegardes et de pièces jointes"
SAUVEGARDES="${GESTIONMPPRO_SAUVEGARDES:-$HOME/gestion-mp-pro-sauvegardes}"
PIECES="${GESTIONMPPRO_PIECES:-$HOME/gestion-mp-pro-pieces}"
for d in "${SAUVEGARDES/#\~/$HOME}" "${PIECES/#\~/$HOME}"; do
  mkdir -p "$d/$BASE_NOM"
  chmod 700 "$d" "$d/$BASE_NOM"
  dire "$d/$BASE_NOM"
done
mkdir -p "$JOURNAUX"
if [ ! -f "$APPLI/environnement" ]; then
  cat >"$APPLI/environnement" <<'FIN'
# Réglages permanents de Gestion MP PRO sur ce poste (lus par les scripts du poste au démarrage).
# Une ligne GESTIONMPPRO_NOM=valeur, sans guillemets ; une ligne qui commence par # est ignorée.
# Exemples (ARCHITECTURE § 16) :
# GESTIONMPPRO_SAUVEGARDES_COPIE=/Volumes/Copie/gestion-mp-pro
# GESTIONMPPRO_SMTP_HOTE=smtp.example.com
# GESTIONMPPRO_SMTP_UTILISATEUR=
# GESTIONMPPRO_SMTP_MOT_DE_PASSE=
# GESTIONMPPRO_SMTP_EXPEDITEUR=
FIN
fi
chmod 600 "$APPLI/environnement"
dire "Réglages du poste : $APPLI/environnement (0600)."

etape "7. Raccourci du bureau"
if [ "$RACCOURCI_OUI" = 1 ] && [ "$BASE_NOM" = gestion_mp_pro ] && [ "$GESTIONMPPRO_PORT" = 8050 ]; then
  "$ICI/creer-raccourci.sh"
else
  dire "Pas de raccourci (base $BASE_NOM, port $GESTIONMPPRO_PORT : le raccourci ouvre la base gestion_mp_pro sur 8050)."
fi

etape "8. Démarrage automatique"
if [ "$AUTO" = 1 ]; then
  "$OUTILS/installer_demarrage_automatique.sh"
else
  dire "Non installé (réglage du Mac, à décider par son utilisateur) :"
  dire "  \"$OUTILS/installer_demarrage_automatique.sh\"            # l'installer"
  dire "  \"$OUTILS/installer_demarrage_automatique.sh\" --retirer  # le retirer"
fi

etape "Fait"
dire "Gestion MP PRO est installé (arrêté). Le démarrer : double-clic sur « Gestion MP PRO » du bureau."
dire "Version : $(cat "$VERSION_DIR/VERSION") ; copie : $VERSION_DIR ; journaux : $JOURNAUX."
