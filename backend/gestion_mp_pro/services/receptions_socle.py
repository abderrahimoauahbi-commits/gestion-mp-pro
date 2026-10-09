"""Le socle des réceptions : lecture verrouillée, version, quarantaine, problème d'un bon,
dossier qui porte la réception, recalage d'un brouillon (`gestion_mp/api/receptions.py`,
REGLES § 3.1–3.5).

Le **recalage** d'un brouillon (reste à livrer et prix confirmé du moment) est calculé à la
lecture **sans rien écrire** (A.12-27) ; il s'écrit à la modification et à la validation. Les
autres modules du domaine (`receptions_saisie`, `receptions_blocages`, `receptions`,
`receptions_lecture`, `factures`) s'appuient sur celui-ci.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import flag_modified

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Dossier,
    DossierLigne,
    Magasin,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import (
    QualiteReception,
    StatutCommande,
    StatutDocument,
    StatutDossier,
    TypeMagasin,
)
from gestion_mp_pro.modeles.types import PRIX, QUANTITE, arrondir
from gestion_mp_pro.services import audit, numerotation, reglages
from gestion_mp_pro.services.chargeur.achats import recu_par_ligne
from gestion_mp_pro.services.commandes_socle import nom_commande

ZERO = Decimal(0)
QUALITES = {
    QualiteReception.conforme: "Conforme",
    QualiteReception.reserve: "Sous réserve",
    QualiteReception.refuse: "Refusé",
}
"""Les qualités d'une ligne et leurs libellés d'écran."""
STATUTS = {
    StatutDocument.brouillon: "Brouillon",
    StatutDocument.validee: "Validée",
    StatutDocument.annulee: "Annulée",
}
"""Les statuts d'une réception et leurs libellés."""
LOT_INTERNE = "LOT INTERNE"
"""L'ancienne écriture du lot interne dans Gestion MP (relue comme la case `lot_interne`)."""


def nom_reception(r: Reception) -> str:
    """Le numéro, sinon « brouillon n° 12 » (R-RCP-14)."""
    return r.numero or numerotation.libelle_brouillon(r.id)


def charger(s: Session, rid: int, *, verrou: bool = False) -> Reception:
    """La réception et ses lignes (404 « Réception introuvable. »), verrouillée pour un geste,
    relue en base (ce qui attend dans la session est d'abord écrit)."""
    s.flush()
    requete = (
        select(Reception)
        .where(Reception.id == rid)
        .options(selectinload(Reception.lignes))
        .execution_options(populate_existing=True)
    )
    if verrou:
        requete = requete.with_for_update(of=Reception)
    r = s.scalars(requete).first()
    if r is None:
        raise Refus.introuvable("Réception introuvable.")
    return r


def lignes_triees(r: Reception) -> list[ReceptionLigne]:
    """Les lignes dans l'ordre de leur saisie."""
    return sorted(r.lignes, key=lambda x: x.id or 0)


def verifier(s: Session, r: Reception, version: int) -> None:
    """409 `conflit_version` si la réception a changé depuis sa lecture."""
    audit.verifier_version(s, r, version, "Cette réception")


def toucher(r: Reception) -> None:
    """Marque la réception modifiée : sa `version` monte même si seules ses lignes changent."""
    flag_modified(r, "observations")


def quarantaine(s: Session) -> Magasin | None:
    """Le magasin de quarantaine : le premier en service, par id (R-RCP-21)."""
    requete = (
        select(Magasin)
        .where(Magasin.type == TypeMagasin.quarantaine, Magasin.actif.is_(True))
        .order_by(Magasin.id)
    )
    return s.scalars(requete).first()


Probleme = tuple[str, str]
"""(code de refus, phrase)."""


def probleme_du_bon(c: Commande, jour: date) -> Probleme | None:
    """Pourquoi une réception ne peut pas s'imputer à ce bon (`None` : elle le peut, R-RCP-09) :
    bon pas encore parti, annulé, ou parti après la date de la réception."""
    if not c.numero:
        return (
            "etat_incompatible",
            f"Le {nom_commande(c)} n'est pas encore parti chez le fournisseur : le marquer "
            "comme envoyé (il reçoit son numéro), ou recevoir hors commande.",
        )
    if c.statut == StatutCommande.annulee:
        return (
            "bon_clos",
            f"Le bon {nom_commande(c)} est annulé : le rouvrir, ou recevoir hors commande.",
        )
    if jour < c.date_commande:
        return (
            "date_invalide",
            f"La réception du {jour:%d/%m/%Y} précède l'envoi du bon {nom_commande(c)} "
            f"({c.date_commande:%d/%m/%Y}) : la date de l'une ou de l'autre est fausse.",
        )
    return None


def refuser(probleme: Probleme) -> Refus:
    """Le refus d'un problème (422 ou 409 selon son code)."""
    return Refus(probleme[0], probleme[1])


def dossier_de(s: Session, r: Reception) -> Dossier | None:
    """Le dossier d'importation (non annulé) qui porte une ligne de la réception."""
    if r.statut != StatutDocument.validee or not r.lignes:
        return None
    requete = (
        select(Dossier)
        .join(DossierLigne, DossierLigne.dossier_id == Dossier.id)
        .where(
            DossierLigne.reception_ligne_id.in_([x.id for x in r.lignes]),
            Dossier.statut != StatutDossier.annule,
        )
        .limit(1)
    )
    return s.scalars(requete).first()


