"""Qui fait quoi dans les opérations de stock : **une table** (API-PRO § 1.13, REGLES S82, S100).

- ouverture, ajustement, retour au fournisseur : direction, achats ;
- retour des machines : direction, alimentation ;
- transfert : direction, achats, alimentation ;
- motif « Libération de quarantaine » (sortir un lot d'une quarantaine) : direction, achats
  seulement — décision de Mohamed : libérer est une décision de la direction ou des achats,
  après contrôle (le message le dit : REGLES OR24 nommait les seuls achats, RESTES3) ;
- motif « Mise en quarantaine » : direction, achats, alimentation (l'atelier y met un lot
  douteux, avec ses observations).

La garde de chaque route est `droit(*C)` ; le service tranche ici selon le type (403 au
message de Gestion MP, OR2, OR24, OR33, C-01).
"""

from __future__ import annotations

from collections.abc import Iterable

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles.enums import Role, SerieNumero, TypeMouvement, TypeOperation
from gestion_mp_pro.services.comptes import libelle_role
from gestion_mp_pro.services.referentiels import TYPES_MOTIF

D, A, L = Role.direction, Role.achats, Role.alimentation
_TYPES = {t.value for t in TypeOperation}

LIBELLES: dict[TypeOperation, str] = {
    TypeOperation(t.value): libelle for t, (libelle, _) in TYPES_MOTIF.items() if t.value in _TYPES
}
"""Libellés des types (S80) : ceux de `GET /motifs` (lot D1, une seule table)."""

DROITS: dict[TypeOperation, frozenset[str]] = {
    TypeOperation(t.value): frozenset(roles)
    for t, (_, roles) in TYPES_MOTIF.items()
    if t.value in _TYPES
}
"""Les rôles qui créent, modifient, suppriment, valident et annulent chaque type : la table de
`services.referentiels.TYPES_MOTIF` (servie à l'écran par `GET /motifs`)."""

LIBERATION = "Libération de quarantaine"
MISE_EN_QUARANTAINE = "Mise en quarantaine"
LIBERER: frozenset[str] = frozenset({D, A})
"""Sortir de la matière d'une quarantaine (décision de Mohamed : direction et achats)."""
METTRE_EN_QUARANTAINE: frozenset[str] = frozenset({D, A, L})
"""Mettre un lot douteux en quarantaine (l'alimentation aussi)."""

SERIES: dict[TypeOperation, SerieNumero] = {
    TypeOperation.ouverture: SerieNumero.OUV,
    TypeOperation.retour_machine: SerieNumero.RET,
    TypeOperation.transfert: SerieNumero.TRF,
    TypeOperation.ajustement: SerieNumero.AJU,
    TypeOperation.retour_fournisseur: SerieNumero.RFO,
}
"""Série du numéro donné à la validation (S81, M65)."""

TYPE_MOUVEMENT: dict[TypeOperation, TypeMouvement] = {
    TypeOperation.ouverture: TypeMouvement.OUVERTURE,
    TypeOperation.retour_machine: TypeMouvement.RETOUR_MACHINE,
    TypeOperation.ajustement: TypeMouvement.AJUSTEMENT,
    TypeOperation.retour_fournisseur: TypeMouvement.RETOUR_FOURNISSEUR,
    TypeOperation.transfert: TypeMouvement.TRANSFERT,
}
"""Type des mouvements écrits (S86)."""

RANG: dict[str, int] = {
    TypeOperation.ouverture: 0,
    TypeOperation.transfert: 1,
    TypeOperation.ajustement: 2,
    "ordre": 3,
    TypeOperation.retour_machine: 4,
    TypeOperation.retour_fournisseur: 5,
}
"""Le même jour, ce qui apporte la matière passe avant ce qui la prend (S131)."""

REFUS_LIBERATION = (
    "Libérer une quarantaine est une décision de la direction ou des achats, après contrôle de "
    "la matière."
)
"""OR24, OR33 : la phrase de Gestion MP nommait les achats seuls ; la règle (et le droit servi)
est « direction ou achats » — la phrase le dit (RESTES3, F6)."""


def type_operation(type_: str) -> TypeOperation:
    """Le type, ou 422 « Type d'opération inconnu. » (OR1)."""
    try:
        return TypeOperation(type_)
    except ValueError:
        raise Refus.saisie("Type d'opération inconnu.", code="valeur_inconnue") from None


def noms_des_roles(roles: Iterable[str]) -> str:
    """« responsable achats, responsable alimentation machines » (la direction n'est citée que
    seule, comme les refus de Gestion MP)."""
    permis = set(roles)
    noms = [libelle_role(r).lower() for r in (A, L) if r in permis]
    return ", ".join(noms) if noms else "la direction"


def reserve_a(type_: TypeOperation) -> str:
    """« « Stock d'ouverture » est réservé à : responsable achats. » (OR2)."""
    return f"« {LIBELLES[type_]} » est réservé à : {noms_des_roles(DROITS[type_])}."


def peut_type(role: str, type_: TypeOperation) -> bool:
    """Ce rôle fait-il ce type d'opération ?"""
    return role in DROITS[type_]


def autoriser(role: str, type_: TypeOperation) -> None:
    """403 si ce rôle ne fait pas ce type d'opération (OR2)."""
    if not peut_type(role, type_):
        raise Refus.droit(reserve_a(type_))


def types_permis(role: str) -> list[TypeOperation]:
    """Les types que ce rôle fait (onglets de l'écran, export 241)."""
    return [t for t in TypeOperation if role in DROITS[t]]


def peut_liberer(role: str) -> bool:
    """Ce rôle sort-il de la matière d'une quarantaine ?"""
    return role in LIBERER
