"""Tables de transitions des documents du lot D5, rejouées **exhaustivement** (LOTS § 2) :

- opération : 5 types × 3 statuts × 4 gestes × 3 rôles → code HTTP et statut suivant ;
- inventaire : 4 statuts × 5 gestes → code HTTP et statut suivant (rôles : la garde des routes,
  direction et achats, vérifiée par la matrice des droits).

Chaque cas part d'un document neuf, dans un point de reprise défait ensuite.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import pytest
from fabriques import stock as fabriques_stock
from fabriques.operations import Monde, acteur, ligne, monde, motif, ordre_valide, saisie
from fabriques.stock import JOUR
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Inventaire, Operation
from gestion_mp_pro.modeles.enums import Role, StatutDocument, StatutInventaire, TypeOperation
from gestion_mp_pro.services import inventaires as inv
from gestion_mp_pro.services import operations as ops
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.inventaires import Comptage, Criteres, LotTrouve, Ouverture
from gestion_mp_pro.services.operations.droits import DROITS

s = fabriques_stock.s
"""La session de l'essai, annulée à la fin (fixture du lot S4)."""

B, V, X = StatutDocument.brouillon, StatutDocument.validee, StatutDocument.annulee
GESTES_OPERATION = ("modifier", "supprimer", "valider", "annuler")
ATTENDU_OPERATION: dict[tuple[StatutDocument, str], tuple[int, str]] = {
    (B, "modifier"): (200, B),
    (B, "supprimer"): (200, "supprimee"),
    (B, "valider"): (200, V),
    (B, "annuler"): (409, B),
    (V, "modifier"): (409, V),
    (V, "supprimer"): (409, V),
    (V, "valider"): (409, V),
    (V, "annuler"): (200, X),
    (X, "modifier"): (409, X),
    (X, "supprimer"): (409, X),
    (X, "valider"): (409, X),
    (X, "annuler"): (409, X),
}
"""(statut, geste) → (code, statut suivant) pour un rôle qui fait ce type ; 403 sinon."""


def _saisies(s: Session, m: Monde) -> dict[TypeOperation, object]:
    ordre = ordre_valide(s, [(m.lots["E-L2"], 40)])
    x = m.lots
    return {
        TypeOperation.ouverture: saisie(
            "ouverture", ligne(m.a2.id, m.courant.id, 5, lot_numero="T-OUV")
        ),
        TypeOperation.transfert: saisie(
            "transfert",
            ligne(
                m.a1.id,
                m.courant.id,
                5,
                lot_id=x["E-L1"].id,
                magasin_destination_id=fabriques_stock.autre_magasin(s).id,
            ),
            motif_id=motif(s, "transfert", "Rangement"),
        ),
        TypeOperation.ajustement: saisie(
            "ajustement",
            ligne(m.a2.id, m.courant.id, -5, lot_id=x["E-T1"].id),
            motif_id=motif(s, "ajustement", "Perte / casse"),
            commentaire="casse constatée",
        ),
        TypeOperation.retour_fournisseur: saisie(
            "retour_fournisseur",
            ligne(m.a2.id, m.courant.id, 5, lot_id=x["E-T1"].id),
            motif_id=motif(s, "retour_fournisseur", "Bobines endommagées"),
        ),
        TypeOperation.retour_machine: saisie(
            "retour_machine",
            ligne(m.a1.id, m.courant.id, 5, lot_id=x["E-L2"].id),
            ordre_id=ordre.id,
            motif_id=motif(s, "retour_machine", "Reliquat de fin d'ordre"),
        ),
    }


def _geste(s: Session, qui: Acteur, o: Operation, geste: str, e: object) -> None:
    if geste == "modifier":
        ops.modifier(s, qui, o.id, o.version, e)  # type: ignore[arg-type]
    elif geste == "supprimer":
        ops.supprimer(s, qui, o.id, o.version)
    elif geste == "valider":
        ops.valider(s, qui, o.id, o.version)
    else:
        ops.annuler(s, qui, o.id, o.version)


def _en_etat(s: Session, qui: Acteur, e: object, statut: StatutDocument) -> Operation:
    o = ops.creer(s, qui, e, valider=statut != B)  # type: ignore[arg-type]
    if statut == X:
        o = ops.annuler(s, qui, o.id, o.version)
    return o


