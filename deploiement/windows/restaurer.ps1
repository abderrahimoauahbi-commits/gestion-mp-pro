#Requires -Version 5.1
<#
Gestion MP PRO — restaure une sauvegarde, tout ou rien (même service que l'écran : relecture,
refus d'une sauvegarde d'une autre base ou d'une version plus récente, sauvegarde « avant
restauration » d'abord, remplacement en une transaction, pièces jointes remises, schéma mis à
cette version). Serveur ARRÊTÉ (arreter.ps1) ; serveur en marche, restaurer depuis l'écran
(Administration › Sauvegardes). À lancer en administrateur :

  & 'C:\Program Files\Gestion MP PRO\outils\restaurer.ps1' -Fichier gestion-mp-pro-2026-10-08-220000-quotidienne.dump
  & '…\restaurer.ps1' -Fichier 'E:\transfert\gestion-mp-pro-…-manuelle.dump' -Comptes 'E:\transfert\comptes-mac.json'

Un fichier pris ailleurs (clé USB) est d'abord copié, avec son .pieces.tar, dans le dossier des
sauvegardes de la base. -Comptes compare ensuite la base restaurée, table par table, aux
comptes faits sur l'autre serveur (scripts/compter.sh sur le Mac) : c'est la preuve d'un
transfert (INSTALLATION-WINDOWS.md § 9).
#>
param(
    [Parameter(Mandatory = $true)][string]$Fichier,
    [string]$Comptes = '',
    [string]$Confirmation = '',
    [string]$Motif = 'restauration depuis le serveur Windows (restaurer.ps1)'
)
. "$PSScriptRoot\commun.ps1"

Exiger-Administrateur
$null = Lire-Environnement
$base = Nom-De-Base $env:GESTIONMPPRO_BASE
Garder-La-Base $base
if (@(Pids-Pro).Count -gt 0) {
    Echouer "le serveur tourne : l'arrêter d'abord (arreter.ps1), ou restaurer depuis l'écran (Administration › Sauvegardes)."
}
if ($Comptes -and -not (Test-Path -LiteralPath $Comptes)) { Echouer "fichier des comptes introuvable : $Comptes" }
$dossier = Join-Path $env:GESTIONMPPRO_SAUVEGARDES $base
$nom = Split-Path $Fichier -Leaf
if ((Split-Path $Fichier -Parent) -and (Test-Path -LiteralPath $Fichier)) {
    $source = (Resolve-Path -LiteralPath $Fichier).Path
    if ((Split-Path $source -Parent) -ne $dossier) {
        Dire "Copie de $nom (et de ses pièces jointes) dans $dossier…"
        Copy-Item -LiteralPath $source -Destination $dossier -Force
        $pieces = "$source.pieces.tar"
        if (Test-Path -LiteralPath $pieces) { Copy-Item -LiteralPath $pieces -Destination $dossier -Force }
        else { Avertir "pas d'archive des pièces jointes à côté ($nom.pieces.tar) : seules les données reviendront." }
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $dossier $nom))) { Echouer "sauvegarde introuvable : $(Join-Path $dossier $nom)" }

if (-not $Confirmation) {
    Dire "Toute la base $base va être remplacée par $nom."
    Dire 'L''état actuel sera sauvegardé d''abord (« avant restauration »).'
    $Confirmation = Read-Host 'Pour confirmer, tapez RESTAURER'
}
$code = Lancer-Poste @('restaurer', $nom, '--confirmation', $Confirmation, '--motif', $Motif)
if ($code -ne 0) { Echouer "restauration non faite ou échouée (code $code, voir ci-dessus)." }
if ($Comptes) {
    Dire 'Comparaison avec les comptes de l''autre serveur…'
    $code = Lancer-Poste @('comparer-comptes', (Resolve-Path -LiteralPath $Comptes).Path)
    if ($code -ne 0) { Echouer 'la base restaurée ne compte pas les mêmes lignes (voir ci-dessus).' }
}
Dire 'Restauration faite. Démarrer le serveur : demarrer.ps1 (puis etat.ps1).'
