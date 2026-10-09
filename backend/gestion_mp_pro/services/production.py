"""Le plan de production et ses versions (REGLES A § 1.9 ; Gestion MP `api/production_plan.py`).

Le plan d'une qualité est une base mensuelle (m²) et douze coefficients de saisonnalité (0 à 20) ;
le plan glissant n'est pas stocké, il en découle. **Tout chemin qui change le plan** (base,
saisonnalité, arrêt ou remise en service) passe par `noter_plan`, qui écrit une `plan_version`
datée et signée **seulement si quelque chose change** : le passé reste jugé sur le plan de son
époque. La première version d'une qualité, écrite à sa création, est le plan « d'avant » (en
vigueur depuis toujours) ; chaque suivante est un changement (S4, `services/chargeur/qualites`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import PlanVersion, PlanVersionSaison, Qualite, QualiteSaison
from gestion_mp_pro.modeles.enums import ObjetJournal, OrigineVersion
from gestion_mp_pro.modeles.types import COEFFICIENT, SURFACE, arrondir
from gestion_mp_pro.services import audit
from gestion_mp_pro.services.audit import Qui
from gestion_mp_pro.services.recettes import texte

MOIS = 12
COEFFICIENT_MAXI = Decimal(20)
UN = Decimal(1)
ACTION = "plan de production"


@dataclass(frozen=True)
class Plan:
    """Le plan d'une qualité : base mensuelle, douze coefficients, en service."""

    base: Decimal
    coefficients: tuple[Decimal, ...]
    actif: bool

    def en_json(self) -> dict[str, object]:
        """Pour le journal (avant / après)."""
        return {
            "base_mensuelle": float(self.base),
            "coefficients": [float(c) for c in self.coefficients],
            "en_service": self.actif,
        }


def coefficients_de(s: Session, qualite_id: int) -> tuple[Decimal, ...]:
    """Les douze coefficients d'une qualité (1 pour un mois sans ligne)."""
    lus = dict(
        s.execute(
            select(QualiteSaison.mois, QualiteSaison.coefficient).where(
                QualiteSaison.qualite_id == qualite_id
            )
        ).all()
    )
    return tuple(lus.get(m, UN) for m in range(1, MOIS + 1))


def plan_de(s: Session, q: Qualite) -> Plan:
    """Le plan courant d'une qualité."""
    s.flush()
    return Plan(base=q.base_mensuelle, coefficients=coefficients_de(s, q.id), actif=q.actif)


def coefficients_valables(coefficients: Sequence[Decimal]) -> bool:
    """Douze coefficients entre 0 et 20 (un NaN n'arrive pas jusqu'ici : 422 de la saisie)."""
    return len(coefficients) == MOIS and all(0 <= c <= COEFFICIENT_MAXI for c in coefficients)


def _arrondi(base: Decimal, coefficients: Sequence[Decimal]) -> tuple[Decimal, tuple[Decimal, ...]]:
    """Base et coefficients à l'échelle de leurs colonnes."""
    return arrondir(base, SURFACE), tuple(arrondir(c, COEFFICIENT) for c in coefficients)


def refuser_si_arretee(
    s: Session, q: Qualite, base: Decimal, coefficients: Sequence[Decimal], suite: str = ""
) -> None:
    """Le plan d'une qualité arrêtée ne compte plus : le changer est refusé (D-01) ; le renvoyer
    inchangé passe (l'écran envoie ce qu'il a)."""
    if q.actif:
        return
    avant = plan_de(s, q)
    base, coefs = _arrondi(base, coefficients)
    if avant.base != base or avant.coefficients != coefs:
        raise Refus.etat(
            f"La qualité {q.code} est arrêtée : son plan ne compte plus. La remettre en "
            "service (Qualités) avant de le changer." + suite
        )


def ecrire_version(
    s: Session,
    q: Qualite,
    plan: Plan,
    par_id: int | None,
    *,
    origine: OrigineVersion = OrigineVersion.saisie,
    motif: str = "",
) -> PlanVersion:
    """Une `plan_version` et ses douze coefficients."""
    version = PlanVersion(
        qualite_id=q.id,
        base_mensuelle=plan.base,
        en_service=plan.actif,
        par_id=par_id,
        origine=origine,
        motif=motif,
    )
    s.add(version)
    s.flush()
    for mois, coefficient in enumerate(plan.coefficients, start=1):
        s.add(PlanVersionSaison(version_id=version.id, mois=mois, coefficient=coefficient))
    s.flush()
    return version


