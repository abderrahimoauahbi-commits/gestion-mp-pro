#Requires -Version 5.1
# Gestion MP PRO — fonctions d'administration du serveur Windows (PostgreSQL en administrateur,
# tâche planifiée, pare-feu, dossiers), lues (dot-source) par installer.ps1, recette.ps1 et
# desinstaller.ps1 après commun.ps1.
#
# Mots de passe : jamais sur une ligne de commande (la liste des processus les montrerait) ni
# affichés. Celui de l'administrateur « postgres » passe par PGPASSWORD, dans ce seul
# processus, effacé à la fin ; les requêtes qui portent un mot de passe passent par l'entrée de
# psql, et leurs messages d'erreur ne sont pas affichés (ils pourraient citer la requête).

$Script:Psql = ''
$Script:PortPg = 5432

function Lire-Secret([string]$Invite) {
    $secret = Read-Host -AsSecureString $Invite
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Nouveau-Mot-De-Passe([int]$Longueur = 32) {
    # Lettres et chiffres seulement (il entre dans une adresse de connexion), tirage sans biais.
    $alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    $limite = 256 - (256 % $alphabet.Length)
    $hasard = [Security.Cryptography.RandomNumberGenerator]::Create()
    $octet = New-Object byte[] 1
    $mot = New-Object System.Text.StringBuilder
    while ($mot.Length -lt $Longueur) {
        $hasard.GetBytes($octet)
        if ($octet[0] -lt $limite) { [void]$mot.Append($alphabet[$octet[0] % $alphabet.Length]) }
    }
    return $mot.ToString()
}

function Sql([string]$Requete, [string]$Base = 'postgres', [string]$Role = 'postgres') {
    # Une requête par l'entrée de psql (rien sur la ligne de commande) ; rend sa sortie (-At).
    $lignes = @(Invoke-Natif { $Requete | & $Script:Psql -X -q -At -v ON_ERROR_STOP=1 -h localhost -p $Script:PortPg -U $Role -d $Base -f - })
    if ($LASTEXITCODE -ne 0) { Echouer "PostgreSQL a refusé la requête (base $Base, rôle $Role) : voir le message ci-dessus." }
    return ($lignes -join "`n").Trim()
}

function Sql-Secrete([string]$Requete) {
    # Comme Sql, pour une requête qui porte un mot de passe : son message d'erreur est tu.
    $null = Invoke-Natif { $Requete | & $Script:Psql -X -q -At -v ON_ERROR_STOP=1 -h localhost -p $Script:PortPg -U postgres -d postgres -f - 2>$null }
    if ($LASTEXITCODE -ne 0) { Echouer 'PostgreSQL a refusé de poser le mot de passe du rôle (message tu : il citerait le mot de passe).' }
}

function Trouver-PostgreSQL([string]$Choisi) {
    # Le psql.exe de PostgreSQL 16 ou plus (le plus récent installé) ; le service doit tourner.
    $bin = $Choisi
    if (-not $bin) {
        $racine = Join-Path $env:ProgramFiles 'PostgreSQL'
        $dossiers = @(Get-ChildItem -LiteralPath $racine -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^\d+$' -and [int]$_.Name -ge 16 } |
            Sort-Object { [int]$_.Name } -Descending)
        if ($dossiers.Count -eq 0) { Echouer "PostgreSQL 16 introuvable dans $racine : l'installer d'abord (INSTALLATION-WINDOWS.md § 2)." }
        $bin = Join-Path $dossiers[0].FullName 'bin'
    }
    foreach ($o in @('psql.exe', 'pg_dump.exe', 'pg_restore.exe')) {
        if (-not (Test-Path -LiteralPath (Join-Path $bin $o))) { Echouer "$o introuvable dans $bin." }
    }
    $services = @(Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue)
    if (@($services | Where-Object { $_.Status -eq 'Running' }).Count -eq 0) {
        Echouer 'aucun service PostgreSQL en marche (services.msc : « postgresql-x64-16 »).'
    }
    foreach ($s in $services) {
        if ($s.StartType -ne 'Automatic') { Avertir "le service $($s.Name) ne démarre pas avec Windows (services.msc : type de démarrage Automatique)." }
    }
    return (Join-Path $bin 'psql.exe')
}

function Verifier-Outils-Pg([string]$Bin, [int]$VersionServeur) {
    # pg_dump doit être de la version du serveur ou plus récent (sinon il refuse de sauvegarder).
    $texte = [string](Invoke-Natif { & (Join-Path $Bin 'pg_dump.exe') --version })
    if ($texte -notmatch '(\d+)\.') { Echouer "version de pg_dump illisible : $texte" }
    if ([int]$Matches[1] -lt [math]::Floor($VersionServeur / 10000)) {
        Echouer "pg_dump $($Matches[1]) est plus ancien que le serveur PostgreSQL : indiquer le bon dossier (-PostgreSQL)."
    }
    Dire "Serveur PostgreSQL $VersionServeur ; $texte."
}

function Trouver-Python([string]$Choisi) {
    # Python 3.12 64 bits, installé pour tous les utilisateurs (le compte du service doit le lire).
    $candidats = @()
    if ($Choisi) { $candidats += $Choisi } else {
        $py = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($py) {
            $chemin = [string](Invoke-Natif { & $py.Source -3.12 -c 'import sys; print(sys.executable)' 2>$null })
            if ($LASTEXITCODE -eq 0 -and $chemin.Trim()) { $candidats += $chemin.Trim() }
        }
        $candidats += (Join-Path $env:ProgramFiles 'Python312\python.exe')
    }
    foreach ($c in $candidats) {
        if (-not (Test-Path -LiteralPath $c)) { continue }
        $info = [string](Invoke-Natif { & $c -c 'import sys,struct; print(sys.version_info[0], sys.version_info[1], struct.calcsize(chr(80))*8, sys.base_prefix)' })
        $morceaux = $info.Trim() -split ' ', 4
        if ($morceaux.Count -lt 4 -or $morceaux[0] -ne '3' -or $morceaux[1] -ne '12') { continue }
        if ($morceaux[2] -ne '64') { Echouer "$c est un Python 32 bits : installer Python 3.12 64 bits (« Windows installer (64-bit) »)." }
        if ($morceaux[3] -like "$env:SystemDrive\Users\*") {
            Echouer "$c est installé pour un seul utilisateur : réinstaller Python 3.12 avec « Install for all users » (le service ne lit pas un profil)."
        }
        return $c
    }
    Echouer 'Python 3.12 64 bits introuvable : l''installer depuis python.org (« Install for all users »), ou indiquer -Python.'
}

function Choisir-Compte([string]$Compte) {
    # Le compte du service : celui demandé, sinon celui de la tâche déjà enregistrée, sinon
    # SERVICE LOCAL (compte intégré sans mot de passe, peu de droits).
    if ($Compte) {
        $id = Get-Credential -UserName $Compte -Message "Mot de passe du compte $Compte (tâche planifiée de Gestion MP PRO)"
        if (-not $id) { Echouer 'mot de passe du compte non donné.' }
        return @{ Nom = $Compte; Sid = (Sid-De-Compte $Compte); Identifiant = $id }
    }
    $tache = Get-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache -ErrorAction SilentlyContinue
    if ($tache) {
        try { return @{ Nom = $tache.Principal.UserId; Sid = (Sid-De-Compte $tache.Principal.UserId); Identifiant = $null; Garder = $true } }
        catch { Avertir "compte de la tâche existante illisible ($($tache.Principal.UserId)) : SERVICE LOCAL." }
    }
    return @{ Nom = (Nom-De-Sid $Script:SidServiceLocal); Sid = $Script:SidServiceLocal; Identifiant = $null }
}

function Choisir-Mot-De-Passe {
    $mot = Lire-Secret 'Mot de passe du rôle PostgreSQL gestion_mp_pro (Entrée : tiré au hasard, conseillé)'
    if (-not $mot) { return (Nouveau-Mot-De-Passe) }
    if ($mot -notmatch '^[A-Za-z0-9]{16,}$') { Echouer 'mot de passe refusé : 16 lettres ou chiffres au moins, rien d''autre (il entre dans une adresse).' }
    return $mot
}

function Preparer-Role-Et-Base {
    # Le rôle gestion_mp_pro (propriétaire de sa base seulement) et sa base ; rend l'adresse de
    # connexion (GESTIONMPPRO_BASE), mot de passe compris, pour le fichier environnement.
    $role = 'gestion_mp_pro'
    $base = 'gestion_mp_pro'
    $motDePasse = ''
    $valeurs = Lire-Environnement
    if ($valeurs.ContainsKey('GESTIONMPPRO_BASE')) { $motDePasse = (Parties-De-Base $valeurs['GESTIONMPPRO_BASE']).MotDePasse }
    if ((Sql "SELECT 1 FROM pg_roles WHERE rolname = '$role'") -ne '1') {
        if (-not $motDePasse) { $motDePasse = Choisir-Mot-De-Passe }
        Sql-Secrete "CREATE ROLE $role LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '$motDePasse'"
        Dire "Rôle $role : créé."
    } elseif (-not $motDePasse) {
        $motDePasse = Choisir-Mot-De-Passe
        Sql-Secrete "ALTER ROLE $role PASSWORD '$motDePasse'"
        Dire "Rôle $role : déjà là ; nouveau mot de passe posé (aucun fichier environnement ne le portait)."
    } else {
        Dire "Rôle $role : déjà là."
    }
    $proprietaire = Sql "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = '$base'"
    if (-not $proprietaire) {
        Sql "CREATE DATABASE $base OWNER $role ENCODING 'UTF8' TEMPLATE template0" | Out-Null
        Dire "Base $base : créée (propriétaire $role, UTF-8, tri de la langue du serveur)."
    } elseif ($proprietaire -ne $role) {
        Echouer "la base $base existe mais appartient à $proprietaire (et non $role) : rien n'est changé."
    } else {
        Dire "Base $base : déjà là."
    }
    Sql "REVOKE CONNECT, TEMPORARY ON DATABASE $base FROM PUBLIC" | Out-Null
    $admin = $env:PGPASSWORD
    $env:PGPASSWORD = $motDePasse
    try { $null = Sql 'SELECT 1' $base $role } finally { $env:PGPASSWORD = $admin }
    return "postgresql+psycopg://$($role):$motDePasse@localhost:$($Script:PortPg)/$base"
}

function Preparer-Dossiers([string]$SidService, [string]$Copie) {
    # ProgramData\Gestion MP PRO fermé aux autres comptes (le service y écrit), puis ses dossiers.
    New-Item -ItemType Directory -Force -Path $Script:Donnees | Out-Null
    Proteger $Script:Donnees $SidService 'M'
    foreach ($d in @('sauvegardes\gestion_mp_pro', 'pieces\gestion_mp_pro', 'journaux', 'paquets')) {
        New-Item -ItemType Directory -Force -Path (Join-Path $Script:Donnees $d) | Out-Null
    }
    Dire "$($Script:Donnees) : administrateurs, SYSTEM et compte du service seulement."
    if ($Copie) {
        New-Item -ItemType Directory -Force -Path $Copie | Out-Null
        try { Proteger $Copie $SidService 'M' } catch { Avertir "droits non posés sur $Copie (disque FAT/exFAT ou partage ?) : vérifier que le compte du service peut y écrire." }
        Dire "Copie des sauvegardes : $Copie"
    }
}

function Poser-Reglage([string]$Nom, [string]$Valeur) {
    # Remplace (ou ajoute) la ligne NOM=valeur du fichier environnement, le reste intact.
    $lignes = @(Get-Content -LiteralPath $Script:FichierEnvironnement -Encoding UTF8)
    $trouve = $false
    for ($i = 0; $i -lt $lignes.Count; $i++) {
        if ($lignes[$i] -like "$Nom=*") { $lignes[$i] = "$Nom=$Valeur"; $trouve = $true }
    }
    if (-not $trouve) { $lignes += "$Nom=$Valeur" }
    Ecrire-Texte $Script:FichierEnvironnement (($lignes -join "`r`n") + "`r`n")
}

function Ecrire-Environnement([string]$Adresse, [string]$BinPg, [int]$Port, [string]$Copie, [string]$SidService) {
    # Le fichier environnement : créé une fois (modèle commenté), puis seuls la base et la copie
    # demandées sont reposées ; droits : administrateurs, SYSTEM, lecture pour le service.
    if (-not (Test-Path -LiteralPath $Script:FichierEnvironnement)) {
        $d = $Script:Donnees
        $modele = @(
            '# Réglages de Gestion MP PRO sur ce serveur Windows, lus à chaque démarrage du serveur.',
            '# Une ligne GESTIONMPPRO_NOM=valeur, sans guillemets. Ce fichier porte le mot de passe de',
            '# la base : lisible des administrateurs et du service seulement. Après un changement :',
            '# arreter.ps1 puis demarrer.ps1. Tous les réglages : docs/ARCHITECTURE.md § 16.',
            "GESTIONMPPRO_BASE=$Adresse",
            'GESTIONMPPRO_ECOUTE=0.0.0.0',
            "GESTIONMPPRO_PORT=$Port",
            'GESTIONMPPRO_FUSEAU=Africa/Casablanca',
            "GESTIONMPPRO_SAUVEGARDES=$d\sauvegardes",
            "GESTIONMPPRO_PIECES=$d\pieces",
            "GESTIONMPPRO_JOURNAL_FICHIER=$d\journaux\serveur.log",
            "GESTIONMPPRO_PG_BIN=$BinPg",
            '# Copie de chaque sauvegarde sur un AUTRE disque (second disque, disque USB, partage) :',
            '# indispensable (un disque qui meurt emporte la base ET ses sauvegardes).',
            "GESTIONMPPRO_SAUVEGARDES_COPIE=$Copie",
            '# Serveur loué sur Internet, derrière un relais HTTPS sur ce serveur (guide § 8) :',
            '# GESTIONMPPRO_ECOUTE=127.0.0.1',
            '# GESTIONMPPRO_HTTPS=1',
            '# GESTIONMPPRO_ADRESSE=https://gestion-mp-pro.exemple.ma',
            '# Courriels d''alerte (facultatif) :',
            '# GESTIONMPPRO_SMTP_HOTE=',
            '# GESTIONMPPRO_SMTP_PORT=587',
            '# GESTIONMPPRO_SMTP_UTILISATEUR=',
            '# GESTIONMPPRO_SMTP_MOT_DE_PASSE=',
            '# GESTIONMPPRO_SMTP_EXPEDITEUR=')
        Ecrire-Texte $Script:FichierEnvironnement (($modele -join "`r`n") + "`r`n")
        Dire "Réglages : $($Script:FichierEnvironnement) (créé)."
    } else {
        Poser-Reglage 'GESTIONMPPRO_BASE' $Adresse
        if ($Copie) { Poser-Reglage 'GESTIONMPPRO_SAUVEGARDES_COPIE' $Copie }
        Dire "Réglages : $($Script:FichierEnvironnement) (gardé ; base$(if ($Copie) { ' et copie' }) reposées)."
    }
    Proteger $Script:FichierEnvironnement $SidService 'R'
}

function Enregistrer-Tache($Compte) {
    # La tâche « Gestion MP PRO » : au démarrage de Windows (30 s après, le temps de
    # PostgreSQL), sans limite de durée, relancée chaque minute en cas d'échec, priorité normale.
    $existante = Get-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache -ErrorAction SilentlyContinue
    if ($existante -and $Compte.ContainsKey('Garder')) { Dire "Tâche planifiée : déjà là (compte $($Compte.Nom))."; return }
    $ps = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $lanceur = Join-Path $Script:Outils 'lancer-serveur.ps1'
    $action = New-ScheduledTaskAction -Execute $ps -WorkingDirectory $Script:Outils `
        -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$lanceur`""
    $declencheur = New-ScheduledTaskTrigger -AtStartup
    $declencheur.Delay = 'PT30S'
    $reglages = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 `
        -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -Priority 4
    $description = "Gestion MP PRO : serveur de l'écran (port $env:GESTIONMPPRO_PORT). Scripts : $($Script:Outils)."
    if ($Compte.Identifiant) {
        Register-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache -Action $action `
            -Trigger $declencheur -Settings $reglages -Description $description -User $Compte.Nom `
            -Password $Compte.Identifiant.GetNetworkCredential().Password -RunLevel Limited -Force | Out-Null
    } else {
        $principal = New-ScheduledTaskPrincipal -UserId $Compte.Nom -LogonType ServiceAccount -RunLevel Limited
        Register-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache -Action $action `
            -Trigger $declencheur -Settings $reglages -Description $description -Principal $principal -Force | Out-Null
    }
    Dire "Tâche planifiée « $($Script:NomTache) » : au démarrage de Windows, compte $($Compte.Nom)."
}

