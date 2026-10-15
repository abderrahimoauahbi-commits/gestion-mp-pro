# Gestion MP PRO — Installer sur un serveur Windows

Ce guide s'adresse au **technicien** qui installe Gestion MP PRO sur un serveur Windows, à l'usine
ou chez un hébergeur. Il suit l'ordre des gestes, avec les commandes exactes à taper. Le reste de
l'exploitation (sauvegardes, restauration, surveillance) est commun à tous les serveurs et décrit
dans [EXPLOITATION.md](EXPLOITATION.md) ; l'usage par rôle dans [NOTICE.md](NOTICE.md).

> **Où en est ce kit (15 octobre 2026).** Le serveur Python a été audité pour Windows et corrigé
> (docs/lots/WINDOWS-SERVEUR.md) ; les scripts du kit (`deploiement/windows`) sont écrits et
> vérifiés **sur le Mac** (encodage, syntaxe de PowerShell 5.1, réglages) — mais **aucun n'a encore
> tourné sur un vrai Windows**. La première installation se fait donc avec ce guide ouvert, en
> notant chaque écart ; la recette (§ 10) dit si tout est en ordre. La liste de ce qui n'a pas pu
> être éprouvé est au § 13.

---

## 1. Ce qu'il faut

| | |
|---|---|
| Système | **Windows Server 2019, 2022 ou 2025**, 64 bits, à jour (Windows Update). Windows 10/11 Pro convient pour un essai. |
| Machine | 4 Go de mémoire au moins (8 conseillés), 2 cœurs, 40 Go libres sur le disque système. |
| **Un second disque** | Pour la **copie des sauvegardes** (§ 6) : second disque interne, disque USB toujours branché (formaté NTFS), ou partage réseau. **Indispensable.** |
| Compte | Un compte **administrateur** de la machine (pour installer ; le serveur tourne ensuite sous un compte de service sans droits). |
| Réseau | Une adresse fixe dans le réseau de l'usine (ou un nom DNS), joignable par les postes et les téléphones (Wi-Fi). Serveur loué sur Internet : lire le § 8 **avant** d'ouvrir quoi que ce soit. |
| Internet | Pendant l'installation seulement (dépendances Python). Sans Internet : paquet fait avec `--avec-roues` (§ 3). |
| Logiciels | **PostgreSQL 16** et **Python 3.12** (64 bits), téléchargés par vous aux adresses officielles du § 2. PowerShell 5.1 est fourni par Windows. Rien d'autre : pas de Node, pas de Docker, pas d'outil tiers. |

Durée : une heure environ, transfert des données compris.

---

## 2. Les téléchargements officiels (à faire vous-même)

Ne prendre ces deux logiciels **que** sur leurs sites officiels, jamais sur un site de
téléchargement ni depuis une clé reçue :

