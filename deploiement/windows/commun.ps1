#Requires -Version 5.1
# Gestion MP PRO — réglages et fonctions communs aux scripts du serveur Windows.
#
# Lu (dot-source : `. "$PSScriptRoot\commun.ps1"`) par installer.ps1, lancer-serveur.ps1,
# demarrer.ps1, arreter.ps1, etat.ps1, sauvegarder.ps1, restaurer.ps1, mettre-a-jour.ps1,
# desinstaller.ps1 et recette.ps1. PowerShell 5.1 (celui de Windows Server) : rien de plus
# récent (ni `??`, ni `&&`, ni Join-Path à trois morceaux).
#
# Où sont les choses (docs/INSTALLATION-WINDOWS.md § 4) :
#   C:\Program Files\Gestion MP PRO\versions\<version>\   le code, l'écran construit, son Python
#   C:\Program Files\Gestion MP PRO\outils\               ces scripts (copiés par l'installation)
#   C:\Program Files\Gestion MP PRO\actuelle.txt          la version en service
#   C:\ProgramData\Gestion MP PRO\environnement           les réglages (mot de passe de la base)
#   C:\ProgramData\Gestion MP PRO\sauvegardes\, pieces\, journaux\
#
# Les noms de comptes Windows changent avec la langue (« Administrateurs ») : on n'utilise que
# leurs identifiants (SID), identiques partout.

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$Script:Appli = Join-Path $env:ProgramFiles 'Gestion MP PRO'
$Script:Donnees = Join-Path $env:ProgramData 'Gestion MP PRO'
$Script:Versions = Join-Path $Script:Appli 'versions'
$Script:Outils = Join-Path $Script:Appli 'outils'
$Script:FichierActuelle = Join-Path $Script:Appli 'actuelle.txt'
$Script:FichierPrecedente = Join-Path $Script:Appli 'precedente.txt'
$Script:FichierEnvironnement = Join-Path $Script:Donnees 'environnement'
$Script:Journaux = Join-Path $Script:Donnees 'journaux'
$Script:NomTache = 'Gestion MP PRO'
$Script:CheminTache = '\Gestion MP PRO\'
$Script:NomRegle = 'GestionMPPRO-Ecran'
$Script:QuiScripts = 'serveur Windows (scripts)'
$Script:SidAdministrateurs = 'S-1-5-32-544'
$Script:SidSysteme = 'S-1-5-18'
$Script:SidServiceLocal = 'S-1-5-19'

# Les programmes lancés d'ici parlent UTF-8 (Python, psql) ; la console aussi, si elle existe.
$env:PYTHONUTF8 = '1'
$env:PGCLIENTENCODING = 'UTF8'
$OutputEncoding = New-Object System.Text.UTF8Encoding $false
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch { }

function Dire([string]$Texte) { Write-Host $Texte }
function Etape([string]$Texte) { Write-Host ''; Write-Host "== $Texte" -ForegroundColor Cyan }
function Avertir([string]$Texte) { Write-Host "Attention : $Texte" -ForegroundColor Yellow }
function Echouer([string]$Texte) {
    Write-Host "Gestion MP PRO : $Texte" -ForegroundColor Red
    exit 1
}

function Exiger-Administrateur {
    $moi = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $moi.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Echouer 'ouvrir PowerShell « en tant qu''administrateur » (clic droit), puis relancer.'
    }
}

function Nom-De-Sid([string]$Sid) {
    # Le nom local d'un compte connu (« AUTORITE NT\SERVICE LOCAL » sur un Windows français).
    $id = New-Object System.Security.Principal.SecurityIdentifier($Sid)
    return $id.Translate([System.Security.Principal.NTAccount]).Value
}

function Sid-De-Compte([string]$Compte) {
    $nom = New-Object System.Security.Principal.NTAccount($Compte)
    return $nom.Translate([System.Security.Principal.SecurityIdentifier]).Value
}

function Invoke-Natif {
    # Lance un programme (psql, python…) sans que ses messages d'erreur deviennent des
    # exceptions de PowerShell : c'est son code de retour ($LASTEXITCODE) qui compte.
    param([scriptblock]$Bloc)
    $avant = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Bloc } finally { $ErrorActionPreference = $avant }
}

