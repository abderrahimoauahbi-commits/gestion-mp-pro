"""Classification des matières et rôles de nomenclature (routes 57–63 ; R-REF-05…15).

- Quatre listes (compositions, types de fil, titrages, couleurs), tenues par les achats et la
  direction : code unique **sans tenir compte de la casse** (« pp » et « PP » ne coexistent pas,
  A-12), au plus la longueur de sa colonne (A-06) ; le code se corrige (les matières suivent :
  clé technique `id`) ; une valeur portée ne se supprime pas, elle se désactive — et l'écran est
  averti des matières qui la gardent (A-24).
- Les rôles de nomenclature (Poil, Chaîne, Trame… direction) : le calcul compte au mètre Cuir,
  Franges et Ruban, et eux seuls (rôles de base, qui gardent leur nom et ne se suppriment pas) ;
  un rôle ajouté se renomme librement (clé technique, A-13) et se supprime s'il n'est porté ni
  par une matière ni par un poids > 0 (les poids nuls partent avec lui).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from sqlalchemy import delete, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Composition,
    Couleur,
    InventaireCritere,
    Matiere,
    QualitePoids,
    RecetteVersionLigne,
    RecetteVersionPoids,
    RoleNomenclature,
    Titrage,
    TypeFil,
)
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.services import audit

Valeur = Composition | TypeFil | Titrage | Couleur
ROLES_LINEAIRES = ("Cuir", "Franges", "Ruban")


@dataclass(frozen=True)
class Liste:
    """Une liste de classification : son modèle, sa colonne sur la matière, son libellé."""

    nom: str
    modele: type[Valeur]
    colonne: InstrumentedAttribute[int | None]
    libelle: str


LISTES: dict[str, Liste] = {
    "compositions": Liste("compositions", Composition, Matiere.composition_id, "Composition"),
    "types-fil": Liste("types-fil", TypeFil, Matiere.type_fil_id, "Type de fil"),
    "titrages": Liste("titrages", Titrage, Matiere.titrage_id, "Titrage"),
    "couleurs": Liste("couleurs", Couleur, Matiere.couleur_id, "Couleur"),
}
"""Les listes, par leur nom d'adresse (`/classification/{liste}`)."""


def liste(nom: str) -> Liste:
    """Une liste par son nom (404 « Liste inconnue. »)."""
    if nom not in LISTES:
        raise Refus.introuvable("Liste inconnue.")
    return LISTES[nom]


def _comptes(s: Session, colonne: Any) -> dict[int, int]:
    """Le nombre de lignes par valeur d'une colonne."""
    return dict(
        s.execute(select(colonne, func.count()).where(colonne.is_not(None)).group_by(colonne)).all()
    )


@dataclass
class Lecture:
    """La classification entière : chaque liste, ses valeurs et leurs usages ; les rôles."""

    valeurs: dict[str, list[tuple[Valeur, int]]] = field(default_factory=dict)
    roles: list[tuple[RoleNomenclature, int, int]] = field(default_factory=list)


def lire(s: Session) -> Lecture:
    """Les quatre listes triées par code (avec leurs matières), les rôles par ordre puis code."""
    lecture = Lecture()
    for nom, x in LISTES.items():
        portes = _comptes(s, x.colonne)
        valeurs = [cast(Valeur, v) for v in s.scalars(select(x.modele).order_by(x.modele.code))]
        lecture.valeurs[nom] = [(v, portes.get(v.id, 0)) for v in valeurs]
    matieres = _comptes(s, Matiere.role_id)
    qualites = dict(
        s.execute(
            select(QualitePoids.role_id, func.count())
            .where(QualitePoids.poids > 0)
            .group_by(QualitePoids.role_id)
        ).all()
    )
    roles = s.scalars(
        select(RoleNomenclature).order_by(RoleNomenclature.ordre, RoleNomenclature.code)
    )
    lecture.roles = [(r, matieres.get(r.id, 0), qualites.get(r.id, 0)) for r in roles]
    return lecture


# --- Valeurs ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class ValeurSaisie:
    """Ce qu'on saisit d'une valeur (seuls les champs que sa table possède sont écrits)."""

    code: str
    champs: dict[str, Any]


