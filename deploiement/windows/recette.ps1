#Requires -Version 5.1
<#
Gestion MP PRO — recette automatique du serveur Windows (INSTALLATION-WINDOWS.md § 10). Elle
ne change rien à la base de production : elle la lit, la sauvegarde (une sauvegarde manuelle
de plus), puis restaure cette sauvegarde sur une base d'essai À PART,
gestion_mp_pro_recette_essai, la fait servir un instant par un second serveur (port 8059, sur
127.0.0.1 seulement), compare ses lignes à la production, et la supprime. À lancer en
administrateur, serveur en marche, à un moment calme (sans saisie en cours) :

  & 'C:\Program Files\Gestion MP PRO\outils\recette.ps1'
  & '…\recette.ps1' -SansRestauration     # sans la base d'essai (pas de mot de passe postgres)

Chaque contrôle s'affiche « ok » ou « KO » ; code de sortie 0 si tout est ok.
#>
param([switch]$SansRestauration, [int]$PortEssai = 8059)
. "$PSScriptRoot\commun.ps1"
. "$PSScriptRoot\fonctions-admin.ps1"

$Script:Bilan = @{ Ok = 0; Ko = 0 }
function Controle([string]$Nom, [bool]$Bon, [string]$Detail = '') {
    if ($Bon) { $Script:Bilan.Ok++; $marque = 'ok'; $couleur = 'Green' } else { $Script:Bilan.Ko++; $marque = 'KO'; $couleur = 'Red' }
    $texte = "  $marque   $Nom"
    if ($Detail) { $texte += " — $Detail" }
    Write-Host $texte -ForegroundColor $couleur
}

function Avec-Mot-De-Passe([string]$MotDePasse, [scriptblock]$Bloc) {
    $avant = $env:PGPASSWORD
    $env:PGPASSWORD = $MotDePasse
    try { & $Bloc } finally { $env:PGPASSWORD = $avant }
}