function Lire-Environnement {
    # Les lignes GESTIONMPPRO_NOM=valeur du fichier « environnement » deviennent des variables
    # de ce processus (une variable déjà posée par l'appelant l'emporte, comme sur le Mac).
    $valeurs = @{}
    if (-not (Test-Path -LiteralPath $Script:FichierEnvironnement)) { return $valeurs }
    foreach ($ligne in (Get-Content -LiteralPath $Script:FichierEnvironnement -Encoding UTF8)) {
        if ($ligne -notmatch '^(GESTIONMPPRO_[A-Z_]+)=(.*)$') { continue }
        $nom = $Matches[1]
        $valeur = $Matches[2]
        $valeurs[$nom] = $valeur
        if (-not [Environment]::GetEnvironmentVariable($nom, 'Process')) {
            [Environment]::SetEnvironmentVariable($nom, $valeur, 'Process')
        }
    }
    if (-not $env:GESTIONMPPRO_PORT) { $env:GESTIONMPPRO_PORT = '8050' }
    if (-not $env:GESTIONMPPRO_ECOUTE) { $env:GESTIONMPPRO_ECOUTE = '0.0.0.0' }
    return $valeurs
}

function Nom-De-Base([string]$Adresse) {
    # Le dernier segment de l'adresse, sans paramètres : …/gestion_mp_pro?x=y → gestion_mp_pro.
    if ($Adresse -match '/([^/?]+)(\?.*)?$') { return $Matches[1] }
    return ''
}

function Garder-La-Base([string]$Nom) {
    # Jamais la base de Gestion MP, ni une base qui n'est pas de Gestion MP PRO.
    if ($Nom -ne 'gestion_mp_pro' -and $Nom -notlike 'gestion_mp_pro_*') {
        Echouer "base « $Nom » refusée : seules gestion_mp_pro et gestion_mp_pro_* sont de Gestion MP PRO."
    }
}

function Parties-De-Base([string]$Adresse) {
    # postgresql+psycopg://role:motdepasse@hote:port/base → ses morceaux (pour psql).
    if ($Adresse -notmatch '^[^:]+://([^:@/]+)(:([^@/]*))?@([^:/]+)(:(\d+))?/([^/?]+)') {
        Echouer 'GESTIONMPPRO_BASE illisible dans le fichier environnement.'
    }
    $port = '5432'
    if ($Matches[6]) { $port = $Matches[6] }
    return @{ Role = $Matches[1]; MotDePasse = $Matches[3]; Hote = $Matches[4]; Port = $port
        Base = $Matches[7] }
}

function Version-Actuelle {
    if (-not (Test-Path -LiteralPath $Script:FichierActuelle)) { return '' }
    return (Get-Content -LiteralPath $Script:FichierActuelle -Encoding UTF8 | Select-Object -First 1).Trim()
}

function Dossier-De-Version([string]$Version) { return Join-Path $Script:Versions $Version }

function Python-De([string]$Version) {
    return Join-Path (Join-Path (Dossier-De-Version $Version) 'venv') 'Scripts\python.exe'
}

function Exiger-Version {
    $v = Version-Actuelle
    if (-not $v -or -not (Test-Path -LiteralPath (Python-De $v))) {
        Echouer "aucune version installée ($Script:Appli) : lancer installer.ps1."
    }
    return $v
}

function Poste {
    # poste.py (gestes de la base : migrer, sauvegarder, restaurer, compter) avec le code et le
    # Python de la version donnée (la version en service par défaut) ; ses messages d'erreur
    # s'affichent. Rend @{ Code = <code de retour> ; Sortie = <lignes de sa sortie> }.
    param([string[]]$Arguments, [string]$Version = '')
    if (-not $Version) { $Version = Exiger-Version }
    $dossier = Dossier-De-Version $Version
    $code = Join-Path $dossier 'backend'
    $py = Python-De $Version
    $poste = Join-Path (Join-Path $dossier 'outils') 'poste.py'
    $env:PYTHONPATH = $code
    Push-Location -LiteralPath $code
    try {
        $sortie = @(Invoke-Natif { & $py $poste --qui $Script:QuiScripts @Arguments })
        return @{ Code = $LASTEXITCODE; Sortie = $sortie }
    } finally {
        Pop-Location
    }
}

function Lancer-Poste {
    # Comme Poste, sortie affichée ; rend le code de retour seulement.
    param([string[]]$Arguments, [string]$Version = '')
    $r = Poste -Arguments $Arguments -Version $Version
    foreach ($ligne in $r.Sortie) { Dire $ligne }
    return $r.Code
}

function Etat-Http([int]$Port = 0, [int]$Delai = 5) {
    # /api/sante du serveur de ce poste : @{ Code = 200 ; Sante = <objet> } (Code 0 sans réponse).
    if ($Port -eq 0) { $Port = [int]$env:GESTIONMPPRO_PORT }
    try {
        $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec $Delai -Uri "http://127.0.0.1:$Port/api/sante"
        return @{ Code = [int]$r.StatusCode; Sante = ($r.Content | ConvertFrom-Json) }
    } catch {
        $reponse = $null
        if ($_.Exception.PSObject.Properties['Response']) { $reponse = $_.Exception.Response }
        if ($reponse) { return @{ Code = [int]$reponse.StatusCode; Sante = $null } }
        return @{ Code = 0; Sante = $null }
    }
}

