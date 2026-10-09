"""Lire les bons : la liste (route 152) et la fiche (153), avec reçu net, quarantaine, état de
livraison, montants estimés, version partie, décisions et gestes permis (REGLES § 2.4 ;
`gestion_mp/api/achats.py` : `Contexte`, `commande_dict`, `_statut_livraison`).

Tout ce que la liste lit (reçu, tolérances, seuil, cours, réceptions, décisions, noms) se lit
une fois (`Lecture`), en requêtes groupées : aucune requête par bon. Rien ne s'écrit.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.calcul.suivi_livraison import BonALivrer, LigneBon, statut_livraison
from gestion_mp_pro.modeles import (
    Commande,
    CommandeDecision,
    CommandeLigne,
    CommandeVersion,
    Fournisseur,
    Matiere,
    Reception,
    ReceptionLigne,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import (
    DecisionCommande,
    MotifVersionCommande,
    OrigineSolde,
    StatutCommande,
)
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services.chargeur.achats import en_quarantaine_par_ligne, recu_par_ligne
from gestion_mp_pro.services.commandes_socle import (
    CLOS,
    lignes_receptionnees,
    prix_catalogue_kg,
    prix_estime,
    reglage_nombre,
    taux_des_devises,
)

LIVRAISONS = {
    "🟢 Livré": "livre",
    "⚫ Soldé": "solde",
    "⚫ Soldé sans livraison": "solde_sans_livraison",
    "⚫ Annulé": "annule",
    "🟡 Reçu sous réserve": "sous_reserve",
    "🟡 En cours": "en_cours",
    "🟠 Partiel retard": "partiel_retard",
    "⚪ Attendu": "attendu",
    "🔴 En retard": "en_retard",
}
"""L'état de livraison du moteur (libellés de Gestion MP) → code de l'écran (`statuts.ts`)."""

LIBELLES_LIVRAISON = {
    "pas_envoye": "Pas envoyé",
    "attendu": "Attendu",
    "en_cours": "En cours",
    "sous_reserve": "Reçu sous réserve",
    "partiel_retard": "Partiel retard",
    "en_retard": "En retard",
    "livre": "Livré",
    "solde": "Soldé",
    "solde_main": "Soldé à la main",
    "solde_sans_livraison": "Soldé sans livraison",
    "annule": "Annulé",
}
LIBELLES_STATUT = {
    "brouillon": "Brouillon",
    "a_approuver": "À approuver",
    "envoyee": "Envoyée",
    "confirmee": "Confirmée",
    "soldee": "Soldée",
    "annulee": "Annulée",
}
EFFACENT_LE_RENVOI = (DecisionCommande.demande_approbation, DecisionCommande.approbation)


@dataclass
class ReceptionDuBon:
    """Une réception qui nomme une ligne du bon, et ce qu'elle a pesé pour lui."""

    id: int
    numero: str | None
    date: date
    statut: str
    pese: float = 0.0


@dataclass
class Renvoi:
    """Le dernier renvoi de la direction, tant qu'aucune soumission ni envoi ne l'a suivi."""

    par: str
    le: datetime
    motif: str


@dataclass
class Lecture:
    """Ce que la lecture des bons lit une fois pour toutes."""

    recu: dict[int, float]
    bloque: dict[int, float]
    tolerance: float
    retard_tolere: float
    seuil: float
    taux: dict[str, float]
    receptionnees: set[int]
    matieres: dict[int, Matiere]
    fournisseurs: dict[int, Fournisseur]
    noms: dict[int, str]
    receptions: dict[int, list[ReceptionDuBon]] = field(default_factory=dict)
    decisions: dict[int, list[CommandeDecision]] = field(default_factory=dict)
    envois: dict[int, list[datetime]] = field(default_factory=dict)
    avec_version: set[int] = field(default_factory=set)

    def nom(self, ident: int | None) -> str | None:
        """Le nom d'un compte (ou `None`)."""
        return None if ident is None else self.noms.get(ident, "")


