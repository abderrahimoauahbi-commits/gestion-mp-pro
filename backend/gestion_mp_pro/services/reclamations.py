"""Les réclamations aux fournisseurs (routes 181–186 ; `gestion_mp/api/suivi.py`, R20r ; A-10,
A-22, A-28 corrigés).

On réclame à un fournisseur **ce qu'il a livré** : sa réception validée, sa ligne (une ligne
refusée n'a pas de lot : la réclamation garde la ligne, sa référence et sa pesée, A-10), son lot ;
la quantité réclamée ne dépasse pas ce qui est arrivé ; jamais dans le futur ni avant la
réception. Le numéro `RCL-AAAA-NNNN` est donné à l'ouverture. Une réclamation close garde son
issue (A-22) : sa réponse et l'avoir obtenu se complètent sans la rouvrir ; changer d'issue se
fait en la rouvrant (avec un motif).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Devise,
    Fournisseur,
    Lot,
    Matiere,
    Reception,
    ReceptionLigne,
    Reclamation,
)
from gestion_mp_pro.modeles.enums import (
    IssueReclamation,
    MotifReclamation,
    QualiteReception,
    SerieNumero,
    StatutDocument,
    StatutReclamation,
)
from gestion_mp_pro.modeles.types import MONTANT, QUANTITE, arrondir
from gestion_mp_pro.services import audit, horloge, numerotation
from gestion_mp_pro.services.conversions import kg
from gestion_mp_pro.services.referentiels import ISSUES_RECLAMATION, MOTIFS_RECLAMATION

PRECISION = Decimal("0.0005")


def motif_de(valeur: str) -> MotifReclamation:
    """Le motif, par son code ou son libellé ; hors de la liste, refusé (A-22)."""
    for code, libelle in MOTIFS_RECLAMATION.items():
        if valeur in (code.value, libelle):
            return code
    raise Refus.saisie(
        f"Motif : {', '.join(MOTIFS_RECLAMATION.values())}.", champs={"motif": "hors liste"}
    )


def issue_de(valeur: str) -> IssueReclamation:
    """L'issue, par son code ou son libellé ; sinon la liste."""
    for code, libelle in ISSUES_RECLAMATION.items():
        if valeur in (code.value, libelle):
            return code
    raise Refus.saisie(
        f"Issue : {', '.join(ISSUES_RECLAMATION.values())}.", champs={"issue": "hors liste"}
    )


@dataclass(frozen=True)
class Ouverture:
    """Le corps de la route 183."""

    fournisseur_id: int
    motif: str
    reception_id: int | None = None
    reception_ligne_id: int | None = None
    lot_id: int | None = None
    description: str = ""
    quantite: Decimal = Decimal(0)
    montant_demande: Decimal = Decimal(0)
    devise: str = ""
    ouverte_le: dt.date | None = None


@dataclass
class _Visee:
    """Ce que la réclamation vise : réception, ligne, lot (vérifiés)."""

    reception: Reception | None = None
    ligne: ReceptionLigne | None = None
    lot: Lot | None = None
    references: dict[int, str] = field(default_factory=dict)


def _ligne(s: Session, e: Ouverture) -> tuple[ReceptionLigne | None, int | None, int | None]:
    """La ligne en cause dit sa réception, et son lot quand elle en a un."""
    if e.reception_ligne_id is None:
        return None, e.reception_id, e.lot_id
    ligne = s.get(ReceptionLigne, e.reception_ligne_id)
    if ligne is None:
        raise Refus.saisie("Ligne de réception inconnue.", code="valeur_inconnue")
    if e.reception_id is not None and ligne.reception_id != e.reception_id:
        raise Refus.saisie("Cette ligne n'est pas dans la réception choisie.")
    if e.lot_id is not None and ligne.lot_id != e.lot_id:
        raise Refus.saisie("Le lot choisi n'est pas celui de cette ligne.")
    return ligne, ligne.reception_id, ligne.lot_id


def _reception(s: Session, f: Fournisseur, rid: int | None) -> Reception | None:
    """La réception visée : du fournisseur, validée."""
    if rid is None:
        return None
    r = s.get(Reception, rid)
    if r is None:
        raise Refus.saisie("Réception inconnue.", code="valeur_inconnue")
    nom = r.numero or numerotation.libelle_brouillon(r.id)
    if r.fournisseur_id != f.id:
        autre = s.get(Fournisseur, r.fournisseur_id)
        raise Refus.saisie(
            f"La réception {nom} est de {autre.nom if autre else '?'}, pas de {f.nom}."
        )
    if r.statut != StatutDocument.validee:
        etat = (
            "n'est pas encore validée." if r.statut == StatutDocument.brouillon else "est annulée."
        )
        raise Refus.etat(f"On réclame sur ce que le fournisseur a livré : cette réception {etat}")
    return r


