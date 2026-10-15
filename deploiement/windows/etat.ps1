#Requires -Version 5.1
<#
Gestion MP PRO — l'état du serveur en un coup d'œil : /api/sante (base, schéma, version,
âge de la dernière sauvegarde, tâches), tâche planifiée, dernières sauvegardes et leur copie,
place libre. Lecture seule ; utilisateur ordinaire possible (la tâche et les dossiers protégés
ne s'affichent alors qu'en partie).

  & 'C:\Program Files\Gestion MP PRO\outils\etat.ps1'

Code de sortie : 0 si /api/sante répond 200 avec l'état « ok », 1 sinon.
#>
. "$PSScriptRoot\commun.ps1"

try { $null = Lire-Environnement } catch { Avertir 'fichier environnement illisible (lancer en administrateur).' }
if (-not $env:GESTIONMPPRO_PORT) { $env:GESTIONMPPRO_PORT = '8050' }
$version = Version-Actuelle
Dire "Version en service : $(if ($version) { $version } else { '(aucune)' }) ; port $env:GESTIONMPPRO_PORT"

$e = Etat-Http
if ($e.Code -eq 200 -and $e.Sante) {
    $s = $e.Sante
    Dire "Serveur : répond (état $($s.etat)) ; version servie $($s.version)"
    Dire "Schéma de la base : $($s.schema) (attendu $($s.schema_attendu)) ; base en $($s.base_ms) ms"
    $age = if ($null -ne $s.sauvegarde_age_h) { "$([math]::Round([double]$s.sauvegarde_age_h, 1)) h" } else { 'aucune' }
    Dire "Dernière sauvegarde : $age $(if ($s.sauvegarde_alerte) { '— ' + $s.sauvegarde_alerte })"
    foreach ($t in $s.taches.PSObject.Properties) { Dire "  tâche $($t.Name) : $($t.Value)" }
    if ($s.courriels_en_attente) { Dire "Courriels en attente : $($s.courriels_en_attente)" }
} elseif ($e.Code -eq 0) {
    Dire "Serveur : ne répond pas sur le port $env:GESTIONMPPRO_PORT (demarrer.ps1 ; journaux : $($Script:Journaux))."
} else {
    Dire "Serveur : répond $($e.Code) sur /api/sante (journaux : $($Script:Journaux))."
}

$tache = Get-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache -ErrorAction SilentlyContinue
if ($tache) {
    $info = Get-ScheduledTaskInfo -TaskName $Script:NomTache -TaskPath $Script:CheminTache -ErrorAction SilentlyContinue
    $dernier = if ($info) { "$($info.LastRunTime) (résultat $($info.LastTaskResult))" } else { '?' }
    Dire "Tâche planifiée : $($tache.State) ; compte $($tache.Principal.UserId) ; dernier lancement $dernier"
} else {
    Dire 'Tâche planifiée : absente ou illisible (démarrage automatique non installé, ou droits).'
}

$base = Nom-De-Base $env:GESTIONMPPRO_BASE
if (-not $base) { $base = 'gestion_mp_pro' }
$dossiers = @{ 'Sauvegardes' = $env:GESTIONMPPRO_SAUVEGARDES; 'Copie (autre disque)' = $env:GESTIONMPPRO_SAUVEGARDES_COPIE }
foreach ($nom in @('Sauvegardes', 'Copie (autre disque)')) {
    $racine = $dossiers[$nom]
    if (-not $racine) { Dire "${nom} : non réglé"; continue }
    $d = $racine
    if ($nom -eq 'Sauvegardes') { $d = Join-Path $racine $base }
    $fichiers = @(Get-ChildItem -LiteralPath $d -Filter 'gestion-mp-pro-*.dump' -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending)
    Dire "${nom} : $d ($($fichiers.Count) fichier(s))"
    foreach ($f in ($fichiers | Select-Object -First 3)) { Dire ('  {0}  {1:N1} Mo' -f $f.Name, ($f.Length / 1MB)) }
}
foreach ($disque in @(Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | Where-Object { $null -ne $_.Free })) {
    Dire ('Disque {0}: {1:N1} Go libres' -f $disque.Name, ($disque.Free / 1GB))
}
if ($e.Code -eq 200 -and $e.Sante -and $e.Sante.etat -eq 'ok') { exit 0 }
exit 1
