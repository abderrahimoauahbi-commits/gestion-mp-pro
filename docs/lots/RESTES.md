# Restes à reprendre (tenu par le coordinateur)

Points relevés par un lot pour un autre, à traiter avant la recette finale.

| Origine | Pour | Point |
|---|---|---|
| E2 | S2 | Désactiver un compte ferme ses sessions : la requête suivante reçoit « Connectez-vous pour continuer. » et l'écran dit « Votre session a expiré ». Rendre `compte_inactif` (« Ce compte n'est plus actif. », H-09) en gardant la raison de fermeture des sessions. |
| E2 | S2 | Les `lien` des notifications et de la recherche globale doivent être des adresses d'écran déclarées dans `frontend/src/routes.ts`. |
| E2 | D4 | Déclarer `contexte.COMPTEURS["a_approuver"]` et `["receptions_brouillon"]` (pastilles Commandes et Réceptions). |
| E2 | D8 | Déclarer `alerte_rouge` et `anomalies` dans les compteurs du contexte. |
| E2 | D10 | `alerte_serveur` est une phrase affichée telle quelle en rouge pour D et T. |
| E2 | S0 | Cible `make notice` (un essai vitest vérifie déjà que docs/NOTICE.md est à jour). |
| S2 | docs | Reporter dans API-PRO les champs ajoutés par S2 (Connexion.compte, Visage.role_libelle, Moi.vu_le/version, UtilisateurModification.code, ValeursJournal, Contexte.compteurs/base_essai/roles_au_metre, Acces.adresse_qr) ; ARCHITECTURE : `securite/` est un paquet. |
