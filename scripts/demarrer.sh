#!/bin/bash
# Lance Gestion MP PRO sur le poste Mac (ARCHITECTURE § 13.2) : 127.0.0.1:8050, base
# gestion_mp_pro — à côté de Gestion MP (8030, gestion_mp), sans rien partager (§ 14.1).
#
#   scripts/demarrer.sh               # prépare la copie figée au besoin, puis sert
#   scripts/demarrer.sh --preparer    # prépare seulement (installer.sh)
#   scripts/demarrer.sh --refaire     # refait la copie même si la version n'a pas changé
#
# Le serveur tourne sur une **copie figée** du dernier commit du projet — le code ET l'écran,
# construit depuis ce même commit — dans « ~/Library/Application Support/Gestion MP PRO/
# version » (une copie par base) ; `VERSION` (le commit) est ce que dit /api/sante. Travailler
# dans le projet ne change rien au serveur en service avant son prochain démarrage. La copie
# n'est refaite que si le commit a changé : une relance (launchd, raccourci) est immédiate.
# Avant de servir une autre version que la précédente : sauvegarde « avant mise à jour ».
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$ICI/commun.sh" ]; then . "$ICI/commun.sh"; else . "$ICI/../deploiement/mac/commun.sh"; fi
garder_la_base

PREPARER=0 REFAIRE=0
for argument in "$@"; do
  case "$argument" in
    --preparer) PREPARER=1 ;;
    --refaire) REFAIRE=1 ;;
    *) echouer "option inconnue : $argument" ;;
  esac
done

# Un second lancement ne touche pas la copie en service : port pris, il s'arrête avant tout.
if [ "$PREPARER" = 0 ] && [ -n "$(pids_sur_le_port)" ]; then
  if [ -n "$(pids_pro)" ]; then
    echouer "déjà en marche sur le port $GESTIONMPPRO_PORT : rien n'est fait (scripts/arreter.sh pour l'arrêter)."
  fi
  echouer "le port $GESTIONMPPRO_PORT est pris par un autre programme : rien n'est fait."
fi
git -C "$PROJET" rev-parse --verify -q HEAD >/dev/null || echouer "projet introuvable ou sans commit : $PROJET"
COMMIT="$(git -C "$PROJET" rev-parse --short=7 HEAD)"

mkdir -p "$APPLI" "$JOURNAUX"
# Un seul lancement prépare une copie à la fois ; un verrou laissé par un lancement mort est
# repris (son processus n'existe plus).
VERROU="$VERSION_DIR.verrou"
if ! mkdir "$VERROU" 2>/dev/null; then
  autre="$(cat "$VERROU/pid" 2>/dev/null || true)"
  if [ -n "$autre" ] && kill -0 "$autre" 2>/dev/null; then
    echouer "un autre lancement prépare déjà $VERSION_DIR (processus $autre) : rien n'est fait."
  fi
  rm -rf "$VERROU"
  mkdir "$VERROU" || echouer "verrou $VERROU impossible à prendre."
fi
echo $$ >"$VERROU/pid"
NOUVELLE="$VERSION_DIR.nouvelle"
trap 'rm -rf "$VERROU" "$NOUVELLE"' EXIT INT TERM

# L'environnement Python d'un requirements.lock, créé une fois et partagé entre copies ; il
# n'est tenu pour prêt qu'une fois toutes ses dépendances installées (repère `.complet`).
preparer_python() {
  empreinte="$(shasum -a 256 "$1" | cut -c1-12)"
  cible="$APPLI/python/$empreinte"
  if [ ! -f "$cible/.complet" ]; then
    dire "Environnement Python $empreinte : installation des dépendances figées…" >&2
    rm -rf "$cible"
    mkdir -p "$APPLI/python"
    python3.12 -m venv "$cible"
    "$cible/bin/python" -m pip install -q --disable-pip-version-check -r "$1" >&2 \
      || { rm -rf "$cible"; echouer "dépendances impossibles à installer (voir ci-dessus)."; }
    touch "$cible/.complet"
  fi
  printf '%s\n' "$empreinte"
}

