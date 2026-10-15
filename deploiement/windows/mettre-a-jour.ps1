#Requires -Version 5.1
<#
Gestion MP PRO — passe le serveur à une nouvelle version (un paquet fait sur le Mac par
scripts/paquet_windows.sh), avec retour arrière. À lancer en administrateur :

  & 'C:\Program Files\Gestion MP PRO\outils\mettre-a-jour.ps1' -Paquet 'C:\Users\…\gestion-mp-pro-windows-abc1234.zip'
  & 'C:\Program Files\Gestion MP PRO\outils\mettre-a-jour.ps1' -RetourArriere

Dans l'ordre (comme scripts/demarrer.sh sur le Mac) :
  1. la nouvelle version est préparée à côté (code, écran, environnement Python) pendant que
     l'ancienne sert encore ;
  2. le serveur est arrêté, puis la base sauvegardée (« avant mise à jour », relue) : rien ne
     peut plus changer entre cette sauvegarde et le passage ;
  3. la nouvelle version est mise en service et démarrée ; elle met la base à son schéma au
     démarrage (migrations, sous verrou) ;
  4. contrôle : /api/sante répond 200 avec la nouvelle version et le schéma attendu (3 min) ;
  5. sinon, retour arrière automatique : l'ancienne version revient et, si la base a déjà été
     migrée, la sauvegarde « avant mise à jour » est restaurée (personne n'a pu écrire : le
     serveur ne répondait pas).

-RetourArriere, plus tard (un défaut vu le lendemain) : l'ancienne version revient ; si son
schéma diffère, la dernière sauvegarde « avant mise à jour » est restaurée après confirmation
tapée — ce qui a été saisi depuis la mise à jour est perdu (il reste dans la sauvegarde
« avant restauration » faite au passage).
#>
param(
    [string]$Paquet = '',
    [string]$Roues = '',
    [switch]$RetourArriere
)
. "$PSScriptRoot\commun.ps1"

function Derniere-Avant-Mise-A-Jour {
    $d = Join-Path $env:GESTIONMPPRO_SAUVEGARDES (Nom-De-Base $env:GESTIONMPPRO_BASE)
    $f = Get-ChildItem -LiteralPath $d -Filter 'gestion-mp-pro-*-avant-mise-a-jour.dump' -File |
        Sort-Object Name -Descending | Select-Object -First 1
    if ($f) { return $f.Name }
    return ''
}

function Schema-Connu([string]$Version) {
    # La base est-elle à la révision qu'attend cette version ? (poste.py etat, code de la version)
    $r = Poste -Arguments @('etat') -Version $Version
    if ($r.Code -ne 0) { return $false }
    $etat = $r.Sortie | Select-Object -Last 1 | ConvertFrom-Json
    return ($etat.revision -eq $etat.attendue)
}

function Revenir([string]$Ancienne, [string]$Fautive, [string]$Sauvegarde, [string]$Confirmation) {
    # Remet l'ancienne version en service ; restaure la sauvegarde si son schéma n'est plus là.
    Arreter-Serveur
    Ecrire-Texte $Script:FichierActuelle "$Ancienne`r`n"
    Ecrire-Texte $Script:FichierPrecedente "$Fautive`r`n"
    Mettre-Outils-En-Place $Ancienne
    if (-not (Schema-Connu $Ancienne)) {
        if (-not $Sauvegarde) { Echouer "le schéma de la base n'est plus celui de $Ancienne et aucune sauvegarde « avant mise à jour » n'existe : appeler l'assistance." }
        Dire "La base a été migrée par $Fautive : restauration de $Sauvegarde…"
        $code = Lancer-Poste -Version $Ancienne -Arguments @('restaurer', $Sauvegarde, '--confirmation',
            $Confirmation, '--motif', "retour arrière de la mise à jour $Fautive vers $Ancienne")
        if ($code -ne 0) { Echouer "restauration de $Sauvegarde impossible (voir ci-dessus) : la version $Ancienne est en place, serveur arrêté." }
    }
    Start-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache
    $e = Attendre-Sante $Ancienne 180
    if ($e.Code -ne 200) { Echouer "la version $Ancienne ne répond pas non plus : voir $($Script:Journaux)." }
    Dire "Retour arrière fait : la version $Ancienne est en service."
}