def _receptions(s: Session, ids: list[int]) -> dict[int, list[ReceptionDuBon]]:
    """Les réceptions de chaque bon, dans l'ordre des dates, une fois chacune."""
    requete = (
        select(
            Reception.id,
            Reception.numero,
            Reception.date,
            Reception.statut,
            CommandeLigne.commande_id,
            func.sum(ReceptionLigne.quantite_pesee),
        )
        .join(ReceptionLigne, ReceptionLigne.reception_id == Reception.id)
        .join(CommandeLigne, CommandeLigne.id == ReceptionLigne.commande_ligne_id)
        .where(CommandeLigne.commande_id.in_(ids))
        .group_by(Reception.id, CommandeLigne.commande_id)
        .order_by(Reception.date, Reception.id)
    )
    resultat: dict[int, list[ReceptionDuBon]] = defaultdict(list)
    for rid, numero, jour, statut, cid, pese in s.execute(requete):
        resultat[cid].append(ReceptionDuBon(rid, numero, jour, str(statut), float(pese or 0)))
    return dict(resultat)


def lecture(s: Session, commandes: list[Commande]) -> Lecture:
    """Le contexte de lecture de ces bons (requêtes groupées)."""
    ids = [c.id for c in commandes]
    mids = {x.matiere_id for c in commandes for x in c.lignes}
    fids = {c.fournisseur_id for c in commandes}
    decisions: dict[int, list[CommandeDecision]] = defaultdict(list)
    for d in s.scalars(
        select(CommandeDecision)
        .where(CommandeDecision.commande_id.in_(ids))
        .order_by(CommandeDecision.quand, CommandeDecision.id)
    ):
        decisions[d.commande_id].append(d)
    envois: dict[int, list[datetime]] = defaultdict(list)
    avec_version: set[int] = set()
    versions = select(CommandeVersion.commande_id, CommandeVersion.figee_le, CommandeVersion.motif)
    for cid, quand, motif in s.execute(versions.where(CommandeVersion.commande_id.in_(ids))):
        avec_version.add(cid)
        if motif == MotifVersionCommande.envoi:
            envois[cid].append(quand)
    return Lecture(
        recu=recu_par_ligne(s),
        bloque=en_quarantaine_par_ligne(s),
        tolerance=reglage_nombre(s, "toler_in_full"),
        retard_tolere=reglage_nombre(s, "toler_retard_jours"),
        seuil=reglage_nombre(s, "seuil_approbation"),
        taux=taux_des_devises(s),
        receptionnees=lignes_receptionnees(s, [x.id for c in commandes for x in c.lignes]),
        matieres={m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(mids)))},
        fournisseurs={
            f.id: f for f in s.scalars(select(Fournisseur).where(Fournisseur.id.in_(fids)))
        },
        noms=dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).all()),
        receptions=_receptions(s, ids),
        decisions=dict(decisions),
        envois=dict(envois),
        avec_version=avec_version,
    )


def charger_commandes(s: Session, ids: list[int] | None = None) -> list[Commande]:
    """Les bons (et leurs lignes), du plus récent au plus ancien."""
    requete = select(Commande).options(selectinload(Commande.lignes)).order_by(Commande.id.desc())
    if ids is not None:
        requete = requete.where(Commande.id.in_(ids))
    return list(s.scalars(requete))


# ── Calculs d'un bon ─────────────────────────────────────────────────────────


def livraison(c: Commande, ctx: Lecture, jour: date | None = None) -> str:
    """Le code de l'état de livraison du bon (« pas_envoye » tant qu'il n'est pas parti)."""
    f = ctx.fournisseurs[c.fournisseur_id]
    bon = BonALivrer(
        numero=c.numero,
        statut=str(c.statut),
        lignes=[LigneBon(x.id, float(x.quantite)) for x in c.lignes],
        eta=c.eta,
        date_livraison_prevue=c.date_livraison_prevue,
        date_commande=c.date_commande,
        delai_fournisseur=f.delai_jours,
    )
    libelle = statut_livraison(
        bon,
        ctx.recu,
        ctx.bloque,
        ctx.tolerance,
        jour=jour or horloge.aujourd_hui(),
        retard_tolere=ctx.retard_tolere,
    )
    code = LIVRAISONS.get(libelle, "pas_envoye")
    if code == "solde" and c.solde_origine == OrigineSolde.manuel:
        return "solde_main"
    return code