def _lot(s: Session, f: Fournisseur, lot_id: int | None, r: Reception | None) -> Lot | None:
    """Le lot visé : livré par ce fournisseur, et dans la réception si elle est nommée."""
    if lot_id is None:
        return None
    lot = s.get(Lot, lot_id)
    if lot is None:
        raise Refus.saisie("Lot inconnu.", code="valeur_inconnue")
    livre_par = set(
        s.scalars(
            select(Reception.fournisseur_id)
            .join(ReceptionLigne, ReceptionLigne.reception_id == Reception.id)
            .where(ReceptionLigne.lot_id == lot.id)
        )
    )
    if lot.fournisseur_id is not None:
        livre_par.add(lot.fournisseur_id)
    if livre_par and f.id not in livre_par:
        raise Refus.saisie(f"Le lot {lot.numero} n'a pas été livré par {f.nom}.")
    if r is not None:
        dans = s.scalar(
            select(func.count()).where(
                ReceptionLigne.reception_id == r.id, ReceptionLigne.lot_id == lot.id
            )
        )
        if not dans:
            raise Refus.saisie(f"Le lot {lot.numero} n'est pas dans la réception {r.numero}.")
    return lot


def _livre(s: Session, v: _Visee) -> tuple[Decimal, str]:
    """Ce qui est arrivé, et où : la ligne, la réception (ou son lot), sinon le lot."""
    if v.ligne is not None and v.reception is not None:
        ref = s.scalar(select(Matiere.reference).where(Matiere.id == v.ligne.matiere_id))
        return v.ligne.quantite_pesee, f"la ligne « {ref} » de la réception {v.reception.numero}"
    if v.reception is not None:
        requete = select(func.coalesce(func.sum(ReceptionLigne.quantite_pesee), 0)).where(
            ReceptionLigne.reception_id == v.reception.id,
            ReceptionLigne.qualite != QualiteReception.refuse,
        )
        if v.lot is not None:
            requete = requete.where(ReceptionLigne.lot_id == v.lot.id)
        return Decimal(s.scalar(requete) or 0), f"la réception {v.reception.numero}"
    lot_id, numero = (v.lot.id, v.lot.numero) if v.lot is not None else (0, "")
    requete = (
        select(func.coalesce(func.sum(ReceptionLigne.quantite_pesee), 0))
        .join(Reception, Reception.id == ReceptionLigne.reception_id)
        .where(ReceptionLigne.lot_id == lot_id, Reception.statut == StatutDocument.validee)
    )
    return Decimal(s.scalar(requete) or 0), f"le lot {numero}"


def _dates(e: Ouverture, r: Reception | None) -> dt.date:
    """Le jour d'ouverture : pas dans le futur, pas avant la réception visée."""
    jour = e.ouverte_le or horloge.aujourd_hui()
    if jour > horloge.aujourd_hui():
        raise Refus.saisie("Une réclamation ne s'ouvre pas dans le futur.", code="date_future")
    if r is not None and jour < r.date:
        raise Refus.saisie(
            f"Une réclamation ne précède pas la réception qu'elle vise ({r.date:%d/%m/%Y}).",
            code="date_invalide",
        )
    return jour


def ouvrir(s: Session, qui: audit.Qui, e: Ouverture) -> Reclamation:
    """Route 183 : une réclamation ouverte, numérotée tout de suite."""
    f = s.get(Fournisseur, e.fournisseur_id)
    if f is None:
        raise Refus.saisie("Fournisseur inconnu.", code="valeur_inconnue")
    motif = motif_de(e.motif)
    ligne, rid, lot_id = _ligne(s, e)
    v = _Visee(ligne=ligne)
    v.reception = _reception(s, f, rid)
    v.lot = _lot(s, f, lot_id, v.reception)
    if e.quantite and (v.reception is not None or v.lot is not None):
        livre, ou = _livre(s, v)
        if e.quantite > livre + PRECISION:
            raise Refus.saisie(
                f"{kg(e.quantite, 1)} kg réclamés pour {kg(livre, 1)} kg livrés par {ou}.",
                code="quantite_invalide",
            )
    devise = (e.devise or (v.reception.devise if v.reception else f.devise) or "MAD").upper()
    if s.get(Devise, devise) is None:
        raise Refus.saisie(f"Devise inconnue : {devise}.", code="valeur_inconnue")
    jour = _dates(e, v.reception)
    r = Reclamation(
        numero=numerotation.numero(s, SerieNumero.RCL, jour),
        fournisseur_id=f.id,
        reception_id=v.reception.id if v.reception else None,
        reception_ligne_id=ligne.id if ligne else None,
        lot_id=v.lot.id if v.lot else None,
        motif=motif,
        description=e.description,
        quantite=arrondir(e.quantite, QUANTITE),
        montant_demande=arrondir(e.montant_demande, MONTANT),
        devise=devise,
        ouverte_le=jour,
        cree_par_id=qui.id,
    )
    s.add(r)
    audit.creation(s, qui, "réclamation ouverte", r, numero=r.numero,
                   detail=f"{r.numero} · {MOTIFS_RECLAMATION[motif]}")  # fmt: skip
    return r


