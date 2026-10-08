"""Droits par route (`droit(...)`) et droits fins par geste (ARCHITECTURE § 5.2 ; héritage D3, K2).

**Interdit par défaut** : chaque route nomme ses rôles, `dependencies=[droit(D, A)]`. Pas de
passe-droit implicite : la direction est nommée dans chaque route qui lui est ouverte,
l'administrateur technique seulement dans les routes techniques. La garde porte ses rôles
(`.roles`), lus par la matrice (`securite.matrice`) et par l'essai qui vérifie que toute route
est gardée.

Les droits fins (un geste dans une route ouverte à plusieurs rôles) sont déclarés une fois dans
`GESTES` : `exiger(qui, "liberer_quarantaine")` ; `/moi` les rend à l'écran (`droits`).
"""

from __future__ import annotations

from fastapi import Depends, params

from gestion_mp_pro.api.dependances import ActeurDep, ActeurProtocole
from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.services.comptes import message_refus

D, A, L, T = Role.direction, Role.achats, Role.alimentation, Role.administrateur
C: tuple[Role, ...] = (D, A, L)
"""Les trois rôles métier."""
TOUS: tuple[Role, ...] = (D, A, L, T)
"""Tous les comptes connectés, administrateur compris."""

ATTRIBUT_ROLES = "roles"


def droit(*roles: Role) -> params.Depends:
    """La garde d'une route : seuls ces rôles passent (403 sinon, 401 sans session)."""
    if not roles:
        raise ValueError("droit() nomme au moins un rôle")
    permis = frozenset(Role(r) for r in roles)
    message = message_refus(permis)

    def garde(qui: ActeurDep) -> ActeurProtocole:
        """Refuse un rôle qui n'est pas dans la liste."""
        if qui.role not in permis:
            raise Refus.droit(message)
        return qui

    setattr(garde, ATTRIBUT_ROLES, permis)
    garde.__name__ = "droit_" + "_".join(sorted(permis))
    return Depends(garde)


GESTES: dict[str, frozenset[str]] = {
    "voir_prix": frozenset({D, A}),
    "liberer_quarantaine": frozenset({D, A}),
    "mettre_en_quarantaine": frozenset({D, A, L}),
    "approuver": frozenset({D}),
    "monter": frozenset({D, L}),
    "clore_periode": frozenset({D}),
    "gerer_comptes": frozenset({D, T}),
}
"""Droits fins (ARCHITECTURE § 5.2) ; un domaine ajoute les siens par `declarer_geste`."""


def declarer_geste(nom: str, *roles: Role) -> None:
    """Déclare (ou redéclare) un droit fin."""
    GESTES[nom] = frozenset(Role(r) for r in roles)


def peut(qui: ActeurProtocole, geste: str) -> bool:
    """Le rôle de la personne a-t-il ce geste ?"""
    return qui.role in GESTES[geste]


def exiger(qui: ActeurProtocole, geste: str) -> None:
    """403 avec le message de Gestion MP si le rôle n'a pas ce geste."""
    if not peut(qui, geste):
        raise Refus.droit(message_refus(GESTES[geste]))


def gestes_de(role: str) -> list[str]:
    """Les gestes permis à un rôle, triés (champ `droits` de `/moi`)."""
    return sorted(nom for nom, roles in GESTES.items() if role in roles)
