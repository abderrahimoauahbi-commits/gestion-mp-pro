#Requires -Version 5.1
<#
Gestion MP PRO — arrête le serveur, et lui seul (un autre programme sur le port n'est jamais
touché). À lancer en administrateur :

  & 'C:\Program Files\Gestion MP PRO\outils\arreter.ps1'
  & 'C:\Program Files\Gestion MP PRO\outils\arreter.ps1' -Desactiver   # et pas au prochain démarrage de Windows

Sans -Desactiver, le serveur repart au prochain démarrage de Windows (ou avec demarrer.ps1).
Une sauvegarde ou une restauration en cours est attendue (10 minutes au plus) ; -Force ne
l'attend pas (elle laisse alors un fichier « .partiel », ignoré).
#>
param([switch]$Desactiver, [switch]$Force)
. "$PSScriptRoot\commun.ps1"

Exiger-Administrateur
$null = Lire-Environnement
if ($Desactiver) {
    $tache = Get-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache -ErrorAction SilentlyContinue
    if ($tache) {
        Disable-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache | Out-Null
        Dire 'Démarrage automatique désactivé (demarrer.ps1 le réactive).'
    }
}
if (@(Pids-Pro).Count -eq 0) {
    Arreter-Serveur -Force:$Force  # la tâche peut tourner (relance en attente) sans serveur
    if (Port-Pris-Par-Un-Autre) {
        Dire "Le port $env:GESTIONMPPRO_PORT est tenu par un autre programme que Gestion MP PRO : rien n'est arrêté."
    } else {
        Dire "Gestion MP PRO ne tourne pas sur le port $env:GESTIONMPPRO_PORT."
    }
    exit 0
}
Arreter-Serveur -Force:$Force
Dire "Gestion MP PRO arrêté (port $env:GESTIONMPPRO_PORT)."
