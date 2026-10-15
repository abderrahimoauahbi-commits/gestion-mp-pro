#Requires -Version 5.1
<#
Gestion MP PRO — démarre le serveur (la tâche planifiée « Gestion MP PRO ») et attend qu'il
réponde. Rien n'est fait s'il tourne déjà. À lancer en administrateur :

  & 'C:\Program Files\Gestion MP PRO\outils\demarrer.ps1'

Une tâche désactivée (arreter.ps1 -Desactiver) est réactivée : le serveur redémarrera aussi avec
Windows.
#>
. "$PSScriptRoot\commun.ps1"

Exiger-Administrateur
$null = Lire-Environnement
$version = Exiger-Version
if (@(Pids-Pro).Count -gt 0) {
    Dire "Gestion MP PRO tourne déjà sur le port $env:GESTIONMPPRO_PORT : rien n'est fait (arreter.ps1 pour l'arrêter)."
    exit 0
}
if (Port-Pris-Par-Un-Autre) { Echouer "le port $env:GESTIONMPPRO_PORT est pris par un autre programme : rien n'est fait." }
Demarrer-Tache
Dire "Démarrage de la version $version…"
$e = Attendre-Sante $version 180
if ($e.Code -ne 200) {
    Echouer "le serveur ne répond pas : voir $($Script:Journaux)\demarrage.log et lanceur.log."
}
Dire "Gestion MP PRO $version répond sur le port $env:GESTIONMPPRO_PORT (état : $($e.Sante.etat))."
