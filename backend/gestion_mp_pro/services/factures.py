"""Les factures des fournisseurs : saisies avec la réception, complétées après coup, réglées
(REGLES § 3.3, 3.9 ; A-04, A-21, A-28 corrigés).

- Avec la réception (brouillon) : une facture nouvelle se crée ; une facture déjà connue
  s'**attache** seulement si elle est engagée — réglée, portée par une autre réception (le
  second camion d'une facture) ou par un dossier d'importation : elle ne se réécrit pas en
  silence (A-04) ; celle que seule cette réception porte se complète (un champ vide n'efface
  rien).
- Après la validation (route 174) : champ absent = inchangé, `numero: ""` détache ; une facture
  réglée ne change plus (annuler d'abord le règlement), ni une facture d'un dossier clos ; d'un
  dossier ouvert, le coût d'un mois clos ne bouge pas.
- Une facture n'a qu'une devise, celle de sa réception. **Un dossier d'importation = une facture
  = une livraison** (décision I3) : le lot D7 s'appuie sur ces factures (une par dossier).
- Le règlement (route 229 du lot D8) : jamais dans le futur ni dans une période close, jamais
  avant la pièce ; l'annuler est une décision de la direction, avec son motif (A-21, B-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Dossier, Facture, Fournisseur, Reception
from gestion_mp_pro.modeles.enums import Role, StatutDocument, StatutDossier
from gestion_mp_pro.modeles.types import MONTANT, arrondir
from gestion_mp_pro.services import audit, horloge, periode
from gestion_mp_pro.services.conversions import kg as nombre_fr
from gestion_mp_pro.services.receptions_saisie import FactureSaisie

MOTIF_MIN = 3


# ── Ce qui engage une facture ────────────────────────────────────────────────


def porteur(s: Session, facture_id: int) -> Dossier | None:
    """Le dossier d'importation (non annulé) qui porte la facture."""
    requete = select(Dossier).where(
        Dossier.facture_id == facture_id, Dossier.statut != StatutDossier.annule
    )
    return s.scalars(requete.limit(1)).first()


def autres_receptions(s: Session, facture_id: int, reception_id: int | None) -> int:
    """Combien d'autres réceptions (non annulées) portent la facture."""
    requete = (
        select(func.count())
        .select_from(Reception)
        .where(
            Reception.facture_id == facture_id,
            Reception.statut != StatutDocument.annulee,
            Reception.id != (reception_id or 0),
        )
    )
    return int(s.scalar(requete) or 0)


def engagee(s: Session, f: Facture, reception_id: int | None) -> str:
    """Pourquoi une facture ne se réécrit pas depuis la saisie d'une réception (vide : elle le
    peut) : réglée, portée par une autre réception, ou par un dossier d'importation."""
    if f.payee_le is not None:
        return f"La facture {f.numero} est réglée le {f.payee_le:%d/%m/%Y}"
    autres = autres_receptions(s, f.id, reception_id)
    if autres:
        return f"La facture {f.numero} porte déjà {autres} autre(s) réception(s)"
    dossier = porteur(s, f.id)
    if dossier is not None:
        return f"La facture {f.numero} est portée par le dossier d'importation {dossier.numero}"
    return ""


def _date_de_facture(jour: date | None) -> None:
    """Une facture ne se date pas dans le futur (la date de facture a son plafond, anom. 4.16)."""
    if jour is not None and jour > horloge.aujourd_hui():
        raise Refus.saisie(
            f"Une facture ne se date pas dans le futur ({jour:%d/%m/%Y}).",
            code="date_future",
            champs={"date": "date dans le futur"},
        )


def _echeance_apres(jour: date | None, echeance: date | None) -> None:
    """L'échéance ne précède pas la date de la facture (X-RCP-25)."""
    if echeance is not None and jour is not None and echeance < jour:
        raise Refus.saisie(
            "L'échéance ne précède pas la date de la facture.",
            code="date_invalide",
            champs={"echeance": "avant la date de la facture"},
        )


def echeance_proposee(jour: date | None, delai: int) -> date | None:
    """La date de la facture plus le délai de paiement du fournisseur (s'il est réglé)."""
    if jour is None or not delai:
        return None
    return jour + timedelta(days=int(delai))


