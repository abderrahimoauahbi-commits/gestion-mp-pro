"""Le bon de commande tel que le fournisseur le lit (routes 164 et 165) : en anglais, sans aucun
prix, montant ni devise (décision de Mohamed, A22), chaque ligne dans son conditionnement et en
kilos — avec ses mètres, à titre indicatif, pour un cuir, des franges, un ruban (le drapeau
`lineaire` du rôle, pas la seule présence d'une densité) — et les
remarques au fournisseur à part (`gestion_mp/api/achats.py` : `impression`, `lignes_du_bon` ;
`exports_achats.py` : `exporter_bon_fournisseur`).

Une seule définition du contenu pour ses deux formes : le document HTML
(`documents/bon_commande.py`) et le classeur (`exports/bon_fournisseur.py`) disent la même chose.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.documents.anglais import au_poids, conditionnement_en, nombre_en
from gestion_mp_pro.documents.format import date_en
from gestion_mp_pro.services.commandes_socle import charger, kg_par_ml

TITRE = "Purchase order"
BROUILLON = "Draft — not sent"
CONFIRMATION = (
    "Please confirm this order by return — quantities and delivery date — and quote its "
    "number on your delivery note and on your invoice."
)
SIGNATURE_ACHETEUR = "Purchasing manager"
SIGNATURE_FOURNISSEUR = ("Accepted by the supplier", "Stamp and signature")
COLONNES = (
    "No.",
    "Item",
    "Description",
    "Packing",
    "Qty",
    "Total weight (kg)",
    "Length (m, indicative)",
)
"""Les colonnes du tableau, communes au HTML et au classeur (la dernière, s'il y a des mètres)."""


@dataclass(frozen=True)
class Usine:
    """Où livrer : la raison sociale, l'adresse et la ville de l'usine (papier à en-tête)."""

    nom: str = ""
    adresse: str = ""
    ville: str = ""


@dataclass
class LigneBon:
    """Une ligne telle que le fournisseur la lit (aucun prix)."""

    rang: int
    reference: str
    designation: str
    conditionnement: str
    unites: float | None
    kg: float
    metres: float | None

    @property
    def unites_texte(self) -> str:
        """« 448 », ou « — » pour une ligne au poids."""
        return "—" if self.unites is None else nombre_en(self.unites)

    @property
    def kg_texte(self) -> str:
        """« 1,120 kg »."""
        return f"{nombre_en(self.kg)} kg"

    @property
    def metres_texte(self) -> str:
        """« ≈ 1,200 m » (indicatif), ou vide."""
        return "" if self.metres is None else f"≈ {nombre_en(round(self.metres), 0)} m"


@dataclass
class BonFournisseur:
    """Le contenu du bon fournisseur : en-tête, fournisseur, livraison, lignes, remarques."""

    id: int
    numero: str
    brouillon: bool
    date: str
    livraison: str
    fournisseur: str
    fournisseur_lignes: list[tuple[str, str]]
    livrer_a: list[tuple[str, str]]
    lignes: list[LigneBon] = field(default_factory=list)
    remarques: str = ""

    @property
    def total_kg(self) -> float:
        """Le total commandé, en kilos."""
        return sum(x.kg for x in self.lignes)

    @property
    def total_texte(self) -> str:
        """« 1,120 kg »."""
        return f"{nombre_en(self.total_kg)} kg"

    @property
    def avec_metres(self) -> bool:
        """Une ligne au moins dit ses mètres (la colonne « Length » s'imprime alors)."""
        return any(x.metres is not None for x in self.lignes)

    @property
    def colonnes(self) -> tuple[str, ...]:
        """Les colonnes du tableau de ce bon."""
        return COLONNES if self.avec_metres else COLONNES[:-1]

    @property
    def titre(self) -> str:
        """Le titre de l'onglet et du document : le numéro, ou « Draft — not sent »."""
        return self.numero or BROUILLON

    @property
    def nom_fichier(self) -> str:
        """« BC-2026-0012.xlsx », ou « draft-7.xlsx »."""
        return f"{self.numero}.xlsx" if self.numero else f"draft-{self.id}.xlsx"


def contenu(
    s: Session, cid: int, usine: Usine, *, introuvable: str = "Commande introuvable."
) -> BonFournisseur:
    """Le bon fournisseur d'une commande (404 `introuvable` : la phrase de chaque route)."""
    try:
        bon = charger(s, cid)
    except Refus as refus:
        raise Refus.introuvable(introuvable) from refus
    c, f = bon.commande, bon.fournisseur
    prevue = date_en(c.date_livraison_prevue) if c.date_livraison_prevue else "to be agreed"
    lignes = []
    for rang, x in enumerate(bon.lignes, start=1):
        m = bon.matieres[x.matiere_id]
        kg, densite = float(x.quantite), kg_par_ml(m)
        poids = au_poids(x.unite_achat, x.contenance)
        lignes.append(
            LigneBon(
                rang=rang,
                reference=m.reference,
                designation=m.designation,
                conditionnement=conditionnement_en(x.unite_achat, x.contenance),
                unites=None if poids else round(kg / float(x.contenance), 3),
                kg=kg,
                metres=kg / densite if densite else None,
            )
        )
    fournisseur = [("Country", f.pays), ("Contact", f.contact), ("Phone", f.telephone),
                   ("Email", f.email)]  # fmt: skip
    livrer = [("Company", usine.nom), ("Address", usine.adresse), ("City", usine.ville),
              ("Expected date", prevue), ("Incoterm", f.incoterm)]  # fmt: skip
    return BonFournisseur(
        id=c.id,
        numero=c.numero or "",
        brouillon=not c.numero,
        date=date_en(c.date_commande) if c.numero else "on sending",
        livraison=prevue,
        fournisseur=f.nom,
        fournisseur_lignes=[(k, v) for k, v in fournisseur if v],
        livrer_a=[(k, v) for k, v in livrer if v],
        lignes=lignes,
        remarques=c.observations.strip(),
    )