def renvoi(c: Commande, ctx: Lecture) -> Renvoi | None:
    """Le dernier renvoi de la direction, s'il n'a été suivi ni d'une soumission, ni d'une
    approbation, ni d'un envoi (R-CMD-23, lu dans `commande_decision`)."""
    if c.statut not in (StatutCommande.brouillon, StatutCommande.envoyee, StatutCommande.confirmee):
        return None
    dernier: CommandeDecision | None = None
    for d in ctx.decisions.get(c.id, []):
        if d.decision == DecisionCommande.renvoi:
            dernier = d
        elif d.decision in EFFACENT_LE_RENVOI:
            dernier = None
    if dernier is None or any(quand > dernier.quand for quand in ctx.envois.get(c.id, [])):
        return None
    return Renvoi(ctx.nom(dernier.par_id) or "", dernier.quand, dernier.motif)


def estime(c: Commande, ctx: Lecture) -> float:
    """Le montant estimé du bon dans sa devise."""
    return sum(
        float(x.quantite) * prix_estime(x, ctx.matieres[x.matiere_id], c.devise, ctx.taux)
        for x in c.lignes
    )


def cours(c: Commande, ctx: Lecture) -> float:
    """Le cours figé du bon, sinon celui du jour."""
    return float(c.cours) if c.cours else ctx.taux.get(c.devise, 1.0)


def approbation_requise(c: Commande, ctx: Lecture) -> bool:
    """Parti : il attend la direction ; pas parti : la règle de l'envoi (A-17)."""
    if c.numero:
        return c.statut == StatutCommande.a_approuver
    if c.statut in CLOS:
        return False
    en_mad = estime(c, ctx) * cours(c, ctx)
    return bool(ctx.seuil) and en_mad > ctx.seuil and c.approuvee_par_id is None


@dataclass
class LigneLue:
    """Une ligne du bon telle que la fiche la montre."""

    id: int
    matiere_id: int
    reference: str
    designation: str
    kg_par_ml: float
    unite_prix: str
    quantite: float
    unite_achat: str
    contenance: float
    unites: float
    metres: float | None
    prix: float
    prix_confirme: bool
    prix_catalogue: float
    devise_catalogue: str
    prix_estime: float
    montant: float
    montant_estime: float
    recu: float
    en_quarantaine: float
    reste: float
    reste_estime: float
    confirme_par: str | None
    confirme_le: datetime | None


def lignes(c: Commande, ctx: Lecture) -> list[LigneLue]:
    """Les lignes du bon : reçu net, quarantaine, reste (R-CMD-20), prix et montants."""
    resultat = []
    for x in c.lignes:
        m = ctx.matieres[x.matiere_id]
        quantite, recu = float(x.quantite), ctx.recu.get(x.id, 0.0)
        reste = 0.0 if c.statut in CLOS else max(0.0, quantite - recu)
        if reste <= quantite * ctx.tolerance:
            reste = 0.0
        prix = prix_estime(x, m, c.devise, ctx.taux)
        densite = float(m.densite)
        resultat.append(
            LigneLue(
                id=x.id,
                matiere_id=m.id,
                reference=m.reference,
                designation=m.designation,
                kg_par_ml=densite,
                unite_prix=str(m.unite_prix),
                quantite=quantite,
                unite_achat=x.unite_achat,
                contenance=float(x.contenance),
                unites=quantite / float(x.contenance) if x.contenance else quantite,
                metres=quantite / densite if densite else None,
                prix=float(x.prix),
                prix_confirme=x.prix_confirme,
                prix_catalogue=prix_catalogue_kg(m),
                devise_catalogue=m.devise,
                prix_estime=prix,
                montant=quantite * float(x.prix) if x.prix_confirme else 0.0,
                montant_estime=quantite * prix,
                recu=recu,
                en_quarantaine=ctx.bloque.get(x.id, 0.0),
                reste=reste,
                reste_estime=reste * prix,
                confirme_par=ctx.nom(x.confirme_par_id),
                confirme_le=x.confirme_le,
            )
        )
    return resultat
