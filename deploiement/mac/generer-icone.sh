#!/bin/bash
# Refait Gestion-MP-PRO.icns (icône du raccourci du bureau) depuis icone.svg : le motif de
# l'application installée au téléphone (frontend/public/icone.svg), au gabarit des icônes du
# Mac. Distincte de celle de Gestion MP (carré bleu uni, « MP ») : fond dégradé nuit, « MP PRO ».
# Outils du Mac seulement : qlmanage (rendu du SVG), sips, iconutil.
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
TRAVAIL="$(mktemp -d "${TMPDIR:-/tmp}/gestion-mp-pro-icone.XXXXXX")"
trap 'rm -rf "$TRAVAIL"' EXIT
qlmanage -t -s 1024 -o "$TRAVAIL" "$ICI/icone.svg" >/dev/null 2>&1
SOURCE="$TRAVAIL/icone.svg.png"
[ -f "$SOURCE" ] || { echo "Rendu de icone.svg impossible (qlmanage)." >&2; exit 1; }
JEU="$TRAVAIL/Gestion-MP-PRO.iconset"
mkdir -p "$JEU"
for taille in 16 32 128 256 512; do
  sips -z "$taille" "$taille" "$SOURCE" --out "$JEU/icon_${taille}x${taille}.png" >/dev/null
  double=$((taille * 2))
  sips -z "$double" "$double" "$SOURCE" --out "$JEU/icon_${taille}x${taille}@2x.png" >/dev/null
done
iconutil -c icns "$JEU" -o "$ICI/Gestion-MP-PRO.icns"
echo "Icône refaite : $ICI/Gestion-MP-PRO.icns"