def test_table_des_operations(s: Session) -> None:
    """180 cas : chaque type × statut × geste × rôle donne le code et le statut attendus."""
    m = monde(s)
    saisies = _saisies(s, m)
    roles = {r: acteur(s, r) for r in (Role.direction, Role.achats, Role.alimentation)}
    ecarts = []
    for type_, e in saisies.items():
        for statut in (B, V, X):
            for geste in GESTES_OPERATION:
                for role, qui in roles.items():
                    code, suivant = _rejouer(
                        s, roles[Role.direction], qui, e, statut=statut, geste=geste
                    )
                    attendu = ATTENDU_OPERATION[(statut, geste)]
                    if role not in DROITS[type_]:
                        attendu = (403, statut)
                    if (code, suivant) != attendu:
                        ecarts.append(
                            f"{type_} {statut} {geste} {role}: {code} {suivant} ≠ {attendu}"
                        )
    assert ecarts == []


def _rejouer(
    s: Session, auteur: Acteur, qui: Acteur, e: object, *, statut: StatutDocument, geste: str
) -> tuple[int, str]:
    point = s.begin_nested()
    try:
        o = _en_etat(s, auteur, e, statut)
        try:
            _geste(s, qui, o, geste, e)
            code = 200
        except Refus as refus:
            code = refus.http
        lue = s.get(Operation, o.id)
        return code, (lue.statut if lue is not None else "supprimee")
    finally:
        point.rollback()


OU, VI, AB, AN = (
    StatutInventaire.ouvert,
    StatutInventaire.valide,
    StatutInventaire.abandonne,
    StatutInventaire.annule,
)
ATTENDU_INVENTAIRE: dict[tuple[StatutInventaire, str], tuple[int, str]] = {
    (OU, "compter"): (200, OU),
    (OU, "lot_trouve"): (200, OU),
    (OU, "valider"): (200, VI),
    (OU, "abandonner"): (200, AB),
    (OU, "annuler"): (409, OU),
    **{(VI, g): (409, VI) for g in ("compter", "lot_trouve", "valider", "abandonner")},
    (VI, "annuler"): (200, AN),
    **{(AB, g): (409, AB) for g in ("compter", "lot_trouve", "valider", "abandonner", "annuler")},
    **{(AN, g): (409, AN) for g in ("compter", "lot_trouve", "valider", "abandonner", "annuler")},
}


def _gestes_inventaire(m: Monde) -> dict[str, Callable[[Session, Acteur, Inventaire], object]]:
    return {
        "compter": lambda s, q, i: inv.compter(
            s,
            q,
            i.id,
            i.version,
            [Comptage(i.lignes[0].id, {"compte": Decimal(1), "justification": "essai"})],
        ),
        "lot_trouve": lambda s, q, i: inv.lot_trouve(
            s,
            q,
            i.id,
            i.version,
            LotTrouve(m.a2.id, lot_numero="T-TROUVE", compte=Decimal(1), justification="essai"),
        ),
        "valider": lambda s, q, i: inv.valider(s, q, i.id, i.version),
        "abandonner": lambda s, q, i: inv.abandonner(s, q, i.id, i.version, "essai"),
        "annuler": lambda s, q, i: inv.annuler(s, q, i.id, i.version, "essai"),
    }


def _inventaire_en_etat(s: Session, qui: Acteur, m: Monde, statut: StatutInventaire) -> Inventaire:
    i = inv.ouvrir(s, qui, Ouverture(JOUR, m.courant.id, criteres=Criteres(matieres=(m.a2.id,))))
    i = inv.compter(
        s,
        qui,
        i.id,
        i.version,
        [Comptage(i.lignes[0].id, {"compte": Decimal(399), "justification": "écart vu"})],
    )
    if statut in (VI, AN):
        i = inv.valider(s, qui, i.id, i.version)
    if statut == AN:
        i = inv.annuler(s, qui, i.id, i.version, "essai")
    if statut == AB:
        i = inv.abandonner(s, qui, i.id, i.version, "essai")
    return i


@pytest.mark.parametrize("statut", [OU, VI, AB, AN])
def test_table_des_inventaires(s: Session, statut: StatutInventaire) -> None:
    """20 cas : chaque statut × geste donne le code et le statut attendus."""
    m = monde(s)
    qui = acteur(s)
    ecarts = []
    for geste, faire in _gestes_inventaire(m).items():
        point = s.begin_nested()
        i = _inventaire_en_etat(s, qui, m, statut)
        try:
            faire(s, qui, i)
            code = 200
        except Refus as refus:
            code = refus.http
        vu = (code, s.get_one(Inventaire, i.id).statut)
        point.rollback()
        if vu != ATTENDU_INVENTAIRE[(statut, geste)]:
            ecarts.append(f"{statut} {geste}: {vu} ≠ {ATTENDU_INVENTAIRE[(statut, geste)]}")
    assert ecarts == []
