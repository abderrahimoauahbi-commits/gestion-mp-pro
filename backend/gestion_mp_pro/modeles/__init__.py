"""Le modèle de données de Gestion MP PRO (MODELE-DONNEES.md, qui fait foi).

Importer ce paquet charge **toutes** les tables (métadonnées complètes pour Alembic), pose les
CHECK génériques (énumérations, refus de `NaN`) et branche l'écouteur de `texte_recherche`.
`tables_d_activite()` donne les tables vidées avec l'activité (incohérence 32).
"""

from __future__ import annotations

from gestion_mp_pro.modeles import recherche
from gestion_mp_pro.modeles.achats import (
    Commande,
    CommandeDecision,
    CommandeLigne,
    CommandeVersion,
    CommandeVersionLigne,
    Facture,
)
from gestion_mp_pro.modeles.base import Base, completer_le_schema
from gestion_mp_pro.modeles.catalogue import Fournisseur, Matiere
from gestion_mp_pro.modeles.communication import (
    Courriel,
    Notification,
    NotificationLecture,
    Sauvegarde,
    TacheExecution,
)
from gestion_mp_pro.modeles.importations import (
    Dossier,
    DossierFrais,
    DossierFraisPart,
    DossierLigne,
)
from gestion_mp_pro.modeles.inventaires import (
    Inventaire,
    InventaireCritere,
    InventaireLigne,
    InventaireMatiere,
)
from gestion_mp_pro.modeles.metiers import Metier, MetierEtage, Montage, MontageEvenement
from gestion_mp_pro.modeles.operations import Operation, OperationLigne
from gestion_mp_pro.modeles.production import Ordre, OrdreLigne, OrdrePrevu, OrdreQualite
from gestion_mp_pro.modeles.qualites import (
    PlanVersion,
    PlanVersionSaison,
    Qualite,
    QualitePoids,
    QualiteSaison,
    Recette,
    RecetteVersion,
    RecetteVersionLigne,
    RecetteVersionPoids,
)
from gestion_mp_pro.modeles.receptions import Reception, ReceptionLigne
from gestion_mp_pro.modeles.referentiels import (
    CodeDouanier,
    Composition,
    Couleur,
    Devise,
    DeviseCours,
    Magasin,
    Motif,
    PosteFrais,
    RoleNomenclature,
    Titrage,
    TypeFil,
)
from gestion_mp_pro.modeles.reprise import RepriseCorrespondance, RepriseExecution
from gestion_mp_pro.modeles.socle import (
    CLES_REGLAGES,
    Appareil,
    Compteur,
    Journal,
    Parametre,
    ParametreHistorique,
    Session,
    Tentative,
    Utilisateur,
)
from gestion_mp_pro.modeles.stock import Lot, Mouvement, Solde
from gestion_mp_pro.modeles.suivi import IndicateurJour, PieceJointe, Reclamation, Signalement

completer_le_schema(Base.metadata)

metadata = Base.metadata
"""Les métadonnées complètes (cible d'Alembic)."""


def tables_d_activite() -> list[str]:
    """Les tables marquées `__activite__` (vidées avec l'activité), par ordre alphabétique."""
    return sorted(m.class_.__tablename__ for m in Base.registry.mappers if m.class_.__activite__)


__all__ = [
    "CLES_REGLAGES",
    "Appareil",
    "Base",
    "CodeDouanier",
    "Commande",
    "CommandeDecision",
    "CommandeLigne",
    "CommandeVersion",
    "CommandeVersionLigne",
    "Composition",
    "Compteur",
    "Couleur",
    "Courriel",
    "Devise",
    "DeviseCours",
    "Dossier",
    "DossierFrais",
    "DossierFraisPart",
    "DossierLigne",
    "Facture",
    "Fournisseur",
    "IndicateurJour",
    "Inventaire",
    "InventaireCritere",
    "InventaireLigne",
    "InventaireMatiere",
    "Journal",
    "Lot",
    "Magasin",
    "Matiere",
    "Metier",
    "MetierEtage",
    "Montage",
    "MontageEvenement",
    "Motif",
    "Mouvement",
    "Notification",
    "NotificationLecture",
    "Operation",
    "OperationLigne",
    "Ordre",
    "OrdreLigne",
    "OrdrePrevu",
    "OrdreQualite",
    "Parametre",
    "ParametreHistorique",
    "PieceJointe",
    "PlanVersion",
    "PlanVersionSaison",
    "PosteFrais",
    "Qualite",
    "QualitePoids",
    "QualiteSaison",
    "Recette",
    "RecetteVersion",
    "RecetteVersionLigne",
    "RecetteVersionPoids",
    "Reception",
    "ReceptionLigne",
    "Reclamation",
    "RoleNomenclature",
    "RepriseCorrespondance",
    "RepriseExecution",
    "Sauvegarde",
    "Session",
    "Signalement",
    "Solde",
    "TacheExecution",
    "Tentative",
    "Titrage",
    "TypeFil",
    "Utilisateur",
    "metadata",
    "recherche",
    "tables_d_activite",
]
