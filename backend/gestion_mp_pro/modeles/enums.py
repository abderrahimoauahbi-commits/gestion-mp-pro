"""Les énumérations du modèle (MODELE-DONNEES § 2), une `StrEnum` chacune, avec leur libellé.

Chaque colonne énumérée est un `VARCHAR(n)` (`sqlalchemy.Enum(native_enum=False)`) **et** un
CHECK nommé `ck_<table>_<colonne>_enum`, posé par `base.completer_le_schema` : aucune autre
valeur n'entre en base. Les valeurs sont celles de Gestion MP (parité, reprise sans
traduction) sauf les harmonisations de § 2 (types de magasin, document `ordre`).

Les quatre dernières (`TypeMotif`, `SourceReprise`, `ModeReprise`, `StatutReprise`) ne sont pas
dans la liste de MODELE-DONNEES § 2 : elles ferment des colonnes que le document décrit en
texte (décision S1, `docs/lots/S1.md`).
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Rôle d'un compte (D12 : l'administrateur technique en plus des trois rôles métier)."""

    direction = "direction"
    achats = "achats"
    alimentation = "alimentation"
    administrateur = "administrateur"


class TypeMagasin(StrEnum):
    """Magasin courant ou quarantaine (en stock, à part, hors achats)."""

    stock_courant = "stock_courant"
    quarantaine = "quarantaine"


class TypeMouvement(StrEnum):
    """Type d'une écriture du journal du stock (le moteur garde sa traduction)."""

    OUVERTURE = "OUVERTURE"
    RECEPTION = "RECEPTION"
    SORTIE = "SORTIE"
    RETOUR_MACHINE = "RETOUR_MACHINE"
    RETOUR_FOURNISSEUR = "RETOUR_FOURNISSEUR"
    AJUSTEMENT = "AJUSTEMENT"
    TRANSFERT = "TRANSFERT"


class DocumentMouvement(StrEnum):
    """Document qui a écrit un mouvement (`sortie` de Gestion MP devient `ordre`)."""

    reception = "reception"
    ordre = "ordre"
    operation = "operation"
    inventaire = "inventaire"
    reprise = "reprise"


class StatutCommande(StrEnum):
    """Statut d'un bon de commande ; `a_approuver` se lit avec `commande.parti`."""

    brouillon = "brouillon"
    a_approuver = "a_approuver"
    envoyee = "envoyee"
    confirmee = "confirmee"
    soldee = "soldee"
    annulee = "annulee"


class OrigineSolde(StrEnum):
    """Comment un bon a été soldé (ou annulé)."""

    automatique = "automatique"
    manuel = "manuel"
    reprise = "reprise"


class DecisionCommande(StrEnum):
    """Décision portée sur un bon (ce que Gestion MP rangeait dans son journal)."""

    demande_approbation = "demande_approbation"
    approbation = "approbation"
    renvoi = "renvoi"
    version_retablie = "version_retablie"
    approbation_plus_necessaire = "approbation_plus_necessaire"
    retour_brouillon = "retour_brouillon"
    rouverture = "rouverture"


class MotifVersionCommande(StrEnum):
    """Pourquoi une version partie d'un bon a été figée."""

    envoi = "envoi"
    approbation = "approbation"
    geste_accepte = "geste_accepte"
    renvoi = "renvoi"
    reprise = "reprise"


class StatutDocument(StrEnum):
    """Statut d'une réception ou d'une opération (féminin, comme dans Gestion MP)."""

    brouillon = "brouillon"
    validee = "validee"
    annulee = "annulee"


class StatutOrdre(StrEnum):
    """Statut d'un ordre de fabrication (masculin : un ordre)."""

    brouillon = "brouillon"
    valide = "valide"
    annule = "annule"


class QualiteReception(StrEnum):
    """Verdict de qualité d'une ligne reçue."""

    conforme = "conforme"
    reserve = "reserve"
    refuse = "refuse"


class TypeOperation(StrEnum):
    """Type d'une opération de stock (ne change jamais : trigger `tr_operation_type_fige`)."""

    ouverture = "ouverture"
    retour_machine = "retour_machine"
    transfert = "transfert"
    ajustement = "ajustement"
    retour_fournisseur = "retour_fournisseur"


class StatutInventaire(StrEnum):
    """Statut d'un inventaire : abandonné (ouvert puis laissé) ou annulé (validé puis défait)."""

    ouvert = "ouvert"
    valide = "valide"
    abandonne = "abandonne"
    annule = "annule"


class CritereInventaire(StrEnum):
    """Genre d'un critère du périmètre d'un inventaire."""

    matiere = "matiere"
    role = "role"
    composition = "composition"
    classe_abc = "classe_abc"


class StatutDossier(StrEnum):
    """Statut d'un dossier d'importation."""

    ouvert = "ouvert"
    clos = "clos"
    annule = "annule"


class OrigineCours(StrEnum):
    """D'où vient le cours d'une marchandise de dossier (`clos_au_jour` : figé à la clôture)."""

    bon = "bon"
    banque = "banque"
    clos_au_jour = "clos_au_jour"
    saisi = "saisi"
    reprise = "reprise"


class CleRepartition(StrEnum):
    """Clé de répartition d'un poste de frais."""

    valeur = "valeur"
    poids = "poids"


class NatureFrais(StrEnum):
    """Nature d'un poste de frais (sort du moteur les codes `DD`, `TPI`, `TVA`…)."""

    droits = "droits"
    tpi = "tpi"
    tva = "tva"
    fret = "fret"
    assurance = "assurance"
    autre = "autre"