def detacher_d_abord(d: Dossier, quoi: str) -> str:
    """Le vrai chemin quand une réception est dans un dossier : l'en détacher (ses frais
    restent au dossier), après l'avoir rouvert s'il est clos (X-RCP-22)."""
    rouvrir = "le rouvrir (c'est tracé), puis " if d.statut == StatutDossier.clos else ""
    return (
        f"Cette réception est dans le dossier d'importation {d.numero} : pour {quoi}, "
        f"{rouvrir}l'en détacher d'abord (dossier {d.numero} › Marchandises › « Détacher la "
        "réception ») — ses frais restent au dossier, et la marchandise y reviendra par sa "
        "facture."
    )


# ── Les bons d'une réception ─────────────────────────────────────────────────


@dataclass
class Bons:
    """Les lignes de bon nommées par des réceptions, leurs bons, et ce qu'elles ont reçu."""

    lignes: dict[int, CommandeLigne]
    commandes: dict[int, Commande]
    recu: dict[int, float]
    tolerance: float
    excedent: float

    def bon(self, commande_ligne_id: int) -> Commande:
        """Le bon d'une ligne de bon."""
        return self.commandes[self.lignes[commande_ligne_id].commande_id]


def bons(s: Session, receptions: Iterable[Reception]) -> Bons:
    """Les bons des lignes de ces réceptions, en trois requêtes (aucune par ligne)."""
    ids = {x.commande_ligne_id for r in receptions for x in r.lignes if x.commande_ligne_id}
    lignes = (
        {x.id: x for x in s.scalars(select(CommandeLigne).where(CommandeLigne.id.in_(ids)))}
        if ids
        else {}
    )
    cids = {x.commande_id for x in lignes.values()}
    commandes = (
        {c.id: c for c in s.scalars(select(Commande).where(Commande.id.in_(cids)))} if cids else {}
    )
    return Bons(
        lignes,
        commandes,
        recu_par_ligne(s) if ids else {},
        reglages.nombre(s, "toler_in_full"),
        reglages.nombre(s, "toler_excedent"),
    )


@dataclass(frozen=True)
class Recale:
    """Ce qu'une ligne de brouillon attend du moment, et le prix confirmé qui s'impose."""

    attendu: Decimal
    prix: Decimal | None


def recaler_ligne(x: ReceptionLigne, b: Bons) -> Recale | None:
    """Le reste à livrer du moment d'une ligne sur un bon (R-RCP-15) : commandé − reçu net,
    nul si le bon est soldé ou annulé ou si le reste est dans la tolérance ; le prix confirmé
    (non nul) du bon s'impose. `None` hors commande."""
    if x.commande_ligne_id is None or x.commande_ligne_id not in b.lignes:
        return None
    cl = b.lignes[x.commande_ligne_id]
    c = b.bon(x.commande_ligne_id)
    quantite = float(cl.quantite)
    reste = max(0.0, quantite - b.recu.get(cl.id, 0.0))
    if c.statut in (StatutCommande.soldee, StatutCommande.annulee) or (
        reste <= quantite * b.tolerance
    ):
        reste = 0.0
    prix = cl.prix if cl.prix_confirme and cl.prix else None
    return Recale(arrondir(reste, QUANTITE), arrondir(prix, PRIX) if prix is not None else None)


def recalage(r: Reception, b: Bons) -> dict[int, Recale]:
    """Le recalage d'un brouillon, ligne par ligne (vide pour une réception validée)."""
    if r.statut != StatutDocument.brouillon:
        return {}
    resultat: dict[int, Recale] = {}
    for x in r.lignes:
        recale = recaler_ligne(x, b)
        if recale is not None:
            resultat[x.id] = recale
    return resultat


def appliquer_recalage(r: Reception, b: Bons) -> None:
    """Écrit le recalage sur les lignes du brouillon (modification, validation)."""
    for x in r.lignes:
        recale = recaler_ligne(x, b) if r.statut == StatutDocument.brouillon else None
        if recale is None:
            continue
        x.quantite_attendue = recale.attendu
        if recale.prix is not None:
            x.prix = recale.prix


def commandes_de(r: Reception, b: Bons) -> set[int]:
    """Les bons touchés par une réception."""
    return {b.lignes[x.commande_ligne_id].commande_id for x in r.lignes if x.commande_ligne_id}


def verrouiller_bons(s: Session, r: Reception) -> None:
    """Les bons touchés puis leurs lignes, verrouillés dans l'ordre des id (pas d'étreinte entre
    deux postes), avant de lire ce qu'ils ont reçu : deux réceptions validées ensemble sur une
    même ligne passent l'une après l'autre, et la seconde voit la première (R-RCP-19)."""
    lignes = sorted({x.commande_ligne_id for x in r.lignes if x.commande_ligne_id})
    if not lignes:
        return
    cids = sorted(
        set(s.scalars(select(CommandeLigne.commande_id).where(CommandeLigne.id.in_(lignes))))
    )
    s.execute(
        select(Commande.id).where(Commande.id.in_(cids)).order_by(Commande.id).with_for_update()
    )
    s.execute(
        select(CommandeLigne.id)
        .where(CommandeLigne.id.in_(lignes))
        .order_by(CommandeLigne.id)
        .with_for_update()
    )
    s.execute(
        select(Commande).where(Commande.id.in_(cids)).execution_options(populate_existing=True)
    ).all()
