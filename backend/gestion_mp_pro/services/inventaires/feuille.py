"""La feuille de comptage (route 133 ; REGLES S161, ECRANS-PRO « Feuille de comptage ») : une
page A4 paysage par magasin (codes triés), sur le papier à en-tête ; lots triés par référence,
date d'entrée, numéro ; **à l'aveugle** par défaut (sans le théorique) ; `theorique` l'ajoute ;
`recomptage` ne garde que les lignes **enregistrées** à recompter, avec le théorique.

Le service prépare les données ; le gabarit `documents/gabarits/feuille_comptage.html` les met
en page (lot D9 : `documents.rendu`).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import inventaire as calcul
from gestion_mp_pro.modeles import Lot, Magasin, Matiere
from gestion_mp_pro.modeles.enums import StatutInventaire
from gestion_mp_pro.services.inventaires.document import charger, ligne_de_calcul


@dataclass(frozen=True)
class LigneFeuille:
    """Un lot à compter : de quoi le reconnaître, et le théorique (feuille de contrôle)."""

    rang: int
    reference: str
    designation: str
    lot: str
    conditionnement: str
    theorique: Decimal


@dataclass
class PageFeuille:
    """Les lots d'un magasin."""

    magasin: str
    lignes: list[LigneFeuille] = field(default_factory=list)


@dataclass
class Feuille:
    """Une feuille de comptage ou de recomptage."""

    numero: str
    libelle: str
    date: date
    tolerance_pourcent: Decimal
    recomptage: bool
    theorique: bool
    abandonne: bool
    pages: list[PageFeuille]

    @property
    def titre(self) -> str:
        """« Feuille de comptage INV-2026-0003 » (ou de recomptage)."""
        genre = "recomptage" if self.recomptage else "comptage"
        return f"Feuille de {genre} {self.numero}"


def conditionnement(poids: Decimal, bobines_palette: Decimal) -> str:
    """« 2,5 kg / bobine · 50 bob. / palette » (rien sans poids de bobine)."""
    if poids <= 0:
        return ""
    texte = f"{poids:.4f}".rstrip("0").rstrip(".").replace(".", ",") + " kg / bobine"
    if bobines_palette > 0:
        texte += f" · {bobines_palette.normalize():f}".replace(".", ",") + " bob. / palette"
    return texte


def feuille(
    s: Session, ident: int, *, recomptage: bool = False, theorique: bool = False
) -> Feuille:
    """Les pages de la feuille d'un inventaire (404 « Inventaire introuvable. »)."""
    i = charger(s, ident)
    matieres = {
        m.id: m
        for m in s.scalars(select(Matiere).where(Matiere.id.in_({x.matiere_id for x in i.lignes})))
    }
    ids_lots = {x.lot_id for x in i.lignes if x.lot_id is not None}
    lots = {x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_(ids_lots)))}
    codes = dict(s.execute(select(Magasin.id, Magasin.code)).all())
    par_magasin: dict[int, list[tuple[tuple[str, date, str], Matiere, str, Decimal, Decimal]]]
    par_magasin = defaultdict(list)
    for x in i.lignes:
        m = matieres[x.matiere_id]
        if recomptage and not calcul.a_recompter(
            ligne_de_calcul(x, m.reference), float(i.tolerance)
        ):
            continue
        lot = lots.get(x.lot_id) if x.lot_id is not None else None
        numero = lot.numero if lot is not None else (x.lot_numero or "LOT INTERNE")
        poids = lot.poids_bobine if lot is not None and lot.poids_bobine > 0 else m.poids_bobine
        cle = (m.reference, lot.entre_le if lot is not None else i.date, numero)
        par_magasin[x.magasin_id].append((cle, m, numero, poids, x.theorique))
    pages = []
    for magasin_id in sorted(par_magasin, key=lambda g: codes.get(g, "")):
        rangs = sorted(par_magasin[magasin_id], key=lambda r: r[0])
        page = PageFeuille(codes.get(magasin_id, ""))
        for n, (_, m, numero, poids, attendu) in enumerate(rangs, start=1):
            designation = m.designation if m.designation != m.reference else ""
            page.lignes.append(
                LigneFeuille(
                    n,
                    m.reference,
                    designation,
                    numero,
                    conditionnement(poids, m.bobines_palette),
                    attendu,
                )
            )
        pages.append(page)
    return Feuille(
        numero=i.numero,
        libelle=i.libelle,
        date=i.date,
        tolerance_pourcent=i.tolerance * 100,
        recomptage=recomptage,
        theorique=theorique or recomptage,
        abandonne=i.statut == StatutInventaire.abandonne,
        pages=pages,
    )
