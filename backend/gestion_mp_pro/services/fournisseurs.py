"""Fournisseurs (routes 64–69 ; héritage R-REF-16…20, A-14, A-23, A-25).

- Nom unique sans tenir compte de la casse ; pays en MAJUSCULES, espaces réduits (« un pays
  s'écrit d'une seule façon ») ; devise connue (en capitales).
- Ce qui pèse sur chaque fournisseur (matières par devise, commandes, réceptions, lots,
  opérations, factures, pièces jointes…) et son **délai mesuré** (commande → réception validée,
  moyenne au dixième sur 365 jours) : l'écran sait d'avance ce qui empêche une suppression.
- `est_local` : la seule définition du « fournisseur local » (A-23), que les importations lisent
  aussi : pays MAROC, MOROCCO ou MA ; à défaut de pays, une facturation en dirhams.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Devise,
    DossierLigne,
    Facture,
    Fournisseur,
    Lot,
    Matiere,
    Operation,
    PieceJointe,
    Reception,
    ReceptionLigne,
    Reclamation,
)
from gestion_mp_pro.modeles.enums import StatutDocument
from gestion_mp_pro.services import audit, horloge, recherche

PAYS_LOCAUX = frozenset({"MAROC", "MOROCCO", "MA"})
FENETRE_DELAI = timedelta(days=365)
TEXTES = ("nom", "code", "contact", "telephone", "email", "port_chargement", "banque")


def est_local(pays: str | None, devise: str | None) -> bool:
    """Un fournisseur marocain : le pays le dit ; à défaut de pays, la facturation en MAD."""
    pays = (pays or "").strip().upper()
    return pays in PAYS_LOCAUX or (not pays and (devise or "MAD") == "MAD")


def pays_normalise(pays: str) -> str:
    """« turkey » → « TURKEY » ; espaces multiples réduits à un."""
    return " ".join(pays.upper().split())


@dataclass
class Usages:
    """Ce qui pèse sur un fournisseur (et l'empêche d'être supprimé)."""

    devises: dict[str, int] = field(default_factory=dict)
    compteurs: dict[str, int] = field(default_factory=dict)
    delais: list[int] = field(default_factory=list)
    pieces_retirees: int = 0

    def nombre(self, cle: str) -> int:
        """Un compteur (0 s'il n'y a rien)."""
        return self.compteurs.get(cle, 0)

    @property
    def delai_mesure(self) -> float | None:
        """Délai moyen commande → réception validée, au dixième de jour, sur 365 jours."""
        return round(sum(self.delais) / len(self.delais), 1) if self.delais else None

    def empechements(self) -> list[str]:
        """Ce qui interdit la suppression, dans l'ordre où le refus le dit."""
        return [quoi for cle, quoi in EMPECHEMENTS if self.nombre(cle)]


EMPECHEMENTS: tuple[tuple[str, str], ...] = (
    ("matieres", "des matières du catalogue"),
    ("commandes", "des commandes"),
    ("receptions", "des réceptions"),
    ("lots", "des lots"),
    ("operations", "des opérations"),
    ("factures", "des factures"),
    ("dossiers", "des dossiers d'importation"),
    ("reclamations", "des réclamations"),
    ("pieces", "des pièces jointes"),
)
COLONNES: dict[str, Any] = {
    "commandes": Commande.fournisseur_id,
    "receptions": Reception.fournisseur_id,
    "lots": Lot.fournisseur_id,
    "operations": Operation.fournisseur_id,
    "factures": Facture.fournisseur_id,
    "dossiers": DossierLigne.fournisseur_id,
    "reclamations": Reclamation.fournisseur_id,
}


def _par_fournisseur(s: Session, colonne: Any, ident: int | None) -> dict[int, int]:
    """Le nombre de lignes par fournisseur d'une colonne (un seul fournisseur si `ident`)."""
    requete = select(colonne, func.count()).where(colonne.is_not(None)).group_by(colonne)
    if ident is not None:
        requete = requete.where(colonne == ident)
    return dict(s.execute(requete).all())


def usages(s: Session, ident: int | None = None) -> dict[int, Usages]:
    """Les usages de chaque fournisseur (ou d'un seul) : requêtes groupées, aucune par ligne."""
    resultat: dict[int, Usages] = defaultdict(Usages)
    devises = select(Matiere.fournisseur_id, Matiere.devise, func.count()).group_by(
        Matiere.fournisseur_id, Matiere.devise
    )
    if ident is not None:
        devises = devises.where(Matiere.fournisseur_id == ident)
    for fid, devise, n in s.execute(devises):
        if fid is not None:
            resultat[fid].devises[devise] = n
            resultat[fid].compteurs["matieres"] = resultat[fid].nombre("matieres") + n
    for cle, colonne in COLONNES.items():
        for fid, n in _par_fournisseur(s, colonne, ident).items():
            resultat[fid].compteurs[cle] = n
    pieces = select(PieceJointe.fournisseur_id, PieceJointe.retiree_le.is_(None), func.count())
    pieces = pieces.where(PieceJointe.fournisseur_id.is_not(None)).group_by(
        PieceJointe.fournisseur_id, PieceJointe.retiree_le.is_(None)
    )
    if ident is not None:
        pieces = pieces.where(PieceJointe.fournisseur_id == ident)
    for fid, active, n in s.execute(pieces):
        if fid is None:
            continue
        if active:
            resultat[fid].compteurs["pieces"] = n
        else:
            resultat[fid].pieces_retirees = n
    _delais(s, resultat, ident)
    return resultat


