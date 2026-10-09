"""Compter les lignes d'un inventaire et ajouter un lot trouvé (REGLES S156–S158, IR8–IR15 ;
C-06, C-08, D-08 ; API-PRO 129, 130).

- Un champ **absent** ne change rien, un `null` **explicite** le vide (C-08 : deux postes qui
  comptent ensemble n'effacent pas le recomptage de l'autre) ; vider le premier comptage vide
  aussi le recomptage. Le premier et le second compteurs sont notés (« à quatre yeux » :
  signalé, jamais bloqué).
- Une bobine se compte entière (D-08) ; une palette peut être entamée.
- Un lot trouvé n'est créé qu'à la validation : sa ligne porte sa matière, son numéro (ou la
  case « Lot interne ») ; une matière hors périmètre l'y ajoute (sa suspension commence).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Inventaire,
    InventaireLigne,
    InventaireMatiere,
    Lot,
    Magasin,
    Matiere,
)
from gestion_mp_pro.services import audit, horloge
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.inventaires.document import encore_ouvert, relire, toucher

CHAMPS = ("compte", "palettes", "bobines", "justification", "second_compte")
COLONNES = {"palettes": "nb_palettes", "bobines": "nb_bobines"}


@dataclass(frozen=True)
class Comptage:
    """Le comptage d'une ligne : les seuls champs envoyés (`None` = vider)."""

    ligne_id: int
    valeurs: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LotTrouve:
    """Un lot trouvé sur place, que le théorique ne connaissait pas."""

    matiere_id: int
    magasin_id: int | None = None
    lot_numero: str = ""
    lot_interne: bool = False
    compte: Decimal | None = None
    palettes: Decimal | None = None
    bobines: Decimal | None = None
    justification: str = ""


def bobines_entieres(bobines: Decimal | None) -> None:
    """Une bobine se compte entière (U20, D-08)."""
    if bobines is not None and bobines != bobines.to_integral_value():
        raise Refus.saisie(
            "Une bobine se compte entière : 2 ou 3, pas 2,5 — saisir le poids en kg pour une "
            "bobine entamée.",
            code="unite_invalide",
        )


def compter(
    s: Session, qui: Acteur, ident: int, version: int, comptages: list[Comptage]
) -> Inventaire:
    """Route 129 : les lignes existantes, champ par champ."""
    i = relire(s, ident, version)
    encore_ouvert(i)
    lignes = {x.id: x for x in i.lignes}
    for c in comptages:
        x = lignes.get(c.ligne_id)
        if x is None:
            raise Refus.saisie("Ligne étrangère à cet inventaire.", code="valeur_inconnue")
        bobines_entieres(c.valeurs.get("bobines"))
        _appliquer(s, qui, x, c.valeurs)
    toucher(i)
    s.flush()
    audit.journal(
        s,
        qui,
        "comptage",
        "inventaire",
        i.id,
        numero=i.numero,
        detail=f"{i.numero} · {len(comptages)} ligne(s)",
    )
    return i


def _appliquer(s: Session, qui: Acteur, x: InventaireLigne, v: Mapping[str, Any]) -> None:
    """Les champs envoyés d'une ligne ; le premier et le second compteurs notés."""
    maintenant = horloge.maintenant()
    if "compte" in v and v["compte"] != x.compte:
        x.compte = v["compte"]
        x.compte_par_id, x.compte_le = (
            (qui.id, maintenant) if x.compte is not None else (None, None)
        )
    for champ in ("palettes", "bobines"):
        if champ in v:
            setattr(x, COLONNES[champ], v[champ])
    if "justification" in v:
        x.justification = v["justification"] or ""
    if "second_compte" in v:
        second = v["second_compte"]
        if second is not None and x.compte is None:
            reference = s.get_one(Matiere, x.matiere_id).reference
            numero = x.lot_numero or "LOT INTERNE"
            raise Refus.saisie(
                f"« {reference} », lot {numero} : un recomptage suit un premier comptage."
            )
        if second != x.second_compte:
            x.second_compte = second
            x.second_par_id, x.second_le = (
                (qui.id, maintenant) if second is not None else (None, None)
            )
    elif x.compte is None:
        x.second_compte, x.second_par_id, x.second_le = None, None, None


def lot_trouve(s: Session, qui: Acteur, ident: int, version: int, e: LotTrouve) -> Inventaire:
    """Route 130 : une ligne de théorique nul ; le lot n'est créé qu'à la validation (C-06)."""
    i = relire(s, ident, version)
    encore_ouvert(i)
    numero = "" if e.lot_interne else e.lot_numero.strip()
    magasin_id = e.magasin_id or i.magasin_id
    if not (e.matiere_id and (numero or e.lot_interne) and magasin_id):
        raise Refus.saisie("Un lot trouvé se décrit : matière, numéro de lot, magasin.")
    if s.get(Matiere, e.matiere_id) is None:
        raise Refus.saisie("Matière inconnue.", code="valeur_inconnue")
    if s.get(Magasin, magasin_id) is None:
        raise Refus.saisie("Magasin inconnu.", code="valeur_inconnue")
    if i.magasin_id is not None and magasin_id != i.magasin_id:
        raise Refus.saisie("Cet inventaire ne compte qu'un magasin : le lot trouvé y est rangé.")
    if numero and re.search(r"\s", numero):
        raise Refus.saisie(
            f"Un numéro de lot s'écrit sans espace : « {numero} ».",
            champs={"lot_numero": "numéro du lot avec un espace"},
        )
    bobines_entieres(e.bobines)
    lot = None
    if numero:
        lot = s.scalars(
            select(Lot).where(Lot.matiere_id == e.matiere_id, Lot.numero == numero)
        ).first()
    _pas_deja_compte(i, e.matiere_id, lot, numero, magasin_id)
    i.lignes.append(
        InventaireLigne(
            matiere_id=e.matiere_id,
            lot_id=lot.id if lot is not None else None,
            lot_numero=numero,
            lot_interne=e.lot_interne,
            magasin_id=magasin_id,
            theorique=Decimal(0),
            lot_trouve=True,
            compte=e.compte,
            nb_palettes=e.palettes,
            nb_bobines=e.bobines,
            justification=e.justification,
            compte_par_id=qui.id if e.compte is not None else None,
            compte_le=horloge.maintenant() if e.compte is not None else None,
        )
    )
    if all(m.matiere_id != e.matiere_id for m in i.matieres):
        i.matieres.append(InventaireMatiere(matiere_id=e.matiere_id))
    toucher(i)
    s.flush()
    audit.journal(
        s,
        qui,
        "lot trouvé",
        "inventaire",
        i.id,
        numero=i.numero,
        detail=f"{i.numero} · {numero or 'lot interne'}",
    )
    return i


def _pas_deja_compte(
    i: Inventaire, matiere_id: int, lot: Lot | None, numero: str, magasin_id: int
) -> None:
    """IR15 : un même lot (ou lot à créer, même matière, même numéro) dans le même magasin."""
    for x in i.lignes:
        if x.magasin_id != magasin_id:
            continue
        meme_lot = lot is not None and x.lot_id == lot.id
        meme_a_creer = (
            lot is None
            and numero
            and x.lot_id is None
            and not x.lot_interne
            and x.matiere_id == matiere_id
            and x.lot_numero == numero
        )
        if meme_lot or meme_a_creer:
            raise Refus.saisie(
                "Ce lot est déjà dans l'inventaire : saisir son comptage sur sa ligne."
            )
