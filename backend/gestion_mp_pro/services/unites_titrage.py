"""Les unités de titrage (routes 57 et 255–257 ; décision de Mohamed du 12/10/2026, F29).

Un référentiel tenu par les achats et la direction, comme les valeurs de classification :

- le **code** s'écrit comme dans les références (« Dtex », « lbs ») : un mot de lettres (deux au
  moins, la longueur de `titrage.unite`), unique **sans tenir compte de la casse** (« LBS » est
  refusé si « lbs » existe ; A-12) ; « Den » est la façon courte d'écrire Deniers (lue par
  `calcul.classification`), pas une unité ;
- une unité est **employée** dès qu'un titrage l'écrit (`titrage.unite`, sans casse ; « Den »
  compte pour Deniers) — et par lui les matières qui portent ce titrage ;
- employée, elle **ne se supprime pas** et **ne se renomme pas** (raison dite : les titrages qui
  l'écrivent ne la retrouveraient plus) : on crée la nouvelle et on désactive l'ancienne ; corriger
  la seule casse reste permis (la lecture ne tient pas compte de la casse) ;
- désactivée, elle n'est plus proposée (écran) ni lue dans une nouvelle référence (`actives`,
  passé à `decomposer`), mais reste affichée sur les titrages qui l'ont.

La liste des unités actives est relue en base à chaque lecture de références (une requête) : pas
de copie en mémoire qu'un autre processus laisserait périmée ; le motif compilé est gardé par
`calcul.classification.lecture_unites`, dont la clé est la liste elle-même.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul.classification import ABREVIATIONS_UNITE
from gestion_mp_pro.modeles import Matiere, Titrage, UniteTitrage
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.services import audit

PAS_D_ORDRE = 10
"""Une unité ajoutée sans ordre se range après la dernière, de dix en dix."""
LETTRES_MIN = 2
"""Une unité d'une seule lettre se confondrait avec le « x » de « 1750x2 »."""


@dataclass(frozen=True)
class Emploi:
    """Ce qui emploie une unité : les titrages qui l'écrivent, les matières qui les portent."""

    titrages: int = 0
    matieres: int = 0

    @property
    def employee(self) -> bool:
        """Au moins un titrage l'écrit."""
        return self.titrages > 0

    def phrase(self) -> str:
        """« 3 titrage(s) (12 matière(s)) »."""
        return f"{self.titrages} titrage(s) ({self.matieres} matière(s))"


@dataclass(frozen=True)
class UniteSaisie:
    """Ce qu'on saisit d'une unité."""

    code: str
    libelle: str = ""
    ordre: int | None = None
    actif: bool = True


def actives(s: Session) -> tuple[str, ...]:
    """Les unités actives, dans leur écriture et leur ordre : ce que lit `decomposer`."""
    requete = (
        select(UniteTitrage.code)
        .where(UniteTitrage.actif)
        .order_by(UniteTitrage.ordre, UniteTitrage.code)
    )
    return tuple(s.scalars(requete))


def _formes(code: str) -> list[str]:
    """Les écritures (en minuscules) qui emploient l'unité : elle-même et ses abréviations."""
    bas = code.lower()
    return [bas, *(court for court, long in ABREVIATIONS_UNITE.items() if long == bas)]


def emploi(s: Session, code: str) -> Emploi:
    """Les titrages qui écrivent l'unité (sans casse) et les matières qui les portent."""
    titrages = select(Titrage.id).where(func.lower(Titrage.unite).in_(_formes(code)))
    nb_titrages = s.scalar(select(func.count()).select_from(titrages.subquery())) or 0
    nb_matieres = s.scalar(select(func.count()).where(Matiere.titrage_id.in_(titrages))) or 0
    return Emploi(nb_titrages, nb_matieres)


def lire(s: Session) -> list[tuple[UniteTitrage, Emploi]]:
    """Toutes les unités (désactivées comprises), dans leur ordre, avec leur emploi."""
    unites = s.scalars(select(UniteTitrage).order_by(UniteTitrage.ordre, UniteTitrage.code))
    titrages: dict[str, int] = dict(
        s.execute(
            select(func.lower(Titrage.unite), func.count()).group_by(func.lower(Titrage.unite))
        ).all()
    )
    matieres: dict[str, int] = dict(
        s.execute(
            select(func.lower(Titrage.unite), func.count())
            .join(Matiere, Matiere.titrage_id == Titrage.id)
            .group_by(func.lower(Titrage.unite))
        ).all()
    )
    return [
        (
            u,
            Emploi(
                sum(titrages.get(f, 0) for f in _formes(u.code)),
                sum(matieres.get(f, 0) for f in _formes(u.code)),
            ),
        )
        for u in unites
    ]


