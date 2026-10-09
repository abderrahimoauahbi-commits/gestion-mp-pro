"""La liste des bons (route 152) et la fiche d'un bon (153), bâties sur `commandes_lecture` :
résumé, lignes, réceptions, décisions, version partie, gestes permis (ECRANS-PRO § 4.5–4.12).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul.achats import echeance_commande
from gestion_mp_pro.modeles import Commande, CommandeVersion, Matiere
from gestion_mp_pro.modeles.enums import StatutCommande
from gestion_mp_pro.modeles.recherche import normaliser
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
from gestion_mp_pro.services.commandes_socle import CLOS

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
class LigneVersion:
    """Une ligne de la version partie."""

    matiere_id: int
    reference: str
    quantite: float
    unite_achat: str
    contenance: float
    prix: float
    prix_confirme: bool


@dataclass
class VersionPartie:
    """Ce que le fournisseur a entre les mains, et le montant auquel une hausse se mesure."""

    figee_le: datetime
    motif: str
    montant_reference: float
    lignes: list[LigneVersion]


@dataclass
class CommandeFiche(CommandeResume):
    """La fiche complète d'un bon (route 153)."""

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
    )


@dataclass(frozen=True)
class FiltresCommandes:
    """Les filtres de la liste et de son classeur (mêmes que l'écran)."""

    statut: str = ""
    retard: bool = False
    fournisseur_id: int | None = None
    q: str = ""


def _texte(r: CommandeResume, c: Commande, ctx: Lecture) -> str:
    """Ce que la recherche lit d'un bon (champs de l'écran, références des lignes)."""
    morceaux = [
        r.numero or "brouillon",
        r.fournisseur,
        r.pays,
        r.devise,
        r.livraison_libelle,
        r.statut_libelle,
        r.cree_par or "",
        r.observations,
        r.expedition.conteneur,
        r.expedition.navire,
        *(f"{ctx.matieres[x.matiere_id].reference} {ctx.matieres[x.matiere_id].designation}"
          for x in c.lignes),
    ]  # fmt: skip
    return normaliser(" ".join(morceaux))


@dataclass
class BonDetaille:
    """Un bon de la liste, avec ses lignes et son retard (classeur des bons, route 166)."""

    resume: CommandeResume
    lignes: list[LigneLue]
    retard_jours: int | None


def detailler(s: Session, f: FiltresCommandes) -> list[BonDetaille]:
    """Les bons filtrés comme l'écran, du plus récent au plus ancien, avec leurs lignes ; un bon
    en retard dit de combien de jours, depuis son échéance (ETA, promesse, sinon date + délai)."""
    if f.statut and f.statut not in ONGLETS:
        raise Refus.saisie(
            f"Statut inconnu : « {f.statut} ».",
            code="valeur_inconnue",
            champs={"statut": "inconnu"},
        )
    s.flush()
    commandes = charger_commandes(s)
    if f.statut:
        commandes = [c for c in commandes if c.statut in ONGLETS[f.statut]]
    if f.fournisseur_id is not None:
        commandes = [c for c in commandes if c.fournisseur_id == f.fournisseur_id]
    ctx = lecture(s, commandes)
    mots = normaliser(f.q).split()
    resultat = []
    for c in commandes:
        lues = lignes(c, ctx)
        r = resume(c, ctx, lues)
        en_retard = bool(c.numero) and c.statut not in CLOS and r.livraison in EN_RETARD
        if (f.retard and not en_retard) or (mots and not all(m in _texte(r, c, ctx) for m in mots)):
            continue
        resultat.append(BonDetaille(r, lues, _retard(c, ctx) if en_retard else None))
    return resultat


def _retard(c: Commande, ctx: Lecture) -> int | None:
    """Les jours de retard d'un bon en retard (la règle de la liste, du courriel et de C06)."""
    delai = ctx.fournisseurs[c.fournisseur_id].delai_jours
    prevue = echeance_commande(c.eta, c.date_livraison_prevue, c.date_commande, delai)
    return (horloge.aujourd_hui() - prevue).days if prevue else None


def liste(s: Session, f: FiltresCommandes) -> list[CommandeResume]:
    """Route 152 : les bons du plus récent au plus ancien, filtrés au serveur."""
    return [x.resume for x in detailler(s, f)]


def _version_partie(s: Session, cid: int) -> VersionPartie | None:
    """La dernière version partie, lisible (références)."""
    v = s.scalars(
        select(CommandeVersion)
        .where(CommandeVersion.commande_id == cid)
        .options(selectinload(CommandeVersion.lignes))
        .order_by(CommandeVersion.figee_le.desc(), CommandeVersion.id.desc())
        .limit(1)
    ).first()
    if v is None:
        return None
    ids = [x.matiere_id for x in v.lignes]
    refs = dict(s.execute(select(Matiere.id, Matiere.reference).where(Matiere.id.in_(ids))).all())
    return VersionPartie(
        v.figee_le,
        str(v.motif),
        float(v.montant_reference),
        [
            LigneVersion(
                x.matiere_id,
                refs.get(x.matiere_id, ""),
                float(x.quantite),
                x.unite_achat,
                float(x.contenance),
                float(x.prix),
                x.prix_confirme,
            )
            for x in v.lignes
        ],  # fmt: skip
    )


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
        version_partie=_version_partie(s, c.id),
    )