function Pids-Pro([int]$Port = 0) {
    # Les processus de Gestion MP PRO qui écoutent sur le port (jamais un autre programme).
    if ($Port -eq 0) { $Port = [int]$env:GESTIONMPPRO_PORT }
    $trouves = @()
    $ecoutes = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($p in ($ecoutes | Select-Object -ExpandProperty OwningProcess -Unique)) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $p" -ErrorAction SilentlyContinue
        if ($proc -and $proc.CommandLine -match 'gestion_mp_pro\.main:app') { $trouves += [int]$p }
    }
    return $trouves
}

function Port-Pris-Par-Un-Autre([int]$Port = 0) {
    if ($Port -eq 0) { $Port = [int]$env:GESTIONMPPRO_PORT }
    $ecoutes = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    return ($ecoutes.Count -gt 0 -and @(Pids-Pro $Port).Count -eq 0)
}

function Outils-En-Cours([int[]]$Parents) {
    # pg_dump / pg_restore / psql lancés par le serveur (une sauvegarde ou une restauration).
    $enfants = @()
    foreach ($p in $Parents) {
        $enfants += @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $p" -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^(pg_dump|pg_restore|psql)\.exe$' })
    }
    return $enfants
}

function Arreter-Serveur([switch]$Force) {
    # Arrête la tâche planifiée (sans relance) puis le processus du serveur. Une sauvegarde ou
    # une restauration en cours est attendue (10 minutes au plus) : l'interrompre laisserait un
    # fichier partiel. Le processus est arrêté net (Windows n'a pas de signal d'arrêt doux pour
    # lui) : PostgreSQL annule toute transaction en cours, rien n'est écrit à moitié.
    $tache = Get-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache -ErrorAction SilentlyContinue
    $pids = @(Pids-Pro)
    if (-not $Force) {
        for ($i = 0; $i -lt 600 -and @(Outils-En-Cours $pids).Count -gt 0; $i++) {
            if ($i -eq 0) { Dire 'Une sauvegarde ou une restauration est en cours : attente de sa fin…' }
            Start-Sleep -Seconds 1
        }
    }
    if ($tache -and $tache.State -eq 'Running') {
        Stop-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache
    }
    foreach ($p in @(Pids-Pro)) {
        foreach ($e in @(Outils-En-Cours @($p))) { Stop-Process -Id $e.ProcessId -Force -ErrorAction SilentlyContinue }
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
    for ($i = 0; $i -lt 40 -and @(Pids-Pro).Count -gt 0; $i++) { Start-Sleep -Milliseconds 500 }
    if (@(Pids-Pro).Count -gt 0) { Echouer 'le serveur ne s''est pas arrêté.' }
}

function Attendre-Sante([string]$Version, [int]$Secondes = 180) {
    # Attend que /api/sante réponde 200, avec cette version et le schéma attendu. Rend l'état.
    $fin = (Get-Date).AddSeconds($Secondes)
    $e = @{ Code = 0; Sante = $null }
    while ((Get-Date) -lt $fin) {
        $e = Etat-Http
        if ($e.Code -eq 200 -and $e.Sante -and ($e.Sante.version -eq $Version) -and
            ($e.Sante.schema -eq $e.Sante.schema_attendu)) { return $e }
        Start-Sleep -Seconds 2
    }
    return $e
}

function Proteger([string]$Chemin, [string]$SidService, [string]$DroitService) {
    # Droits propres (sans héritage) : administrateurs et SYSTEM complets, le compte du service
    # avec `DroitService` (R lecture, M modification). Les autres comptes n'y lisent rien
    # (le fichier environnement porte le mot de passe de la base ; les sauvegardes, les
    # empreintes des codes).
    $heritage = ''
    if (Test-Path -LiteralPath $Chemin -PathType Container) { $heritage = '(OI)(CI)' }
    $droits = @("*$($Script:SidAdministrateurs):$heritage(F)", "*$($Script:SidSysteme):$heritage(F)",
        "*$($SidService):$heritage($DroitService)")
    Invoke-Natif { & icacls.exe $Chemin /inheritance:r /grant:r @droits /Q | Out-Null }
    if ($LASTEXITCODE -ne 0) { Echouer "droits impossibles à poser sur $Chemin." }
}

function Ecrire-Texte([string]$Chemin, [string]$Texte) {
    # UTF-8 sans BOM (lu tel quel par Python et par ces scripts).
    [System.IO.File]::WriteAllText($Chemin, $Texte, (New-Object System.Text.UTF8Encoding $false))
}

function Installer-Version([string]$Paquet, [string]$Python, [string]$Roues = '') {
    # Copie le code et l'écran construit du paquet dans versions\<version>, avec son propre
    # environnement Python (dépendances figées de requirements-windows.lock, roues binaires
    # seulement : rien n'est compilé sur le serveur). Rend la version. Idempotent.
    $version = (Get-Content -LiteralPath (Join-Path $Paquet 'VERSION') -Encoding UTF8 | Select-Object -First 1).Trim()
    if ($version -notmatch '^[0-9A-Za-z._-]+$') { Echouer "VERSION illisible dans $Paquet." }
    $cible = Dossier-De-Version $version
    if (Test-Path -LiteralPath (Join-Path $cible '.complet')) {
        Dire "Version $version : déjà prête ($cible)."
        return $version
    }
    if ((Version-Actuelle) -eq $version) { Echouer "la version $version en service est incomplète : la réinstaller exige d'arrêter le serveur (arreter.ps1)." }
    if (Test-Path -LiteralPath $cible) { Remove-Item -LiteralPath $cible -Recurse -Force }
    New-Item -ItemType Directory -Force -Path (Join-Path $cible 'backend') | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $cible 'frontend') | Out-Null
    Copy-Item -LiteralPath (Join-Path $Paquet 'VERSION') -Destination $cible
    Copy-Item -LiteralPath (Join-Path $Paquet 'backend\gestion_mp_pro') -Destination (Join-Path $cible 'backend') -Recurse
    Copy-Item -LiteralPath (Join-Path $Paquet 'backend\requirements-windows.lock') -Destination (Join-Path $cible 'backend')
    Copy-Item -LiteralPath (Join-Path $Paquet 'frontend\dist') -Destination (Join-Path $cible 'frontend') -Recurse
    Copy-Item -LiteralPath (Join-Path $Paquet 'windows') -Destination (Join-Path $cible 'outils') -Recurse
    Dire "Version $version : environnement Python (dépendances figées)…"
    Invoke-Natif { & $Python -m venv (Join-Path $cible 'venv') | Out-Host }
    if ($LASTEXITCODE -ne 0) { Echouer 'environnement Python impossible à créer.' }
    $pip = @('-m', 'pip', 'install', '--disable-pip-version-check', '--no-input', '--only-binary=:all:',
        '-r', (Join-Path $cible 'backend\requirements-windows.lock'))
    if ($Roues) { $pip += @('--no-index', '--find-links', $Roues) }
    Invoke-Natif { & (Python-De $version) @pip | Out-Host }
    if ($LASTEXITCODE -ne 0) {
        Remove-Item -LiteralPath $cible -Recurse -Force -ErrorAction SilentlyContinue
        Echouer 'dépendances impossibles à installer (accès à Internet ? sinon le paquet avec ses roues : -Roues).'
    }
    Ecrire-Texte (Join-Path $cible '.complet') "$version`r`n"
    return $version
}

