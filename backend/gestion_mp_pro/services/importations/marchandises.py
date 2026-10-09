"""Les marchandises d'un dossier : saisie à la main (route 193), cours et observations
(194), retrait (195), un cours pour toute une devise (196), le cours des bons (197),
détachement d'une réception (198) — REGLES R-IMP-31 à R-IMP-40.

Le cours d'une marchandise dit d'où il vient (`cours_origine`) : `bon` (cours figé à la
confirmation des prix), `banque` (cours payé, saisi), `saisi` (dossier d'avant la mise en
service) ; sans cours (`NULL`), elle vaut le cours du jour jusqu'à la clôture.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Devise,
    Dossier,
    DossierLigne,
    Facture,
    Fournisseur,
    Lot,
    Matiere,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import OrigineCours, StatutDocument
from gestion_mp_pro.services import audit, horloge, lots, periode
from gestion_mp_pro.services.importations.parties import refus_saisie
from gestion_mp_pro.services.importations.socle import (
    DIRHAM,
    bons,
    mad,
    noter,
    ouvert,
)


@dataclass(frozen=True)
class LigneManuelle:
    """Une marchandise d'un dossier d'avant la mise en service (route 193)."""

    matiere_id: int
    quantite_kg: Decimal
    valeur_devise: Decimal
    lot_numero: str = ""
    fournisseur_id: int | None = None
    devise: str = DIRHAM
    cours: Decimal | None = None
    commentaire: str = ""


def _matiere(s: Session, matiere_id: int) -> Matiere:
    """La matière saisie (422 si elle n'existe pas)."""
    m = s.get(Matiere, matiere_id)
    if m is None:
        raise Refus.saisie("Matière inconnue.", code="valeur_inconnue")
    return m


def _lot_pas_recu(s: Session, m: Matiere, numero: str) -> None:
    """Un lot déjà reçu a son coût par sa réception (X-IMP-21, R-IMP-32)."""
    requete = (
        select(Reception.numero)
        .join(ReceptionLigne, ReceptionLigne.reception_id == Reception.id)
        .join(Lot, Lot.id == ReceptionLigne.lot_id)
        .where(
            Lot.matiere_id == m.id,
            Lot.numero == numero,
            Reception.statut == StatutDocument.validee,
        )
        .limit(1)
    )
    recu = s.scalar(requete)
    if recu:
        raise Refus.etat(
            f"Le lot « {numero} » de {m.reference} est arrivé par la réception {recu} : son coût "
            "vient du dossier de sa facture. La saisie à la main ne vaut que pour un lot d'avant "
            "la mise en service."
        )


def _devise_et_fournisseur(s: Session, e: LigneManuelle, m: Matiere) -> tuple[str, int | None]:
    """La devise (connue) et le fournisseur (connu, à défaut celui de la matière)."""
    devise = e.devise.strip().upper() or DIRHAM
    if s.get(Devise, devise) is None:
        raise Refus.saisie(f"Devise inconnue : « {devise} ».", code="valeur_inconnue")
    if e.fournisseur_id is not None and s.get(Fournisseur, e.fournisseur_id) is None:
        raise Refus.saisie("Fournisseur inconnu.", code="valeur_inconnue")
    return devise, e.fournisseur_id or m.fournisseur_id


def saisir(s: Session, qui: audit.Qui, did: int, version: int, e: LigneManuelle) -> Dossier:
    """Une marchandise saisie à la main, comme un stock d'ouverture (R-IMP-31 à 33)."""
    d = ouvert(s, did, version)
    facture = s.get(Facture, d.facture_id) if d.facture_id else None
    refus = refus_saisie(d, facture.numero if facture else None)
    if refus:
        raise Refus.etat(refus)
    m = _matiere(s, e.matiere_id)
    numero = e.lot_numero.strip()
    if numero:
        _lot_pas_recu(s, m, numero)
    devise, fournisseur_id = _devise_et_fournisseur(s, e, m)
    lot = None
    if numero:
        entree = d.date_arrivee or horloge.aujourd_hui()
        lot = lots.lot_ou_creer(s, m.id, numero, entree, fournisseur_id=fournisseur_id)
    periode.cout_hors_periode_close(
        s, d, "marchandise saisie à la main", [lot.entre_le] if lot else []
    )
    cours = e.cours if devise != DIRHAM else None
    d.lignes.append(
        DossierLigne(
            matiere_id=m.id,
            lot_id=lot.id if lot else None,
            fournisseur_id=fournisseur_id,
            quantite_kg=e.quantite_kg,
            valeur_devise=e.valeur_devise,
            devise=devise,
            cours=cours,
            cours_origine=OrigineCours.saisi if cours else None,
            commentaire=e.commentaire.strip(),
        )
    )
    s.flush()
    detail = f"{d.numero} · {m.reference}" + (f" · lot {lot.numero}" if lot else "")
    noter(s, qui, d, "marchandise saisie à la main", detail)
    return d


def _ligne(d: Dossier, lid: int) -> DossierLigne:
    """La marchandise du dossier (404 sinon, X-IMP-24)."""
    x = next((y for y in d.lignes if y.id == lid), None)
    if x is None:
        raise Refus.introuvable("Marchandise introuvable dans ce dossier.")
    return x


def _reference(s: Session, x: DossierLigne) -> str:
    """La référence de la matière d'une marchandise."""
    return s.scalar(select(Matiere.reference).where(Matiere.id == x.matiere_id)) or ""


def _cours_lisible(cours: Decimal | None) -> str:
    """« 10.95 » ou « cours du jour »."""
    return f"{cours:g}" if cours is not None else "cours du jour"


@dataclass(frozen=True)
class LigneModifiee:
    """Le corps de la route 194 : un champ absent ne change pas (`cours_donne`)."""

    version: int
    cours_donne: bool = False
    cours: Decimal | None = None
    commentaire: str | None = None


def modifier(s: Session, qui: audit.Qui, did: int, lid: int, e: LigneModifiee) -> Dossier:
    """Le cours payé à la banque d'une marchandise (vide : le cours du jour), et ses
    observations (R-IMP-35)."""
    d = ouvert(s, did, e.version)
    x = _ligne(d, lid)
    reference = _reference(s, x)
    if e.cours_donne:
        if x.devise == DIRHAM and e.cours is not None:
            raise Refus.saisie("Une marchandise facturée en MAD n'a pas de cours.")
        if e.cours != x.cours:
            periode.cout_hors_periode_close(s, d, "cours")
            avant = {"cours": x.cours}
            x.cours = e.cours
            x.cours_origine = OrigineCours.banque if e.cours is not None else None
            detail = f"{d.numero} · {reference} · {_cours_lisible(e.cours)}"
            noter(s, qui, d, "cours", detail, avant=avant, apres={"cours": x.cours})
    if e.commentaire is not None and e.commentaire.strip() != x.commentaire:
        avant_texte, x.commentaire = x.commentaire, e.commentaire.strip()
        noter(
            s,
            qui,
            d,
            "commentaire marchandise",
            f"{d.numero} · {reference}",
            avant={"commentaire": avant_texte},
            apres={"commentaire": x.commentaire},
        )
    return d


def cours_devise(
    s: Session, qui: audit.Qui, did: int, version: int, *, devise: str, cours: Decimal | None
) -> Dossier:
    """Un seul cours pour toutes les marchandises du dossier dans une devise (R-IMP-36)."""
    d = ouvert(s, did, version)
    devises = sorted({x.devise for x in d.lignes if x.devise != DIRHAM})
    voulue = devise.strip().upper() or (devises[0] if len(devises) == 1 else "")
    if not voulue:
        raise Refus.saisie(
            f"Le dossier mêle {', '.join(devises)} : donner le cours de chaque devise à part."
            if devises
            else "Aucune marchandise en devise dans ce dossier."
        )
    if voulue not in devises:
        raise Refus.saisie(f"Aucune marchandise en {voulue} dans ce dossier.")
    periode.cout_hors_periode_close(s, d, "cours")
    for x in d.lignes:
        if x.devise == voulue:
            x.cours = cours
            x.cours_origine = OrigineCours.banque if cours is not None else None
    noter(s, qui, d, "cours", f"{d.numero} · {voulue} à {_cours_lisible(cours)}")
    return d


def cours_des_bons(s: Session, qui: audit.Qui, did: int, version: int) -> Dossier:
    """Remet sur chaque marchandise le cours figé de son bon (R-IMP-37)."""
    d = ouvert(s, did, version)
    periode.cout_hors_periode_close(s, d, "cours")
    figes = bons(s, (x.reception_ligne_id for x in d.lignes if x.reception_ligne_id))
    n = 0
    for x in d.lignes:
        bon = figes.get(x.reception_ligne_id) if x.reception_ligne_id else None
        if bon and bon.devise == x.devise and x.devise != DIRHAM:
            x.cours, x.cours_origine = bon.cours, OrigineCours.bon
            n += 1
    if not n:
        raise Refus.saisie("Aucune ligne de ce dossier ne vient d'un bon au cours figé.")
    noter(s, qui, d, "cours", f"{d.numero} · cours des bons sur {n} ligne(s)")
    return d


def _sans_parts_sur(d: Dossier, sortantes: set[int]) -> None:
    """Un frais à répartition figée qui avait une part sur une marchandise sortante la perd
    tout entière : il se répartit de nouveau à la clé de son poste (R-IMP-40)."""
    for frais in d.frais:
        if any(p.ligne_id in sortantes for p in frais.parts):
            frais.parts.clear()


def retirer(s: Session, qui: audit.Qui, did: int, lid: int, version: int) -> Dossier:
    """Retire une marchandise saisie à la main (R-IMP-38)."""
    d = ouvert(s, did, version)
    x = _ligne(d, lid)
    if x.reception_ligne_id:
        numero = s.scalar(
            select(Reception.numero)
            .join(ReceptionLigne, ReceptionLigne.reception_id == Reception.id)
            .where(ReceptionLigne.id == x.reception_ligne_id)
        )
        raise Refus.etat(
            "Une marchandise reçue ne sort pas seule du dossier : elle sort avec toute sa "
            f"réception {numero} (« Détacher la réception »), et les frais restent au dossier."
        )
    lies = [f for f in d.frais if f.ligne_id == x.id]
    if lies:
        raise Refus.etat(
            f"{len(lies)} frais porte(nt) sur cette seule marchandise : les affecter à tout le "
            "dossier, ou les retirer, avant de la retirer."
        )
    periode.cout_hors_periode_close(s, d, "retrait d'une marchandise")
    reference = _reference(s, x)
    _sans_parts_sur(d, {x.id})
    s.flush()
    d.lignes.remove(x)
    s.flush()
    noter(s, qui, d, "marchandise retirée", f"{d.numero} · {reference}")
    return d


def detacher(s: Session, qui: audit.Qui, did: int, version: int, reception_id: int) -> Dossier:
    """Détache toute une réception du dossier : sa marchandise attend de nouveau son dossier,
    les frais restent ici (R-IMP-39, 40)."""
    d = ouvert(s, did, version)
    r = s.get(Reception, reception_id)
    if r is None:
        raise Refus.introuvable("Réception inconnue.")
    ids = set(s.scalars(select(ReceptionLigne.id).where(ReceptionLigne.reception_id == r.id)))
    sortantes = [x for x in d.lignes if x.reception_ligne_id in ids]
    if not sortantes:
        raise Refus.introuvable(f"La réception {r.numero} n'est pas dans le dossier {d.numero}.")
    sortants = {x.id for x in sortantes}
    lies = [f for f in d.frais if f.ligne_id in sortants]
    if lies:
        raise Refus.etat(
            f"{len(lies)} frais porte(nt) sur une marchandise de la réception {r.numero} : les "
            "affecter à tout le dossier (onglet Frais, « Porte sur ») avant de la détacher — "
            "sinon ils sortiraient avec elle."
        )
    periode.cout_hors_periode_close(s, d, "détachement d'une réception")
    _sans_parts_sur(d, sortants)
    s.flush()
    for x in sortantes:
        d.lignes.remove(x)
    s.flush()
    total = sum((f.montant for f in d.frais), Decimal(0))
    detail = (
        f"{d.numero} · {r.numero} · {len(sortantes)} ligne(s) · {len(d.frais)} frais gardés "
        f"({mad(total)})"
    )
    noter(s, qui, d, "réception détachée", detail)
    return d
