"""Dates permises et période close (ARCHITECTURE § 8 ; héritage REGLES § 0.5, B.0.3, B.1.17).

- `date_permise(s, jour)` : un fait ne se date ni avant l'an 2000 (faute de frappe : 2006 pour
  2026), ni dans le futur (heure de l'usine), ni dans la période close (D1–D3, messages mot
  pour mot ; la période close est un 409, décision S0 n° 3).
- `cout_hors_periode_close(s, dossier, geste)` : le coût d'une marchandise entrée dans un mois
  clos ne change plus (D4, 409).
- `clore(s, qui, jour, motif)` : la direction clôt ou rouvre (route 26) ; motif obligatoire,
  période passée seulement, brouillons datés de la période refusés (E-14), historique et
  journal avant/après ; `APRES_CLOTURE` reçoit les gestes des domaines (cours figés, lot D7).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Dossier,
    DossierLigne,
    Inventaire,
    Lot,
    Operation,
    Ordre,
    Parametre,
    ParametreHistorique,
    Reception,
    ReceptionLigne,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import ObjetJournal, StatutDocument, StatutInventaire, StatutOrdre
from gestion_mp_pro.services import audit, horloge

CLE = "date_cloture"
PREMIER_JOUR = date(2000, 1, 1)
MOTIF_MIN = 3
LIBELLE = "Période close jusqu'au"

APRES_CLOTURE: list[Callable[[Session, audit.Qui, date], None]] = []
"""Gestes des domaines à faire dans la transaction d'une clôture (ex. figer les cours, D7)."""


def fin_de_periode_close(s: Session) -> date | None:
    """Le dernier jour de la période close (réglage de la direction), ou `None`."""
    p = s.get(Parametre, CLE)
    if p is None or not p.valeur:
        return None
    return date.fromisoformat(p.valeur)


def date_permise(s: Session, jour: date, champ: str = "date") -> None:
    """Refuse une date d'avant 2000, du futur ou de la période close (`SEC:210-226`)."""
    if jour < PREMIER_JOUR:
        raise Refus.saisie(
            f"Date trop ancienne ({jour:%d/%m/%Y}) : vérifier l'année.",
            code="date_trop_ancienne",
            champs={champ: "date trop ancienne"},
        )
    if jour > horloge.aujourd_hui():
        raise Refus.saisie(
            f"Date dans le futur ({jour:%d/%m/%Y}) : un mouvement se saisit le jour où il a lieu.",
            code="date_future",
            champs={champ: "date dans le futur"},
        )
    limite = fin_de_periode_close(s)
    if limite is not None and jour <= limite:
        raise Refus.etat(
            f"La période jusqu'au {limite:%d/%m/%Y} est close : rien ne s'y écrit plus. "
            "Dater après la clôture, ou demander à la direction de la rouvrir.",
            code="periode_close",
        )


def _entrees_du_dossier(s: Session, dossier: Dossier) -> list[date]:
    """Dates d'entrée des marchandises d'un dossier : réceptions, et lots saisis à la main."""
    receptions = (
        select(Reception.date)
        .join(ReceptionLigne, ReceptionLigne.reception_id == Reception.id)
        .join(DossierLigne, DossierLigne.reception_ligne_id == ReceptionLigne.id)
        .where(DossierLigne.dossier_id == dossier.id)
    )
    manuelles = (
        select(Lot.entre_le)
        .join(DossierLigne, DossierLigne.lot_id == Lot.id)
        .where(DossierLigne.dossier_id == dossier.id, DossierLigne.reception_ligne_id.is_(None))
    )
    return [*s.scalars(receptions), *s.scalars(manuelles)]


def cout_hors_periode_close(
    s: Session, dossier: Dossier | None, geste: str, entrees_en_plus: Sequence[date] = ()
) -> None:
    """Refuse un geste qui changerait le coût d'une marchandise entrée dans un mois clos (D4).

    `entrees_en_plus` : les dates d'entrée de ce qu'un rattachement ferait entrer (`SEC:235-276`).
    """
    limite = fin_de_periode_close(s)
    if limite is None:
        return
    entrees = [x for x in entrees_en_plus if x]
    if dossier is not None and dossier.id is not None:
        entrees += _entrees_du_dossier(s, dossier)
    closes = [x for x in entrees if x <= limite]
    if not closes:
        return
    numero = dossier.numero if dossier is not None else ""
    nom = f"du dossier {numero}" if numero else "rattachée"
    raise Refus.etat(
        f"La marchandise {nom} est entrée le {min(closes):%d/%m/%Y}, dans la période close "
        f"jusqu'au {limite:%d/%m/%Y} : son coût a été rendu avec le mois et ne change plus "
        f"({geste} refusé). Pour corriger ce mois, la direction rouvre la période (Réglages › "
        "Période close jusqu'au — c'est tracé), on saisit, puis elle la referme.",
        code="cout_periode_close",
    )


