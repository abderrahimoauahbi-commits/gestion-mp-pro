#Requires -Version 5.1
<#
Gestion MP PRO — installe (ou complète) le serveur Windows. Idempotent : relancé, il ne refait
que ce qui manque et ne supprime jamais rien (ni rôle, ni base, ni sauvegarde, ni réglage).
Guide pas à pas : INSTALLATION-WINDOWS.md (dans le paquet, ou docs/ du dépôt).

À lancer depuis le paquet déballé, dans un PowerShell ouvert « en tant qu'administrateur » :

  powershell -ExecutionPolicy Bypass -File .\windows\installer.ps1
  powershell -ExecutionPolicy Bypass -File .\windows\installer.ps1 -Copie 'E:\Sauvegardes Gestion MP PRO'

Options :
  -Copie DOSSIER          copie de chaque sauvegarde sur un AUTRE disque (indispensable)
  -Port 8050              port de l'écran pour les postes et les téléphones
  -Python CHEMIN          python.exe 3.12 64 bits (défaut : py -3.12, puis Program Files\Python312)
  -PostgreSQL DOSSIER     dossier bin de PostgreSQL (défaut : le plus récent, 16 ou plus)
  -PortPostgreSQL 5432
  -Compte NOM             compte du service (défaut : SERVICE LOCAL, sans mot de passe) ; un
                          compte à mot de passe seulement si la copie va sur un partage réseau
  -Roues DOSSIER          dépendances Python sans Internet (paquet fait avec --avec-roues)
  -SansPareFeu            n'ouvre pas le port dans le pare-feu
  -SansDemarrageAutomatique  n'enregistre pas la tâche planifiée

