#!/usr/bin/env bash
# Types de l'API pour l'écran : OpenAPI du serveur → frontend/src/lib/types.gen.ts
# (ARCHITECTURE § 9.2, LOTS-DE-TRAVAIL § 0.3 : fichier généré, jamais édité à la main).
#
# Usage :
#   scripts/generer_types.sh                 # depuis le serveur de développement (port 8050)
#   scripts/generer_types.sh URL|FICHIER     # depuis une autre adresse, ou un openapi.json enregistré
#   scripts/generer_types.sh --verifier [SOURCE]
#                                            # n'écrit rien ; échoue si types.gen.ts n'est pas à jour
#
# La source par défaut se change par GESTIONMPPRO_OPENAPI. Le résultat est formaté par Prettier
# (mêmes règles que l'écran) et ne porte aucune date : deux générations de la même API donnent
# le même fichier, au caractère près.
set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ECRAN="$RACINE/frontend"
CIBLE="$ECRAN/src/lib/types.gen.ts"
OUTILS="$ECRAN/node_modules/.bin"

VERIFIER=0
if [[ "${1:-}" == "--verifier" ]]; then
  VERIFIER=1
  shift
fi
SOURCE="${1:-${GESTIONMPPRO_OPENAPI:-http://localhost:8050/api/openapi.json}}"

if [[ ! -x "$OUTILS/openapi-typescript" || ! -x "$OUTILS/prettier" ]]; then
  echo "Outils absents : lancez d'abord « npm install » dans frontend/." >&2
  exit 2
fi

TRAVAIL="$(mktemp -d)"
trap 'rm -rf "$TRAVAIL"' EXIT
SCHEMA="$TRAVAIL/openapi.json"

if [[ "$SOURCE" =~ ^https?:// ]]; then
  if ! curl -fsS --max-time 30 "$SOURCE" -o "$SCHEMA"; then
    echo "Le serveur ne répond pas sur $SOURCE : démarrez-le, ou passez le chemin d'un openapi.json." >&2
    exit 1
  fi
elif [[ -f "$SOURCE" ]]; then
  cp "$SOURCE" "$SCHEMA"
else
  echo "Source introuvable : $SOURCE" >&2
  exit 1
fi

if ! grep -q '"openapi"' "$SCHEMA"; then
  echo "La source n'est pas un document OpenAPI : $SOURCE" >&2
  exit 1
fi

"$OUTILS/openapi-typescript" "$SCHEMA" --output "$TRAVAIL/brut.ts" >/dev/null

{
  echo '// Fichier généré par scripts/generer_types.sh depuis l'"'"'OpenAPI du serveur : ne pas le modifier.'
  echo '// Le régénérer après tout changement de route ou de schéma (make types).'
  cat "$TRAVAIL/brut.ts"
} >"$TRAVAIL/avec-entete.ts"

(cd "$ECRAN" && "$OUTILS/prettier" --stdin-filepath src/lib/types.gen.ts <"$TRAVAIL/avec-entete.ts") >"$TRAVAIL/types.gen.ts"

if [[ "$VERIFIER" == 1 ]]; then
  if ! cmp -s "$TRAVAIL/types.gen.ts" "$CIBLE"; then
    echo "frontend/src/lib/types.gen.ts n'est pas à jour avec $SOURCE : lancez scripts/generer_types.sh." >&2
    diff -u "$CIBLE" "$TRAVAIL/types.gen.ts" | head -40 >&2 || true
    exit 1
  fi
  echo "Types de l'API à jour."
  exit 0
fi

mv "$TRAVAIL/types.gen.ts" "$CIBLE"
echo "Types de l'API écrits dans frontend/src/lib/types.gen.ts (source : $SOURCE)."
