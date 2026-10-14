"""Le socle des dossiers : chargement verrouillé, version, contexte de lecture partagé, vue du
moteur, factures du dossier (`gestion_mp/api/importations.py`, REGLES § 4.1–4.3).

Un dossier porte **une ou plusieurs factures** (`dossier.factures`, décision de Mohamed du
12/10/2026 qui amende I3) ; `factures_vives` les donne dans l'ordre de leur ajout (la première
est celle d'ouverture). Un dossier annulé garde la trace des siennes, libérées.

Le **contexte** lit en un nombre fixe de requêtes ce que la fiche d'un ou de plusieurs dossiers
demande (postes, codes douaniers, matières, réceptions d'origine, bons, factures) : la liste des
dossiers ne fait aucune requête par dossier.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import flag_modified

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.modeles import (
    CodeDouanier,
    Commande,
    CommandeLigne,
    Composition,
    Dossier,
    DossierFacture,
    DossierFrais,
    DossierLigne,
    Facture,
    Fournisseur,
    Lot,
    Matiere,
    PosteFrais,
    Reception,
    ReceptionLigne,
    Titrage,
    TypeFil,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import (
    ObjetJournal,
    StatutDossier,
)
from gestion_mp_pro.services import audit
from gestion_mp_pro.services.chargeur.referentiels import parametres

DIRHAM = "MAD"
CENTIME = 0.005
"""En deçà, un écart de montant n'en est pas un (frais non répartis, avoir, TVA)."""
CLOS = "Ce dossier est clos : le rouvrir pour y toucher (c'est tracé)."
ANNULE = "Ce dossier est annulé : il ne se modifie plus."


def mad(montant: float | Decimal) -> str:
    """« 1 234,50 MAD » : un montant à la française dans les messages et le journal (I-15)."""
    texte = f"{float(montant):,.2f}".replace(",", " ").replace(".", ",")
    return f"{texte.replace('-', '−')} MAD"


def lignes_triees(d: Dossier) -> list[DossierLigne]:
    """Les marchandises dans l'ordre de leur saisie."""
    return sorted(d.lignes, key=lambda x: x.id or 0)


def frais_tries(d: Dossier) -> list[DossierFrais]:
    """Les frais dans l'ordre de leur saisie."""
    return sorted(d.frais, key=lambda x: x.id or 0)


def charger(s: Session, did: int, *, verrou: bool = False) -> Dossier:
    """Le dossier, ses marchandises, ses frais et leurs parts (404 sinon) ; verrouillé jusqu'à la
    fin de la transaction quand il va changer."""
    requete = (
        select(Dossier)
        .where(Dossier.id == did)
        .options(
            selectinload(Dossier.factures),
            selectinload(Dossier.lignes),
            selectinload(Dossier.frais).selectinload(DossierFrais.parts),
        )
        .execution_options(populate_existing=True)
    )
    if verrou:
        requete = requete.with_for_update(of=Dossier)
    d = s.scalars(requete).first()
    if d is None:
        raise Refus.introuvable("Dossier introuvable.")
    return d


def verifier(s: Session, d: Dossier, version: int) -> None:
    """409 `conflit_version` si le dossier a changé depuis sa lecture."""
    audit.verifier_version(s, d, version, "Ce dossier", feminin=False)


def refus_statut(d: Dossier) -> str | None:
    """Pourquoi un dossier ne se modifie pas : clos (le rouvrir) ou annulé."""
    if d.statut == StatutDossier.clos:
        return CLOS
    if d.statut == StatutDossier.annule:
        return ANNULE
    return None


def ouvert(s: Session, did: int, version: int | None) -> Dossier:
    """Le dossier verrouillé, à sa version (sauf un geste sur un frais, qui donne la sienne),
    ouvert (X-IMP-01, X-IMP-02)."""
    d = charger(s, did, verrou=True)
    if version is not None:
        verifier(s, d, version)
    refus = refus_statut(d)
    if refus:
        code = "dossier_clos" if d.statut == StatutDossier.clos else "etat_incompatible"
        raise Refus.etat(refus, code=code)
    return d


def toucher(d: Dossier) -> None:
    """Le dossier change (une marchandise, un frais, un cours) : sa `version` monte."""
    flag_modified(d, "libelle")


def noter(
    s: Session,
    qui: audit.Qui,
    d: Dossier,
    action: str,
    detail: str,
    *,
    avant: Mapping[str, object] | None = None,
    apres: Mapping[str, object] | None = None,
) -> None:
    """Une ligne au journal du dossier (son historique), et le dossier marqué changé : chaque
    geste écrit au journal, ce qui invalide aussi le cache du moteur (S4)."""
    toucher(d)
    audit.journal(
        s,
        qui,
        action,
        ObjetJournal.dossier,
        d.id,
        numero=d.numero,
        detail=detail,
        avant={k: audit.valeur_json(v) for k, v in avant.items()} if avant else None,
        apres={k: audit.valeur_json(v) for k, v in apres.items()} if apres else None,
    )
    s.flush()