def _code(s: Session, x: Liste, brut: str, ident: int | None) -> str:
    """Le code nettoyé, dans sa longueur, libre sans tenir compte de la casse."""
    code = brut.strip()
    if not code:
        raise Refus.saisie("Le code est à renseigner.", champs={"code": "obligatoire"})
    longueur = x.modele.__table__.c.code.type.length  # type: ignore[attr-defined]
    if len(code) > longueur:
        raise Refus.saisie(
            f"{x.libelle} : le code tient en {longueur} caractères au plus (« {code} » en a "
            f"{len(code)}).",
            champs={"code": f"{longueur} caractères au plus"},
        )
    autre = s.scalar(
        select(x.modele.code).where(
            func.lower(x.modele.code) == code.lower(), x.modele.id != (ident or 0)
        )
    )
    if autre is not None:
        en_plus = f" (« {code} »)" if autre != code else ""
        raise Refus.etat(f"« {autre} » existe déjà{en_plus}.", code="doublon")
    return code


def _champs(x: Liste, e: ValeurSaisie) -> dict[str, Any]:
    """Les champs que la table possède, textes nettoyés."""
    colonnes = x.modele.__table__.c
    return {
        k: (v.strip() if isinstance(v, str) else v)
        for k, v in e.champs.items()
        if k in colonnes and k not in {"id", "code", "version"}
    }


def valeur(s: Session, x: Liste, ident: int, *, verrou: bool = False) -> Valeur:
    """Une valeur de la liste (404 « Valeur introuvable. »)."""
    v = s.get(x.modele, ident, with_for_update=verrou)
    if v is None:
        raise Refus.introuvable("Valeur introuvable.")
    return cast(Valeur, v)


def ajouter(s: Session, qui: audit.Qui, x: Liste, e: ValeurSaisie) -> Valeur:
    """Une valeur nouvelle (route 61) ; un titrage sans valeur se lit dans son code."""
    code = _code(s, x, e.code, None)
    champs = _champs(x, e)
    if x.modele is Titrage and not champs.get("valeur"):
        valeur_lue, _, unite = code.partition(" ")
        champs["valeur"], champs["unite"] = valeur_lue[: L.VALEUR_TITRAGE], unite[: L.UNITE_TITRAGE]
    v = x.modele(code=code, **champs)
    s.add(v)
    audit.creation(s, qui, f"ajout {x.libelle.lower()}", v, numero=code, detail=code)
    return v


def modifier(
    s: Session, qui: audit.Qui, x: Liste, ident: int, e: ValeurSaisie, *, version: int
) -> tuple[Valeur, str]:
    """Une valeur modifiée (route 62) ; rend aussi l'avertissement d'une valeur désactivée."""
    v = valeur(s, x, ident, verrou=True)
    audit.verifier_version(s, v, version, "Cette valeur")
    code, ancien, etait_active = _code(s, x, e.code, ident), v.code, v.actif
    with audit.suivre(s, qui, f"modification {x.libelle.lower()}", v, numero=code) as geste:
        for k, val in _champs(x, e).items():
            setattr(v, k, val)
        v.code = code
        geste.detail = code if code == ancien else f"{ancien} → {code}"
    s.flush()
    avertissement = ""
    if etait_active and not v.actif:
        portes = s.scalar(select(func.count()).where(x.colonne == v.id)) or 0
        if portes:
            avertissement = (
                f"« {code} » reste porté par {portes} matière(s) : elle ne se choisit plus, ces "
                "matières la gardent."
            )
    return v, avertissement


def supprimer(s: Session, qui: audit.Qui, x: Liste, ident: int, version: int | None) -> None:
    """Une valeur que nulle matière ne porte (route 63 ; X-REF-13)."""
    v = valeur(s, x, ident, verrou=True)
    if version is not None:
        audit.verifier_version(s, v, version, "Cette valeur")
    portes = s.scalar(select(func.count()).where(x.colonne == v.id)) or 0
    if portes:
        raise Refus.etat(
            f"« {v.code} » est porté par {portes} matière(s) : les reclasser d'abord, ou "
            "désactiver la valeur.",
            code="fiche_utilisee",
        )
    if x.modele is Composition and s.scalar(
        select(func.count()).where(InventaireCritere.composition_id == v.id)
    ):
        raise Refus.etat(
            f"« {v.code} » sert de critère à un inventaire : la désactiver plutôt que la "
            "supprimer.",
            code="fiche_utilisee",
        )
    audit.suppression(s, qui, f"suppression {x.libelle.lower()}", v, numero=v.code, detail=v.code)
    s.delete(v)
    s.flush()