def unite(s: Session, ident: int, *, verrou: bool = False) -> UniteTitrage:
    """Une unité (404 « Unité de titrage introuvable. »)."""
    u = s.get(UniteTitrage, ident, with_for_update=verrou)
    if u is None:
        raise Refus.introuvable("Unité de titrage introuvable.")
    return u


def _code(s: Session, brut: str, ident: int | None) -> str:
    """Le code nettoyé : un mot de lettres, dans sa longueur, libre sans tenir compte de casse."""
    code = brut.strip()
    if not code:
        raise Refus.saisie("Le code est à renseigner.", champs={"code": "obligatoire"})
    bornes = f"{LETTRES_MIN} à {L.UNITE_TITRAGE}"
    if not code.isalpha() or not LETTRES_MIN <= len(code) <= L.UNITE_TITRAGE:
        raise Refus.saisie(
            f"Une unité de titrage s'écrit en lettres seules, de {bornes} (« {code} » ne se "
            "lirait pas dans une référence).",
            champs={"code": f"lettres seules, {bornes}"},
        )
    abregee = ABREVIATIONS_UNITE.get(code.lower())
    if abregee is not None:
        raise Refus.etat(
            f"« {code} » abrège « {abregee.title()} » dans les références : ce n'est pas une "
            "unité à part.",
            code="doublon",
        )
    autre = s.scalar(
        select(UniteTitrage.code).where(
            func.lower(UniteTitrage.code) == code.lower(), UniteTitrage.id != (ident or 0)
        )
    )
    if autre is not None:
        en_plus = f" (« {code} »)" if autre != code else ""
        raise Refus.etat(f"L'unité « {autre} » existe déjà{en_plus}.", code="doublon")
    return code


def _ordre_suivant(s: Session) -> int:
    """Après la dernière unité, de dix en dix."""
    return (s.scalar(select(func.max(UniteTitrage.ordre))) or 0) + PAS_D_ORDRE


def ajouter(s: Session, qui: audit.Qui, e: UniteSaisie) -> UniteTitrage:
    """Une unité nouvelle (route 255) : elle se lit aussitôt dans les références."""
    code = _code(s, e.code, None)
    ordre = e.ordre if e.ordre is not None else _ordre_suivant(s)
    u = UniteTitrage(code=code, libelle=e.libelle.strip(), ordre=ordre, actif=e.actif)
    s.add(u)
    audit.creation(s, qui, "ajout unité de titrage", u, numero=code, detail=code)
    return u


def modifier(
    s: Session, qui: audit.Qui, ident: int, e: UniteSaisie, *, version: int
) -> tuple[UniteTitrage, str]:
    """Une unité modifiée (route 256) ; rend l'avertissement d'une unité désactivée employée.

    Employée, son code ne change pas (sa casse seule se corrige) : les titrages qui l'écrivent ne
    la retrouveraient plus.
    """
    u = unite(s, ident, verrou=True)
    audit.verifier_version(s, u, version, "Cette unité de titrage")
    code, ancien, etait_active = _code(s, e.code, ident), u.code, u.actif
    usage = emploi(s, ancien)
    if code.lower() != ancien.lower() and usage.employee:
        raise Refus.etat(
            f"« {ancien} » est écrite sur {usage.phrase()} : son code ne se change pas. Ajouter "
            f"l'unité « {code} », puis désactiver « {ancien} ».",
            code="fiche_utilisee",
        )
    with audit.suivre(s, qui, "modification unité de titrage", u, numero=code) as geste:
        u.code, u.libelle, u.actif = code, e.libelle.strip(), e.actif
        if e.ordre is not None:
            u.ordre = e.ordre
        geste.detail = code if code == ancien else f"{ancien} → {code}"
    s.flush()
    avertissement = ""
    if etait_active and not u.actif and usage.employee:
        avertissement = (
            f"« {code} » reste écrite sur {usage.phrase()} : elle ne se propose plus et ne se lit "
            "plus dans une nouvelle référence ; ces titrages la gardent."
        )
    return u, avertissement


def supprimer(s: Session, qui: audit.Qui, ident: int, version: int | None) -> None:
    """Une unité qu'aucun titrage n'écrit (route 257) ; employée : la désactiver."""
    u = unite(s, ident, verrou=True)
    if version is not None:
        audit.verifier_version(s, u, version, "Cette unité de titrage")
    usage = emploi(s, u.code)
    if usage.employee:
        raise Refus.etat(
            f"« {u.code} » est écrite sur {usage.phrase()} : la désactiver plutôt que la "
            "supprimer.",
            code="fiche_utilisee",
        )
    audit.suppression(s, qui, "suppression unité de titrage", u, numero=u.code, detail=u.code)
    s.delete(u)
    s.flush()


def raison_de_garder(usage: Emploi) -> str | None:
    """Pourquoi « Supprimer » est grisé (la même règle que `supprimer`), ou rien."""
    if not usage.employee:
        return None
    return f"Écrite sur {usage.phrase()} : la désactiver plutôt que la supprimer"
