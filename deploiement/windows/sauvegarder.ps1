#Requires -Version 5.1
<#
Gestion MP PRO — sauvegarde la base maintenant, serveur en marche ou non (même service, mêmes
noms, même relecture que l'écran : pg_dump relu, pièces jointes dans l'archive voisine
.pieces.tar, copie sur l'autre disque si GESTIONMPPRO_SAUVEGARDES_COPIE est réglé). À lancer en
administrateur :

  & 'C:\Program Files\Gestion MP PRO\outils\sauvegarder.ps1'                           # manuelle
  & 'C:\Program Files\Gestion MP PRO\outils\sauvegarder.ps1' -Genre avant-mise-a-jour

Dossier : C:\ProgramData\Gestion MP PRO\sauvegardes\gestion_mp_pro\ (le chemin du fichier est
affiché à la fin). La sauvegarde manuelle est écrite au journal de l'application.
#>
param([ValidateSet('manuelle', 'avant-mise-a-jour')][string]$Genre = 'manuelle')
. "$PSScriptRoot\commun.ps1"

Exiger-Administrateur
$null = Lire-Environnement
Garder-La-Base (Nom-De-Base $env:GESTIONMPPRO_BASE)
$code = Lancer-Poste @('sauvegarder', '--genre', $Genre)
if ($code -ne 0) { Echouer "sauvegarde impossible (code $code, voir ci-dessus)." }
Dire 'Sauvegarde relue et rangée.'
