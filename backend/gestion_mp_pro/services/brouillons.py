"""« À valider » et « Tout valider » (REGLES B.1.15, S130–S133, C-17 ; API-PRO 122, 123).

Tout ce qui attend d'être validé — opérations de stock (lot D5), ordres de fabrication (D6),
réceptions (D4, direction et achats) — avec ce qui bloquerait sa validation et si le lecteur
peut la faire. « Tout valider » valide dans l'ordre des dates, puis du **rang du même jour**
(ce qui apporte la matière avant ce qui la prend), chacun dans son **point de reprise**
(`SAVEPOINT`) : un document refusé reste brouillon, intact, les autres passent ; la raison est
celle d'une validation à l'unité (la même fonction). Ce que le rôle ne peut pas valider est
rendu dans `ignores` **avec sa raison** (C-17), au lieu d'être écarté en silence.

Chaque domaine **s'inscrit** : son module de service définit `GENRE_BROUILLON`, un objet qui
suit `Genre` (`nom`, `lister`, `valider`) ; les modules connus (`MODULES`) sont importés à la
première lecture. Un domaine pas encore livré n'a simplement pas de brouillons.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from importlib import import_module
from importlib.util import find_spec
from typing import Protocol

from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.services.comptes import Acteur

MODULES = (
    "gestion_mp_pro.services.operations",
    "gestion_mp_pro.services.ordres",
    "gestion_mp_pro.services.receptions",
)
"""Les services qui ont des brouillons (lots D5, D6, D4)."""

RANG_PAR_DEFAUT = 9


@dataclass
class Brouillon:
    """Un document en brouillon, tel que « À valider » le montre."""

    genre: str
    type: str
    id: int
    version: int
    date: date
    libelle: str
    resume: str
    quantite: Decimal
    cree_par: str
    cree_le: datetime | None
    lien: str
    rang: int = RANG_PAR_DEFAUT
    peut_valider: bool = False
    raison: str = ""
    valide_par: str = ""
    blocages: list[str] = field(default_factory=list)


class Genre(Protocol):
    """Ce qu'un domaine inscrit pour ses brouillons."""

    @property
    def nom(self) -> str:
        """« operation », « ordre », « reception »."""

    def lister(self, s: Session, qui: Acteur) -> list[Brouillon]:
        """Ses brouillons, avec blocages, `peut_valider` et la raison sinon."""

    def valider(self, s: Session, qui: Acteur, ident: int, version: int | None) -> str:
        """Valide un brouillon (la même fonction qu'à l'unité) ; rend son numéro."""


GENRES: dict[str, Genre] = {}
"""Les genres inscrits, par nom."""


def inscrire(genre: Genre) -> None:
    """Inscrit (ou réinscrit) un genre de brouillon."""
    GENRES[genre.nom] = genre


def _charger() -> dict[str, Genre]:
    """Importe les services connus qui existent (ils s'inscrivent à l'import)."""
    for module in MODULES:
        if module not in _CHARGES and find_spec(module) is not None:
            charge = import_module(module)
            genre = getattr(charge, "GENRE_BROUILLON", None)
            if genre is not None:
                inscrire(genre)
            _CHARGES.add(module)
    return GENRES


_CHARGES: set[str] = set()


@dataclass
class Brouillons:
    """Route 122 : les brouillons par genre, la liste dans l'ordre de validation, les totaux."""

    lignes: list[Brouillon]
    ordres: list[Brouillon]
    operations: list[Brouillon]
    receptions: list[Brouillon]
    nombre: int
    bloques: int
    validables: int


def _cle(x: Brouillon) -> tuple[date, int, int]:
    """Date, rang du même jour, numéro (S131)."""
    return (x.date, x.rang, x.id)


def lister(s: Session, qui: Acteur) -> Brouillons:
    """Route 122 : du plus ancien au plus récent, chacun avec ce qui le ferait refuser."""
    tous = sorted((x for g in _charger().values() for x in g.lister(s, qui)), key=_cle)
    return Brouillons(
        lignes=tous,
        ordres=[x for x in tous if x.genre == "ordre"],
        operations=[x for x in tous if x.genre == "operation"],
        receptions=[x for x in tous if x.genre == "reception"],
        nombre=len(tous),
        bloques=sum(1 for x in tous if x.blocages),
        validables=sum(1 for x in tous if x.peut_valider and not x.blocages),
    )


@dataclass(frozen=True)
class Choix:
    """Un document choisi : son genre, son numéro, la version lue (facultative)."""

    genre: str
    id: int
    version: int | None = None


@dataclass
class Issue:
    """Ce qu'est devenu un document : validé (son numéro) ou refusé / ignoré (la raison)."""

    genre: str
    type: str
    id: int
    date: date | None
    libelle: str
    resume: str
    lien: str
    numero: str = ""
    raison: str = ""


@dataclass
class ResultatValidationGroupee:
    """Route 123 : validés, refusés (restés brouillons), ignorés (le rôle ne peut pas)."""

    valides: list[Issue] = field(default_factory=list)
    refuses: list[Issue] = field(default_factory=list)
    ignores: list[Issue] = field(default_factory=list)


def _issue(x: Brouillon, *, numero: str = "", raison: str = "") -> Issue:
    return Issue(x.genre, x.type, x.id, x.date, x.libelle, x.resume, x.lien, numero, raison)


def _vises(s: Session, qui: Acteur, choix: list[Choix] | None) -> list[tuple[Brouillon, Choix]]:
    """Les brouillons visés, dans l'ordre de validation ; un document choisi qui n'est plus en
    brouillon (ou inconnu) est quand même tenté : sa raison est celle du geste à l'unité."""
    liste = lister(s, qui).lignes
    if choix is None:
        return [(x, Choix(x.genre, x.id)) for x in liste]
    par_cle = {(x.genre, x.id): x for x in liste}
    vises = []
    for c in choix:
        x = par_cle.get((c.genre, c.id))
        if x is None:
            x = Brouillon(c.genre, "", c.id, 0, date.min, "", "", Decimal(0), "", None, "",
                          peut_valider=True)  # fmt: skip
        vises.append((x, c))
    return sorted(vises, key=lambda v: _cle(v[0]))


def tout_valider(s: Session, qui: Acteur, choix: list[Choix] | None) -> ResultatValidationGroupee:
    """Route 123 : `choix` vide (`None`) = tout ce que ce compte peut valider."""
    genres = _charger()
    resultat = ResultatValidationGroupee()
    for x, c in _vises(s, qui, choix):
        genre = genres.get(c.genre)
        if genre is None or not x.peut_valider:
            raison = x.raison or "Ce genre de document ne se valide pas ici."
            resultat.ignores.append(_issue(x, raison=raison))
            continue
        point = s.begin_nested()
        try:
            numero = genre.valider(s, qui, c.id, c.version)
        except Refus as refus:
            point.rollback()
            resultat.refuses.append(_issue(x, raison=refus.detail))
            continue
        except (IntegrityError, DataError):
            point.rollback()
            resultat.refuses.append(
                _issue(x, raison="Cette saisie contredit une règle de la base : la vérifier.")
            )
            continue
        point.commit()
        resultat.valides.append(_issue(x, numero=numero))
    return resultat
