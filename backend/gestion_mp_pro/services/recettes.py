"""La recette d'une qualité : règles d'enregistrement et versions (REGLES A § 1.8 ; MODELE § 3.2.8).

- Dans chaque rôle utilisé (lignes à part > 0), les parts font **100 % à 0,01 point** près — la
  tolérance du contrôle C01 : une recette que l'enregistrement accepte, le contrôle ne la déclare
  pas bloquante le lendemain. Une ligne à 0 % est gardée mais ne compte pas.
- Aucun rôle qui pèse dans le m² sans matière : refusé pour une qualité en service, accepté avec
  un avertissement pour une qualité arrêtée (elle ne part plus dans un ordre, O6 ; D-05).
- Une version naît **seulement si** les lignes ou les poids au m² changent (D-04) ; elle désigne
  les matières par leur **id** et fige leur rôle du moment (D-03) ; la première naît avec la
  qualité (D-18) ; elle est signée (`par_id`) et numérotée 1, 2, 3… par qualité.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Matiere,
    Qualite,
    QualitePoids,
    Recette,
    RecetteVersion,
    RecetteVersionLigne,
    RecetteVersionPoids,
    RoleNomenclature,
)
from gestion_mp_pro.modeles.enums import OrigineVersion
from gestion_mp_pro.modeles.types import POURCENTAGE, arrondir

CENT = Decimal(100)
TOLERANCE = Decimal("0.01")
"""La tolérance du contrôle C01 (`calcul.constantes.TOLERANCE_RECETTE`)."""


@dataclass(frozen=True)
class LigneSaisie:
    """Une ligne de recette envoyée : la matière (id) et sa part dans son rôle (0 à 100)."""

    matiere_id: int
    pourcentage: Decimal


@dataclass(frozen=True)
class Etat:
    """Ce qu'une version photographie : les lignes (matière → part) et les poids non nuls."""

    lignes: dict[int, Decimal]
    poids: dict[int, Decimal]


def texte(valeur: Decimal | float) -> str:
    """« 98 », « 99,9 », « 1200 » : le nombre sans zéros inutiles, à la française."""
    exact = valeur if isinstance(valeur, Decimal) else Decimal(str(valeur))
    return f"{exact.normalize():f}".replace(".", ",")


def codes_des_roles(s: Session) -> dict[int, RoleNomenclature]:
    """Les rôles de nomenclature par id."""
    return {r.id: r for r in s.scalars(select(RoleNomenclature))}


def poids_de(s: Session, qualite_id: int) -> dict[int, Decimal]:
    """Les poids au m² non nuls d'une qualité : rôle → poids."""
    requete = select(QualitePoids.role_id, QualitePoids.poids).where(
        QualitePoids.qualite_id == qualite_id, QualitePoids.poids > 0
    )
    return {role: poids for role, poids in s.execute(requete)}


def lignes_de(s: Session, qualite_id: int) -> dict[int, Decimal]:
    """Les lignes de la recette d'une qualité : matière → part."""
    requete = select(Recette.matiere_id, Recette.pourcentage).where(
        Recette.qualite_id == qualite_id
    )
    return {matiere: part for matiere, part in s.execute(requete)}


def etat(s: Session, qualite_id: int) -> Etat:
    """La recette telle qu'elle est en base (après `flush`)."""
    s.flush()
    return Etat(lignes=lignes_de(s, qualite_id), poids=poids_de(s, qualite_id))


def message_oublies(oublies: Sequence[tuple[str, Decimal]]) -> str:
    """Le refus (ou l'avertissement) d'un rôle pesant sans matière (X-REF-48, mot pour mot)."""
    un = len(oublies) == 1
    roles = ", ".join(f"{code} ({texte(poids)} au m²)" for code, poids in oublies)
    suite = (
        " : y mettre ses matières, ou ramener son poids au m² à 0 dans la fiche."
        if un
        else " : y mettre leurs matières, ou ramener leur poids au m² à 0 dans la fiche."
    )
    return ("La recette oublie le rôle " if un else "La recette oublie les rôles ") + roles + suite


def _matieres(s: Session, lignes: Sequence[LigneSaisie]) -> dict[int, Matiere]:
    """Les matières des lignes ; inconnue ou en double : 422 (X-REF-45, X-REF-46)."""
    ids = [x.matiere_id for x in lignes]
    trouvees = {m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(ids)))}
    vues: set[int] = set()
    for x in lignes:
        matiere = trouvees.get(x.matiere_id)
        if matiere is None:
            raise Refus.saisie("Matière inconnue dans la recette.", code="valeur_inconnue")
        if x.matiere_id in vues:
            raise Refus.saisie(
                f"« {matiere.reference} » figure deux fois dans la recette.",
                code="ligne_en_double",
            )
        vues.add(x.matiere_id)
    return trouvees


def _sommes(lignes: Sequence[LigneSaisie], matieres: dict[int, Matiere]) -> dict[int, Decimal]:
    """La somme des parts (> 0) de chaque rôle utilisé."""
    sommes: dict[int, Decimal] = defaultdict(Decimal)
    for x in lignes:
        if x.pourcentage > 0:
            sommes[matieres[x.matiere_id].role_id] += x.pourcentage
    return dict(sommes)


