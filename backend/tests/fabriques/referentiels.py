"""Fabriques des référentiels (lot D1) : de quoi bâtir un essai de n'importe quel domaine.

Chaque fonction écrit **directement en base** (sans journal ni contrôle de service : c'est un
décor d'essai) et rend l'identifiant de ce qu'elle crée. Deux façons de l'appeler :

- sans `s` : une session à elle, validée aussitôt (la donnée est vue par l'API) ;
- avec `s=` : dans la transaction de l'essai (annulée à la fin, sans trace).

Les codes, noms et références sont uniques par défaut (compteur + suffixe aléatoire) : les
essais partagent la base de la séance, et `test_migrations` peut la remigrer entre-temps.

    from fabriques.referentiels import fournisseur, matiere, devise, magasin, poste_frais

    f = fournisseur(devise="USD", pays="TURKEY")
    m = matiere(fournisseur_id=f, prix="2.5", devise="USD")      # rôle Poil, en service
    cuir = matiere(role="Cuir", unite_prix="ml", prix="0.5", densite="0.014")
    q = qualite(recette={m: 100}, poids={"Poil": "1.2"})          # une qualité minimale
    principal, quarantaine = magasin_seme("stock_courant"), magasin_seme("quarantaine")
"""

from __future__ import annotations

import itertools
import random
import string
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.db import fabrique as fabrique_de_sessions
from gestion_mp_pro.modeles import (
    CodeDouanier,
    Composition,
    Couleur,
    Devise,
    DeviseCours,
    Fournisseur,
    Magasin,
    Matiere,
    PosteFrais,
    Qualite,
    QualitePoids,
    Recette,
    RoleNomenclature,
    Titrage,
    TypeFil,
)
from gestion_mp_pro.modeles.enums import CleRepartition, NatureFrais, TypeMagasin, UnitePrix

__all__ = [
    "code_douanier",
    "devise",
    "fournisseur",
    "magasin",
    "magasin_seme",
    "matiere",
    "poste_frais",
    "poste_seme",
    "qualite",
    "role_id",
    "stock_initial",
    "unique",
    "valeur_classification",
]

_RANG = itertools.count(1)
_GRAINE = "".join(random.choices(string.ascii_uppercase, k=3))
ROLES_LINEAIRES = ("Cuir", "Franges", "Ruban")
CLASSIFICATION: dict[str, type[Composition | TypeFil | Titrage | Couleur]] = {
    "composition": Composition,
    "type_fil": TypeFil,
    "titrage": Titrage,
    "couleur": Couleur,
}


def unique(prefixe: str) -> str:
    """Un texte unique dans la séance : « F-ABC-12 »."""
    return f"{prefixe}-{_GRAINE}-{next(_RANG)}"


def _ecrire[T](s: Session | None, faire: Callable[[Session], T]) -> T:
    """Exécute `faire` dans la session donnée (flush) ou dans une session à soi (commit)."""
    if s is not None:
        resultat = faire(s)
        s.flush()
        return resultat
    with fabrique_de_sessions()() as propre, propre.begin():
        resultat = faire(propre)
        propre.flush()
        return resultat


def role_id(code: str = "Poil", s: Session | None = None) -> int:
    """L'id d'un rôle de nomenclature semé (Poil, Chaîne, Trame, Colle, Cuir, Franges…)."""
    return _ecrire(
        s,
        lambda x: x.scalars(select(RoleNomenclature.id).where(RoleNomenclature.code == code)).one(),
    )


def valeur_classification(
    liste: str, code: str | None = None, *, s: Session | None = None, **champs: Any
) -> int:
    """Une valeur de classification (`composition`, `type_fil`, `titrage`, `couleur`)."""
    modele = CLASSIFICATION[liste]

    def faire(x: Session) -> int:
        valeur = modele(code=code or unique(liste[:3].upper()), **champs)
        x.add(valeur)
        x.flush()
        return valeur.id

    return _ecrire(s, faire)


def devise(
    code: str | None = None,
    *,
    nom: str = "Devise d'essai",
    cours: str = "10",
    actif: bool = True,
    s: Session | None = None,
) -> str:
    """Une devise (code de trois lettres, tiré au hasard s'il n'est pas donné) ; rend le code."""

    def faire(x: Session) -> str:
        choisi = code
        while choisi is None or (code is None and x.get(Devise, choisi) is not None):
            choisi = "".join(random.choices(string.ascii_uppercase, k=3))
        x.add(Devise(code=choisi, nom=nom, cours=Decimal(cours), actif=actif))
        x.flush()
        x.add(DeviseCours(devise=choisi, cours=Decimal(cours)))
        return choisi

    return _ecrire(s, faire)


def fournisseur(
    nom: str | None = None,
    *,
    devise: str = "MAD",
    pays: str = "",
    delai_jours: int = 60,
    actif: bool = True,
    s: Session | None = None,
    **champs: Any,
) -> int:
    """Un fournisseur (nom unique par défaut), en dirhams, délai 60 j, en service."""

    def faire(x: Session) -> int:
        f = Fournisseur(
            nom=nom or unique("Fournisseur"),
            devise=devise,
            pays=pays.upper(),
            delai_jours=delai_jours,
            actif=actif,
            **champs,
        )
        x.add(f)
        x.flush()
        return f.id

    return _ecrire(s, faire)


