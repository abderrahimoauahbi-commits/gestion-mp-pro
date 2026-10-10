# Gestion MP PRO — rapport de livraison

*Pour Mohamed. 10 octobre 2026.*

Gestion MP PRO est la version **professionnelle** de Gestion MP : même métier, **mêmes chiffres**
(c'est prouvé), mais une structure, une sécurité et une vérification au niveau d'un logiciel de
service. Gestion MP continue de tourner à côté, sans rien partager, le temps que vous décidiez de
basculer.

## Ce qui est livré

- **Tout le métier de Gestion MP** : catalogue et classification, fournisseurs, qualités et
  recettes, métiers ; plan d'achat, commandes avec approbation, bon fournisseur A4 anglais sans
  prix ; réceptions, quarantaine, réclamations ; importations et coût de revient ; stock en kilos
  (magasin, quarantaine, **sur les métiers**), alimentation des machines **au téléphone** ;
  valorisation (CMUP), inventaire, pilotage (cockpit, matrice des prix, opportunités, 38
  contrôles, bilan).
- **Quatre rôles** : direction, achats, alimentation (aucun prix nulle part), et un
  **administrateur technique** (aucune donnée métier).
- **La sécurité** : chaque action vérifiée côté serveur, prix invisibles à l'atelier, sessions,
  sauvegardes relues et restauration réversible.
- **Les outils** pour comparer les deux versions quand vous voulez, et pour reprendre vos vraies
  données le jour de la bascule.

## Les chiffres de la vérification (tout rejouable)

| Épreuve | Résultat |
|---|---|
| Essais automatiques | **2 871** côté serveur (2 866 verts, 5 sur outils externes) + **822** côté écran, tous verts |
| Parité avec Gestion MP (année d'essai, 19 dates) | **à corriger : 0** ; 188 579 écarts, tous expliqués |
| Vérification indépendante des chiffres (3 bases, 13 dates) | **0 écart** sur 65 762 + 161 046 + 161 964 contrôles |
| Scénario d'un mois d'usine, de bout en bout | **25 étapes sur 25**, 661 valeurs, **0 écart** |
| Recette au navigateur (4 rôles, écrans, téléphone) | **552 écrans, 0 anomalie**, 0 prix chez l'atelier |
| Charge au volume réel du service | tous les écrans sous 0,3 s ; 20 postes ensemble sous 0,7 s |
| Robustesse (saisies malformées sur 115 routes) | **5 775 essais, 0 erreur de serveur (500)** |

Détail complet dans [`RECETTE.md`](RECETTE.md) ; comparaison chiffrée dans
[`COMPARAISON-GESTION-MP.md`](COMPARAISON-GESTION-MP.md).

## Lancer PRO et comparer les deux versions

- **Ouvrir PRO** : le raccourci « Gestion MP PRO » sur le bureau (port 8050). Gestion MP garde son
  raccourci (port 8030). Les deux cohabitent sans se gêner.
- **Rafraîchir le miroir** (recopier Gestion MP dans PRO pour comparer sur les mêmes données) :
  dans PRO, *Administration › Reprise › « Rafraîchir le miroir… »*, ou `make miroir`.
- **Comparer chiffre par chiffre** : `make comparer` (ou l'outil `comparer_avec_gestion_mp.py`).
  Il lit les deux logiciels, compare, et dit « à corriger : 0 » quand tout concorde.

## Les neuf questions qui vous reviennent

PRO n'a rien changé en silence : là où Gestion MP n'avait pas tranché, il garde son comportement
et le signale. À décider à votre rythme (recommandation « pratique d'usine » en face, détail dans
[`RECETTE.md § 7`](RECETTE.md)) :

1. **Prix de la bande et du cuir** : au kilo ou au mètre ? (probablement au mètre — à voir sur une
   facture SOFIA)
2. **Franges** : créer la matière (avec sa densité) ou mettre le poids à 0 ?
3. **Importations** : valoriser à la pesée × prix (gardé) ou à la facture ?
4. **TPI 0,25 %** dans la TVA attendue : à confirmer avec le transitaire.
5. **Sortie oubliée** à cheval sur une fin de mois : laisser la direction la dater à la vraie date.
6. **Données de reprise signalées** : approuver la correction de deux couleurs mal orthographiées,
   fusionner les deux comptes « Mohamed ».
7. **Consommation et fil monté** : garder le fil monté comme du stock (décidé), le montrer à part
   dans le bilan.
8. **« Les numéros suivent les dates »** : garder la numérotation dans l'ordre de validation.
9. **Mise en service** : fournir les codes douaniers, une adresse d'envoi de courriel, et le
   compte Tailscale pour la 4G/5G.

À confirmer aussi, sans que cela bloque : les 4 réceptions payées en deux devises (garder ou
scinder), ce que l'administrateur technique voit du journal, et les conventions de recherche des
grandes listes.

## Ce qui reste, honnêtement

- **Mise en service réelle** : vider l'année d'essai et reprendre la production définitive se font
  le jour de la bascule par l'informaticien ; d'ici là, PRO n'est qu'un miroir de Gestion MP.
- **Serveur Linux / Docker** : les fichiers sont prêts et contrôlés, mais l'image Docker et le
  serveur Linux (HTTPS pour les téléphones) **restent à construire et à essayer sur une machine
  Linux** (pas possible sur ce Mac).
- **Très gros volumes (plusieurs années en ligne)** : les grandes listes et l'export des
  mouvements ont été rendus économes (pagination, export en flux) ; un détail d'ancien écran a été
  retiré au passage — le menu déroulant « État de livraison » des commandes (remplacé par le
  filtre « En retard seulement » et les onglets). Au volume d'une à deux années, rien ne gêne.
- La **restauration d'une vraie base de production** n'a été essayée que sur des bases d'essai ;
  un essai réel est à refaire chaque mois (c'est dans la liste d'exploitation).

## Pour aller plus loin

- Ce que fait le logiciel, par domaine et par rôle : [`CAHIER-DES-CHARGES.md`](CAHIER-DES-CHARGES.md).
- Installation, sauvegardes, serveur : [`EXPLOITATION.md`](EXPLOITATION.md).
- Comment c'est fait : [`ARCHITECTURE.md`](ARCHITECTURE.md).

*Travail fini, vérifié, rejouable. Les quelques points ouverts ci-dessus sont des décisions, pas
des travaux en retard.*