# L'écran de ce commit, construit dans un dossier à part avec les modules du projet (ou ses
# propres modules si la liste des versions diffère).
construire_ecran() {
  source_ecran="$NOUVELLE/.ecran-source"
  mkdir -p "$source_ecran"
  git -C "$PROJET" archive HEAD frontend | tar -x -C "$source_ecran"
  if [ -d "$PROJET/frontend/node_modules" ] \
    && cmp -s "$source_ecran/frontend/package-lock.json" "$PROJET/frontend/package-lock.json"; then
    ln -s "$PROJET/frontend/node_modules" "$source_ecran/frontend/node_modules"
  else
    (cd "$source_ecran/frontend" && npm ci --no-audit --no-fund >/dev/null)
  fi
  if ! (cd "$source_ecran/frontend" && npm run build >"$NOUVELLE/.construction.log" 2>&1); then
    cat "$NOUVELLE/.construction.log" >&2
    echouer "l'écran du commit $COMMIT n'a pas pu être construit : arrêt (la copie en service est intacte)."
  fi
  mkdir -p "$NOUVELLE/frontend"
  mv "$source_ecran/frontend/dist" "$NOUVELLE/frontend/dist"
  rm -rf "$source_ecran" "$NOUVELLE/.construction.log"
}

ANCIENNE="$(cat "$VERSION_DIR/VERSION" 2>/dev/null || true)"
if [ "$REFAIRE" = 1 ] || [ "$ANCIENNE" != "$COMMIT" ] || [ ! -f "$VERSION_DIR/frontend/dist/index.html" ] \
  || ! python_de "$VERSION_DIR" >/dev/null; then
  # Jamais sous un serveur en marche (--preparer) : sa copie ne se remplace pas sous lui.
  [ -z "$(pids_pro)" ] || echouer "le serveur tourne sur le port $GESTIONMPPRO_PORT : l'arrêter d'abord (scripts/arreter.sh) pour préparer la version $COMMIT."
  dire "Copie figée du commit $COMMIT (base $BASE_NOM)…"
  rm -rf "$NOUVELLE"
  mkdir -p "$NOUVELLE"
  git -C "$PROJET" archive HEAD backend/gestion_mp_pro backend/pyproject.toml \
    backend/requirements.lock backend/alembic.ini | tar -x -C "$NOUVELLE"
  construire_ecran
  preparer_python "$NOUVELLE/backend/requirements.lock" >"$NOUVELLE/ENVIRONNEMENT"
  printf '%s\n' "$COMMIT" >"$NOUVELLE/VERSION"
  # Une autre version que celle en service : la base est sauvegardée d'abord (avec le code
  # de la nouvelle copie ; la copie en service reste en place si la sauvegarde échoue).
  if [ -n "$ANCIENNE" ] && [ "$ANCIENNE" != "$COMMIT" ]; then
    py="$(python_de "$NOUVELLE")"
    if (cd "$NOUVELLE/backend" && PYTHONPATH="$NOUVELLE/backend" "$py" "$POSTE_PY" a-un-schema); then
      dire "Mise à jour $ANCIENNE → $COMMIT : sauvegarde « avant mise à jour »…"
      (cd "$NOUVELLE/backend" && PYTHONPATH="$NOUVELLE/backend" "$py" "$POSTE_PY" sauvegarder \
        --genre avant-mise-a-jour) || echouer "sauvegarde « avant mise à jour » impossible : la version $ANCIENNE reste en place."
    fi
  fi
  rm -rf "$VERSION_DIR"
  mv "$NOUVELLE" "$VERSION_DIR"
  # Les environnements que plus aucune copie n'utilise sont retirés.
  for env in "$APPLI"/python/*; do
    [ -f "$env/.complet" ] || continue  # absent, ou en cours de création par un autre lancement
    nom="$(basename "$env")"
    if ! cat "$APPLI"/version*/ENVIRONNEMENT 2>/dev/null | grep -qx "$nom"; then rm -rf "$env"; fi
  done
fi
rm -rf "$VERROU"
trap - EXIT INT TERM
[ "$PREPARER" = 0 ] || { dire "Copie figée prête : $VERSION_DIR (version $COMMIT)."; exit 0; }

PY="$(python_de "$VERSION_DIR")"
cd "$VERSION_DIR/backend"
export PYTHONPATH="$VERSION_DIR/backend" GESTIONMPPRO_ECRAN="$VERSION_DIR/frontend/dist"
PROCESSUS=()
[ "${GESTIONMPPRO_PROCESSUS:-1}" = 1 ] || PROCESSUS=(--workers "$GESTIONMPPRO_PROCESSUS")
dire "Gestion MP PRO $COMMIT : http://$GESTIONMPPRO_ECOUTE:$GESTIONMPPRO_PORT (base $BASE_NOM)."
exec "$PY" -m uvicorn gestion_mp_pro.main:app --host "$GESTIONMPPRO_ECOUTE" \
  --port "$GESTIONMPPRO_PORT" --no-access-log ${PROCESSUS[@]+"${PROCESSUS[@]}"}