def factures_vives(d: Dossier) -> list[DossierFacture]:
    """Les factures du dossier (non libérées), la première ajoutée d'abord."""
    vives = [x for x in d.factures if x.liberee_le is None]
    return sorted(vives, key=lambda x: (x.ajoutee_le, x.facture_id))


def factures_lues(d: Dossier) -> list[DossierFacture]:
    """Les factures que la fiche montre : les siennes ; celles qu'un dossier annulé a libérées."""
    return sorted(d.factures, key=lambda x: (x.ajoutee_le, x.facture_id))


def a_la_main(d: Dossier) -> bool:
    """Saisi à la main, sans facture ni marchandise reçue : un dossier d'avant la mise en
    service (un dossier ouvert depuis une facture ne le devient jamais, même vidé)."""
    return (
        d.saisi_a_la_main
        and not factures_vives(d)
        and not any(x.reception_ligne_id for x in d.lignes)
    )


def repris(d: Dossier) -> bool:
    """Sans facture du dossier mais avec des réceptions : un dossier repris de l'ERP Fil (B-11),
    dont les factures se lisent sur ses marchandises."""
    return d.saisi_a_la_main and any(x.reception_ligne_id for x in d.lignes)


# ── Le contexte de lecture ───────────────────────────────────────────────────


@dataclass(frozen=True)
class MatiereLue:
    """Ce que le dossier lit d'une matière : référence, famille de fil, code douanier."""

    reference: str
    famille: str
    code_douanier_id: int | None


@dataclass(frozen=True)
class Origine:
    """La réception d'une marchandise reçue, et sa facture."""

    reception_id: int
    reception: str
    facture_id: int | None
    date: dt.date
    fournisseur_id: int


@dataclass(frozen=True)
class BonFige:
    """Le bon d'une marchandise reçue, quand ses prix ont été confirmés à un cours figé."""

    cours: Decimal
    devise: str
    numero: str
    commande_id: int


@dataclass
class Contexte:
    """Ce que la lecture d'un ou de plusieurs dossiers partage (lu une fois)."""

    parametres: c.Parametres
    postes: dict[int, PosteFrais]
    codes: dict[int, CodeDouanier]
    fournisseurs: dict[int, Fournisseur]
    personnes: dict[int, str]
    matieres: dict[int, MatiereLue] = field(default_factory=dict)
    lots: dict[int, str] = field(default_factory=dict)
    origines: dict[int, Origine] = field(default_factory=dict)
    bons: dict[int, BonFige] = field(default_factory=dict)
    factures: dict[int, Facture] = field(default_factory=dict)

    def nom(self, fournisseur_id: int | None) -> str:
        """Le nom d'un fournisseur (vide s'il n'est pas dit)."""
        f = self.fournisseurs.get(fournisseur_id) if fournisseur_id else None
        return f.nom if f else ""


def famille(m: Matiere, compositions: dict[int, str], types: dict[int, str],
            titrages: dict[int, Titrage]) -> str:  # fmt: skip
    """« PP Frisé 2900 Dtex » : la matière, la façon, le titrage (son code, comme Gestion MP :
    « Plastique 45 », pas « Plastique 45 Cm ») — sans la couleur (M56)."""
    titrage = titrages.get(m.titrage_id) if m.titrage_id else None
    morceaux = [
        compositions.get(m.composition_id, "") if m.composition_id else "",
        types.get(m.type_fil_id, "").split(" (")[0] if m.type_fil_id else "",
        titrage.code if titrage else "",
    ]
    return " ".join(x for x in morceaux if x) or m.reference


def matieres(s: Session, ids: Iterable[int]) -> dict[int, MatiereLue]:
    """Les matières citées : référence, famille de fil, code douanier."""
    voulues = set(ids)
    if not voulues:
        return {}
    compositions = dict(s.execute(select(Composition.id, Composition.code)).all())
    types = dict(s.execute(select(TypeFil.id, TypeFil.libelle)).all())
    titrages = {x.id: x for x in s.scalars(select(Titrage))}
    return {
        m.id: MatiereLue(m.reference, famille(m, compositions, types, titrages), m.code_douanier_id)
        for m in s.scalars(select(Matiere).where(Matiere.id.in_(voulues)))
    }


