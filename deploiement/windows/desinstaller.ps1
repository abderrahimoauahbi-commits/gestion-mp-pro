#Requires -Version 5.1
<#
Gestion MP PRO — retire le logiciel du serveur. Par défaut, ne retire QUE le programme : le
serveur est arrêté, la tâche planifiée et la règle du pare-feu supprimées, le dossier
C:\Program Files\Gestion MP PRO effacé. La base, les sauvegardes, les pièces jointes, les
journaux et les réglages restent, intacts (installer.ps1 remet tout en service sur eux).

  & 'C:\Program Files\Gestion MP PRO\outils\desinstaller.ps1'

Deux options, chacune avec sa confirmation TAPÉE (aucune ne passe sans elle, ni en silence) :
  -SupprimerLaBase       fait d'abord une dernière sauvegarde, puis supprime la base
                         gestion_mp_pro et son rôle (mot de passe de « postgres » demandé) ;
                         à taper : SUPPRIMER LA BASE
  -SupprimerLesDonnees   efface C:\ProgramData\Gestion MP PRO (sauvegardes, pièces jointes,
                         journaux, réglages) ; à taper : SUPPRIMER LES DONNEES
Le dossier de copie des sauvegardes (autre disque) n'est jamais touché. PostgreSQL et Python
ne sont pas désinstallés (Paramètres › Applications, s'ils ne servent plus à rien d'autre).
#>
param([switch]$SupprimerLaBase, [switch]$SupprimerLesDonnees)
. "$PSScriptRoot\commun.ps1"
. "$PSScriptRoot\fonctions-admin.ps1"

function Confirmer([string]$Phrase, [string]$Explication) {
    Dire $Explication
    $tape = Read-Host "Pour confirmer, tapez exactement : $Phrase"
    if ($tape -cne $Phrase) { Echouer 'non confirmé : rien n''a été supprimé.' }
}

Exiger-Administrateur
$valeurs = Lire-Environnement
$copie = $env:GESTIONMPPRO_SAUVEGARDES_COPIE
if ($SupprimerLaBase) {
    Confirmer 'SUPPRIMER LA BASE' 'La base gestion_mp_pro (toutes les données de Gestion MP PRO) et son rôle vont être supprimés de PostgreSQL. Une dernière sauvegarde est faite avant.'
}
if ($SupprimerLesDonnees) {
    $explication = "Le dossier $($Script:Donnees) va être effacé : sauvegardes, pièces jointes, journaux, réglages."
    if ($copie) { $explication += " La copie ($copie) est gardée." } else { $explication += ' Aucune copie des sauvegardes n''est réglée : il n''en restera rien.' }
    Confirmer 'SUPPRIMER LES DONNEES' $explication
}

Etape 'Arrêt du serveur'
Set-Location -LiteralPath $env:SystemRoot  # jamais dans un dossier qu'on va effacer
if ($valeurs.Count -gt 0 -and (Version-Actuelle)) { Arreter-Serveur }

if ($SupprimerLaBase) {
    Etape 'Dernière sauvegarde, puis suppression de la base'
    if ((Lancer-Poste @('sauvegarder', '--genre', 'manuelle')) -ne 0) { Echouer 'dernière sauvegarde impossible : rien n''a été supprimé.' }
    $Script:Psql = Trouver-PostgreSQL ([string]$env:GESTIONMPPRO_PG_BIN)
    $Script:PortPg = [int](Parties-De-Base $env:GESTIONMPPRO_BASE).Port
    $env:PGPASSWORD = Lire-Secret 'Mot de passe de l''administrateur « postgres » de PostgreSQL'
    try {
        Sql 'DROP DATABASE IF EXISTS gestion_mp_pro WITH (FORCE)' | Out-Null
        Sql 'DROP ROLE IF EXISTS gestion_mp_pro' | Out-Null
    } finally { Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue }
    Dire 'Base gestion_mp_pro et rôle gestion_mp_pro supprimés.'
}

Etape 'Programme'
Unregister-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache -Confirm:$false -ErrorAction SilentlyContinue
Remove-NetFirewallRule -Name $Script:NomRegle -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $Script:Appli) { Remove-Item -LiteralPath $Script:Appli -Recurse -Force }
Dire "Tâche planifiée, règle du pare-feu et $($Script:Appli) retirés."

if ($SupprimerLesDonnees) {
    Etape 'Données'
    if (Test-Path -LiteralPath $Script:Donnees) { Remove-Item -LiteralPath $Script:Donnees -Recurse -Force }
    Dire "$($Script:Donnees) effacé."
} else {
    Dire "Gardés : $($Script:Donnees) (sauvegardes, pièces jointes, journaux, réglages)$(if (-not $SupprimerLaBase) { ' et la base gestion_mp_pro' })."
}
Dire 'Gestion MP PRO est désinstallé.'
