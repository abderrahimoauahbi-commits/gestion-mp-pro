"""La liste des bons (route 152) et la fiche d'un bon (153), bâties sur `commandes_lecture` :
résumé, lignes, réceptions, décisions, version partie, gestes permis (ECRANS-PRO § 4.5–4.12).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul.achats import echeance_commande
from gestion_mp_pro.modeles import Commande
from gestion_mp_pro.modeles.enums import StatutCommande
from gestion_mp_pro.services import commandes_gestes as gestes
from gestion_mp_pro.services import horloge, reglages
from gestion_mp_pro.services.commandes_lecture import (
    LIBELLES_LIVRAISON,
    LIBELLES_STATUT,
    Lecture,
    LigneLue,
    ReceptionDuBon,
    Renvoi,
    approbation_requise,
    charger_commandes,
    cours,
    estime,
    lecture,
    lignes,
    livraison,
    renvoi,
)
from gestion_mp_pro.services.commandes_saisie import promesse_figee
from gestion_mp_pro.services.commandes_socle import CLOS, prix_deja_confirmes
from gestion_mp_pro.services.commandes_versions import VersionPartie, version_partie

ONGLETS = {
    "brouillon": {StatutCommande.brouillon},
    "a_approuver": {StatutCommande.a_approuver},
    "envoyee": {StatutCommande.envoyee},
    "confirmee": {StatutCommande.confirmee},
    "soldee": {StatutCommande.soldee},
    "annulee": {StatutCommande.annulee},
    "clos": {StatutCommande.soldee, StatutCommande.annulee},
}
"""`?statut=` de la liste : un statut, ou « clos » (soldées et annulées, onglet de l'écran)."""
EN_RETARD = ("en_retard", "partiel_retard")


@dataclass
class Jalons:
    """Le suivi de l'expédition d'un bon."""

    proforma_le: date | None
    acompte_le: date | None
    embarquee_le: date | None
    eta: date | None
    au_port_le: date | None
    dedouanee_le: date | None
    arrivee_usine_le: date | None
    conteneur: str
    navire: str


@dataclass
class CommandeResume:
    """Un bon dans la liste : état de livraison, montants estimés, reçu, reste."""

    id: int
    numero: str | None
    parti: bool
    statut: str
    statut_libelle: str
    version: int
    fournisseur_id: int
    fournisseur: str
    pays: str
    date_commande: date
    date_livraison_prevue: date | None
    devise: str
    cours: float | None
    taux_du_jour: float
    quantite: float
    recu: float
    reste_kg: float
    part_livree: float
    nb_lignes: int
    references: list[str]
    montant: float
    montant_mad: float
    montant_estime: float
    montant_estime_mad: float
    reste_estime_mad: float
    prix_a_confirmer: int
    approbation_requise: bool
    livraison: str
    livraison_libelle: str
    livree_le: date | None
    derniere_reception_le: date | None
    expedition: Jalons
    observations: str
    cree_par: str | None
    cree_le: datetime
    approuvee_par: str | None
    approuvee_le: datetime | None
    montant_approuve: float | None
    solde_origine: str | None
    solde_par: str | None
    solde_le: datetime | None
    renvoi: Renvoi | None
    en_retard: bool = False
    arrivee_attendue: date | None = None
    arrivee_sous_7_jours: bool = False
    kg_en_quarantaine: float = 0.0


@dataclass
class DecisionLue:
    """Une décision sur le bon (onglet « Approbation »)."""

    quand: datetime
    par: str | None
    decision: str
    motif: str
    montant_avant: float | None
    montant_apres: float | None


@dataclass
class CommandeFiche(CommandeResume):
    """La fiche complète d'un bon (route 153)."""

    promesse_figee: str | None = None
    seuil_approbation: float = 0.0
    contact: str = ""
    email: str = ""
    telephone: str = ""
    delai_jours: int = 0
    confirme_le: datetime | None = None
    modifiable: bool = False
    fin_possible: str | None = None
    raison_sociale_reglee: bool = True
    actions: dict[str, str | None] = field(default_factory=dict)
    lignes: list[LigneLue] = field(default_factory=list)
    receptions: list[ReceptionDuBon] = field(default_factory=list)
    decisions: list[DecisionLue] = field(default_factory=list)
    version_partie: VersionPartie | None = None


def _jalons(c: Commande) -> Jalons:
    """Les jalons du bon."""
    return Jalons(
        c.proforma_le,
        c.acompte_le,
        c.embarquee_le,
        c.eta,
        c.au_port_le,
        c.dedouanee_le,
        c.arrivee_usine_le,
        c.conteneur,
        c.navire,
    )


@dataclass(frozen=True)
class Arrivee:
    """Quand le bon doit arriver (ETA, sinon livraison promise) et s'il arrive d'hier à J+7
    (« Arrivées attendues dans les 7 jours » : la règle de Gestion MP, comptée au serveur)."""

    arrivee_attendue: date | None
    arrivee_sous_7_jours: bool


def arrivee(c: Commande) -> Arrivee:
    """L'arrivée attendue d'un bon parti, ni soldé ni annulé (RESTES3, F1)."""
    if not c.numero or c.statut in CLOS:
        return Arrivee(None, False)
    quand = c.eta or c.date_livraison_prevue
    jour = horloge.aujourd_hui()
    proche = quand is not None and jour - timedelta(days=1) <= quand <= jour + timedelta(days=7)
    return Arrivee(quand, proche)


def resume(c: Commande, ctx: Lecture, lues: list[LigneLue] | None = None) -> CommandeResume:
    """Le résumé d'un bon (les champs de la liste)."""
    lues = lignes(c, ctx) if lues is None else lues
    f = ctx.fournisseurs[c.fournisseur_id]
    taux, montant_estime = cours(c, ctx), estime(c, ctx)
    quantite, recu = sum(x.quantite for x in lues), sum(x.recu for x in lues)
    montant = sum(x.montant for x in lues)
    code = livraison(c, ctx)
    validees = [r for r in ctx.receptions.get(c.id, []) if r.statut == "validee"]
    return CommandeResume(
        id=c.id,
        numero=c.numero,
        parti=bool(c.numero),
        statut=str(c.statut),
        statut_libelle=LIBELLES_STATUT[str(c.statut)],
        version=c.version,
        fournisseur_id=f.id,
        fournisseur=f.nom,
        pays=f.pays,
        date_commande=c.date_commande,
        date_livraison_prevue=c.date_livraison_prevue,
        devise=c.devise,
        cours=float(c.cours) if c.cours else None,
        taux_du_jour=ctx.taux.get(c.devise, 1.0),
        quantite=quantite,
        recu=recu,
        reste_kg=sum(x.reste for x in lues),
        part_livree=min(1.0, recu / quantite) if quantite else 0.0,
        nb_lignes=len(lues),
        references=[x.reference for x in lues],
        montant=montant,
        montant_mad=montant * taux,
        montant_estime=montant_estime,
        montant_estime_mad=montant_estime * taux,
        reste_estime_mad=sum(x.reste_estime for x in lues) * taux,
        prix_a_confirmer=sum(1 for x in lues if not x.prix_confirme),
        approbation_requise=approbation_requise(c, ctx),
        livraison=code,
        livraison_libelle=LIBELLES_LIVRAISON[code],
        livree_le=validees[-1].date if validees and code == "livre" else None,
        derniere_reception_le=validees[-1].date if validees else None,
        expedition=_jalons(c),
        observations=c.observations,
        cree_par=ctx.nom(c.cree_par_id),
        cree_le=c.cree_le,
        approuvee_par=ctx.nom(c.approuvee_par_id),
        approuvee_le=c.approuvee_le,
        montant_approuve=float(c.montant_approuve) if c.montant_approuve else None,
        solde_origine=str(c.solde_origine) if c.solde_origine else None,
        solde_par=ctx.nom(c.solde_par_id),
        solde_le=c.solde_le,
        renvoi=renvoi(c, ctx),
        en_retard=bool(c.numero) and c.statut not in CLOS and code in EN_RETARD,
        **vars(arrivee(c)),
        kg_en_quarantaine=sum(x.en_quarantaine for x in lues),
    )


@dataclass(frozen=True)
class FiltresCommandes:
    """Les filtres de la liste et de son classeur (mêmes que l'écran). La liste paginée pousse
    `statut`, `fournisseur_id`, `devise` et la recherche (`q`) en SQL (`commandes_liste`) ;
    `retard` est le drapeau calculé par le moteur (borné)."""

    statut: str = ""
    retard: bool = False
    fournisseur_id: int | None = None
    devise: str = ""
    q: str = ""


@dataclass
class BonDetaille:
    """Un bon de la liste, avec ses lignes et son retard (classeur des bons, route 166)."""

    resume: CommandeResume
    lignes: list[LigneLue]
    retard_jours: int | None


def _retard(c: Commande, ctx: Lecture) -> int | None:
    """Les jours de retard d'un bon en retard (la règle de la liste, du courriel et de C06)."""
    delai = ctx.fournisseurs[c.fournisseur_id].delai_jours
    prevue = echeance_commande(c.eta, c.date_livraison_prevue, c.date_commande, delai)
    return (horloge.aujourd_hui() - prevue).days if prevue else None


def fiche(s: Session, cid: int, role: str) -> CommandeFiche:
    """Route 153 : la fiche complète, dont les gestes permis à ce rôle et pourquoi pas."""
    s.flush()
    commandes = charger_commandes(s, [cid])
    if not commandes:
        raise Refus.introuvable("Commande introuvable.")
    c = commandes[0]
    ctx = lecture(s, commandes)
    lues = lignes(c, ctx)
    f = ctx.fournisseurs[c.fournisseur_id]
    receptions = ctx.receptions.get(c.id, [])
    etat = gestes.EtatBon(
        c.statut,
        c.numero,
        c.numero or f"brouillon n° {c.id}",
        any(x.id in ctx.receptionnees for x in c.lignes),
        c.id in ctx.avec_version,
    )
    actions = gestes.permis(etat, role)
    confirmes = [x.confirme_le for x in lues if x.confirme_le]
    return CommandeFiche(
        **vars(resume(c, ctx, lues)),
        promesse_figee=promesse_figee(c, prix_deja_confirmes(s, c)),
        seuil_approbation=ctx.seuil,
        contact=f.contact,
        email=f.email,
        telephone=f.telephone,
        delai_jours=f.delai_jours,
        confirme_le=max(confirmes) if confirmes else None,
        modifiable=actions["modifier"] is None,
        fin_possible=None
        if actions["solder"] is not None
        else ("solder" if any(r.statut == "validee" for r in receptions) else "annuler"),
        raison_sociale_reglee=bool(reglages.texte(s, "nom_entreprise").strip()),
        actions=actions,
        lignes=lues,
        receptions=receptions,
        decisions=[
            DecisionLue(
                d.quand,
                ctx.nom(d.par_id),
                str(d.decision),
                d.motif,
                float(d.montant_avant) if d.montant_avant is not None else None,
                float(d.montant_apres) if d.montant_apres is not None else None,
            )
            for d in ctx.decisions.get(c.id, [])
        ],  # fmt: skip
        version_partie=version_partie(s, c.id),
    )