def chercher(s: Session, fournisseur_id: int, numero: str) -> Facture | None:
    """La facture (fournisseur, numéro), verrouillée."""
    requete = (
        select(Facture)
        .where(Facture.fournisseur_id == fournisseur_id, Facture.numero == numero)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return s.scalars(requete).first()


def _devise_unique(f: Facture, devise: str) -> None:
    """Une facture n'a qu'une devise : celle de la réception (X-RCP-03)."""
    if f.devise != devise:
        raise Refus.saisie(
            f"La facture {f.numero} est en {f.devise} ; cette réception est en {devise}. Une "
            "facture n'a qu'une devise : saisir la facture de cette devise.",
            code="devise_incompatible",
        )


# ── Avec la saisie de la réception ───────────────────────────────────────────


def attacher(
    s: Session,
    qui: audit.Qui,
    *,
    f: Fournisseur,
    e: FactureSaisie | None,
    devise: str,
    reception_id: int | None,
) -> int | None:
    """La facture saisie avec un brouillon : créée, complétée, ou seulement attachée si elle
    est engagée (A-04). Sans numéro, pas de facture (R-RCP-10)."""
    if e is None or not e.numero.strip():
        return None
    numero = e.numero.strip()
    _date_de_facture(e.date)
    _echeance_apres(e.date, e.echeance)
    facture = chercher(s, f.id, numero)
    if facture is None:
        facture = Facture(fournisseur_id=f.id, numero=numero, devise=devise)
        s.add(facture)
    else:
        _devise_unique(facture, devise)
        if engagee(s, facture, reception_id):
            return facture.id
    nouvelle = facture.id is None
    avant = {} if nouvelle else audit.photo(facture)
    date_changee = e.date is not None and e.date != facture.date
    if e.date is not None:
        facture.date = e.date
    if e.montant is not None:
        facture.montant = arrondir(e.montant, MONTANT)
    if e.echeance is not None:
        facture.echeance = e.echeance
    elif facture.echeance is None or date_changee:
        facture.echeance = echeance_proposee(facture.date, f.delai_paiement_jours) or (
            facture.echeance
        )
    _echeance_apres(facture.date, facture.echeance)
    s.flush()
    a, b = audit.differences(avant, audit.photo(facture))
    if a or b:
        action = "facture créée" if nouvelle else "facture complétée"
        audit.journal(s, qui, action, "facture", facture.id, numero=numero, avant=a, apres=b)
    return facture.id


# ── Après la validation (route 174) ──────────────────────────────────────────


@dataclass(frozen=True)
class Correction:
    """La facture d'une réception validée : seuls les champs envoyés comptent."""

    version: int
    valeurs: dict[str, object]


def preparer_cible(s: Session, r: Reception, actuelle: Facture | None, envoye: object) -> Facture:
    """La facture visée : celle nommée (retrouvée ou créée), sinon l'actuelle."""
    numero = envoye.strip() if isinstance(envoye, str) else ""
    if numero and (actuelle is None or numero != actuelle.numero):
        trouvee = chercher(s, r.fournisseur_id, numero)
        if trouvee is None:
            trouvee = Facture(fournisseur_id=r.fournisseur_id, numero=numero, devise=r.devise)
            s.add(trouvee)
        _devise_unique(trouvee, r.devise)
        return trouvee
    if actuelle is None:
        raise Refus.saisie(
            "Cette réception n'a pas encore de facture : saisir d'abord son numéro.",
            champs={"numero": "numéro de facture manquant"},
        )
    return actuelle


def _valeur(c: Correction, cle: str, defaut: object) -> object:
    """La valeur envoyée, sinon celle de la facture (champ absent = inchangé)."""
    return c.valeurs[cle] if cle in c.valeurs else defaut


def _jour(valeur: object) -> date | None:
    """Une date envoyée (ou rien)."""
    return valeur if isinstance(valeur, date) else None


def _nouvelles_valeurs(
    c: Correction, f: Facture, delai: int
) -> tuple[date | None, Decimal | None, date | None]:
    """Date, montant et échéance après correction ; l'échéance proposée suit la date."""
    jour = _jour(_valeur(c, "date", f.date))
    brut = _valeur(c, "montant", f.montant)
    montant = brut if isinstance(brut, Decimal) else None
    if "echeance" in c.valeurs:
        echeance = _jour(c.valeurs["echeance"])
    elif f.echeance is None or jour != f.date:
        echeance = echeance_proposee(jour, delai) or (f.echeance if jour == f.date else None)
    else:
        echeance = f.echeance
    if jour != f.date:
        _date_de_facture(jour)
    _echeance_apres(jour, echeance)
    return jour, arrondir(montant, MONTANT) if montant is not None else None, echeance


def _garde_fous(s: Session, f: Facture) -> None:
    """Une facture réglée ou portée par un dossier clos ne change plus ; d'un dossier ouvert,
    le coût d'un mois clos ne bouge pas (A-04)."""
    if f.payee_le is not None:
        raise Refus.etat(
            f"La facture {f.numero} est réglée le {f.payee_le:%d/%m/%Y} : annuler d'abord le "
            "règlement (Analyse › Échéancier), puis la corriger."
        )
    if f.id is None:
        return
    dossier = porteur(s, f.id)
    if dossier is None:
        return
    if dossier.statut == StatutDossier.clos:
        raise Refus.etat(
            f"La facture {f.numero} est portée par le dossier {dossier.numero}, clos : la "
            "corriger depuis le dossier après l'avoir rouvert.",
            code="dossier_clos",
        )
    periode.cout_hors_periode_close(s, dossier, f"correction de la facture {f.numero}")


def corriger(s: Session, qui: audit.Qui, r: Reception, f: Facture, c: Correction) -> None:
    """Date, montant, échéance de la facture visée, avec leurs garde-fous ; journal."""
    delai = s.scalar(
        select(Fournisseur.delai_paiement_jours).where(Fournisseur.id == r.fournisseur_id)
    )
    jour, montant, echeance = _nouvelles_valeurs(c, f, int(delai or 0))
    change = (jour, montant, echeance) != (f.date, f.montant, f.echeance)
    if change:
        _garde_fous(s, f)
    avant = {} if f.id is None else audit.photo(f)
    f.date, f.montant, f.echeance = jour, montant, echeance
    s.flush()
    a, b = audit.differences(avant, audit.photo(f))
    if a or b:
        audit.journal(
            s, qui, "facture complétée", "facture", f.id, numero=f.numero, avant=a, apres=b
        )


def detail_facture(f: Facture) -> str:
    """« facture FA-12 · 1 234,50 EUR » (nombres à la française, A-28)."""
    texte = f"facture {f.numero}"
    return texte + (f" · {nombre_fr(f.montant)} {f.devise}" if f.montant else "")


# ── Règlement (route 229, lot D8) ────────────────────────────────────────────


def verifier_annulation_reglement(qui: audit.Qui, payee_le: date, motif: str) -> str:
    """Annuler un règlement : la direction seule, avec un motif (A-21, B-01) — la pièce
    redeviendrait due. Rend le motif nettoyé. Servira aussi aux frais d'importation (D7, D8)."""
    if qui.role != Role.direction:
        raise Refus.droit(
            f"Ce règlement (le {payee_le:%d/%m/%Y}) ne s'annule que par la direction : la pièce "
            "redeviendrait due. Lui demander de le faire, en disant pourquoi."
        )
    motif = motif.strip()
    if len(motif) < MOTIF_MIN:
        raise Refus.saisie(
            "Dire pourquoi le règlement est annulé (le motif reste au journal).",
            code="motif_requis",
            champs={"motif": "motif obligatoire"},
        )
    return motif


def verifier_date_reglement(s: Session, payee_le: date, debut: date | None) -> None:
    """Un règlement est un fait constaté : ni dans le futur, ni dans une période close, ni
    avant la pièce qu'il règle (A-21)."""
    if payee_le > horloge.aujourd_hui():
        raise Refus.saisie(
            "Un règlement ne se date pas dans le futur : c'est un fait constaté.",
            code="date_future",
            champs={"payee_le": "date dans le futur"},
        )
    periode.date_permise(s, payee_le, "payee_le")
    if debut is not None and payee_le < debut:
        raise Refus.saisie(
            f"Le règlement ({payee_le:%d/%m/%Y}) précède la pièce qu'il règle ({debut:%d/%m/%Y}).",
            code="date_invalide",
            champs={"payee_le": "avant la pièce"},
        )


def debut_de_la_facture(s: Session, f: Facture) -> date | None:
    """Le jour avant lequel une facture ne se règle pas : sa date, sinon la première réception
    (non annulée) qui la porte."""
    if f.date is not None:
        return f.date
    requete = select(func.min(Reception.date)).where(
        Reception.facture_id == f.id, Reception.statut != StatutDocument.annulee
    )
    jour = s.scalar(requete)
    return jour if isinstance(jour, date) else None


def regler(
    s: Session,
    qui: audit.Qui,
    fid: int,
    *,
    payee_le: date | None,
    version: int,
    motif: str = "",
) -> Facture:
    """Marque la facture réglée tel jour, ou annule son règlement (`payee_le` vide)."""
    f = s.scalars(
        select(Facture)
        .where(Facture.id == fid)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if f is None:
        raise Refus.introuvable("Pièce introuvable.")
    audit.verifier_version(s, f, version, "Cette facture")
    if payee_le is None:
        if f.payee_le is None:
            raise Refus.etat("Cette facture n'est pas réglée : aucun règlement à annuler.")
        motif = verifier_annulation_reglement(qui, f.payee_le, motif)
        action, detail = "règlement annulé", f"motif : {motif}"
    else:
        verifier_date_reglement(s, payee_le, debut_de_la_facture(s, f))
        action, detail = "règlement", f"réglée le {payee_le:%d/%m/%Y}"
    with audit.suivre(s, qui, action, f, numero=f.numero, detail=detail):
        f.payee_le = payee_le
        f.payee_par_id = qui.id if payee_le is not None else None
        s.flush()
    return f
