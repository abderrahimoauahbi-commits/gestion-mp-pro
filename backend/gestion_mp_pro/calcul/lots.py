"""Lots et traçabilité : ce qu'il reste de chaque lot, et le chemin de la matière.

Portage de `moteur.LigneLot`, `stock_par_lot`, `lots_disponibles`, `tracabilite` (CALCULS B
§ 6). Un mouvement sans lot est rangé sous « (sans lot) » : la somme des lots retombe
toujours sur le stock de la référence.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from gestion_mp_pro.calcul.constantes import EPSILON, POUSSIERE, QUARANTAINE, SANS_LOT
from gestion_mp_pro.calcul.modele import Donnees, Mouvement


@dataclass
class LigneLot:
    """Ce qu'il reste d'un lot, et ce qu'il a servi."""

    reference: str
    lot: str
    entrees: float = 0.0
    sorties: float = 0.0
    stock: float = 0.0
    premiere_entree: date | None = None
    dernier_mouvement: date | None = None
    fournisseur: str = ""
    par_magasin: dict[str, float] = field(default_factory=dict)
    ordres: list[str] = field(default_factory=list)
    mouvements: int = 0

    @property
    def epuise(self) -> bool:
        """Plus rien dans le lot."""
        return abs(self.stock) < EPSILON

    @property
    def negatif(self) -> bool:
        """Plus sorti que rentré : une saisie s'est trompée de lot."""
        return self.stock < -EPSILON


def _ajouter(par_magasin: dict[str, float], magasin: str, quantite: float) -> None:
    par_magasin[magasin] = par_magasin.get(magasin, 0.0) + quantite


def _ventiler(ligne: LigneLot, mouvement: Mouvement, signee: float) -> None:
    """Le transfert déplace, l'entrée crédite la destination, la sortie débite la source."""
    if mouvement.type == "TRANSFERT_MAGASIN":
        if mouvement.magasin_destination:
            _ajouter(ligne.par_magasin, mouvement.magasin_destination, mouvement.quantite)
        if mouvement.magasin_source:
            _ajouter(ligne.par_magasin, mouvement.magasin_source, -mouvement.quantite)
    elif mouvement.magasin_destination:
        _ajouter(ligne.par_magasin, mouvement.magasin_destination, signee)
    elif mouvement.magasin_source:
        _ajouter(ligne.par_magasin, mouvement.magasin_source, signee)


def _compter(ligne: LigneLot, mouvement: Mouvement, annulees: set[int]) -> None:
    """Entré et sorti comme dans la liste des lots : une écriture annulée et son annulation ne
    comptent pas, un transfert ne fait que déplacer, un retour des machines réduit le sorti."""
    signee = mouvement.quantite_signee
    ligne.stock += signee
    ligne.mouvements += 1
    annulation = mouvement.contrepasse_id is not None or (
        mouvement.id is not None and mouvement.id in annulees
    )
    if annulation or mouvement.type == "TRANSFERT_MAGASIN":
        pass
    elif mouvement.type == "RETOUR_PRODUCTION":
        ligne.sorties -= signee
    elif signee > 0:
        ligne.entrees += signee
        if ligne.premiere_entree is None or mouvement.date < ligne.premiere_entree:
            ligne.premiere_entree = mouvement.date
    else:
        ligne.sorties += -signee
    if ligne.dernier_mouvement is None or mouvement.date > ligne.dernier_mouvement:
        ligne.dernier_mouvement = mouvement.date
    _ventiler(ligne, mouvement, signee)
    if mouvement.numero_of and mouvement.numero_of not in ligne.ordres:
        ligne.ordres.append(mouvement.numero_of)


def stock_par_lot(donnees: Donnees, reference: str = "") -> list[LigneLot]:
    """Le stock détenu, lot par lot, à partir du seul journal ; trié par (référence, lot)."""
    annulees = {m.contrepasse_id for m in donnees.mouvements if m.contrepasse_id is not None}
    lots: dict[tuple[str, str], LigneLot] = {}
    for mouvement in donnees.mouvements:
        if reference and mouvement.reference != reference:
            continue
        cle = (mouvement.reference, mouvement.lot_fournisseur or SANS_LOT)
        ligne = lots.get(cle)
        if ligne is None:
            article = donnees.article(mouvement.reference)
            ligne = LigneLot(
                reference=mouvement.reference,
                lot=cle[1],
                fournisseur=mouvement.fournisseur or (article.fournisseur if article else ""),
            )
            lots[cle] = ligne
        _compter(ligne, mouvement, annulees)
    return sorted(lots.values(), key=lambda x: (x.reference, x.lot))


def lots_disponibles(donnees: Donnees, reference: str) -> list[LigneLot]:
    """Les lots d'une référence qui ont de la matière disponible (hors quarantaine), du plus
    ancien au plus récent — l'ordre où le magasin doit les sortir."""
    quarantaines = {m.code for m in donnees.magasins if m.type == QUARANTAINE}
    resultat = []
    for lot in stock_par_lot(donnees, reference):
        if lot.lot == SANS_LOT:
            continue
        par_magasin = {
            code: q
            for code, q in lot.par_magasin.items()
            if code not in quarantaines and q > EPSILON
        }
        disponible = sum(par_magasin.values())
        if disponible > POUSSIERE:
            resultat.append(replace(lot, stock=disponible, par_magasin=par_magasin))
    return sorted(resultat, key=lambda x: (x.premiere_entree or date.max, x.lot))


@dataclass
class Tracabilite:
    """Le chemin de la matière : par lot, par ordre de fabrication, ou par fil."""

    lot: str
    ordre: str
    reference: str
    mouvements: list[Mouvement]
    references: list[str]
    ordres: list[str]
    lots: list[str]
    entrees: float
    sorties: float


def tracabilite(
    donnees: Donnees, *, lot: str = "", ordre: str = "", reference: str = ""
) -> Tracabilite:
    """D'où vient un lot et où il est parti ; ce qu'un ordre a consommé ; un fil, tous lots.

    Entré et sorti se comptent comme dans `stock_par_lot` et la route 112 : une écriture annulée
    et son annulation ne comptent pas, un transfert ne fait que déplacer, un retour des machines
    réduit le sorti au lieu de s'ajouter à l'entré."""
    mouvements = [
        m
        for m in donnees.mouvements
        if (lot and (m.lot_fournisseur or SANS_LOT) == lot)
        or (ordre and m.numero_of == ordre)
        or (reference and m.reference == reference)
    ]
    annulees = {m.contrepasse_id for m in donnees.mouvements if m.contrepasse_id is not None}
    comptes = [
        m
        for m in mouvements
        if m.contrepasse_id is None
        and (m.id is None or m.id not in annulees)
        and m.type != "TRANSFERT_MAGASIN"
    ]
    entrees = [m for m in comptes if m.quantite_signee > 0 and m.type != "RETOUR_PRODUCTION"]
    sorties = [m for m in comptes if m.quantite_signee < 0 or m.type == "RETOUR_PRODUCTION"]
    return Tracabilite(
        lot=lot,
        ordre=ordre,
        reference=reference,
        mouvements=mouvements,
        references=sorted({m.reference for m in mouvements}),
        ordres=sorted({m.numero_of for m in mouvements if m.numero_of}),
        lots=sorted({m.lot_fournisseur for m in mouvements if m.lot_fournisseur}),
        entrees=sum(m.quantite_signee for m in entrees),
        sorties=-sum(m.quantite_signee for m in sorties),
    )
