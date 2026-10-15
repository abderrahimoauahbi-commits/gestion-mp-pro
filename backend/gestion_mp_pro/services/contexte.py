"""Le contexte de démarrage de l'écran en un appel (route 3 `GET /contexte`, ECRANS-PRO § 2).

Période close, inventaires ouverts (ce qu'ils suspendent), raison sociale, rôles au mètre,
base d'essai, compteurs du menu et alerte du serveur. Deux registres extensibles par les
domaines (aucun fichier de S2 à modifier) :

- `COMPTEURS["alerte_rouge"] = fonction(s, role) -> int | None` (lot D8 : ruptures et
  critiques ; anomalies des contrôles) ; `None` : le compteur ne regarde pas ce rôle ;
- `ALERTES_SERVEUR.append(fonction(s) -> str | None)` (lot D10 : sauvegarde en défaut).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.config import reglages
from gestion_mp_pro.modeles import Inventaire, InventaireMatiere, Magasin, RoleNomenclature
from gestion_mp_pro.modeles.enums import Role, StatutInventaire
from gestion_mp_pro.services import comptes, fonds_de_lot, periode

COMPTEURS: dict[str, Callable[[Session, str], int | None]] = {}
"""Compteurs des pastilles du menu, par nom (déclarés par les domaines)."""

ALERTES_SERVEUR: list[Callable[[Session], str | None]] = []
"""Alertes rouges du `BandeauServeur` (direction et administrateur seulement)."""

VOIENT_LE_SERVEUR = frozenset({Role.direction, Role.administrateur})
ECOUTES_LOCALES = frozenset({"127.0.0.1", "localhost", "::1"})


@dataclass(frozen=True)
class InventaireOuvert:
    """Un inventaire ouvert : ce qu'il suspend (magasin, ou tous ; matières de son périmètre)."""

    id: int
    numero: str
    date: date
    magasin: str | None
    matieres: list[int]


@dataclass(frozen=True)
class Contexte:
    """Ce que l'écran lit une fois au démarrage (puis relit après chaque geste)."""

    societe: str
    date_cloture: date | None
    inventaires_ouverts: list[InventaireOuvert]
    roles_au_metre: list[str]
    base_essai: bool
    compteurs: dict[str, int] = field(default_factory=dict)
    alerte_serveur: str | None = None
    seuil_rebut: float = 0
    """Le seuil de rebut (kg) : l'écran marque les fonds de lot « fond de lot (< 100 g) »."""


def inventaires_ouverts(s: Session) -> list[InventaireOuvert]:
    """Les inventaires ouverts et leur périmètre (suspension limitée, K2)."""
    requete = (
        select(Inventaire, Magasin.nom)
        .outerjoin(Magasin, Magasin.id == Inventaire.magasin_id)
        .where(Inventaire.statut == StatutInventaire.ouvert)
        .order_by(Inventaire.date, Inventaire.id)
    )
    lignes = s.execute(requete).all()
    ids = [inv.id for inv, _ in lignes]
    perimetre: dict[int, list[int]] = {i: [] for i in ids}
    if ids:
        matieres = select(InventaireMatiere.inventaire_id, InventaireMatiere.matiere_id).where(
            InventaireMatiere.inventaire_id.in_(ids)
        )
        for inventaire_id, matiere_id in s.execute(matieres).all():
            perimetre[inventaire_id].append(matiere_id)
    return [
        InventaireOuvert(inv.id, inv.numero, inv.date, nom, sorted(perimetre[inv.id]))
        for inv, nom in lignes
    ]


def alerte_serveur(s: Session) -> str | None:
    """La première alerte du serveur : écoute réseau sans HTTPS, puis celles des domaines."""
    r = reglages()
    if r.ecoute not in ECOUTES_LOCALES and not r.https:
        return (
            "Le serveur écoute le réseau sans HTTPS : les codes y passent en clair. Passer "
            "par Caddy (HTTPS) ou par Tailscale."
        )
    for alerte in ALERTES_SERVEUR:
        texte = alerte(s)
        if texte:
            return texte
    return None


def compteurs(s: Session, role: str) -> dict[str, int]:
    """Les compteurs du menu qui regardent ce rôle."""
    valeurs = {nom: fonction(s, role) for nom, fonction in COMPTEURS.items()}
    return {nom: v for nom, v in valeurs.items() if v is not None}


def contexte(s: Session, role: str) -> Contexte:
    """Le contexte de démarrage pour un rôle."""
    au_metre = s.scalars(
        select(RoleNomenclature.code)
        .where(RoleNomenclature.lineaire)
        .order_by(RoleNomenclature.ordre)
    )
    return Contexte(
        societe=comptes.societe(s),
        date_cloture=periode.fin_de_periode_close(s),
        inventaires_ouverts=inventaires_ouverts(s),
        roles_au_metre=list(au_metre),
        base_essai=reglages().nom_base.endswith("_essai"),
        compteurs=compteurs(s, role),
        alerte_serveur=alerte_serveur(s) if role in VOIENT_LE_SERVEUR else None,
        seuil_rebut=float(fonds_de_lot.seuil(s)),
    )