def noter_plan(
    s: Session, qui: Qui, q: Qualite, avant: Plan, *, detail: str, motif: str = ""
) -> bool:
    """Trace le plan d'après s'il diffère du plan d'avant : version et journal ; vrai si noté."""
    apres = plan_de(s, q)
    if apres == avant:
        return False
    ecrire_version(s, q, apres, qui.id, motif=motif)
    audit.journal(
        s,
        qui,
        ACTION,
        ObjetJournal.qualite,
        q.id,
        detail=detail,
        avant=avant.en_json(),
        apres=apres.en_json(),
    )
    return True


def ecrire_saisons(s: Session, q: Qualite, coefficients: Sequence[Decimal]) -> None:
    """Remplace les douze coefficients d'une qualité."""
    s.execute(delete(QualiteSaison).where(QualiteSaison.qualite_id == q.id))
    for mois, coefficient in enumerate(coefficients, start=1):
        s.add(QualiteSaison(qualite_id=q.id, mois=mois, coefficient=coefficient))
    s.flush()


def enregistrer_plan(
    s: Session,
    qui: Qui,
    q: Qualite,
    base: Decimal,
    *,
    coefficients: Sequence[Decimal],
    motif: str = "",
) -> bool:
    """Écrit la base et la saisonnalité d'une qualité et en trace la version ; vrai si changé."""
    avant = plan_de(s, q)
    base, coefs = _arrondi(base, coefficients)
    if avant.base == base and avant.coefficients == coefs:
        return False
    q.base_mensuelle = base
    ecrire_saisons(s, q, coefs)
    return noter_plan(s, qui, q, avant, detail=f"{q.code} : {texte(base)} m²/mois", motif=motif)


@dataclass(frozen=True)
class LignePlan:
    """Le plan envoyé pour une qualité (route 146), avec la version lue de la qualité."""

    qualite_id: int
    base: Decimal
    coefficients: tuple[Decimal, ...]
    version: int


RIEN = " Rien n'a été enregistré."


def _qualites_verrouillees(s: Session, lignes: Sequence[LignePlan]) -> dict[int, Qualite]:
    """Les qualités du plan envoyé, sous verrou, dans l'ordre des ids (pas d'interblocage)."""
    ids = [x.qualite_id for x in lignes]
    if len(set(ids)) != len(ids):
        raise Refus.saisie(
            "Une qualité apparaît deux fois dans le plan envoyé.", code="ligne_en_double"
        )
    requete = (
        select(Qualite)
        .where(Qualite.id.in_(ids))
        .order_by(Qualite.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    qualites = {q.id: q for q in s.scalars(requete)}
    if len(qualites) != len(ids):
        raise Refus.introuvable("Qualité introuvable : le plan n'a pas été enregistré.")
    return qualites


def ecrire_plan_global(s: Session, qui: Qui, lignes: Sequence[LignePlan], motif: str = "") -> int:
    """Route 146 : le plan de plusieurs qualités d'un bloc, tout ou rien ; rend le nombre de
    qualités dont le plan a changé (une ligne renvoyée telle quelle ne compte pas)."""
    qualites = _qualites_verrouillees(s, lignes)
    for x in lignes:
        q = qualites[x.qualite_id]
        audit.verifier_version(s, q, x.version, f"La qualité {q.code}")
        if not coefficients_valables(x.coefficients):
            raise Refus.saisie(
                f"{q.code} : un coefficient de saisonnalité reste entre 0 et 20." + RIEN
            )
        refuser_si_arretee(s, q, x.base, x.coefficients, RIEN)
    modifiees = 0
    for x in lignes:
        q = qualites[x.qualite_id]
        if enregistrer_plan(s, qui, q, x.base, coefficients=x.coefficients, motif=motif):
            q.modifie_par_id = qui.id
            flag_modified(q, "modifie_par_id")
            modifiees += 1
    s.flush()
    return modifiees
