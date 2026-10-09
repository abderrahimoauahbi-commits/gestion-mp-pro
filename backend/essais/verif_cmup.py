"""Le coût moyen (CMUP glissant) rejoué depuis le journal de la base (lot V1).

Formules de la documentation (CALCULS B § 1.3), écrites une seconde fois, sans le moteur :

- ordre : par date puis n° ; une annulation se rejoue juste après ce qu'elle annule ;
- transfert : au coût moyen, rien ne bouge ;
- annulation : au coût de l'original ; un achat (ouverture, réception) entre à son coût
  d'entrée ; une autre entrée, au coût moyen si le stock n'est pas vide, sinon au coût de la
  sortie de l'ordre qu'elle rend, à défaut au coût d'entrée de son lot, au dernier coût moyen,
  au catalogue ;
- une sortie part au coût moyen ; un retour au fournisseur, au coût d'entrée de son lot ;
- une sortie au-delà du stock n'est valorisée que jusqu'au stock (pas de stock négatif).

Chaque ligne du journal valorisé (coût unitaire) et le CMUP de la Valorisation sont comparés.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from verif_couts import couts_d_entree
from verif_socle import Acces, Releve, cours_de

ACHATS = ("OUVERTURE", "RECEPTION")
NUL = 1e-9


def _catalogue(a: Acces, taux: dict[str, float]) -> dict[int, float]:
    """Le prix du catalogue au kilo, en MAD au cours du jour."""
    return {
        mid: (prix / densite if unite == "ml" and densite else prix) * cours_de(devise, None, taux)
        for mid, prix, unite, densite, devise in a.sql(
            "SELECT id, prix, unite_prix, densite, devise FROM matiere"
        )
    }


def rejouer(a: Acces, taux: dict[str, float]) -> tuple[dict[int, float], dict[int, list[float]]]:
    """Rejoue le journal : (coût unitaire de chaque mouvement, [kg, MAD] par matière)."""
    entree = couts_d_entree(a, taux)
    catalogue = _catalogue(a, taux)
    lignes = a.sql(
        "SELECT id, date_effet, type, matiere_id, lot_id, quantite, ordre_id, contrepasse_id "
        "FROM mouvement"
    )
    lignes.sort(key=lambda x: (x[1], x[7], 1, x[0]) if x[7] is not None else (x[1], x[0], 0, 0))
    etat: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    lots: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0.0, 0.0])
    ordre: dict[tuple[Any, ...], float] = {}
    dernier: dict[int, float] = {}
    unitaire: dict[int, float] = {}
    for mid, _jour, genre, matiere, lot, quantite, of, original in lignes:
        bloc = etat[matiere]
        moyen = bloc[1] / bloc[0] if bloc[0] > NUL else 0.0
        if genre == "TRANSFERT":
            unitaire[mid] = moyen
            continue
        q = float(quantite)
        if original is not None and original in unitaire:
            cout = unitaire[original]
            if genre in ACHATS:
                lots[(matiere, lot)][0] += q
                lots[(matiere, lot)][1] += q * cout
        elif q > 0 and genre in ACHATS:
            cout = entree.get(mid, catalogue.get(matiere, 0.0))
            lots[(matiere, lot)][0] += q
            lots[(matiere, lot)][1] += q * cout
        elif q > 0:
            cout = (
                moyen
                if bloc[0] > NUL
                else _reentree((of, matiere, lot), ordre, lots, dernier, catalogue)
            )
        else:
            cout = moyen
            achat = lots[(matiere, lot)]
            if genre == "RETOUR_FOURNISSEUR" and achat[0] > NUL:
                cout = achat[1] / achat[0]
            if genre == "SORTIE" and of is not None:
                ordre[(of, matiere, lot)] = ordre[(of, matiere)] = cout
        _bouger(bloc, q, cout)
        if bloc[0] > NUL:
            dernier[matiere] = bloc[1] / bloc[0]
        unitaire[mid] = cout
    return unitaire, dict(etat)


def _reentree(
    cle: tuple[Any, int, int],
    ordre: dict[tuple[Any, ...], float],
    lots: dict[tuple[int, int], list[float]],
    dernier: dict[int, float],
    catalogue: dict[int, float],
) -> float:
    """Le coût d'une matière qu'on n'achète pas, entrant dans un stock vide."""
    of, matiere, lot = cle
    if of is not None and (of, matiere, lot) in ordre:
        return ordre[(of, matiere, lot)]
    if of is not None and (of, matiere) in ordre:
        return ordre[(of, matiere)]
    achat = lots.get((matiere, lot))
    if achat and achat[0] > NUL and achat[1] > 0:
        return achat[1] / achat[0]
    if matiere in dernier:
        return dernier[matiere]
    return catalogue.get(matiere, 0.0)


def _bouger(bloc: list[float], q: float, cout: float) -> None:
    """Le stock d'une matière après une écriture (plancher : jamais de stock négatif)."""
    if q > 0:
        bloc[0] += q
        bloc[1] += q * cout
        return
    sortie = min(-q, bloc[0]) if bloc[0] > 0 else 0.0
    bloc[0] -= sortie
    bloc[1] -= sortie * cout
    if bloc[0] <= NUL:
        bloc[0], bloc[1] = max(bloc[0], 0.0), 0.0
    elif bloc[1] < 0:
        bloc[1] = 0.0


def verifier(
    a: Acces,
    r: Releve,
    *,
    journal: list[dict[str, Any]],
    valo: dict[str, Any],
    taux: dict[str, float],
    jour: date,
) -> None:
    """Coût unitaire de chaque ligne du journal valorisé, et CMUP du jour de chaque matière."""
    nom = "CMUP rejoué depuis le journal : coût de chaque écriture"
    unitaire, etat = rejouer(a, taux)
    for x in journal:
        r.comparer(
            nom,
            f"mouvement {x['id']} ({x['type']}, {x['date']})",
            x["cout_mad"],
            unitaire.get(x["id"]),
            1e-4,
        )
    nom = f"CMUP rejoué depuis le journal : coût moyen de chaque matière au {jour}"
    for x in valo["lignes"]:
        q, v = etat.get(x["matiere_id"], [0.0, 0.0])
        if q > NUL:
            r.comparer(nom, f"matière {x['matiere_id']}", x["cmup_mad"], v / q, 1e-4)