Fait, dans l'ordre :
  1. vérifie Windows 64 bits, les droits d'administrateur, PostgreSQL 16 (service en marche,
     outils psql/pg_dump/pg_restore de même version ou plus récents) et Python 3.12 64 bits
     installé pour tous les utilisateurs ;
  2. crée le rôle PostgreSQL gestion_mp_pro (mot de passe demandé ou tiré au hasard, jamais
     affiché ni écrit ailleurs que dans le fichier environnement) et sa base gestion_mp_pro ;
  3. installe la version du paquet dans C:\Program Files\Gestion MP PRO\versions\<version>
     (code, écran construit, environnement Python à elle) et les scripts dans …\outils ;
  4. crée C:\ProgramData\Gestion MP PRO (sauvegardes, pièces jointes, journaux), fermé aux
     autres comptes, et y écrit le fichier environnement (s'il n'existe pas) ;
  5. met la base au schéma de cette version (migrations Alembic) et, base vide, en fait une
     sauvegarde « base vide de référence » ;
  6. enregistre la tâche planifiée « Gestion MP PRO » (au démarrage de Windows, sous le compte
     du service, relancée en cas d'échec, sans limite de durée) ;
  7. ouvre le port dans le pare-feu, profils Domaine et Privé seulement ;
  8. démarre le serveur et attend que /api/sante réponde.
#>
param(
    [string]$Paquet = '',
    [string]$Copie = '',
    [int]$Port = 8050,
    [string]$Python = '',
    [string]$PostgreSQL = '',
    [int]$PortPostgreSQL = 5432,
    [string]$Compte = '',
    [string]$Roues = '',
    [switch]$SansPareFeu,
    [switch]$SansDemarrageAutomatique
)

. "$PSScriptRoot\commun.ps1"
. "$PSScriptRoot\fonctions-admin.ps1"

Etape '1. Prérequis'
Exiger-Administrateur
if (-not [Environment]::Is64BitOperatingSystem -or -not [Environment]::Is64BitProcess) {
    Echouer 'Windows et PowerShell 64 bits sont nécessaires.'
}
if (-not $Paquet) { $Paquet = Split-Path $PSScriptRoot -Parent }
$Paquet = Trouver-Paquet $Paquet
foreach ($f in @('VERSION', 'backend\gestion_mp_pro\main.py', 'backend\requirements-windows.lock',
        'frontend\dist\index.html', 'windows\poste.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Paquet $f))) { Echouer "paquet incomplet : $f manque ($Paquet)." }
}
$Script:Psql = Trouver-PostgreSQL $PostgreSQL
$binPg = Split-Path $Script:Psql -Parent
$Script:PortPg = $PortPostgreSQL
$Python = Trouver-Python $Python
Dire "Paquet : $Paquet (version $((Get-Content -LiteralPath (Join-Path $Paquet 'VERSION')).Trim()))"
Dire "PostgreSQL : $binPg ; Python : $Python"

$compteService = Choisir-Compte $Compte
$sidService = $compteService.Sid

Etape '2. Rôle et base PostgreSQL'
$adminDejaDonne = [bool]$env:PGPASSWORD
if (-not $adminDejaDonne) {
    $env:PGPASSWORD = Lire-Secret 'Mot de passe de l''administrateur « postgres » de PostgreSQL (choisi à son installation)'
}
try {
    $versionServeur = [int](Sql 'SHOW server_version_num')
    if ($versionServeur -lt 160000) { Echouer "PostgreSQL 16 au moins est attendu (trouvé $versionServeur)." }
    Verifier-Outils-Pg $binPg $versionServeur
    $adresse = Preparer-Role-Et-Base
} finally {
    if (-not $adminDejaDonne) { Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue }
}

Etape '3. Version et scripts'
New-Item -ItemType Directory -Force -Path $Script:Versions | Out-Null
$version = Installer-Version $Paquet $Python $Roues
$ancienne = Version-Actuelle
if ($ancienne -and $ancienne -ne $version) {
    Avertir "la version $ancienne est en service : pour passer à $version, utiliser mettre-a-jour.ps1 (sauvegarde d'abord, retour arrière possible). Rien n'est changé à la version en service."
    $version = $ancienne
} else {
    Ecrire-Texte $Script:FichierActuelle "$version`r`n"
}
Mettre-Outils-En-Place $version
Dire "Version en service : $version ; scripts : $($Script:Outils)"

Etape '4. Dossiers des données et réglages'
Preparer-Dossiers $sidService $Copie
Ecrire-Environnement $adresse $binPg $Port $Copie $sidService
$null = Lire-Environnement

Etape '5. Schéma de la base'
if ((Lancer-Poste @('migrer')) -ne 0) { Echouer 'la mise au schéma de la base a échoué (voir ci-dessus).' }
$etat = (Poste @('etat')).Sortie | Select-Object -Last 1 | ConvertFrom-Json
if ($etat.comptes -eq 0) {
    Dire 'Base vide : sauvegarde « base vide de référence »…'
    if ((Lancer-Poste @('sauvegarder', '--genre', 'reference-vide')) -ne 0) { Echouer 'sauvegarde impossible (voir ci-dessus).' }
}

Etape '6. Démarrage automatique'
if ($SansDemarrageAutomatique) {
    Dire 'Non enregistré (-SansDemarrageAutomatique) : le serveur ne démarrera pas seul.'
} else {
    Enregistrer-Tache $compteService
}

Etape '7. Pare-feu'
if ($SansPareFeu) { Dire 'Port non ouvert (-SansPareFeu).' } else { Ouvrir-Pare-Feu $Port }

Etape '8. Démarrage'
if ($SansDemarrageAutomatique) {
    Dire 'Démarrage : enregistrer la tâche (relancer sans -SansDemarrageAutomatique).'
} else {
    if (@(Pids-Pro).Count -eq 0) { Demarrer-Tache }
    $e = Attendre-Sante $version 180
    if ($e.Code -ne 200) { Echouer "le serveur ne répond pas sur le port $Port : voir $($Script:Journaux)\demarrage.log et lanceur.log." }
    Dire "Gestion MP PRO $version répond (/api/sante : $($e.Sante.etat))."
}
Etape 'Fait'
Dire 'Ouvrir l''écran depuis un poste ou un téléphone de l''usine :'
foreach ($a in (Adresses-Du-Serveur $Port)) { Dire "  $a" }
Dire 'Au premier accès, l''écran demande de créer le compte de la direction.'
if (-not $Copie -and -not $env:GESTIONMPPRO_SAUVEGARDES_COPIE) {
    Avertir "aucune copie des sauvegardes sur un autre disque : la régler (GESTIONMPPRO_SAUVEGARDES_COPIE dans $($Script:FichierEnvironnement), ou relancer avec -Copie), puis arreter.ps1 et demarrer.ps1."
}