def origines(s: Session, ids: Iterable[int]) -> dict[int, Origine]:
    """La réception (et la facture) de chaque ligne reçue citée."""
    voulues = set(ids)
    if not voulues:
        return {}
    requete = (
        select(ReceptionLigne.id, Reception)
        .join(Reception, Reception.id == ReceptionLigne.reception_id)
        .where(ReceptionLigne.id.in_(voulues))
    )
    return {
        lid: Origine(r.id, r.numero or "", r.facture_id, r.date, r.fournisseur_id)
        for lid, r in s.execute(requete)
    }


def bons(s: Session, ids: Iterable[int]) -> dict[int, BonFige]:
    """Le cours figé du bon de chaque ligne reçue citée (à la confirmation des prix)."""
    voulues = set(ids)
    if not voulues:
        return {}
    requete = (
        select(ReceptionLigne.id, Commande)
        .join(CommandeLigne, CommandeLigne.id == ReceptionLigne.commande_ligne_id)
        .join(Commande, Commande.id == CommandeLigne.commande_id)
        .where(ReceptionLigne.id.in_(voulues), Commande.cours.is_not(None))
    )
    return {
        lid: BonFige(b.cours, b.devise, b.numero or "", b.id)
        for lid, b in s.execute(requete)
        if b.cours is not None
    }


def contexte(s: Session, dossiers: Sequence[Dossier]) -> Contexte:
    """Le contexte de lecture de ces dossiers (un nombre fixe de requêtes)."""
    ctx = Contexte(
        parametres=parametres(s),
        postes={p.id: p for p in s.scalars(select(PosteFrais))},
        codes={x.id: x for x in s.scalars(select(CodeDouanier))},
        fournisseurs={f.id: f for f in s.scalars(select(Fournisseur))},
        personnes=dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).all()),
    )
    lignes = [x for d in dossiers for x in d.lignes]
    recues = [x.reception_ligne_id for x in lignes if x.reception_ligne_id]
    ctx.matieres = matieres(s, (x.matiere_id for x in lignes))
    lots = {x.lot_id for x in lignes if x.lot_id}
    if lots:
        ctx.lots = dict(s.execute(select(Lot.id, Lot.numero).where(Lot.id.in_(lots))).all())
    ctx.origines = origines(s, recues)
    ctx.bons = bons(s, recues)
    factures = {x.facture_id for d in dossiers for x in d.factures}
    factures |= {o.facture_id for o in ctx.origines.values() if o.facture_id}
    if factures:
        ctx.factures = {f.id: f for f in s.scalars(select(Facture).where(Facture.id.in_(factures)))}
    return ctx


def factures_moteur(d: Dossier, ctx: Contexte) -> list[c.FactureImport]:
    """Les factures du dossier pour le moteur, chacune avec les marchandises qu'elle a apportées
    (comme `services/chargeur/production._factures`)."""
    resultat = []
    for x in factures_vives(d):
        f = ctx.factures[x.facture_id]
        lignes = [
            y.id
            for y in lignes_triees(d)
            if y.reception_ligne_id
            and (o := ctx.origines.get(y.reception_ligne_id)) is not None
            and o.facture_id == f.id
        ]
        resultat.append(c.FactureImport(f.numero, float(f.montant or 0), f.devise, lignes))
    return resultat


def vue(d: Dossier, ctx: Contexte) -> c.DossierImport:
    """Le dossier tel que le moteur le calcule (comme `services/chargeur/production.dossiers`)."""
    return c.DossierImport(
        numero=d.numero,
        libelle=d.libelle,
        date_arrivee=d.date_arrivee,
        banque=d.banque,
        statut="Clos" if d.statut == StatutDossier.clos else "Ouvert",
        commentaire=d.commentaire,
        lignes=[
            c.LigneImport(
                id=x.id,
                reference=ctx.matieres[x.matiere_id].reference,
                quantite=float(x.quantite_kg),
                valeur_devise=float(x.valeur_devise),
                devise=x.devise,
                cours=float(x.cours or 0),
                lot_fournisseur=ctx.lots.get(x.lot_id, "") if x.lot_id else "",
                fournisseur=ctx.nom(x.fournisseur_id),
                ligne_reception_id=x.reception_ligne_id,
            )
            for x in lignes_triees(d)
        ],
        charges=[
            c.ChargeImport(
                poste=ctx.postes[x.poste_id].code,
                montant=float(x.montant),
                ligne=x.ligne_id,
                piece=x.piece,
                commentaire=x.commentaire,
                recuperable_poste=ctx.postes[x.poste_id].recuperable,
                cle=str(ctx.postes[x.poste_id].cle),
                parts={p.ligne_id: float(p.montant) for p in x.parts},
                nature=str(ctx.postes[x.poste_id].nature),
                entre_valeur_douane=ctx.postes[x.poste_id].entre_valeur_douane,
            )
            for x in frais_tries(d)
        ],
        factures=factures_moteur(d, ctx),
    )