function Mettre-Outils-En-Place([string]$Version) {
    # Les scripts de la version en service deviennent ceux de « outils » (un retour arrière
    # reprend donc aussi les scripts de la version précédente).
    # Fichier par fichier (le dossier lui-même peut être le dossier courant d'une console).
    $source = Join-Path (Dossier-De-Version $Version) 'outils'
    New-Item -ItemType Directory -Force -Path $Script:Outils | Out-Null
    $gardes = @(Get-ChildItem -LiteralPath $source -File | Select-Object -ExpandProperty Name)
    foreach ($f in @(Get-ChildItem -LiteralPath $Script:Outils -File)) {
        if ($gardes -notcontains $f.Name) { Remove-Item -LiteralPath $f.FullName -Force }
    }
    foreach ($nom in $gardes) {
        Copy-Item -LiteralPath (Join-Path $source $nom) -Destination $Script:Outils -Force
    }
}

function Trouver-Paquet([string]$Chemin) {
    # Un dossier de paquet (qui contient VERSION), ou un .zip à déballer dans ProgramData.
    if (-not (Test-Path -LiteralPath $Chemin)) { Echouer "paquet introuvable : $Chemin" }
    if ($Chemin -like '*.zip') {
        $dest = Join-Path $Script:Donnees ('paquets\' + [IO.Path]::GetFileNameWithoutExtension($Chemin))
        if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
        Expand-Archive -LiteralPath $Chemin -DestinationPath $dest
        $Chemin = $dest
    }
    $version = Get-ChildItem -LiteralPath $Chemin -Recurse -Filter VERSION -File |
        Sort-Object { $_.FullName.Length } | Select-Object -First 1
    if (-not $version) { Echouer "ce n'est pas un paquet de Gestion MP PRO (pas de fichier VERSION) : $Chemin" }
    $racine = $version.DirectoryName
    # Un fichier copié depuis Internet ou une clé est « bloqué » par Windows : on le débloque.
    Get-ChildItem -LiteralPath $racine -Recurse -File | Unblock-File
    return $racine
}
