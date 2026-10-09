"""Remplir un brouillon d'ordre (REGLES B.2.4 : P20–P22, PR3–PR10 ; D-08, D-21).

Tout est vérifié **avant** d'écrire : magasin de sortie, métier, date permise, une qualité une
fois et en service, chaque lot de sa matière, chaque quantité ramenée aux kilos (bobine
entière). Puis l'en-tête est réécrit et les qualités et les lignes sont remplacées. Une
matière hors recette est admise (ordre « hors recette » : aucune qualité) ; un même lot peut
figurer sur plusieurs lignes (additionné aux contrôles).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Metier, Ordre, OrdreLigne, OrdreQualite
from gestion_mp_pro.modeles.types import SURFACE, arrondir
from gestion_mp_pro.services import periode
from gestion_mp_pro.services.conversions import Unite
from gestion_mp_pro.services.ordres import regles


@dataclass(frozen=True)
class SaisieQualite:
    """Une qualité tissée par l'ordre et ses m²."""

    qualite_id: int
    m2: Decimal


@dataclass(frozen=True)
class SaisieLigne:
    """Un lot à sortir : quantité dans l'unité saisie ; la matière, si l'écran la dit."""

    lot_id: int
    quantite: Decimal
    unite: Unite = Unite.kg
    matiere_id: int | None = None


@dataclass(frozen=True)
class SaisieOrdre:
    """Ce que l'écran envoie pour créer ou modifier un brouillon."""

    date: date
    magasin_id: int
    metier_id: int | None = None
    commentaire: str = ""
    qualites: tuple[SaisieQualite, ...] = ()
    lignes: tuple[SaisieLigne, ...] = ()


def _lignes(s: Session, e: SaisieOrdre) -> list[OrdreLigne]:
    """Les lignes, en kilos au gramme (PR9, PR10)."""
    if not e.lignes:
        raise Refus.saisie(
            "Un ordre sort au moins une matière : ajouter une ligne.",
            champs={"lignes": "au moins une ligne"},
        )
    lignes = []
    for x in e.lignes:
        lot, matiere = regles.lot_de(s, x.lot_id, x.matiere_id)
        kilos = regles.en_kilos(matiere, lot, x.quantite, x.unite)
        lignes.append(OrdreLigne(matiere_id=matiere.id, lot_id=lot.id, quantite=kilos))
    return lignes


def verifier(s: Session, e: SaisieOrdre) -> tuple[list[OrdreQualite], list[OrdreLigne]]:
    """Les contrôles d'un brouillon, dans l'ordre de Gestion MP ; rend qualités et lignes."""
    regles.magasin_de_sortie(s, e.magasin_id)
    if e.metier_id is not None and s.get(Metier, e.metier_id) is None:
        raise Refus.saisie("Métier inconnu.", code="valeur_inconnue")
    periode.date_permise(s, e.date)
    regles.une_fois([q.qualite_id for q in e.qualites])
    qualites = []
    for q in e.qualites:
        regles.qualite_tissable(s, q.qualite_id)
        qualites.append(OrdreQualite(qualite_id=q.qualite_id, m2=arrondir(q.m2, SURFACE)))
    return qualites, _lignes(s, e)


def remplir(s: Session, o: Ordre, e: SaisieOrdre) -> None:
    """Vérifie la saisie puis réécrit l'en-tête, les qualités et les lignes (P21)."""
    qualites, lignes = verifier(s, e)
    o.date, o.magasin_id, o.metier_id = e.date, e.magasin_id, e.metier_id
    o.commentaire = e.commentaire
    o.qualites.clear()
    o.lignes.clear()
    s.flush()
    o.qualites.extend(qualites)
    o.lignes.extend(lignes)
