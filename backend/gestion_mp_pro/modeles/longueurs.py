"""Longueurs des textes, une seule fois pour le modèle et les schémas (MODELE-DONNEES § 1.1).

Les schémas Pydantic des domaines lisent ces constantes (`Field(max_length=longueurs.NOM)`) :
une saisie acceptée par l'API tient toujours dans sa colonne (incohérence 21 de Gestion MP).
Une constante par **sens** de texte ; une colonne qui a sa propre longueur a sa constante.
"""

from __future__ import annotations

# --- Personnes, comptes, appareils -------------------------------------------------------
IDENTIFIANT = 40
NOM_PERSONNE = 80
EMAIL_COMPTE = 120
EMPREINTE_CODE = 200
EMPREINTE = 64
"""SHA-256 en hexadécimal (jetons, pièces, sources de reprise)."""
ADRESSE_IP = 64
AGENT = 200
NOM_APPAREIL = 80
ROLE = 16

# --- Journal, réglages, notifications, exploitation ---------------------------------------
ACTION = 80
OBJET = 24
NUMERO_DOCUMENT = 40
DETAIL = 2000
REQUETE = 16
CLE_REGLAGE = 60
VALEUR_REGLAGE = 500
MOTIF = 300
"""Motif d'annulation, de restauration, de clôture ; commentaires courts."""
COMMENTAIRE = 300
TEXTE_NOTIFICATION = 300
LIEN = 200
CLE_NOTIFICATION = 120
CLE_COURRIEL = 60
DESTINATAIRES = 500
SUJET = 200
ERREUR = 300
NOM_TACHE = 40
FICHIER = 200
NOM_BASE = 63

# --- Référentiels --------------------------------------------------------------------------
CODE_DEVISE = 3
NOM_DEVISE = 40
CODE_CLASSIFICATION = 32
CODE_TITRAGE = 48
CODE_COULEUR = 64
LIBELLE = 120
FAMILLE = 64
COMPOSITION_DETAILLEE = 160
VALEUR_TITRAGE = 32
UNITE_TITRAGE = 16
CODE_ROLE = 32
NOM_FOURNISSEUR = 160
CODE_FOURNISSEUR = 32
PAYS = 80
CONTACT = 120
TELEPHONE = 60
EMAIL_FOURNISSEUR = 160
MODE_PAIEMENT = 40
CONDITIONS_PAIEMENT = 160
INCOTERM = 20
PORT = 80
BANQUE = 120
CODE_DOUANIER = 20
LIBELLE_DOUANIER = 160
REFERENCE = 160
DESIGNATION = 160
COULEUR_CODE = 32
UNITE_ACHAT = 32
GROUPE_EQUIV = 64
CODE_QUALITE = 32
NOM_QUALITE = 120
CODE_MAGASIN = 64
NOM_MAGASIN = 120
CONTENU_MAGASIN = 120
CODE_METIER = 32
NOM_METIER = 120
CODE_POSTE = 16
LIBELLE_POSTE = 80
LIBELLE_MOTIF = 80
ALERTE = 300

# --- Documents -------------------------------------------------------------------------------
NUMERO = 32
"""Numéro d'une pièce : `BC-2026-0001`, `REC-…`, `OF-…`, `INV-…`, `RCL-…`."""
NUMERO_LOT = 80
NUMERO_FACTURE = 64
NUMERO_BL = 64
CONTROLE_PAR = 80
CONTENEUR = 60
NAVIRE = 80
MOTIF_DECISION = 500
NUMERO_DOSSIER = 16
LIBELLE_DOSSIER = 160
BANQUE_DOSSIER = 32
PIECE = 64
PRESTATAIRE = 120
LIBELLE_INVENTAIRE = 120
TEXTE_SIGNALEMENT = 500
NOM_PIECE = 200
TYPE_MIME = 100
CHEMIN_PIECE = 300
TABLE = 40
SOURCE_REPRISE = 40
