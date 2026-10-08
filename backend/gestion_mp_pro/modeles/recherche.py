"""`texte_recherche` : le texte cherché « à la frappe », tenu à jour avant chaque flush (§ 1.4).

`normaliser` est la règle unique, la même que l'écran (E0) : décomposition NFD, accents
retirés (U+0300–U+036F), minuscules, blancs réduits à un espace. Le texte d'une fiche met
bout à bout ses champs cherchables **et** ceux de ses voisins (le nom du fournisseur d'un bon,
la référence de la matière d'un lot) ; renommer un voisin met à jour les fiches qui le citent.

L'écouteur `before_flush` couvre tout ce qui passe par l'ORM. Une écriture SQL directe (la
reprise) appelle `recalculer_table(session, Modele)` après coup.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable
from typing import Any

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles.achats import Commande
from gestion_mp_pro.modeles.base import Base
from gestion_mp_pro.modeles.catalogue import Fournisseur, Matiere
from gestion_mp_pro.modeles.importations import Dossier
from gestion_mp_pro.modeles.metiers import Metier
from gestion_mp_pro.modeles.production import Ordre
from gestion_mp_pro.modeles.qualites import Qualite
from gestion_mp_pro.modeles.receptions import Reception
from gestion_mp_pro.modeles.referentiels import Composition, Couleur, Titrage, TypeFil
from gestion_mp_pro.modeles.stock import Lot

_BLANCS = re.compile(r"\s+")
_ACCENTS = range(0x300, 0x370)
"""Les diacritiques combinants (U+0300–U+036F) retirés après décomposition."""


def normaliser(texte: str) -> str:
    """« Écru  Polyester » → « ecru polyester » (règle unique, écran et serveur)."""
    decompose = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in decompose if ord(c) not in _ACCENTS)
    return _BLANCS.sub(" ", sans_accents.lower()).strip()


def _code(s: Session, modele: type[Base], ident: int | None) -> str | None:
    """Le code (ou le nom) d'une fiche voisine, lu dans la session ou en base."""
    if ident is None:
        return None
    voisin = s.get(modele, ident)
    if voisin is None:
        return None
    return str(getattr(voisin, "code", None) or getattr(voisin, "nom", ""))


def _matiere(s: Session, m: Matiere) -> Iterable[str | None]:
    """Référence, désignation, classification, fournisseur, code couleur, groupe."""
    return (
        m.reference,
        m.designation,
        _code(s, Composition, m.composition_id),
        _code(s, TypeFil, m.type_fil_id),
        _code(s, Titrage, m.titrage_id),
        _code(s, Couleur, m.couleur_id),
        _code(s, Fournisseur, m.fournisseur_id),
        m.couleur_code,
        m.groupe_equiv,
    )


def _lot(s: Session, lot: Lot) -> Iterable[str | None]:
    """Numéro du lot, référence et désignation de sa matière."""
    matiere = s.get(Matiere, lot.matiere_id) if lot.matiere_id is not None else None
    return (lot.numero, *((matiere.reference, matiere.designation) if matiere else ()))


TEXTES: dict[type[Base], Callable[[Session, Any], Iterable[str | None]]] = {
    Fournisseur: lambda s, f: (f.nom, f.code, f.pays, f.contact),
    Matiere: _matiere,
    Lot: _lot,
    Qualite: lambda s, q: (q.code, q.nom),
    Commande: lambda s, c: (
        c.numero,
        _code(s, Fournisseur, c.fournisseur_id),
        c.conteneur,
        c.navire,
    ),
    Reception: lambda s, r: (
        r.numero,
        _code(s, Fournisseur, r.fournisseur_id),
        r.numero_bl,
        r.controle_par,
    ),
    Dossier: lambda s, d: (d.numero, d.libelle, d.banque),
    Ordre: lambda s, o: (o.numero, _code(s, Metier, o.metier_id), o.commentaire),
}
"""Les champs cherchables de chaque table qui porte `texte_recherche`."""

VOISINS: dict[type[Base], tuple[str, tuple[tuple[type[Base], str], ...]]] = {
    Fournisseur: ("nom", ((Matiere, "fournisseur_id"), (Commande, "fournisseur_id"),
                          (Reception, "fournisseur_id"))),
    Matiere: ("reference", ((Lot, "matiere_id"),)),
    Composition: ("code", ((Matiere, "composition_id"),)),
    TypeFil: ("code", ((Matiere, "type_fil_id"),)),
    Titrage: ("code", ((Matiere, "titrage_id"),)),
    Couleur: ("code", ((Matiere, "couleur_id"),)),
    Metier: ("code", ((Ordre, "metier_id"),)),
}  # fmt: skip
"""Fiche renommée (attribut) → fiches qui la citent dans leur texte (table, clé)."""


def texte_de(s: Session, objet: Base) -> str:
    """Le `texte_recherche` d'une fiche."""
    morceaux = TEXTES[type(objet)](s, objet)
    return normaliser(" ".join(m for m in morceaux if m))


def recalculer(s: Session, objet: Base) -> None:
    """Remet à jour le `texte_recherche` d'une fiche (sans écriture s'il n'a pas changé)."""
    texte = texte_de(s, objet)
    if getattr(objet, "texte_recherche", None) != texte:
        objet.texte_recherche = texte  # type: ignore[attr-defined]


def recalculer_table(s: Session, modele: type[Base]) -> int:
    """Recalcule toute une table (après une écriture SQL directe) ; rend le nombre de fiches."""
    fiches = list(s.scalars(select(modele)))
    for fiche in fiches:
        recalculer(s, fiche)
    return len(fiches)


def _renomme(objet: Base, attribut: str) -> bool:
    """Vrai si l'attribut cité par d'autres fiches vient de changer."""
    return bool(inspect(objet).attrs[attribut].history.has_changes())


@event.listens_for(Session, "before_flush")
def _tenir_a_jour(s: Session, _contexte: object, _instances: object) -> None:
    """Avant chaque flush : fiches nouvelles ou modifiées, puis celles qui citent un renommé."""
    with s.no_autoflush:
        for objet in [*s.new, *s.dirty]:
            if type(objet) in TEXTES:
                recalculer(s, objet)
        for objet in list(s.dirty):
            voisins = VOISINS.get(type(objet))
            if voisins is None or not _renomme(objet, voisins[0]):
                continue
            ident = inspect(objet).identity
            for modele, cle in voisins[1]:
                for fiche in s.scalars(select(modele).where(getattr(modele, cle) == ident[0])):
                    recalculer(s, fiche)