function Controler-Serveur([string]$Version) {
    $e = Etat-Http
    Controle '/api/sante répond 200' ($e.Code -eq 200) "code $($e.Code)"
    if ($e.Sante) {
        Controle 'version servie = version en service' ($e.Sante.version -eq $Version) "$($e.Sante.version)"
        Controle 'schéma de la base = schéma attendu' ($e.Sante.schema -eq $e.Sante.schema_attendu) "$($e.Sante.schema)"
        Controle 'état « ok »' ($e.Sante.etat -eq 'ok') "$($e.Sante.sauvegarde_alerte)"
    }
    $t = Get-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache -ErrorAction SilentlyContinue
    Controle 'tâche planifiée enregistrée et active' ($null -ne $t -and $t.State -ne 'Disabled') "$(if ($t) { $t.State })"
    if ($t) {
        $auDemarrage = @($t.Triggers | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskBootTrigger' }).Count -gt 0
        Controle 'tâche : au démarrage de Windows' $auDemarrage
        Controle 'tâche : sans limite de durée' ($t.Settings.ExecutionTimeLimit -eq 'PT0S') "$($t.Settings.ExecutionTimeLimit)"
        Controle 'tâche : relancée en cas d''échec' ($t.Settings.RestartCount -gt 0) "$($t.Settings.RestartCount) fois"
        Controle 'tâche : droits limités (pas « plus haut niveau »)' ($t.Principal.RunLevel -eq 'Limited') "$($t.Principal.UserId)"
    }
    $regle = Get-NetFirewallRule -Name $Script:NomRegle -ErrorAction SilentlyContinue
    if ($regle) {
        $port = ($regle | Get-NetFirewallPortFilter).LocalPort
        Controle 'pare-feu : port de l''écran ouvert' ([string]$regle.Enabled -eq 'True' -and [string]$port -eq $env:GESTIONMPPRO_PORT) "port $port"
        Controle 'pare-feu : Domaine et Privé seulement' ([string]$regle.Profile -notmatch 'Public|Any') "$($regle.Profile)"
    } else {
        Controle 'pare-feu : règle présente' $false 'installer.ps1 sans -SansPareFeu (inutile derrière un relais HTTPS)'
    }
    $ecoute = @(Get-NetTCPConnection -LocalPort ([int]$env:GESTIONMPPRO_PORT) -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty LocalAddress -Unique)
    Controle "écoute sur $env:GESTIONMPPRO_ECOUTE" ($ecoute -contains $env:GESTIONMPPRO_ECOUTE) ($ecoute -join ', ')
    $ouverts = @('S-1-1-0', 'S-1-5-11', 'S-1-5-32-545')  # Tout le monde, Utilisateurs authentifiés, Utilisateurs
    $lecteurs = @((Get-Acl -LiteralPath $Script:FichierEnvironnement).Access | ForEach-Object {
            try { $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value } catch { '' } })
    Controle 'fichier environnement fermé aux autres comptes' (@($lecteurs | Where-Object { $ouverts -contains $_ }).Count -eq 0)
}

function Controler-Sauvegarde {
    # Une sauvegarde manuelle maintenant : écrite, relue, ses pièces, sa copie. Rend le fichier.
    $r = Poste @('sauvegarder', '--genre', 'manuelle')
    $fichier = [string]($r.Sortie | Select-Object -Last 1)
    Controle 'sauvegarde écrite et relue (pg_dump, pg_restore --list)' ($r.Code -eq 0 -and (Test-Path -LiteralPath $fichier)) $fichier
    if ($r.Code -ne 0) { return '' }
    Controle 'archive des pièces jointes à côté' (Test-Path -LiteralPath "$fichier.pieces.tar")
    $liste = @(Invoke-Natif { & (Join-Path $env:GESTIONMPPRO_PG_BIN 'pg_restore.exe') --list $fichier })
    $tables = @($liste | Where-Object { $_ -match ' TABLE DATA ' }).Count
    Controle 'relue ici aussi : tables présentes' ($LASTEXITCODE -eq 0 -and $tables -gt 0) "$tables tables"
    $copie = $env:GESTIONMPPRO_SAUVEGARDES_COPIE
    if ($copie) {
        $double = Join-Path $copie (Split-Path $fichier -Leaf)
        $memeTaille = (Test-Path -LiteralPath $double) -and ((Get-Item -LiteralPath $double).Length -eq (Get-Item -LiteralPath $fichier).Length)
        Controle 'copie sur l''autre disque, même taille' $memeTaille $double
    } else {
        Controle 'copie sur un autre disque réglée' $false 'GESTIONMPPRO_SAUVEGARDES_COPIE vide : indispensable (guide § 6)'
    }
    return $fichier
}

function Servir-Un-Instant([string]$Version, [string]$Adresse, [string]$Temp) {
    # Un second serveur sur la base d'essai (127.0.0.1:$PortEssai, sans tâches) : /api/sante.
    $gardes = @{}
    $essai = @{ GESTIONMPPRO_BASE = $Adresse; GESTIONMPPRO_PORT = "$PortEssai"; GESTIONMPPRO_ECOUTE = '127.0.0.1'
        GESTIONMPPRO_TACHES = '0'; GESTIONMPPRO_SAUVEGARDES = "$Temp\sauvegardes"; GESTIONMPPRO_PIECES = "$Temp\pieces"
        GESTIONMPPRO_JOURNAL_FICHIER = "$Temp\serveur.log"; GESTIONMPPRO_SAUVEGARDES_COPIE = '' }
    foreach ($k in $essai.Keys) { $gardes[$k] = [Environment]::GetEnvironmentVariable($k, 'Process'); [Environment]::SetEnvironmentVariable($k, $essai[$k], 'Process') }
    $env:PYTHONPATH = Join-Path (Dossier-De-Version $Version) 'backend'
    $p = $null
    try {
        $p = Start-Process -FilePath (Python-De $Version) -WorkingDirectory $env:PYTHONPATH -NoNewWindow -PassThru `
            -ArgumentList "-m uvicorn gestion_mp_pro.main:app --host 127.0.0.1 --port $PortEssai --no-access-log" `
            -RedirectStandardError "$Temp\demarrage.log" -RedirectStandardOutput "$Temp\sortie.log"
        $e = @{ Code = 0; Sante = $null }
        for ($i = 0; $i -lt 60 -and $e.Code -ne 200; $i++) { Start-Sleep -Seconds 1; $e = Etat-Http $PortEssai }
        $bon = $e.Code -eq 200 -and $e.Sante -and $e.Sante.schema -eq $e.Sante.schema_attendu
        Controle 'la base restaurée est servie (second serveur, /api/sante)' $bon "code $($e.Code)"
    } finally {
        if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
        foreach ($k in $gardes.Keys) { [Environment]::SetEnvironmentVariable($k, $gardes[$k], 'Process') }
    }
}

function Controler-Restauration([string]$Version, [string]$Fichier, $Parties) {
    # Restaure la sauvegarde sur gestion_mp_pro_recette_essai comme le fait l'application
    # (pg_restore -f, puis psql en une transaction), compare, sert, puis supprime la base.
    $essai = 'gestion_mp_pro_recette_essai'
    $temp = Join-Path $Script:Donnees "recette-$PID"
    New-Item -ItemType Directory -Force -Path $temp | Out-Null
    $admin = Lire-Secret 'Mot de passe de l''administrateur « postgres » de PostgreSQL (base d''essai)'
    $adresse = "postgresql+psycopg://$($Parties.Role):$($Parties.MotDePasse)@$($Parties.Hote):$($Parties.Port)/$essai"
    try {
        Avec-Mot-De-Passe $admin {
            Sql "DROP DATABASE IF EXISTS $essai WITH (FORCE)" | Out-Null
            Sql "CREATE DATABASE $essai OWNER $($Parties.Role) ENCODING 'UTF8' TEMPLATE template0" | Out-Null
            Sql "REVOKE CONNECT, TEMPORARY ON DATABASE $essai FROM PUBLIC" | Out-Null
        }
        $script = Join-Path $temp 'restauration.sql'
        Invoke-Natif { & (Join-Path $env:GESTIONMPPRO_PG_BIN 'pg_restore.exe') --no-owner --no-privileges -f $script $Fichier }
        Controle 'script de restauration écrit (pg_restore)' ($LASTEXITCODE -eq 0)
        Avec-Mot-De-Passe $Parties.MotDePasse {
            Invoke-Natif { & $Script:Psql -X -q -1 -v ON_ERROR_STOP=1 -h $Parties.Hote -p $Parties.Port -U $Parties.Role -d $essai `
                    -c 'DROP SCHEMA IF EXISTS public CASCADE' -c 'CREATE SCHEMA public' -f $script | Out-Null }
        }
        Controle 'restaurée en une transaction (psql -1, comme l''application)' ($LASTEXITCODE -eq 0)
        $comptes = Join-Path $temp 'comptes-production.json'
        Ecrire-Texte $comptes ([string]((Poste @('comptes')).Sortie | Select-Object -Last 1))
        $avant = $env:GESTIONMPPRO_BASE
        $env:GESTIONMPPRO_BASE = $adresse
        try { $r = Poste @('comparer-comptes', $comptes) } finally { $env:GESTIONMPPRO_BASE = $avant }
        foreach ($l in $r.Sortie) { Dire "       $l" }
        Controle 'mêmes lignes que la production, table par table' ($r.Code -eq 0) 'un écart pendant une saisie : relancer à un moment calme'
        Servir-Un-Instant $Version $adresse $temp
    } finally {
        Avec-Mot-De-Passe $admin {
            Sql "DROP DATABASE IF EXISTS $essai WITH (FORCE)" | Out-Null
            Controle 'base d''essai supprimée' ((Sql "SELECT count(*) FROM pg_database WHERE datname = '$essai'") -eq '0')
        }
        Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Exiger-Administrateur
$null = Lire-Environnement
$version = Exiger-Version
Garder-La-Base (Nom-De-Base $env:GESTIONMPPRO_BASE)
$parties = Parties-De-Base $env:GESTIONMPPRO_BASE
$Script:Psql = Join-Path $env:GESTIONMPPRO_PG_BIN 'psql.exe'
$Script:PortPg = [int]$parties.Port

Etape "1. Serveur (version $version)"
Controler-Serveur $version
$tri = Avec-Mot-De-Passe $parties.MotDePasse { Sql "SELECT 'a' < 'B', chr(233) > 'z', lower(chr(201)) = chr(233), upper(chr(231)) = chr(199)" $parties.Base $parties.Role }
Controle 'tri et majuscules comme sur le Mac (a<B, é<z, É→é, ç→Ç)' ($tri -eq 't|f|t|t') $tri

Etape '2. Sauvegarde'
$fichier = Controler-Sauvegarde

Etape '3. Restauration sur une base d''essai'
if ($SansRestauration) { Dire '  --   sautée (-SansRestauration)' }
elseif (-not $fichier) { Controle 'restauration' $false 'pas de sauvegarde à restaurer' }
else { Controler-Restauration $version $fichier $parties }

Etape 'Bilan'
Dire "$($Script:Bilan.Ok) contrôle(s) ok, $($Script:Bilan.Ko) KO. Les contrôles à la main : INSTALLATION-WINDOWS.md § 10."
if ($Script:Bilan.Ko -gt 0) { exit 1 }
exit 0
