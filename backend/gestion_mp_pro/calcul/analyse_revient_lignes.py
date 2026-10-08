"""Les lignes de l'analyse du coût de revient : groupes, détail, résultat (CALCULS B § 9.12).

Portage des dicts construits par `gestion_mp/api/analyse_import.py` (`analyse_revient` :
`groupes`, `lignes_detail`, le dict rendu) en dataclasses aux mêmes clés, et des calculs par
groupe (revient, décaissé, au kilo, surcoût). Les filtres sont dans `analyse_revient.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from gestion_mp_pro.calcul.importations import LigneRevient
from gestion_mp_pro.calcul.modele import Article, DossierImport

UNITE = "kg"
"""Tout se compte en kilos, le cuir, les franges et le ruban compris."""


@dataclass
class BlocRevient:
    """Ce qu'un groupe accumule, ligne après ligne."""

    valeur: str
    quantite: float = 0.0
    unites: set[str] = field(default_factory=set)
    poids: float = 0.0
    marchandise_mad: float = 0.0
    charges_mad: float = 0.0
    tva_mad: float = 0.0
    lignes: int = 0
    dossiers: set[str] = field(default_factory=set)
    detail: dict[str, float] = field(default_factory=dict)


@dataclass
class GroupeRevient:
    """Un groupe de l'analyse (une valeur de l'axe) ; `role` … `cout_m2` : posés par le coût
    d'une qualité seulement."""

    valeur: str
    quantite: float | None
    unites: list[str]
    poids: float
    marchandise_mad: float
    charges_mad: float
    tva_mad: float
    lignes: int
    dossiers: list[str]
    detail: dict[str, float]
    unite: str | None
    revient_mad: float
    decaisse_mad: float
    marchandise_unite: float | None
    revient_unite: float | None
    marchandise_kg: float
    revient_kg: float
    surcout: float
    role: str | None = None
    part_recette: float | None = None
    poids_m2: float | None = None
    cout_m2: float | None = None


@dataclass
class LigneDetailRevient:
    """Une ligne de dossier qui a fait le compte (`detail=true`)."""

    dossier: str
    date_arrivee: date | None
    statut: str
    reference: str
    lot_fournisseur: str
    fournisseur: str
    composition: str
    type_fil: str
    titrage: str
    couleur: str
    role_bom: str
    quantite: float
    unite: str
    poids: float
    marchandise_mad: float
    charges_mad: float
    revient_mad: float
    tva_mad: float
    decaisse_mad: float
    valeur_unite: float
    revient_unite: float
    revient_kg: float
    surcout: float


@dataclass
class DossierNonReparti:
    """Les frais d'un dossier qu'aucune marchandise ne porte."""

    dossier: str
    montant: float


@dataclass
class AnalyseRevient:
    """Le résultat de la route `GET /importations/analyse/revient` (mêmes clés)."""

    axe: str
    ids_dossiers: dict[str, int]
    frais_non_repartis_mad: float
    dossiers_non_repartis: list[DossierNonReparti]
    libelle_axe: str
    lignes: list[GroupeRevient]
    detail_lignes: list[LigneDetailRevient]
    total_lignes: int
    total_poids: float
    total_marchandise_mad: float
    total_charges_mad: float
    total_revient_mad: float
    total_tva_mad: float
    total_decaisse_mad: float


def ajouter(groupes: dict[str, BlocRevient], cle: str, r: LigneRevient, dossier: str) -> None:
    """Une ligne retenue s'ajoute au groupe de sa valeur sur l'axe."""
    bloc = groupes.setdefault(cle, BlocRevient(valeur=cle))
    bloc.quantite += r.quantite
    bloc.unites.add(UNITE)
    bloc.poids += r.poids_kg
    bloc.marchandise_mad += r.valeur_mad
    bloc.charges_mad += r.charges_mad
    bloc.tva_mad += r.tva_mad
    bloc.lignes += 1
    bloc.dossiers.add(dossier)
    for poste, montant in r.detail.items():
        bloc.detail[poste] = bloc.detail.get(poste, 0.0) + montant


def groupe(bloc: BlocRevient) -> GroupeRevient:
    """Un groupe achevé : revient, décaissé, coûts à l'unité et au kilo, surcoût."""
    marchandise = bloc.marchandise_mad
    revient_total = marchandise + bloc.charges_mad
    unite = next(iter(bloc.unites)) if len(bloc.unites) == 1 else None
    quantite = bloc.quantite if unite else None
    return GroupeRevient(
        valeur=bloc.valeur,
        quantite=quantite,
        unites=sorted(bloc.unites),
        poids=bloc.poids,
        marchandise_mad=marchandise,
        charges_mad=bloc.charges_mad,
        tva_mad=bloc.tva_mad,
        lignes=bloc.lignes,
        dossiers=sorted(bloc.dossiers),
        detail=bloc.detail,
        unite=unite,
        revient_mad=revient_total,
        decaisse_mad=revient_total + bloc.tva_mad,
        marchandise_unite=marchandise / quantite if quantite else None,
        revient_unite=revient_total / quantite if quantite else None,
        marchandise_kg=marchandise / bloc.poids if bloc.poids else 0.0,
        revient_kg=revient_total / bloc.poids if bloc.poids else 0.0,
        surcout=bloc.charges_mad / marchandise if marchandise else 0.0,
    )


def ligne_detail(a: Article, r: LigneRevient, d: DossierImport) -> LigneDetailRevient:
    """Une ligne une à une : d'où vient chaque kilo."""
    return LigneDetailRevient(
        dossier=d.numero,
        date_arrivee=d.date_arrivee,
        statut=d.statut,
        reference=r.reference,
        lot_fournisseur=r.lot_fournisseur,
        fournisseur=r.fournisseur or a.fournisseur,
        composition=a.composition or a.nature,
        type_fil=a.type_fil,
        titrage=f"{a.titrage} {a.titrage_unite}".strip(),
        couleur=a.couleur or a.designation,
        role_bom=a.role_bom,
        quantite=r.quantite,
        unite=UNITE,
        poids=r.poids_kg,
        marchandise_mad=r.valeur_mad,
        charges_mad=r.charges_mad,
        revient_mad=r.revient_mad,
        tva_mad=r.tva_mad,
        decaisse_mad=r.revient_mad + r.tva_mad,
        valeur_unite=r.valeur_unite,
        revient_unite=r.revient_unite,
        revient_kg=r.revient_mad / r.poids_kg if r.poids_kg else 0.0,
        surcout=r.surcout,
    )