def oublies(
    poids: dict[int, Decimal], portes: set[int], roles: dict[int, RoleNomenclature]
) -> list[tuple[str, Decimal]]:
    """Les rôles qui pèsent dans le m² sans matière qui les porte, triés par code."""
    return sorted((roles[r].code, p) for r, p in poids.items() if p > 0 and r not in portes)


def roles_portes(s: Session, qualite_id: int) -> set[int]:
    """Les rôles portés par une ligne à part > 0 de la recette en base."""
    requete = (
        select(Matiere.role_id)
        .join(Recette, Recette.matiere_id == Matiere.id)
        .where(Recette.qualite_id == qualite_id, Recette.pourcentage > 0)
    )
    return set(s.scalars(requete))


def remplacer(s: Session, q: Qualite, lignes: Sequence[LigneSaisie]) -> list[tuple[str, Decimal]]:
    """Vérifie puis remplace la recette ; rend les rôles oubliés (acceptés si arrêtée).

    Refus : matière inconnue, en double, rôle à ≠ 100 % (X-REF-47), rôle pesant sans matière
    pour une qualité en service (X-REF-48).
    """
    lignes = [LigneSaisie(x.matiere_id, arrondir(x.pourcentage, POURCENTAGE)) for x in lignes]
    matieres = _matieres(s, lignes)
    roles = codes_des_roles(s)
    sommes = _sommes(lignes, matieres)
    faux = sorted((roles[r].code, t) for r, t in sommes.items() if abs(t - CENT) > TOLERANCE)
    if faux:
        raise Refus.saisie(
            "Dans chaque rôle, la recette doit faire 100 % : "
            + ", ".join(f"{code} {texte(t)} %" for code, t in faux)
            + ".",
            code="recette_incomplete",
        )
    manquants = oublies(poids_de(s, q.id), set(sommes), roles)
    if manquants and q.actif:
        raise Refus.saisie(message_oublies(manquants), code="recette_incomplete")
    s.execute(delete(Recette).where(Recette.qualite_id == q.id))
    for x in lignes:
        s.add(Recette(qualite_id=q.id, matiere_id=x.matiere_id, pourcentage=x.pourcentage))
    s.flush()
    return manquants


def _derniere(s: Session, qualite_id: int) -> RecetteVersion | None:
    """La version la plus récente d'une qualité."""
    requete = (
        select(RecetteVersion)
        .where(RecetteVersion.qualite_id == qualite_id)
        .order_by(RecetteVersion.numero.desc())
        .limit(1)
    )
    return s.scalars(requete).first()


def etat_de_version(s: Session, version_id: int) -> Etat:
    """Les lignes et les poids (non nuls) d'une version."""
    lignes = select(RecetteVersionLigne.matiere_id, RecetteVersionLigne.pourcentage).where(
        RecetteVersionLigne.version_id == version_id
    )
    poids = select(RecetteVersionPoids.role_id, RecetteVersionPoids.poids).where(
        RecetteVersionPoids.version_id == version_id, RecetteVersionPoids.poids > 0
    )
    return Etat(
        lignes={m: p for m, p in s.execute(lignes)}, poids={r: p for r, p in s.execute(poids)}
    )


def enregistrer_version(
    s: Session,
    q: Qualite,
    par_id: int | None,
    *,
    origine: OrigineVersion = OrigineVersion.saisie,
    motif: str = "",
    restauree_de_id: int | None = None,
) -> RecetteVersion | None:
    """Photographie la recette de `q` en une version nouvelle, **si elle a changé** (D-04).

    Une version d'avant les poids (`poids_connus` faux) ne vaut jamais la recette d'aujourd'hui :
    la suivante les garde.
    """
    courant = etat(s, q.id)
    derniere = _derniere(s, q.id)
    if (
        derniere is not None
        and derniere.poids_connus
        and etat_de_version(s, derniere.id) == courant
    ):
        return None
    numero = (
        s.scalar(
            select(func.coalesce(func.max(RecetteVersion.numero), 0)).where(
                RecetteVersion.qualite_id == q.id
            )
        )
        or 0
    ) + 1
    version = RecetteVersion(
        qualite_id=q.id,
        numero=numero,
        par_id=par_id,
        origine=origine,
        motif=motif,
        restauree_de_id=restauree_de_id,
        poids_connus=True,
    )
    s.add(version)
    s.flush()
    roles = dict(
        s.execute(
            select(Matiere.id, Matiere.role_id).where(Matiere.id.in_(list(courant.lignes)))
        ).all()
    )
    for matiere, part in courant.lignes.items():
        s.add(
            RecetteVersionLigne(
                version_id=version.id, matiere_id=matiere, role_id=roles[matiere], pourcentage=part
            )
        )
    for role, poids in courant.poids.items():
        s.add(RecetteVersionPoids(version_id=version.id, role_id=role, poids=poids))
    s.flush()
    return version