def matiere(
    reference: str | None = None,
    *,
    role: str = "Poil",
    fournisseur_id: int | None = None,
    prix: str = "10",
    devise: str = "MAD",
    unite_prix: str = "kg",
    densite: str | None = None,
    actif: bool = True,
    s: Session | None = None,
    **champs: Any,
) -> int:
    """Une matière en service (référence unique) ; un fournisseur est créé s'il n'est pas donné.

    Un rôle au mètre (Cuir, Franges, Ruban) ou un prix au mètre reçoit une densité de 0,014 kg/ml
    si elle n'est pas donnée (la base l'exige).
    """

    def faire(x: Session) -> int:
        fid = fournisseur_id if fournisseur_id is not None else fournisseur(devise=devise, s=x)
        au_metre = role in ROLES_LINEAIRES or unite_prix == UnitePrix.ml
        m = Matiere(
            reference=reference or unique("REF"),
            role_id=role_id(role, s=x),
            fournisseur_id=fid,
            prix=Decimal(prix),
            devise=devise,
            unite_prix=UnitePrix(unite_prix),
            densite=Decimal(densite if densite is not None else ("0.014" if au_metre else "0")),
            actif=actif,
            **champs,
        )
        x.add(m)
        x.flush()
        return m.id

    return _ecrire(s, faire)


def magasin(
    code: str | None = None,
    *,
    type: str = TypeMagasin.stock_courant,  # noqa: A002 — le nom de la colonne
    nom: str = "",
    actif: bool = True,
    s: Session | None = None,
) -> int:
    """Un magasin (courant par défaut, `type="quarantaine"` pour une quarantaine)."""

    def faire(x: Session) -> int:
        g = Magasin(code=code or unique("MAG"), nom=nom, type=TypeMagasin(type), actif=actif)
        x.add(g)
        x.flush()
        return g.id

    return _ecrire(s, faire)


def magasin_seme(type: str = TypeMagasin.stock_courant, s: Session | None = None) -> int:  # noqa: A002
    """Le premier magasin semé d'un type : « Magasin principal » ou « Quarantaine »."""
    return _ecrire(
        s,
        lambda x: (
            x.scalars(
                select(Magasin.id).where(Magasin.type == TypeMagasin(type)).order_by(Magasin.id)
            ).first()
            or magasin(type=type, s=x)
        ),
    )


def poste_frais(
    code: str | None = None,
    *,
    libelle: str = "Poste d'essai",
    cle: str = CleRepartition.valeur,
    recuperable: bool = False,
    nature: str = NatureFrais.autre,
    s: Session | None = None,
) -> int:
    """Un poste de frais d'importation (à la valeur, non récupérable, nature « autre »)."""

    def faire(x: Session) -> int:
        p = PosteFrais(
            code=code or unique("P")[-16:].replace("-", "_"),
            libelle=libelle,
            cle=CleRepartition(cle),
            recuperable=recuperable,
            nature=NatureFrais(nature),
            ordre=900,
        )
        x.add(p)
        x.flush()
        return p.id

    return _ecrire(s, faire)


def poste_seme(code: str = "DD", s: Session | None = None) -> int:
    """L'id d'un poste semé : DD, TPI, TVA, PORT, FRET, ASSUR, TRANSIT, TIMBRE, INT_OC…"""
    return _ecrire(
        s, lambda x: x.scalars(select(PosteFrais.id).where(PosteFrais.code == code)).one()
    )


def code_douanier(
    code: str | None = None, *, taux: str = "0.1", actif: bool = True, s: Session | None = None
) -> int:
    """Un code douanier (taux de droits en fraction : 0,1 = 10 %)."""

    def faire(x: Session) -> int:
        choisi = code or f"5402.{next(_RANG):04d}.{random.randint(10, 99)}"
        c = CodeDouanier(
            code=choisi, libelle="Code d'essai", taux_droits=Decimal(taux), actif=actif
        )
        x.add(c)
        x.flush()
        return c.id

    return _ecrire(s, faire)


def qualite(
    code: str | None = None,
    *,
    recette: dict[int, float | str] | None = None,
    poids: dict[str, float | str] | None = None,
    base_mensuelle: str = "0",
    actif: bool = True,
    s: Session | None = None,
) -> int:
    """Une qualité minimale : poids par rôle (kg/m²) et recette {matière: % de son rôle}.

    Sans contrôle des 100 % (c'est l'affaire du lot D2) : à l'essai de donner une recette juste.
    """

    def faire(x: Session) -> int:
        q = Qualite(code=code or unique("Q"), nom="Qualité d'essai", actif=actif)
        q.base_mensuelle = Decimal(base_mensuelle)
        x.add(q)
        x.flush()
        for role, kg in (poids or {}).items():
            x.add(QualitePoids(qualite_id=q.id, role_id=role_id(role, s=x), poids=Decimal(str(kg))))
        for mid, part in (recette or {}).items():
            x.add(Recette(qualite_id=q.id, matiere_id=mid, pourcentage=Decimal(str(part))))
        return q.id

    return _ecrire(s, faire)


def stock_initial(
    matiere_id: int,
    kg: float | str,
    *,
    magasin_id: int | None = None,
    prix: str = "0",
    devise: str = "MAD",
    le: date | None = None,
    s: Session | None = None,
) -> int:
    """Du stock d'ouverture sur une matière (par le seul chemin, `services/stock`) ; rend le lot."""
    from gestion_mp_pro.modeles.enums import DocumentMouvement, TypeMouvement
    from gestion_mp_pro.services import horloge, lots, stock

    def faire(x: Session) -> int:
        jour = le or horloge.aujourd_hui()
        nouveau = lots.lot_ou_creer(x, matiere_id, unique("L"), jour)
        stock.ecrire(
            x,
            type=TypeMouvement.OUVERTURE,
            lot=nouveau,
            magasin_id=magasin_id or magasin_seme(s=x),
            quantite=Decimal(str(kg)),
            jour=jour,
            piece=stock.Piece(DocumentMouvement.reprise, None, ""),
            auteur_id=None,
            prix=Decimal(prix),
            devise=devise,
        )
        return nouveau.id

    return _ecrire(s, faire)
