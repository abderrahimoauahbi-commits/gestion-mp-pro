"""Journal d'audit : une ligne par geste, avec avant/après ; historique d'une fiche (§ 5.5).

Le journal s'écrit dans la **transaction du geste** (un refus l'annule avec lui), n'est jamais
modifié ni purgé, et ne se relit plus comme donnée (MODELE-DONNEES § 4). Trois façons d'écrire :

- `journal(s, qui, action, objet, objet_id, ...)` : la ligne brute (avant/après donnés) ;
- `creation(s, qui, action, fiche)` / `suppression(...)` : la fiche entière après / avant ;
- `with suivre(s, qui, action, fiche) as geste:` : photo de la fiche à l'entrée, comparée à la
  sortie ; seuls les champs changés vont dans `avant` / `apres` (robuste aux `flush`).

Les prix restent dans le journal (lu par la direction ; l'historique d'une fiche passe par le
filtre des prix pour les autres rôles). Les secrets (empreintes de code, de jeton) n'y entrent
jamais. `verifier_version` donne le 409 « modifiée entre-temps par {nom} ({heure}) »
(API-PRO § 0.1).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Base, Journal
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import ObjetJournal
from gestion_mp_pro.services import horloge

SYSTEME = "système"
"""Nom écrit quand le geste n'a pas d'auteur (tâche de fond, enrôlement d'un appareil)."""

TECHNIQUES = frozenset(
    {"version", "texte_recherche", "modifie_le", "modifie_par_id", "cree_le", "cree_par_id"}
)
"""Colonnes tenues par le système : elles changent à chaque geste et ne disent rien."""

SECRETES = frozenset(
    {"empreinte_code", "empreinte", "empreinte_jeton", "empreinte_enrolement", "code_change_le"}
)
"""Colonnes qui ne doivent jamais apparaître dans le journal (secrets et leurs dates)."""


class Qui(Protocol):
    """Ce que le journal sait de l'auteur d'un geste (`services.comptes.Acteur`)."""

    @property
    def id(self) -> int:
        """Identifiant du compte."""

    @property
    def nom(self) -> str:
        """Nom affiché, copié dans la ligne (le journal reste lisible si le nom change)."""

    @property
    def role(self) -> str:
        """Rôle au moment du geste."""

    @property
    def requete(self) -> str:
        """Identifiant de la requête HTTP (relie au journal du serveur)."""

    @property
    def adresse(self) -> str:
        """Adresse réseau d'où vient le geste."""


def valeur_json(valeur: object) -> object:
    """Une valeur de colonne en JSON : nombres pour les `NUMERIC`, ISO pour les dates."""
    if isinstance(valeur, Decimal):
        return int(valeur) if valeur == valeur.to_integral_value() else float(valeur)
    if isinstance(valeur, dt.datetime | dt.date):
        return valeur.isoformat()
    if isinstance(valeur, Enum):
        return valeur.value
    return valeur


def photo(fiche: Base) -> dict[str, object]:
    """Les colonnes d'une fiche telles qu'elles sont (hors colonnes techniques et secrets)."""
    etat = inspect(fiche)
    return {
        attribut.key: valeur_json(getattr(fiche, attribut.key))
        for attribut in etat.mapper.column_attrs
        if attribut.key not in TECHNIQUES and attribut.key not in SECRETES
    }


def differences(
    avant: Mapping[str, object], apres: Mapping[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    """Les seuls champs changés : `({champ: avant}, {champ: après})`."""
    cles = [c for c in apres if avant.get(c) != apres.get(c)]
    cles += [c for c in avant if c not in apres]
    return {c: avant.get(c) for c in cles}, {c: apres.get(c) for c in cles}


def objet_de(fiche: Base) -> ObjetJournal:
    """L'objet du journal d'une fiche : le nom de sa table (liste fermée `ObjetJournal`)."""
    return ObjetJournal(str(getattr(fiche, "__tablename__", "")))


def journal(
    s: Session,
    qui: Qui | None,
    action: str,
    objet: ObjetJournal | str = ObjetJournal.systeme,
    objet_id: int | None = None,
    *,
    numero: str = "",
    detail: str = "",
    avant: Mapping[str, object] | None = None,
    apres: Mapping[str, object] | None = None,
) -> Journal:
    """Ajoute une ligne au journal, dans la transaction du geste (`SEC:159-176`, § 0.3)."""
    ligne = Journal(
        quand=horloge.maintenant(),
        utilisateur_id=qui.id if qui is not None else None,
        utilisateur_nom=(qui.nom if qui is not None else SYSTEME)[: L.NOM_PERSONNE],
        role=(str(qui.role) if qui is not None else "")[: L.ROLE],
        action=action[: L.ACTION],
        objet=ObjetJournal(objet),
        objet_id=objet_id,
        numero=(numero or "")[: L.NUMERO_DOCUMENT],
        detail=(detail or "")[: L.DETAIL],
        avant=dict(avant) if avant else None,
        apres=dict(apres) if apres else None,
        requete=(qui.requete if qui is not None else "")[: L.REQUETE],
        adresse=(qui.adresse if qui is not None else "")[: L.ADRESSE_IP],
    )
    s.add(ligne)
    return ligne


def creation(
    s: Session, qui: Qui | None, action: str, fiche: Base, *, numero: str = "", detail: str = ""
) -> Journal:
    """La création d'une fiche : `apres` = la fiche entière (l'`id` est obtenu par un flush)."""
    s.flush()
    ident = getattr(fiche, "id", None)
    return journal(
        s,
        qui,
        action,
        objet_de(fiche),
        ident if isinstance(ident, int) else None,
        numero=numero,
        detail=detail,
        apres=photo(fiche),
    )


def suppression(
    s: Session, qui: Qui | None, action: str, fiche: Base, *, numero: str = "", detail: str = ""
) -> Journal:
    """La suppression d'une fiche (un brouillon) : `avant` = la fiche entière."""
    ident = getattr(fiche, "id", None)
    return journal(
        s,
        qui,
        action,
        objet_de(fiche),
        ident if isinstance(ident, int) else None,
        numero=numero,
        detail=detail,
        avant=photo(fiche),
    )


@dataclass
class Geste:
    """Ce que l'appelant peut compléter dans un bloc `suivre` (numéro, phrase, ligne écrite)."""

    numero: str = ""
    detail: str = ""
    ligne: Journal | None = None


@contextmanager
def suivre(
    s: Session, qui: Qui | None, action: str, fiche: Base, *, numero: str = "", detail: str = ""
) -> Iterator[Geste]:
    """Photo de la fiche à l'entrée, comparée à la sortie : la ligne porte les seuls changements.

    Rien n'est écrit si le bloc lève une exception (le geste est de toute façon annulé).
    """
    avant = photo(fiche)
    geste = Geste(numero=numero, detail=detail)
    yield geste
    a, b = differences(avant, photo(fiche))
    ident = getattr(fiche, "id", None)
    geste.ligne = journal(
        s,
        qui,
        action,
        objet_de(fiche),
        ident if isinstance(ident, int) else None,
        numero=geste.numero,
        detail=geste.detail,
        avant=a,
        apres=b,
    )


def historique(s: Session, objet: ObjetJournal | str, objet_id: int) -> list[Journal]:
    """Les lignes du journal d'une fiche, dans l'ordre où elles ont été écrites."""
    requete = (
        select(Journal)
        .where(Journal.objet == ObjetJournal(objet), Journal.objet_id == objet_id)
        .order_by(Journal.id)
    )
    return list(s.scalars(requete))


def derniere_ligne(s: Session, objet: ObjetJournal | str, objet_id: int) -> Journal | None:
    """La dernière ligne du journal d'une fiche (l'auteur de sa version courante)."""
    requete = (
        select(Journal)
        .where(Journal.objet == ObjetJournal(objet), Journal.objet_id == objet_id)
        .order_by(Journal.id.desc())
        .limit(1)
    )
    return s.scalars(requete).first()


def horodatage(instant: dt.datetime) -> str:
    """« 08/10/2026 10:00 » à l'heure de l'usine (ARCHITECTURE § 9.3)."""
    return instant.astimezone(horloge.FUSEAU).strftime("%d/%m/%Y %H:%M")


def verifier_version(
    s: Session, fiche: Base, version_lue: int, quoi: str, *, feminin: bool = True
) -> None:
    """409 `conflit_version` si la fiche a changé depuis sa lecture (API-PRO § 0.1).

    `quoi` commence la phrase (« Cette commande », « Ce compte ») ; l'auteur et l'heure sont
    ceux de la dernière ligne du journal de la fiche.
    """
    actuelle = getattr(fiche, "version", None)
    if actuelle == version_lue:
        return
    ident = getattr(fiche, "id", None)
    ligne = derniere_ligne(s, objet_de(fiche), ident) if isinstance(ident, int) else None
    nom = ligne.utilisateur_nom if ligne is not None else "un autre poste"
    heure = horodatage(ligne.quand) if ligne is not None else "à l'instant"
    modifie, pronom = ("modifiée", "la") if feminin else ("modifié", "le")
    raise Refus.etat(
        f"{quoi} a été {modifie} entre-temps par {nom} ({heure}) : rouvrez-{pronom} pour "
        "repartir de sa dernière version.",
        code="conflit_version",
    )