def _delais(s: Session, resultat: dict[int, Usages], ident: int | None) -> None:
    """Délai commande → réception validée, par couple réception/bon, sur 365 jours."""
    depuis = horloge.aujourd_hui() - FENETRE_DELAI
    requete = (
        select(Reception.fournisseur_id, Reception.id, Commande.id, Reception.date)
        .add_columns(Commande.date_commande)
        .join(ReceptionLigne, ReceptionLigne.reception_id == Reception.id)
        .join(CommandeLigne, CommandeLigne.id == ReceptionLigne.commande_ligne_id)
        .join(Commande, Commande.id == CommandeLigne.commande_id)
        .where(Reception.statut == StatutDocument.validee, Reception.date >= depuis)
        .distinct()
    )
    if ident is not None:
        requete = requete.where(Reception.fournisseur_id == ident)
    for fid, _r, _c, recu_le, commande_le in s.execute(requete):
        resultat[fid].delais.append(max(0, (recu_le - commande_le).days))


def lister(s: Session, q: str | None = None, actif: bool | None = None) -> list[Fournisseur]:
    """Les fournisseurs triés par nom ; `q` : tous les mots, sans accents ; `actif` : filtre."""
    requete = select(Fournisseur).order_by(Fournisseur.nom)
    if q:
        requete = requete.where(*recherche.conditions(Fournisseur.texte_recherche, q))
    if actif is not None:
        requete = requete.where(Fournisseur.actif == actif)
    return list(s.scalars(requete))


def fournisseur(s: Session, ident: int, *, verrou: bool = False) -> Fournisseur:
    """Un fournisseur (404 « Fournisseur introuvable. »)."""
    f = s.get(Fournisseur, ident, with_for_update=verrou)
    if f is None:
        raise Refus.introuvable("Fournisseur introuvable.")
    return f


def devise_connue(s: Session, brut: str, avant: str | None = None) -> str:
    """Une devise connue, en capitales ; hors service, seulement si elle ne change pas."""
    code = brut.strip().upper()
    d = s.get(Devise, code) if code else None
    if d is None:
        raise Refus.saisie(
            f"Devise inconnue : « {code} ». L'ajouter d'abord (Réglages › Devises).",
            code="valeur_inconnue",
            champs={"devise": "inconnue"},
        )
    if not d.actif and code != avant:
        raise Refus.saisie(
            f"La devise « {code} » est hors service : la remettre en service d'abord "
            "(Réglages › Devises).",
            code="valeur_inconnue",
            champs={"devise": "hors service"},
        )
    return code


def _donnees(s: Session, champs: dict[str, Any], avant: Fournisseur | None) -> dict[str, Any]:
    """Les champs nettoyés : textes, pays en capitales, devise connue."""
    donnees = dict(champs)
    for k in TEXTES:
        donnees[k] = str(donnees.get(k) or "").strip()
    donnees["pays"] = pays_normalise(str(donnees.get("pays") or ""))
    donnees["devise"] = devise_connue(
        s, str(donnees.get("devise") or "MAD"), avant.devise if avant else None
    )
    return donnees


def _nom_libre(s: Session, nom: str, ident: int | None) -> None:
    """Un nom ne désigne qu'un fournisseur, quelle que soit sa casse (X-REF-15)."""
    if s.scalar(
        select(Fournisseur.id).where(
            func.lower(Fournisseur.nom) == nom.lower(), Fournisseur.id != (ident or 0)
        )
    ):
        raise Refus.etat(f"Le fournisseur « {nom} » existe déjà.", code="doublon")


def creer(s: Session, qui: audit.Qui, champs: dict[str, Any]) -> Fournisseur:
    """Un fournisseur nouveau (route 66)."""
    donnees = _donnees(s, champs, None)
    _nom_libre(s, donnees["nom"], None)
    f = Fournisseur(**donnees, modifie_par_id=qui.id, modifie_le=horloge.maintenant())
    s.add(f)
    audit.creation(s, qui, "création fournisseur", f, detail=f.nom)
    return f


def modifier(
    s: Session, qui: audit.Qui, ident: int, champs: dict[str, Any], version: int
) -> Fournisseur:
    """Un fournisseur modifié (route 67), sous verrou, à sa version lue."""
    f = fournisseur(s, ident, verrou=True)
    audit.verifier_version(s, f, version, "Ce fournisseur", feminin=False)
    donnees = _donnees(s, champs, f)
    _nom_libre(s, donnees["nom"], ident)
    with audit.suivre(s, qui, "modification fournisseur", f, detail=donnees["nom"]):
        for k, v in donnees.items():
            setattr(f, k, v)
        f.modifie_par_id = qui.id
    s.flush()
    return f


def supprimer(s: Session, qui: audit.Qui, ident: int, version: int | None) -> None:
    """Un fournisseur sans aucune trace (route 68) ; sinon le désactiver (X-REF-18, 19)."""
    f = fournisseur(s, ident, verrou=True)
    if version is not None:
        audit.verifier_version(s, f, version, "Ce fournisseur", feminin=False)
    u = usages(s, ident).get(ident, Usages())
    for quoi in u.empechements():
        if quoi == "des pièces jointes":
            raise Refus.etat(
                f"« {f.nom} » a des pièces jointes : les retirer d'abord, ou le désactiver.",
                code="fiche_utilisee",
            )
        raise Refus.etat(
            f"« {f.nom} » a {quoi} : le désactiver plutôt que le supprimer.", code="fiche_utilisee"
        )
    if u.pieces_retirees:
        raise Refus.etat(
            f"« {f.nom} » a des pièces jointes retirées, gardées pour l'historique : le "
            "désactiver plutôt que le supprimer.",
            code="fiche_utilisee",
        )
    audit.suppression(s, qui, "suppression fournisseur", f, detail=f.nom)
    s.delete(f)
    s.flush()