def brouillons_dans_la_periode(s: Session, jour: date) -> list[str]:
    """Ce qui resterait à faire dans la période à clore : brouillons et inventaires ouverts."""
    restes: list[str] = []
    a_voir: tuple[tuple[str, type[Reception | Ordre | Operation | Inventaire], str], ...] = (
        ("réception", Reception, StatutDocument.brouillon),
        ("ordre de fabrication", Ordre, StatutOrdre.brouillon),
        ("opération", Operation, StatutDocument.brouillon),
        ("inventaire", Inventaire, StatutInventaire.ouvert),
    )
    for libelle, modele, statut in a_voir:
        nombre = s.scalar(
            select(func.count())
            .select_from(modele)
            .where(modele.statut == statut, modele.date <= jour)
        )
        if nombre:
            restes.append(f"{nombre} {libelle}(s)")
    return restes


@dataclass(frozen=True)
class Periode:
    """L'état de la clôture : jusqu'où, par qui, quand (route 26)."""

    date_cloture: date | None
    par: str
    quand: datetime | None


def etat(s: Session) -> Periode:
    """La période close telle qu'elle est réglée."""
    p = s.get(Parametre, CLE)
    if p is None:
        return Periode(None, "", None)
    par = s.get(Utilisateur, p.modifie_par_id) if p.modifie_par_id is not None else None
    return Periode(fin_de_periode_close(s), par.nom if par is not None else "", p.modifie_le)


def _verifier_cloture(s: Session, jour: date | None, motif: str) -> None:
    """Motif, période passée, aucun brouillon laissé dans la période (KR33, E-14)."""
    if len(motif.strip()) < MOTIF_MIN:
        raise Refus.saisie(
            "Le motif est obligatoire : 3 caractères au moins.",
            code="motif_requis",
            champs={"motif": "3 caractères au moins"},
        )
    if jour is None:
        return
    if jour >= horloge.aujourd_hui():
        raise Refus.saisie("On ne clôt qu'une période passée.", code="date_invalide")
    if jour < PREMIER_JOUR:
        date_permise(s, jour, "date_cloture")
    restes = brouillons_dans_la_periode(s, jour)
    if restes:
        raise Refus.etat(
            f"Des brouillons sont datés de la période à clore : {', '.join(restes)}. Les "
            "valider, les supprimer ou les redater d'abord : après la clôture, ils ne "
            "pourraient plus se valider."
        )


def _lisible(jour: date | None) -> str:
    """« 30/09/2026 », ou « — » quand rien n'est clos."""
    return f"{jour:%d/%m/%Y}" if jour is not None else "—"


def clore(s: Session, qui: audit.Qui, jour: date | None, motif: str) -> Periode:
    """Clôt (ou rouvre, `jour=None`) la période ; tracé dans l'historique et le journal."""
    _verifier_cloture(s, jour, motif)
    p = s.scalars(select(Parametre).where(Parametre.cle == CLE).with_for_update()).one()
    avant = fin_de_periode_close(s)
    if avant == jour:
        return etat(s)
    texte = jour.isoformat() if jour is not None else ""
    s.add(
        ParametreHistorique(
            cle=CLE,
            avant=p.valeur,
            apres=texte,
            quand=horloge.maintenant(),
            par_id=qui.id,
            motif=motif.strip(),
        )
    )
    p.valeur, p.modifie_le, p.modifie_par_id = texte, horloge.maintenant(), qui.id
    audit.journal(
        s,
        qui,
        "paramètre",
        ObjetJournal.periode,
        detail=f"{LIBELLE} : {_lisible(avant)} → {_lisible(jour)} ({motif.strip()})",
        avant={CLE: avant.isoformat() if avant else None},
        apres={CLE: texte or None},
    )
    if jour is not None:
        for geste in APRES_CLOTURE:
            geste(s, qui, jour)
    s.flush()
    return etat(s)
