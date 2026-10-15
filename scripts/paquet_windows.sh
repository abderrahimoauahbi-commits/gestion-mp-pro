#!/bin/bash
# Fabrique, sur le Mac, le paquet à copier sur le serveur Windows (docs/INSTALLATION-WINDOWS.md) :
# un .zip avec le code du serveur, l'écran DÉJÀ CONSTRUIT (pas de Node sur le serveur), les
# dépendances figées pour Windows et le kit deploiement/windows. Ni base, ni sauvegarde, ni
# réglage, ni secret : seulement des fichiers suivis par git, au commit demandé.
#
#   scripts/paquet_windows.sh                       # le dernier commit (HEAD)
#   scripts/paquet_windows.sh --commit a1b2c3d      # un autre commit
#   scripts/paquet_windows.sh --sortie ~/Desktop    # où écrire le .zip (défaut ~/gestion-mp-pro-paquets)
#   scripts/paquet_windows.sh --avec-roues          # + les roues Python Windows (serveur sans Internet)
#
# Le paquet s'appelle gestion-mp-pro-windows-<commit>.zip ; à côté, son empreinte .sha256.
# Contenu : VERSION (le commit, lu par /api/sante), backend/ (gestion_mp_pro, pyproject.toml,
# requirements-windows.lock), frontend/dist, windows/ (scripts PowerShell + poste.py),
# INSTALLATION-WINDOWS.md.
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
RACINE="$(cd "$ICI/.." && pwd)"
REF=HEAD SORTIE="$HOME/gestion-mp-pro-paquets" ROUES=0
while [ $# -gt 0 ]; do
  case "$1" in
    --commit) REF="${2:?--commit demande un commit}"; shift 2 ;;
    --sortie) SORTIE="${2:?--sortie demande un dossier}"; shift 2 ;;
    --avec-roues) ROUES=1; shift ;;
    *) echo "Option inconnue : $1" >&2; exit 1 ;;
  esac
done
echouer() { printf 'paquet_windows : %s\n' "$*" >&2; exit 1; }
git -C "$RACINE" rev-parse --verify -q "$REF^{commit}" >/dev/null || echouer "commit inconnu : $REF"
COMMIT="$(git -C "$RACINE" rev-parse --short=7 "$REF")"
NOM="gestion-mp-pro-windows-$COMMIT"
TRAVAIL="$(mktemp -d "${TMPDIR:-/tmp}/paquet-windows.XXXXXX")"
trap 'rm -rf "$TRAVAIL"' EXIT INT TERM
SOURCE="$TRAVAIL/source" PAQUET="$TRAVAIL/$NOM"
mkdir -p "$SOURCE" "$PAQUET/backend" "$PAQUET/frontend" "$PAQUET/windows"

echo "Paquet Windows du commit $COMMIT…"
git -C "$RACINE" archive "$REF" backend/gestion_mp_pro backend/pyproject.toml \
  backend/requirements-windows.lock deploiement/windows deploiement/mac/poste.py frontend \
  docs/INSTALLATION-WINDOWS.md | tar -x -C "$SOURCE"

# L'écran de ce commit, construit ici (modules du projet si leur liste est la même).
if [ -d "$RACINE/frontend/node_modules" ] \
  && cmp -s "$SOURCE/frontend/package-lock.json" "$RACINE/frontend/package-lock.json"; then
  ln -s "$RACINE/frontend/node_modules" "$SOURCE/frontend/node_modules"
else
  (cd "$SOURCE/frontend" && npm ci --no-audit --no-fund >/dev/null)
fi
(cd "$SOURCE/frontend" && npm run build >"$TRAVAIL/construction.log" 2>&1) \
  || { cat "$TRAVAIL/construction.log" >&2; echouer "l'écran du commit $COMMIT n'a pas pu être construit."; }

printf '%s\n' "$COMMIT" >"$PAQUET/VERSION"
mv "$SOURCE/backend/gestion_mp_pro" "$SOURCE/backend/pyproject.toml" \
  "$SOURCE/backend/requirements-windows.lock" "$PAQUET/backend/"
mv "$SOURCE/frontend/dist" "$PAQUET/frontend/dist"
cp "$SOURCE"/deploiement/windows/* "$SOURCE/deploiement/mac/poste.py" "$PAQUET/windows/"
cp "$SOURCE/docs/INSTALLATION-WINDOWS.md" "$PAQUET/"
if [ "$ROUES" = 1 ]; then
  # Les roues binaires Windows 64 bits de Python 3.12, pour installer sans Internet (-Roues).
  "$RACINE/backend/.venv/bin/python" -m pip download -q --only-binary=:all: --platform win_amd64 \
    --python-version 3.12 --implementation cp -r "$PAQUET/backend/requirements-windows.lock" \
    -d "$PAQUET/roues"
fi

# Garde-fous : rien d'une base, d'un réglage ou d'un poste dans le paquet.
interdits="$(cd "$PAQUET" && find . \( -name '*.dump' -o -name '*.pieces.tar' -o -name '.env' \
  -o -name 'environnement' -o -name '*.log' -o -name '__pycache__' -o -name 'node_modules' \
  -o -name '.DS_Store' -o -name 'tests' \) -print)"
[ -z "$interdits" ] || echouer "fichiers interdits dans le paquet : $interdits"
[ -f "$PAQUET/frontend/dist/index.html" ] || echouer "écran construit absent."
if grep -rIl --exclude-dir=dist -E 'MOT_DE_PASSE=[A-Za-z0-9]|postgresql\+psycopg://[A-Za-z0-9_]+:[A-Za-z0-9]{8,}@' \
  "$PAQUET" >/dev/null; then
  echouer "un mot de passe semble écrit dans le paquet : rien n'est livré."
fi

mkdir -p "$SORTIE"
(cd "$TRAVAIL" && rm -f "$SORTIE/$NOM.zip" && zip -q -r -X "$SORTIE/$NOM.zip" "$NOM")
(cd "$SORTIE" && shasum -a 256 "$NOM.zip" >"$NOM.zip.sha256")
echo "Paquet : $SORTIE/$NOM.zip ($(du -h "$SORTIE/$NOM.zip" | cut -f1))"
echo "Empreinte : $(cut -d' ' -f1 "$SORTIE/$NOM.zip.sha256")"
echo "Sur le serveur : déballer, puis INSTALLATION-WINDOWS.md § 3 (première fois) ou § 7 (mise à jour)."