# ── Suivi ─────────────────────────────────────────────────────────────────────


def charger(s: Session, rid: int, version: int | None = None) -> Reclamation:
    """La réclamation verrouillée (404 « Réclamation introuvable. »), à sa version."""
    s.flush()
    r = s.scalars(
        select(Reclamation)
        .where(Reclamation.id == rid)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if r is None:
        raise Refus.introuvable("Réclamation introuvable.")
    if version is not None:
        audit.verifier_version(s, r, version, "Cette réclamation")
    return r


def completer(
    s: Session, qui: audit.Qui, rid: int, version: int, valeurs: dict[str, object]
) -> Reclamation:
    """Route 184 : réponse, description, montant obtenu (champ absent = inchangé). Une close se
    complète sans se rouvrir (l'avoir arrive après) : son issue ne change pas."""
    r = charger(s, rid, version)
    with audit.suivre(s, qui, "réclamation complétée", r, numero=r.numero, detail=r.numero):
        if isinstance(valeurs.get("reponse"), str):
            r.reponse = str(valeurs["reponse"])
        if isinstance(valeurs.get("description"), str):
            r.description = str(valeurs["description"])
        montant = valeurs.get("montant_obtenu")
        if isinstance(montant, Decimal):
            r.montant_obtenu = arrondir(montant, MONTANT)
        s.flush()
    return r


def clore(
    s: Session,
    qui: audit.Qui,
    rid: int,
    *,
    version: int,
    issue: str,
    montant_obtenu: Decimal | None = None,
    close_le: dt.date | None = None,
    reponse: str | None = None,
) -> Reclamation:
    """Route 185 : clore avec son issue ; une close garde la sienne (A-22)."""
    r = charger(s, rid, version)
    if r.statut == StatutReclamation.close:
        actuelle = ISSUES_RECLAMATION[IssueReclamation(r.issue)] if r.issue else ""
        raise Refus.etat(
            f"Cette réclamation est close avec l'issue « {actuelle} » : elle la garde. "
            "La rouvrir pour changer d'issue."
        )
    if not issue.strip():
        raise Refus.saisie(
            "Pour clore, dire comment elle s'est terminée (avoir, remplacement, refusée…).",
            champs={"issue": "issue obligatoire"},
        )
    fin = close_le or horloge.aujourd_hui()
    if fin > horloge.aujourd_hui():
        raise Refus.saisie("Une réclamation ne se clôt pas dans le futur.", code="date_future")
    if fin < r.ouverte_le:
        raise Refus.saisie(
            f"Une réclamation ne se clôt pas avant son ouverture ({r.ouverte_le:%d/%m/%Y}).",
            code="date_invalide",
        )
    code = issue_de(issue.strip())
    with audit.suivre(s, qui, "réclamation close", r, numero=r.numero,
                      detail=f"{r.numero} · {ISSUES_RECLAMATION[code]}"):  # fmt: skip
        r.statut, r.issue, r.close_le = StatutReclamation.close, code, fin
        if montant_obtenu is not None:
            r.montant_obtenu = arrondir(montant_obtenu, MONTANT)
        if reponse is not None:
            r.reponse = reponse
        s.flush()
    return r


def rouvrir(s: Session, qui: audit.Qui, rid: int, version: int, motif: str) -> Reclamation:
    """Route 186 : on attend de nouveau le fournisseur ; l'issue passée reste au journal."""
    r = charger(s, rid, version)
    if r.statut == StatutReclamation.ouverte:
        raise Refus.etat("Cette réclamation est déjà ouverte.")
    with audit.suivre(s, qui, "réclamation rouverte", r, numero=r.numero,
                      detail=f"{r.numero} · {motif.strip()}"):  # fmt: skip
        r.statut, r.close_le, r.issue = StatutReclamation.ouverte, None, None
        s.flush()
    return r