1. **PostgreSQL 16** — <https://www.postgresql.org/download/windows/> → « Download the installer »
   (installateur d'EDB, celui que recommande PostgreSQL), **version 16.x, Windows x86-64**.
   À l'installation :
   - composants : **PostgreSQL Server** et **Command Line Tools** (pgAdmin facultatif ; Stack
     Builder inutile) ;
   - dossier : celui proposé (`C:\Program Files\PostgreSQL\16`) ;
   - **mot de passe du super-utilisateur `postgres`** : long, unique, **le noter** dans le coffre de
     l'usine — l'installation et la recette de Gestion MP PRO le demandent ;
   - port **5432** ; « Locale » : celle proposée (le tri suit la langue du serveur) ;
   - à la fin, vérifier dans `services.msc` que le service **postgresql-x64-16** est « En cours
     d'exécution » et en démarrage **Automatique**.
2. **Python 3.12** — <https://www.python.org/downloads/windows/> → la dernière **3.12.x**,
   « **Windows installer (64-bit)** ». À l'installation :
   - cocher « **Use admin privileges when installing py.exe** » ;
   - choisir **Customize installation**, puis cocher « **Install Python 3.12 for all users** »
     (il s'installe alors dans `C:\Program Files\Python312` : le compte du service doit pouvoir le
     lire ; une installation « pour moi seul » dans `C:\Users\…` est refusée par l'installeur) ;
   - « Add Python to environment variables » : facultatif.

Vérifier, dans un PowerShell :

```powershell
py -3.12 -c "import sys, struct; print(sys.version, struct.calcsize('P') * 8, sys.executable)"
#   3.12.x … 64 C:\Program Files\Python312\python.exe
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' --version
#   psql (PostgreSQL) 16.x
```

---

## 3. Installer Gestion MP PRO

### 3.1 Le paquet

Le paquet est fabriqué **sur le Mac** de l'usine, depuis le projet, par celui qui le tient à jour :

```bash
cd ~/gestion-mp-pro
scripts/paquet_windows.sh                   # ou : make paquet-windows
#   Paquet : ~/gestion-mp-pro-paquets/gestion-mp-pro-windows-<version>.zip (… Mo)
#   Empreinte : <64 caractères>
scripts/paquet_windows.sh --avec-roues      # serveur SANS Internet : dépendances Python incluses
```

Il contient le code du serveur, **l'écran déjà construit**, les dépendances figées pour Windows
(`requirements-windows.lock`) et le kit (`windows\*.ps1`). Il ne contient **ni base, ni
sauvegarde, ni mot de passe** (le script le vérifie avant d'écrire le zip).

Copier le `.zip` sur le serveur (clé USB, partage), puis vérifier qu'il est intact :

```powershell
Get-FileHash .\gestion-mp-pro-windows-<version>.zip -Algorithm SHA256
#   doit donner l'empreinte affichée sur le Mac (fichier .sha256 à côté du zip)
```

Clic droit sur le zip → **Propriétés** → cocher **Débloquer** → OK (sinon Windows refuse les
scripts venus d'ailleurs). Puis clic droit → **Extraire tout…** vers `C:\Installation\`.

### 3.2 L'installeur

Ouvrir **PowerShell en tant qu'administrateur** (menu Démarrer → clic droit sur « Windows
PowerShell » → « Exécuter en tant qu'administrateur »), puis :

```powershell
cd C:\Installation\gestion-mp-pro-windows-<version>
powershell -ExecutionPolicy Bypass -File .\windows\installer.ps1 -Copie 'E:\Sauvegardes Gestion MP PRO'
```

`-Copie` est le dossier de la **copie des sauvegardes sur l'autre disque** (§ 6). Autres options,
rarement utiles : `-Port 8050`, `-Python <python.exe>`, `-PostgreSQL <dossier bin>`,
`-PortPostgreSQL 5432`, `-Compte <compte>` (§ 6), `-Roues .\roues` (paquet sans Internet),
`-SansPareFeu`, `-SansDemarrageAutomatique`.

L'installeur pose **deux questions** :

1. le **mot de passe de `postgres`** (noté au § 2) — il ne sert que pendant l'installation ;
2. le **mot de passe du rôle `gestion_mp_pro`** : appuyer sur **Entrée** pour qu'il soit tiré au
   hasard (32 lettres et chiffres, conseillé). Il n'est **jamais affiché** : il est écrit dans le
   fichier `environnement` (§ 4), lisible des seuls administrateurs et du service.

Puis il fait, en le disant à chaque étape : prérequis vérifiés ; rôle et base `gestion_mp_pro`
créés (base en UTF-8, fermée aux autres rôles) ; version copiée dans `C:\Program Files\Gestion MP
PRO\versions\<version>` avec son propre Python ; dossiers de données créés et fermés ; schéma de la
base mis à jour ; sauvegarde « base vide de référence » ; **tâche planifiée** « Gestion MP PRO »
(au démarrage de Windows, compte SERVICE LOCAL, relancée en cas d'échec, sans limite de durée) ;
**pare-feu** ouvert sur le port 8050 pour les réseaux Domaine et Privé ; serveur démarré. Il se
termine par les adresses à ouvrir depuis un poste, par exemple `http://SRV-USINE:8050`.

L'installeur est **idempotent** : on peut le relancer (après une erreur corrigée, pour ajouter
`-Copie`…) ; il ne refait que ce qui manque et ne supprime jamais rien.

### 3.3 Le premier accès

Depuis un poste de l'usine, ouvrir l'adresse affichée : l'écran demande de créer le **compte de
la direction** (une seule fois). Ensuite : un compte par personne, avec son rôle (NOTICE.md).
Pour reprendre les données du Mac, **ne rien saisir** et passer directement au § 9.

---

## 4. Où sont les fichiers

| Quoi | Où |
|---|---|
| Le programme (une version par dossier, la précédente gardée pour le retour arrière) | `C:\Program Files\Gestion MP PRO\versions\<version>\` |
| La version en service / la précédente | `C:\Program Files\Gestion MP PRO\actuelle.txt`, `precedente.txt` |
| Les scripts (démarrer, arrêter…) | `C:\Program Files\Gestion MP PRO\outils\` |
| **Les réglages** (base et son mot de passe, écoute, dossiers, copie, courriel) | `C:\ProgramData\Gestion MP PRO\environnement` |
| **Les sauvegardes** | `C:\ProgramData\Gestion MP PRO\sauvegardes\gestion_mp_pro\` |
| Les pièces jointes | `C:\ProgramData\Gestion MP PRO\pieces\gestion_mp_pro\` |
| Les journaux | `C:\ProgramData\Gestion MP PRO\journaux\` : `serveur.log` (le journal du serveur, une ligne par requête, tournant à 10 Mo × 10), `lanceur.log` (démarrages, arrêts), `demarrage.log` (messages au démarrage) |
| La base | dans PostgreSQL (`C:\Program Files\PostgreSQL\16\data`), base `gestion_mp_pro` |
| La tâche planifiée | Planificateur de tâches → dossier « Gestion MP PRO » |

`C:\ProgramData` est un dossier caché : le taper dans la barre d'adresse de l'Explorateur.
`C:\ProgramData\Gestion MP PRO` n'est lisible que des administrateurs, de SYSTEM et du compte du
service (il contient le mot de passe de la base et les sauvegardes).

Le fichier `environnement` se modifie au Bloc-notes (en administrateur), une ligne
`GESTIONMPPRO_NOM=valeur` par réglage, sans guillemets ; après un changement : arrêter puis
démarrer (§ 5). Tous les réglages : ARCHITECTURE.md § 16 et EXPLOITATION.md § 4.

---

## 5. Les gestes courants

Toujours dans un PowerShell **administrateur** :

| Geste | Commande |
|---|---|
| Voir l'état | `& 'C:\Program Files\Gestion MP PRO\outils\etat.ps1'` |
| Démarrer | `& 'C:\Program Files\Gestion MP PRO\outils\demarrer.ps1'` |
| Arrêter | `& 'C:\Program Files\Gestion MP PRO\outils\arreter.ps1'` (repart au prochain démarrage de Windows ; `-Desactiver` : pas avant `demarrer.ps1`) |
| Sauvegarder maintenant | `& 'C:\Program Files\Gestion MP PRO\outils\sauvegarder.ps1'` |
| Restaurer (serveur arrêté) | `& 'C:\Program Files\Gestion MP PRO\outils\restaurer.ps1' -Fichier <nom>.dump` |
| Mettre à jour | § 7 |
| Recette | § 10 |

Si PowerShell refuse d'exécuter un script (« l'exécution de scripts est désactivée »), le lancer
ainsi : `powershell -ExecutionPolicy Bypass -File 'C:\Program Files\Gestion MP PRO\outils\etat.ps1'`.

Le serveur démarre **tout seul** avec Windows (30 secondes après, le temps que PostgreSQL soit
prêt) et repart seul s'il s'arrête sur une panne (10 secondes après). L'arrêt (`arreter.ps1`)
attend la fin d'une sauvegarde en cours. La base est mise au schéma de la version **au démarrage**
du serveur, comme sur le Mac.

---

## 6. Sauvegardes, et leur copie sur un autre disque

Les sauvegardes sont faites **par le serveur lui-même**, comme sur le Mac (EXPLOITATION.md § 7) :
chaque soir à **22 h de l'usine** la quotidienne, le dimanche l'hebdomadaire, le dernier jour du
mois la mensuelle ; chacune relue, avec ses pièces jointes (`.pieces.tar` à côté). Serveur arrêté
à 22 h : elle se fait à son prochain démarrage. Les sauvegardes manuelles (écran ou
`sauvegarder.ps1`) et « avant mise à jour » ne s'effacent jamais seules.

**La copie sur un autre disque est indispensable** : une sauvegarde sur le même disque que la base
ne protège ni d'une panne de disque, ni d'un rançongiciel, ni d'un vol. Le réglage
`GESTIONMPPRO_SAUVEGARDES_COPIE` (option `-Copie` de l'installeur) fait recopier **chaque**
sauvegarde dans ce dossier, taille vérifiée ; une copie qui échoue met le serveur en alerte
(bandeau rouge sur tous les postes) jusqu'à ce que le dossier revienne.

- **Second disque interne ou disque USB** (formaté **NTFS**, lettre fixe, toujours branché) :
  `-Copie 'E:\Sauvegardes Gestion MP PRO'`. L'installeur y donne l'écriture au compte du service.
- **Partage réseau** (NAS) : le compte SERVICE LOCAL ne peut pas écrire sur le réseau. Créer un
  compte dédié (local ou du domaine) qui a l'écriture sur le partage et le droit « Ouvrir une
  session en tant que tâche » (`secpol.msc` › Stratégies locales › Attribution des droits
  utilisateur), puis : `installer.ps1 -Compte 'USINE\gestionmppro' -Copie '\\nas\sauvegardes\gestion-mp-pro'`
  (le mot de passe du compte est demandé et gardé par Windows).
- **Hors de l'usine** : une fois par semaine, copier le dossier de la copie sur une clé ou un
  disque **rangé ailleurs** (incendie, vol). Un serveur loué : la copie va sur un second disque
  ou un stockage d'une autre région, et une copie régulière revient à l'usine.

Vérifier : `etat.ps1` affiche la dernière sauvegarde, son âge et les trois derniers fichiers du
dossier **et** de la copie. Une fois par mois, rejouer la recette (§ 10) : elle restaure la
dernière sauvegarde sur une base d'essai.

---

## 7. Mettre à jour

1. Sur le Mac : `scripts/paquet_windows.sh` (§ 3.1). Copier le zip sur le serveur, vérifier
   l'empreinte, le **débloquer** (Propriétés).
2. Sur le serveur, PowerShell administrateur, **à un moment calme** (2 à 5 minutes d'arrêt) :

   ```powershell
   & 'C:\Program Files\Gestion MP PRO\outils\mettre-a-jour.ps1' -Paquet 'C:\Installation\gestion-mp-pro-windows-<version>.zip'
   ```

Le script prépare la nouvelle version pendant que l'ancienne sert encore, **arrête** le serveur,
fait la sauvegarde **« avant mise à jour »** (relue), met la nouvelle version en service et la
démarre (elle met la base à son schéma), puis attend que `/api/sante` réponde avec la nouvelle
version et le schéma attendu. **Si elle ne répond pas en 3 minutes, il revient seul en arrière** :
ancienne version remise et, si la base avait déjà été migrée, sauvegarde « avant mise à jour »
restaurée (personne n'a pu écrire entre-temps : le serveur ne répondait pas).

Retour arrière décidé plus tard (un défaut vu le lendemain) :

```powershell
& 'C:\Program Files\Gestion MP PRO\outils\mettre-a-jour.ps1' -RetourArriere
```

Si le schéma de la base a changé avec la nouvelle version, il faut restaurer la sauvegarde
« avant mise à jour » : le script le dit et demande de taper **RESTAURER** ; ce qui a été saisi
depuis la mise à jour est alors perdu (il reste dans la sauvegarde « avant restauration »).

---

## 8. Accès des postes et des téléphones ; HTTPS ; serveur loué

### 8.1 Dans le réseau de l'usine

Les postes et les téléphones (Wi-Fi de l'usine) ouvrent **`http://<serveur>:8050`** — `<serveur>`
étant le nom de la machine (`SRV-USINE`) ou son adresse (`192.168.1.20`), affichés à la fin de
l'installation. Le pare-feu de Windows laisse passer le port 8050 pour les réseaux **Domaine** et
**Privé** seulement. Si l'installeur prévient que le réseau est classé « Public », le classer
« Privé » (commande donnée par l'installeur) — sinon les postes ne joignent pas le serveur.

**HTTPS** est nécessaire pour l'**appareil photo** des téléphones (lecture des QR de lot) et pour
installer PRO comme une application (EXPLOITATION.md § 12) ; sans lui, tout le reste fonctionne,
et l'écran Administration › Serveur signale l'écoute sans HTTPS en rouge. Pour l'avoir dans
l'usine : un relais HTTPS sur le serveur, comme au § 8.2 mais avec un nom interne
(`gestion-mp-pro.usine.lan`) et `tls internal` dans le Caddyfile, dont l'autorité est à installer
une fois sur chaque téléphone (EXPLOITATION.md § 3.1, même principe).

Avant d'enrôler les téléphones (Administration › Appareils), poser l'adresse qu'ils utiliseront
dans le fichier `environnement` : `GESTIONMPPRO_ADRESSE=http://SRV-USINE:8050` (ou l'adresse
HTTPS), puis arrêter et démarrer.

### 8.2 Serveur loué sur Internet : HTTPS et accès restreint, obligatoirement

Sur Internet, **jamais** le port 8050 ouvert, **jamais** de HTTP : les mots de passe et les codes
des téléphones passeraient en clair, et tout Internet viendrait essayer les comptes. Deux façons,
la première étant la plus sûre :

1. **Un réseau privé (VPN)** entre l'usine et le serveur : WireGuard ou Tailscale (sites officiels).
   Le serveur n'expose rien sur Internet ; les postes et les téléphones joignent son adresse
   privée. Garder alors l'installation telle quelle (8050, pare-feu Domaine/Privé) et ajouter
   HTTPS comme au § 8.1 pour l'appareil photo.
2. **Un relais HTTPS** sur le serveur (Caddy, téléchargé par vous sur <https://caddyserver.com>,
   « caddy_windows_amd64 »), avec un **nom public** et l'accès **restreint à l'adresse fixe de
   l'usine** :
   - dans `environnement` : `GESTIONMPPRO_ECOUTE=127.0.0.1`, `GESTIONMPPRO_HTTPS=1`,
     `GESTIONMPPRO_ADRESSE=https://gestion-mp-pro.exemple.ma` ; puis arrêter et démarrer ;
   - `C:\Caddy\Caddyfile` (certificat public obtenu seul par Caddy ; la CSP reste celle de
     l'application) :

     ```
     gestion-mp-pro.exemple.ma {
         @dehors not remote_ip 196.200.10.20
         respond @dehors 403
         reverse_proxy 127.0.0.1:8050
     }
     ```

     (`196.200.10.20` : l'adresse fixe de l'usine, à demander au fournisseur d'accès ;
     plusieurs adresses séparées par des espaces) ;
   - Caddy en service Windows (documentation de Caddy, « Windows service ») :
     `sc.exe create caddy start= auto binPath= "C:\Caddy\caddy.exe run --config C:\Caddy\Caddyfile"`
     puis `sc.exe start caddy` ;
   - pare-feu : ouvrir **443** (et 80, pour le certificat) ; retirer la règle du 8050
     (`Remove-NetFirewallRule -Name GestionMPPRO-Ecran`) ; chez l'hébergeur, n'autoriser que
     443/80 (et le bureau à distance **seulement** depuis l'adresse de l'usine).

Dans les deux cas : Windows Update automatique, bureau à distance jamais ouvert à tout Internet,
mots de passe longs, et la copie des sauvegardes hors de ce serveur (§ 6).

---

## 9. Transférer les données depuis le Mac

Gestion MP PRO tourne aujourd'hui sur le Mac de l'usine. Le passage au serveur se fait **en une
fois**, à un moment où personne ne saisit (une demi-heure) : sauvegarde du Mac → copie →
restauration sur le serveur → contrôle des comptes de lignes et de `/api/sante`.

Le serveur doit porter **la même version que le Mac, ou plus récente** (une sauvegarde d'une
version plus récente est refusée). Le plus simple : fabriquer le paquet du serveur depuis le même
commit que la copie en service sur le Mac
(`cat ~/Library/Application\ Support/Gestion\ MP\ PRO/version/VERSION`).

**Sur le Mac** (Terminal) :

```bash
cd ~/gestion-mp-pro
scripts/arreter.sh                                   # plus rien ne change sur le Mac
scripts/sauvegarder.sh                               # affiche le chemin du .dump (relu)
scripts/compter.sh > ~/Desktop/comptes-mac.json      # lignes de chaque table, révision du schéma
ls -l ~/gestion-mp-pro-sauvegardes/gestion_mp_pro/ | tail -3
```

Copier sur une clé USB : le fichier `gestion-mp-pro-…-manuelle.dump`, **son**
`gestion-mp-pro-…-manuelle.dump.pieces.tar` (les pièces jointes), et `comptes-mac.json`.

**Sur le serveur** (PowerShell administrateur ; serveur installé, aucun compte encore créé) :

```powershell
& 'C:\Program Files\Gestion MP PRO\outils\arreter.ps1'
& 'C:\Program Files\Gestion MP PRO\outils\restaurer.ps1' -Fichier 'E:\gestion-mp-pro-<…>-manuelle.dump' -Comptes 'E:\comptes-mac.json'
#   Pour confirmer, tapez RESTAURER : RESTAURER
#   Sauvegarde « avant restauration » : …
#   Base gestion_mp_pro restaurée depuis gestion-mp-pro-<…>-manuelle.dump.
#   Remarque — sauvegarde : 44 là-bas, 2 ici        (registre des sauvegardes : propre à chaque serveur)
#   Remarque — session : 4 là-bas, 0 ici           (sessions fermées par la restauration)
#   Mêmes lignes dans les 69 tables métier (… lignes en tout).
& 'C:\Program Files\Gestion MP PRO\outils\demarrer.ps1'
& 'C:\Program Files\Gestion MP PRO\outils\etat.ps1'
```

Le script copie d'abord la sauvegarde et ses pièces dans le dossier des sauvegardes du serveur,
restaure (tout ou rien), puis compare la base **table par table** aux comptes du Mac. Les tables
d'exploitation (journal, sessions, registre des sauvegardes, état des tâches) diffèrent forcément
et sont seulement signalées ; **toute autre différence est un « ÉCART »** : le transfert n'est pas
fidèle, ne pas ouvrir le serveur, recommencer (et garder les messages).

Ensuite : `etat.ps1` doit montrer `/api/sante` en état « ok », la version du paquet et le schéma
attendu. Se connecter depuis un poste avec un compte du Mac (les comptes, mots de passe et codes
reviennent avec la base), ouvrir le stock et une réception récente, comparer deux ou trois
chiffres avec le Mac. Puis **arrêter Gestion MP PRO sur le Mac pour de bon**, pour que personne
n'y saisisse plus : `deploiement/mac/installer_demarrage_automatique.sh --retirer` s'il démarre
seul, et retirer le raccourci « Gestion MP PRO » du bureau. Gestion MP (l'ancien, port 8030) n'est
pas concerné. Enfin, réenrôler les téléphones sur la nouvelle adresse (§ 8.1).

*Répétition faite sur le Mac le 15 octobre 2026* (même procédure, base « 3 ans » de l'épreuve de
charge) : 171 245 lignes, 38 266 mouvements ; restauration sur une base neuve en 1,8 s ;
« Mêmes lignes dans les 69 tables métier » (docs/lots/WINDOWS-SERVEUR.md).

---

## 10. Recette sur le serveur

### 10.1 Les contrôles automatiques

Serveur en marche, à un moment calme, PowerShell administrateur :

```powershell
& 'C:\Program Files\Gestion MP PRO\outils\recette.ps1'
```

Le mot de passe de `postgres` est demandé (pour la base d'essai). La recette contrôle, et affiche
« ok » ou « KO » pour chacun :

- `/api/sante` répond 200, avec la version en service, le schéma attendu, l'état « ok » ;
- la tâche planifiée : présente, active, au démarrage de Windows, sans limite de durée, relancée
  en cas d'échec, sans droits élevés ; la règle du pare-feu (port, Domaine et Privé seulement) ;
  l'écoute ; le fichier `environnement` fermé aux autres comptes ;
- le tri et les majuscules de la base comme sur le Mac (`a` avant `B`, `é` avant `z`, É → é) ;
- une sauvegarde **maintenant** : écrite, relue, ses pièces jointes, **sa copie sur l'autre
  disque** (même taille) ;
- cette sauvegarde **restaurée** sur une base d'essai à part, **`gestion_mp_pro_recette_essai`**,
  exactement comme l'application restaure (script SQL, une seule transaction) ; ses lignes
  comparées à la production, table par table ; la base d'essai **servie** un instant par un
  second serveur (port 8059, local) dont `/api/sante` doit répondre ; puis la base d'essai
  **supprimée**.

La production n'est que lue (et reçoit une sauvegarde manuelle de plus). Code de sortie 0 si
tout est ok. `-SansRestauration` saute la base d'essai.

### 10.2 Les contrôles à la main (à cocher)

- [ ] `recette.ps1` : 0 KO.
- [ ] Redémarrer Windows (Démarrer › Redémarrer) : sans se connecter, attendre 2 minutes, puis
      depuis un poste l'écran s'ouvre (le serveur démarre seul, sous le compte du service).
- [ ] Depuis un **poste** de l'usine : `http://<serveur>:8050` s'ouvre ; connexion d'un compte
      de la direction ; tableau de bord, stock, une réception, un export Excel, un document à
      imprimer (bouton « Imprimer »).
- [ ] Depuis un **téléphone** en Wi-Fi : l'écran s'ouvre ; un téléphone enrôlé se connecte par
      son code à 4 chiffres ; une alimentation de machine se saisit. Avec HTTPS (§ 8) : l'appareil
      photo lit un QR de lot.
- [ ] Le **lendemain** après 22 h : `etat.ps1` montre une sauvegarde de moins de 24 h, faite par
      le serveur (nom en `-quotidienne.dump`), et **sa copie** dans le dossier de l'autre disque.
- [ ] Débrancher le disque de la copie (ou couper le partage) et lancer `sauvegarder.ps1` : elle
      est **refusée** (copie impossible) ; rebrancher, relancer : elle passe.
- [ ] `arreter.ps1` puis `demarrer.ps1` : l'écran revient ; `lanceur.log` note l'arrêt et le
      démarrage.
- [ ] Transfert depuis le Mac (§ 9) : « Mêmes lignes dans les … tables métier », et deux ou trois
      chiffres comparés à l'écran.
- [ ] Serveur loué : depuis un réseau **hors de l'usine** (téléphone en 4G), l'adresse est
      refusée (403) ou injoignable ; `http://…:8050` injoignable depuis Internet.
- [ ] Le mot de passe de `postgres` et l'emplacement de la copie des sauvegardes sont notés dans le
      coffre de l'usine.

---

## 11. Dépannage

| Ce qu'on voit | Quoi faire |
|---|---|
| « l'exécution de scripts est désactivée sur ce système » | `powershell -ExecutionPolicy Bypass -File <script>` ; et débloquer le zip (Propriétés › Débloquer) avant de l'extraire. |
| L'installeur ne trouve pas Python | Python 3.12 **64 bits**, installé « for all users » (§ 2), ou `-Python 'C:\…\python.exe'`. |
| « PostgreSQL a refusé la requête » à l'installation | Mot de passe de `postgres` erroné ; ou service arrêté (`services.msc`). |
| « dépendances impossibles à installer » | Pas d'accès à Internet (proxy ?) : refaire le paquet avec `--avec-roues` et passer `-Roues <paquet>\roues`. |
| L'écran ne s'ouvre pas depuis un poste, mais `etat.ps1` est « ok » | Réseau classé « Public » (§ 8.1) ; pare-feu d'un autre logiciel ; mauvaise adresse. Essayer sur le serveur : `http://127.0.0.1:8050`. |
| Le serveur ne démarre pas | `C:\ProgramData\Gestion MP PRO\journaux\demarrage.log` (message d'uvicorn ou de Python), `lanceur.log`, puis `serveur.log`. Le port 8050 pris par un autre programme : `Get-NetTCPConnection -LocalPort 8050`. |
| Sauvegarde en échec « WinError 32 » (fichier utilisé par un autre processus) | Un antivirus ou une copie en cours tient le fichier : exclure `C:\ProgramData\Gestion MP PRO\sauvegardes` de l'analyse en temps réel (Windows Defender › Exclusions), puis relancer `sauvegarder.ps1`. |
| `/api/sante` en « degrade », alerte de sauvegarde | Voir le message ; souvent la copie (disque débranché, droits du compte du service). |

---

## 12. Désinstaller

```powershell
& 'C:\Program Files\Gestion MP PRO\outils\desinstaller.ps1'
```

Retire le programme, la tâche planifiée et la règle du pare-feu ; **garde** la base, les
sauvegardes, les pièces jointes, les journaux et les réglages (`installer.ps1` remet tout en
service sur eux). Pour aller plus loin, deux options, chacune avec une phrase à **taper** :
`-SupprimerLaBase` (une dernière sauvegarde est faite d'abord ; « SUPPRIMER LA BASE ») et
`-SupprimerLesDonnees` (« SUPPRIMER LES DONNEES »). Le dossier de la copie sur l'autre disque
n'est jamais touché. PostgreSQL et Python se désinstallent à part (Paramètres › Applications).

---

## 13. Ce qui n'a pas encore été éprouvé sur un vrai Windows

Écrit et vérifié sur le Mac seulement (aucun Windows ni PowerShell disponible le 15 octobre
2026) ; à constater à la première installation, en notant les écarts dans
docs/lots/WINDOWS-SERVEUR.md :

- les scripts PowerShell eux-mêmes (syntaxe vérifiée par un lecteur maison, pas par PowerShell) ;
- la tâche planifiée sous SERVICE LOCAL : démarrage au boot, relance, arrêt du processus du
  serveur par `arreter.ps1` (Windows n'a pas d'arrêt « doux » pour lui : PostgreSQL annule toute
  transaction en cours) ;
- les droits (`icacls`) sur `ProgramData` et la copie ; le dossier temporaire du service (fichier
  de mot de passe de `pg_dump`) ;
- le journal tournant (`serveur.log`) quand un antivirus ou un lecteur le tient ouvert ;
- l'effacement des vieilles sauvegardes (rotation) quand un fichier est ouvert ailleurs ;
- l'installation des dépendances depuis `requirements-windows.lock` (les roues Windows 64 bits
  existent pour chaque dépendance : prouvé par `uv`, pas installé) ;
- le tri de la base selon la langue du serveur (contrôlé par la recette) ;
- Caddy en service Windows (§ 8.2).