# --- Rôles ------------------------------------------------------------------------------------


def role(s: Session, ident: int, *, verrou: bool = False) -> RoleNomenclature:
    """Un rôle (404 « Rôle introuvable. »)."""
    r = s.get(RoleNomenclature, ident, with_for_update=verrou)
    if r is None:
        raise Refus.introuvable("Rôle introuvable.")
    return r


def _code_role(s: Session, brut: str, ident: int | None) -> str:
    """Le code d'un rôle : nettoyé, libre sans tenir compte de la casse (X-REF-02, X-REF-06)."""
    code = brut.strip()
    if not code:
        raise Refus.saisie("Le code est à renseigner.", champs={"code": "obligatoire"})
    if s.scalar(
        select(RoleNomenclature.id).where(
            func.lower(RoleNomenclature.code) == code.lower(), RoleNomenclature.id != (ident or 0)
        )
    ):
        raise Refus.etat(f"Le rôle « {code} » existe déjà.", code="doublon")
    return code


def ajouter_role(s: Session, qui: audit.Qui, code: str, ordre: int) -> RoleNomenclature:
    """Un rôle ajouté (route 58) : compté au poids (seuls Cuir, Franges, Ruban vont au mètre)."""
    code = _code_role(s, code, None)
    if code in ROLES_LINEAIRES:
        raise Refus.etat(f"Le rôle « {code} » existe déjà.", code="doublon")
    r = RoleNomenclature(code=code, ordre=ordre, lineaire=False, de_base=False)
    s.add(r)
    audit.creation(s, qui, "ajout rôle de nomenclature", r, numero=code, detail=code)
    return r


def modifier_role(
    s: Session, qui: audit.Qui, ident: int, code: str, ordre: int, *, version: int
) -> RoleNomenclature:
    """Ordre et nom d'un rôle (route 59) ; un rôle de base garde son nom (X-REF-04) ; version
    périmée → 409 `conflit_version`."""
    r = role(s, ident, verrou=True)
    audit.verifier_version(s, r, version, "Ce rôle", feminin=False)
    nouveau = _code_role(s, code, ident)
    if nouveau != r.code and r.de_base:
        raise Refus.etat(f"« {r.code} » est un rôle de base du calcul : il garde son nom.")
    ancien = r.code
    with audit.suivre(s, qui, "modification rôle de nomenclature", r, numero=nouveau) as geste:
        r.code, r.ordre = nouveau, ordre
        geste.detail = nouveau if nouveau == ancien else f"{ancien} → {nouveau}"
    s.flush()
    return r


def supprimer_role(s: Session, qui: audit.Qui, ident: int) -> None:
    """Un rôle ajouté, que rien ne porte (route 60 ; X-REF-07, X-REF-08)."""
    r = role(s, ident, verrou=True)
    if r.de_base:
        raise Refus.etat(f"« {r.code} » est un rôle de base du calcul : il ne se supprime pas.")
    matieres = s.scalar(select(func.count()).where(Matiere.role_id == r.id)) or 0
    qualites = (
        s.scalar(select(func.count()).where(QualitePoids.role_id == r.id, QualitePoids.poids > 0))
        or 0
    )
    if matieres or qualites:
        raise Refus.etat(
            f"« {r.code} » est porté par {matieres} matière(s) et {qualites} qualité(s) : les "
            "changer d'abord.",
            code="fiche_utilisee",
        )
    for modele in (RecetteVersionLigne, RecetteVersionPoids, InventaireCritere):
        if s.scalar(select(func.count()).where(modele.role_id == r.id)):
            raise Refus.etat(
                f"« {r.code} » figure dans l'historique (versions de recette, inventaires) : il "
                "garde sa place.",
                code="fiche_utilisee",
            )
    s.execute(delete(QualitePoids).where(QualitePoids.role_id == r.id))
    audit.suppression(s, qui, "suppression rôle de nomenclature", r, numero=r.code, detail=r.code)
    s.delete(r)
    s.flush()
