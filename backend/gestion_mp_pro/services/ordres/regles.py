"""Les règles communes des ordres de fabrication (REGLES B.2.3–B.2.7, DEFAUTS D-08 à D-11).

Messages de refus de Gestion MP corrigé, mot pour mot, avec « ordre » partout (D-09) : magasin
de sortie connu et hors quarantaine, métier connu, qualité connue et en service, une qualité
une fois par ordre, lot de la matière, bobine entière (D-08), date du dernier ordre validé
(les numéros suivent les dates, M67).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Lot, Magasin, Matiere, Ordre, Qualite
from gestion_mp_pro.modeles.enums import StatutOrdre, TypeMagasin
from gestion_mp_pro.services import conversions
from gestion_mp_pro.services.conversions import Unite

POUSSIERE = Decimal("0.001")
"""Sous le gramme, une quantité est nulle (REGLES C5)."""

INTROUVABLE = "Ordre introuvable."
QUALITE_INCONNUE = "Qualité inconnue."
QUALITE_DEUX_FOIS = "Une qualité ne figure qu'une fois sur un ordre : additionner ses m²."
LOT_INCONNU = "Lot inconnu, ou d'une autre matière."
QUARANTAINE_SAISIE = (
    "La matière en quarantaine ne part pas aux machines : la libérer d'abord (transfert "
    "« Libération de quarantaine », décidé par les achats)."
)
QUARANTAINE_PROPOSITION = (
    "La matière en quarantaine ne part pas aux machines : choisir le magasin d'où elle sort."
)


def ordre_introuvable() -> Refus:
    """404 « Ordre introuvable. » (D-09)."""
    return Refus.introuvable(INTROUVABLE)


def magasin_de_sortie(s: Session, magasin_id: int, *, proposition: bool = False) -> Magasin:
    """Le magasin d'où la matière part : connu, pas de quarantaine (PR3, PR4 ; D-11 pour la
    proposition, où un magasin inconnu est un 404 comme dans Gestion MP corrigé)."""
    magasin = s.get(Magasin, magasin_id)
    if magasin is None:
        if proposition:
            raise Refus.introuvable("Magasin inconnu.")
        raise Refus.saisie("Magasin inconnu.", code="valeur_inconnue")
    if magasin.type == TypeMagasin.quarantaine:
        raise Refus.saisie(QUARANTAINE_PROPOSITION if proposition else QUARANTAINE_SAISIE)
    return magasin


def qualite_tissable(s: Session, qualite_id: int) -> Qualite:
    """Une qualité qu'on peut mettre sur un ordre : connue (404), en service (422, PR1, PR2)."""
    q = s.get(Qualite, qualite_id)
    if q is None:
        raise Refus.introuvable(QUALITE_INCONNUE)
    if not q.actif:
        raise Refus.saisie(
            f"La qualité {q.code} est arrêtée : elle ne se tisse plus. La direction la remet en "
            "service (Qualités) si une série doit encore partir."
        )
    return q


def une_fois(ids: list[int]) -> None:
    """Une qualité ne figure qu'une fois sur un ordre (PR7, O2)."""
    if len(set(ids)) != len(ids):
        raise Refus.saisie(QUALITE_DEUX_FOIS, code="ligne_en_double")


def lot_de(s: Session, lot_id: int, matiere_id: int | None) -> tuple[Lot, Matiere]:
    """Le lot d'une ligne et sa matière ; inconnu, ou d'une autre matière : 422 (PR9)."""
    lot = s.get(Lot, lot_id)
    if lot is None or (matiere_id is not None and lot.matiere_id != matiere_id):
        raise Refus.saisie(LOT_INCONNU, code="valeur_inconnue")
    return lot, s.get_one(Matiere, lot.matiere_id)


def en_kilos(matiere: Matiere, lot: Lot, quantite: Decimal, unite: Unite) -> Decimal:
    """La quantité saisie (kg, bobines, palettes) ramenée aux kilos, au gramme (P1–P3).

    Une bobine se compte entière (U20, D-08) ; une palette peut être entamée."""
    if unite is Unite.bobine and quantite != quantite.to_integral_value():
        raise Refus.saisie(
            f"« {matiere.reference} » : une bobine se compte entière — saisir un nombre entier "
            "de bobines, ou le poids en kg.",
            code="unite_invalide",
            champs={"unite": "une bobine se compte entière"},
        )
    kilos = conversions.vers_kg(quantite, unite, conversions.conditionnement(matiere, lot))
    if kilos <= 0:
        raise Refus.saisie(
            f"« {matiere.reference} » : moins d'un gramme ne se sort pas.",
            code="quantite_invalide",
        )
    return kilos


def dernier_ordre(s: Session, sauf: int | None = None) -> date | None:
    """La date du dernier ordre validé **ou annulé** (un ordre annulé garde son numéro : il
    compte, P74) ; `sauf` : l'ordre qu'on regarde."""
    requete = select(func.max(Ordre.date)).where(Ordre.statut != StatutOrdre.brouillon)
    if sauf is not None:
        requete = requete.where(Ordre.id != sauf)
    return s.scalar(requete)


def nom(o: Ordre) -> str:
    """Le nom d'un ordre dans le journal : son numéro, sinon « brouillon n° 12 »."""
    return o.numero or f"brouillon n° {o.id}"
