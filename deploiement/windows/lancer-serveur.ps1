#Requires -Version 5.1
# Gestion MP PRO — porte le serveur (uvicorn) : lancé par la tâche planifiée « Gestion MP PRO »
# au démarrage de Windows, sous le compte du service. Ne pas le lancer à la main : demarrer.ps1.
#
# Lit le fichier environnement, sert la version en service (actuelle.txt) sur
# GESTIONMPPRO_ECOUTE:GESTIONMPPRO_PORT (0.0.0.0:8050 par défaut), un seul processus (le journal
# tournant de Windows ne se partage pas entre processus). La migration de la base se fait au
# démarrage du serveur, sous verrou, comme sur le Mac. Si le serveur s'arrête de lui-même
# (panne), il est relancé 10 secondes plus tard ; arreter.ps1 arrête d'abord cette tâche, donc
# rien ne le relance.
#
# Journaux : C:\ProgramData\Gestion MP PRO\journaux\serveur.log (le journal du serveur, tournant)
# et lanceur.log (démarrages, arrêts, messages de démarrage d'uvicorn).

. "$PSScriptRoot\commun.ps1"

$null = Lire-Environnement
$version = Exiger-Version
$base = Nom-De-Base $env:GESTIONMPPRO_BASE
Garder-La-Base $base
New-Item -ItemType Directory -Force -Path $Script:Journaux | Out-Null
$lanceur = Join-Path $Script:Journaux 'lanceur.log'
$demarrage = Join-Path $Script:Journaux 'demarrage.log'
$demarrageSortie = Join-Path $Script:Journaux 'demarrage-sortie.log'

function Noter([string]$Texte) {
    $ligne = '{0:yyyy-MM-dd HH:mm:ss} {1}' -f (Get-Date), $Texte
    Add-Content -LiteralPath $lanceur -Value $ligne -Encoding UTF8
}

# lanceur.log tenu court : au-delà de 5 Mo, l'ancien est mis de côté (un seul gardé).
if ((Test-Path -LiteralPath $lanceur) -and (Get-Item -LiteralPath $lanceur).Length -gt 5MB) {
    Move-Item -LiteralPath $lanceur -Destination "$lanceur.1" -Force
}

if ($env:GESTIONMPPRO_ECOUTE -notmatch '^[0-9A-Fa-f:.]+$' -or $env:GESTIONMPPRO_PORT -notmatch '^\d+$') {
    Noter 'GESTIONMPPRO_ECOUTE ou GESTIONMPPRO_PORT illisible dans le fichier environnement : arrêt.'
    exit 1
}
$dossier = Dossier-De-Version $version
$env:PYTHONPATH = Join-Path $dossier 'backend'
$arguments = @('-m', 'uvicorn', 'gestion_mp_pro.main:app', '--host', $env:GESTIONMPPRO_ECOUTE,
    '--port', $env:GESTIONMPPRO_PORT, '--no-access-log')
if ($env:GESTIONMPPRO_HTTPS -eq '1' -or $env:GESTIONMPPRO_HTTPS -eq 'true') {
    # Derrière un relais HTTPS sur ce serveur (Caddy, IIS) : l'adresse réelle des postes.
    $arguments += @('--proxy-headers', '--forwarded-allow-ips', '127.0.0.1')
}

while ($true) {
    if (Port-Pris-Par-Un-Autre) {
        Noter "le port $env:GESTIONMPPRO_PORT est pris par un autre programme : nouvel essai dans 60 s."
        Start-Sleep -Seconds 60
        continue
    }
    if (Test-Path -LiteralPath $demarrage) { Move-Item -LiteralPath $demarrage -Destination "$demarrage.1" -Force }
    Noter "démarrage de la version $version (base $base, $($env:GESTIONMPPRO_ECOUTE):$($env:GESTIONMPPRO_PORT))."
    # Arguments sans espaces (adresse, port, module) : la ligne est sûre telle quelle.
    $p = Start-Process -FilePath (Python-De $version) -ArgumentList ($arguments -join ' ') `
        -WorkingDirectory $env:PYTHONPATH -NoNewWindow -PassThru `
        -RedirectStandardOutput $demarrageSortie -RedirectStandardError $demarrage
    $null = $p.Handle  # sans cela, PowerShell 5.1 perd le code de retour
    $p.WaitForExit()
    Noter "le serveur s'est arrêté (code $($p.ExitCode)) : relance dans 10 s (voir $demarrage)."
    Start-Sleep -Seconds 10
}