Exiger-Administrateur
$null = Lire-Environnement
Garder-La-Base (Nom-De-Base $env:GESTIONMPPRO_BASE)
$actuelle = Exiger-Version

if ($RetourArriere) {
    $precedente = ''
    if (Test-Path -LiteralPath $Script:FichierPrecedente) { $precedente = (Get-Content -LiteralPath $Script:FichierPrecedente -Encoding UTF8 | Select-Object -First 1).Trim() }
    if (-not $precedente -or -not (Test-Path -LiteralPath (Python-De $precedente))) { Echouer 'aucune version précédente gardée.' }
    $sauvegarde = Derniere-Avant-Mise-A-Jour
    $confirmation = 'RESTAURER'
    if (-not (Schema-Connu $precedente)) {
        Dire "Le schéma de la base a changé avec $actuelle : revenir à $precedente restaure $sauvegarde."
        Dire 'Ce qui a été saisi depuis la mise à jour sera perdu (gardé dans la sauvegarde « avant restauration »).'
        $confirmation = Read-Host 'Pour confirmer, tapez RESTAURER'
        if ($confirmation -ne 'RESTAURER') { Echouer 'non confirmé : rien n''est changé.' }
    }
    Revenir $precedente $actuelle $sauvegarde $confirmation
    exit 0
}

if (-not $Paquet) { Echouer 'quel paquet ? (-Paquet chemin\gestion-mp-pro-windows-<version>.zip)' }
$racine = Trouver-Paquet $Paquet
$nouvelle = (Get-Content -LiteralPath (Join-Path $racine 'VERSION') -Encoding UTF8 | Select-Object -First 1).Trim()
if ($nouvelle -eq $actuelle) { Dire "La version $nouvelle est déjà en service : rien n'est fait."; exit 0 }

Etape "1. Préparation de la version $nouvelle (l'ancienne $actuelle sert encore)"
$py = (Get-Content -LiteralPath (Join-Path (Join-Path (Dossier-De-Version $actuelle) 'venv') 'pyvenv.cfg') |
    Where-Object { $_ -match '^executable\s*=' } | Select-Object -First 1) -replace '^executable\s*=\s*', ''
if (-not $py -or -not (Test-Path -LiteralPath $py)) { Echouer 'Python de base introuvable (pyvenv.cfg) : relancer installer.ps1 avec -Python.' }
$nouvelle = Installer-Version $racine $py.Trim() $Roues

Etape '2. Arrêt et sauvegarde « avant mise à jour »'
Arreter-Serveur
$sortie = Poste -Arguments @('sauvegarder', '--genre', 'avant-mise-a-jour') -Version $actuelle
foreach ($l in $sortie.Sortie) { Dire $l }
if ($sortie.Code -ne 0) {
    Start-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache
    Echouer "sauvegarde « avant mise à jour » impossible : la version $actuelle reste en service (redémarrée)."
}
$sauvegarde = Split-Path ([string]($sortie.Sortie | Select-Object -Last 1)) -Leaf

Etape "3. Mise en service de $nouvelle"
Ecrire-Texte $Script:FichierPrecedente "$actuelle`r`n"
Ecrire-Texte $Script:FichierActuelle "$nouvelle`r`n"
Mettre-Outils-En-Place $nouvelle
Start-ScheduledTask -TaskName $Script:NomTache -TaskPath $Script:CheminTache

Etape '4. Contrôle'
$e = Attendre-Sante $nouvelle 180
if ($e.Code -eq 200) {
    Dire "Gestion MP PRO $nouvelle en service (/api/sante : $($e.Sante.etat), schéma $($e.Sante.schema))."
    # Ne sont gardées que la version en service et la précédente (retour arrière).
    foreach ($d in @(Get-ChildItem -LiteralPath $Script:Versions -Directory)) {
        if ($d.Name -ne $nouvelle -and $d.Name -ne $actuelle) { Remove-Item -LiteralPath $d.FullName -Recurse -Force -ErrorAction SilentlyContinue }
    }
    exit 0
}

Etape "5. Retour arrière vers $actuelle (la version $nouvelle ne répond pas : code $($e.Code))"
Revenir $actuelle $nouvelle $sauvegarde 'RESTAURER'
Echouer "mise à jour vers $nouvelle échouée, version $actuelle remise : voir $($Script:Journaux)\demarrage.log.1 et lanceur.log."
