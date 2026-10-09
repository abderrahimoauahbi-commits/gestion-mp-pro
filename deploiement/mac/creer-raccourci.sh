#!/bin/bash
# Pose « Gestion MP PRO » sur le bureau : un double-clic démarre le serveur s'il ne tourne pas,
# puis ouvre http://localhost:8050 dans le navigateur (comme « Gestion MP.app » pour 8030, qui
# n'est pas touché : autre nom, autre identifiant, autre icône, autre port).
#   deploiement/mac/creer-raccourci.sh               # sur le bureau
#   deploiement/mac/creer-raccourci.sh ~/Applications
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
. "$ICI/commun.sh"
cible="${1:-$HOME/Desktop}/Gestion MP PRO.app"
case "$cible" in */"Gestion MP.app") echouer "refusé : ce nom est celui de Gestion MP." ;; esac
rm -rf "$cible.nouveau"
mkdir -p "$cible.nouveau/Contents/MacOS" "$cible.nouveau/Contents/Resources"
cp "$ICI/Gestion-MP-PRO.icns" "$cible.nouveau/Contents/Resources/Gestion-MP-PRO.icns"
cat >"$cible.nouveau/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Gestion MP PRO</string>
  <key>CFBundleDisplayName</key><string>Gestion MP PRO</string>
  <key>CFBundleIdentifier</key><string>fr.usine.gestion-mp-pro.raccourci</string>
  <key>CFBundleExecutable</key><string>Gestion-MP-PRO</string>
  <key>CFBundleIconFile</key><string>Gestion-MP-PRO</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST
lanceur="$cible.nouveau/Contents/MacOS/Gestion-MP-PRO"
# Seul le dossier des outils installés est écrit dans le lanceur ; le reste est recopié tel quel.
{
  head -n 1 "$ICI/lanceur.sh"
  printf "OUTILS='%s'\n" "$(printf '%s' "$OUTILS" | sed "s/'/'\\\\''/g")"
  tail -n +2 "$ICI/lanceur.sh"
} >"$lanceur"
chmod 755 "$lanceur"
plutil -lint -s "$cible.nouveau/Contents/Info.plist"
rm -rf "$cible"
mv "$cible.nouveau" "$cible"
# Le Finder relit l'icône.
touch "$cible"
dire "Raccourci créé : $cible"