class OriginePart(StrEnum):
    """Pourquoi la répartition d'un frais a été figée."""

    changement_cle = "changement_cle"
    reprise = "reprise"


class StatutReclamation(StrEnum):
    """Statut d'une réclamation au fournisseur."""

    ouverte = "ouverte"
    close = "close"


class MotifReclamation(StrEnum):
    """Motif d'une réclamation."""

    qualite = "qualite"
    quantite_manquante = "quantite_manquante"
    poids_bobines = "poids_bobines"
    bobines_endommagees = "bobines_endommagees"
    retard = "retard"
    documents = "documents"
    autre = "autre"


class IssueReclamation(StrEnum):
    """Issue d'une réclamation close."""

    avoir = "avoir"
    remplacement = "remplacement"
    remise = "remise"
    refusee = "refusee"
    abandonnee = "abandonnee"


class Urgence(StrEnum):
    """Urgence d'un besoin signalé par l'atelier."""

    normale = "normale"
    urgente = "urgente"


class ObjetPiece(StrEnum):
    """Ce à quoi une pièce jointe est attachée (une colonne de clé par objet)."""

    dossier = "dossier"
    reception = "reception"
    commande = "commande"
    reclamation = "reclamation"
    inventaire = "inventaire"
    fournisseur = "fournisseur"
    matiere = "matiere"


class UnitePrix(StrEnum):
    """Unité du prix d'une matière : au kilo ou au mètre (densité connue)."""

    kg = "kg"
    ml = "ml"


class SerieNumero(StrEnum):
    """Séries de numérotation des pièces."""

    BC = "BC"
    REC = "REC"
    OF = "OF"
    OUV = "OUV"
    RET = "RET"
    TRF = "TRF"
    AJU = "AJU"
    RFO = "RFO"
    INV = "INV"
    RCL = "RCL"
    LOT = "LOT"
    DOS = "DOS"


class OrigineVersion(StrEnum):
    """Origine d'une version de recette ou de plan."""

    saisie = "saisie"
    restauration = "restauration"
    releve = "releve"
    reprise = "reprise"


class TonNotification(StrEnum):
    """Ton d'une notification."""

    info = "info"
    succes = "succes"
    alerte = "alerte"
    danger = "danger"


class StatutCourriel(StrEnum):
    """Statut d'un courriel de la file."""

    en_attente = "en_attente"
    envoye = "envoye"
    abandonne = "abandonne"


class GenreCourriel(StrEnum):
    """Genre d'un courriel."""

    lundi = "lundi"
    alerte = "alerte"


class GenreSauvegarde(StrEnum):
    """Genre d'une sauvegarde de la base."""

    quotidienne = "quotidienne"
    manuelle = "manuelle"
    avant_restauration = "avant_restauration"
    avant_reprise = "avant_reprise"
    reference_vide = "reference_vide"


class ObjetJournal(StrEnum):
    """Table visée par une ligne du journal (liste fermée ; `lot` ajouté, décision S1)."""

    utilisateur = "utilisateur"
    appareil = "appareil"
    parametre = "parametre"
    devise = "devise"
    sauvegarde = "sauvegarde"
    composition = "composition"
    type_fil = "type_fil"
    titrage = "titrage"
    couleur = "couleur"
    role_nomenclature = "role_nomenclature"
    fournisseur = "fournisseur"
    matiere = "matiere"
    code_douanier = "code_douanier"
    poste_frais = "poste_frais"
    qualite = "qualite"
    magasin = "magasin"
    metier = "metier"
    lot = "lot"
    commande = "commande"
    reception = "reception"
    facture = "facture"
    ordre = "ordre"
    operation = "operation"
    inventaire = "inventaire"
    dossier = "dossier"
    dossier_frais = "dossier_frais"
    reclamation = "reclamation"
    signalement = "signalement"
    piece_jointe = "piece_jointe"
    periode = "periode"
    reprise = "reprise"
    systeme = "systeme"


class TypeMotif(StrEnum):
    """Ce qu'un motif de mouvement accompagne : un type d'opération, ou l'inventaire."""

    ouverture = "ouverture"
    retour_machine = "retour_machine"
    transfert = "transfert"
    ajustement = "ajustement"
    retour_fournisseur = "retour_fournisseur"
    inventaire = "inventaire"


class SourceReprise(StrEnum):
    """Base d'où une ligne a été reprise."""

    gestion_mp = "gestion_mp"
    erp_fil = "erp_fil"


class ModeReprise(StrEnum):
    """Ce qu'une exécution de la reprise a repris."""

    referentiels = "referentiels"
    activite = "activite"
    tout = "tout"


class StatutReprise(StrEnum):
    """Issue d'une exécution de la reprise."""

    en_cours = "en_cours"
    reussie = "reussie"
    echouee = "echouee"


ENUMERATIONS: tuple[type[StrEnum], ...] = (
    Role, TypeMagasin, TypeMouvement, DocumentMouvement, StatutCommande, OrigineSolde,
    DecisionCommande, MotifVersionCommande, StatutDocument, StatutOrdre, QualiteReception,
    TypeOperation, StatutInventaire, CritereInventaire, StatutDossier, OrigineCours,
    CleRepartition, NatureFrais, OriginePart, StatutReclamation, MotifReclamation,
    IssueReclamation, Urgence, ObjetPiece, UnitePrix, SerieNumero, OrigineVersion,
    TonNotification, StatutCourriel, GenreCourriel, GenreSauvegarde, ObjetJournal,
    TypeMotif, SourceReprise, ModeReprise, StatutReprise,
)  # fmt: skip
"""Toutes les énumérations, dans l'ordre de MODELE-DONNEES § 2 (puis les quatre de S1)."""