function Ouvrir-Pare-Feu([int]$Port) {
    # Le port de l'écran, en entrée, pour les réseaux Domaine et Privé seulement (jamais Public).
    Remove-NetFirewallRule -Name $Script:NomRegle -ErrorAction SilentlyContinue
    New-NetFirewallRule -Name $Script:NomRegle -DisplayName "Gestion MP PRO (écran, TCP $Port)" `
        -Description 'Postes et téléphones de l''usine vers Gestion MP PRO.' -Direction Inbound `
        -Action Allow -Protocol TCP -LocalPort $Port -Profile Domain, Private | Out-Null
    Dire "Pare-feu : TCP $Port ouvert en entrée (profils Domaine et Privé)."
    foreach ($r in @(Get-NetConnectionProfile -ErrorAction SilentlyContinue | Where-Object { $_.NetworkCategory -eq 'Public' })) {
        Avertir "le réseau « $($r.Name) » est classé Public : la règle ne s'y applique pas. Réseau de l'usine : le classer Privé (Set-NetConnectionProfile -InterfaceIndex $($r.InterfaceIndex) -NetworkCategory Private). Serveur loué sur Internet : c'est voulu (guide § 8)."
    }
}

function Adresses-Du-Serveur([int]$Port) {
    $adresses = @("http://$($env:COMPUTERNAME):$Port")
    foreach ($ip in @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue)) {
        if ($ip.IPAddress -notlike '127.*' -and $ip.IPAddress -notlike '169.254.*') { $adresses += "http://$($ip.IPAddress):$Port" }
    }
    return $adresses
}
