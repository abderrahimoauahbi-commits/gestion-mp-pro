"""Ce que les recettes demandent pour un ordre, et le prévu figé à la validation (P11, P14,
P54 ; DECISIONS O5 ; DEFAUTS D-03, D-07).

Le prévu par matière est Σ kg/m² × m² sur la nomenclature du moteur (les rôles au mètre en
kilos : ml/m² × densité), **hors perte** ; la proposition y ajoute la perte. À la validation, il
est figé dans `ordre_prevu` (par **id** de matière : un renommage le suit) avec le taux de perte
du jour (`taux_perte_fige`) : changer ensuite une recette, un poids au m² ou le taux de perte ne
réécrit jamais l'écart de l'ordre.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.nomenclature import controle_recettes, nomenclature
from gestion_mp_pro.modeles import Matiere, Ordre, OrdrePrevu, Qualite
from gestion_mp_pro.modeles.types import QUANTITE, TAUX, arrondir
from gestion_mp_pro.services import donnees_moteur, recettes, reglages

ZERO = Decimal(0)


def taux_perte(s: Session) -> Decimal:
    """Le taux de perte matière des réglages (fraction : 0,02 = 2 %)."""
    return arrondir(Decimal(str(reglages.nombre(s, "taux_perte"))), TAUX)


def codes(s: Session, ids: Iterable[int]) -> dict[int, str]:
    """Le code de chaque qualité."""
    return dict(s.execute(select(Qualite.id, Qualite.code).where(Qualite.id.in_(set(ids)))).all())


def par_matiere(s: Session, d: Donnees, m2: dict[str, Decimal]) -> dict[int, dict[str, Decimal]]:
    """{matière : {qualité : kg hors perte}} pour ces m² par code de qualité (kg/m² > 0)."""
    refs = dict(s.execute(select(Matiere.reference, Matiere.id)).all())
    besoins: dict[int, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for r in nomenclature(d):
        if r.qualite in m2 and r.kg_m2 > 0 and r.reference in refs:
            besoins[refs[r.reference]][r.qualite] += Decimal(repr(r.kg_m2)) * m2[r.qualite]
    return besoins


def incompletes(d: Donnees, voulues: Iterable[str]) -> list[str]:
    """Ce que la recette de ces qualités ne dit pas (P14, mot pour mot) : rien, ou trop peu,
    serait proposé pour ce rôle ; on le dit au lieu de l'omettre en silence."""
    codes_voulus = set(voulues)
    alertes = []
    for controle in controle_recettes(d):
        if controle.qualite not in codes_voulus:
            continue
        fiche = d.qualite(controle.qualite)
        for ecart in controle.ecarts:
            poids = fiche.poids.get(ecart.role, 0.0) if fiche else 0.0
            if ecart.somme <= 0:
                alertes.append(
                    f"{controle.qualite} : le rôle {ecart.role} pèse {poids:g} au m², mais la "
                    "recette ne nomme aucune matière pour lui : rien ne lui est proposé. La "
                    "direction doit compléter la recette."
                )
            else:
                alertes.append(
                    f"{controle.qualite} : le rôle {ecart.role} fait {ecart.somme:g} % dans la "
                    "recette au lieu de 100 % : sa proposition est faussée. La direction doit "
                    "corriger la recette."
                )
    return alertes


def oublis(s: Session, qualites: dict[int, str]) -> list[str]:
    """Les qualités de l'ordre dont la recette oublie un rôle pesant (`recettes.oublies`, le
    message de la fiche qualité) : un prévu figé sans ce rôle serait faux pour toujours."""
    roles = recettes.codes_des_roles(s)
    sans_matiere = recettes.roles_sans_matiere(s)
    raisons = []
    for qid, code in sorted(qualites.items(), key=lambda x: x[1]):
        manque = recettes.oublies(recettes.poids_de(s, qid), recettes.roles_portes(s, qid), roles)
        if manque:
            raisons.append(f"{code} : {recettes.message_oublies(manque, sans_matiere)}")
    return raisons


def figer(s: Session, o: Ordre) -> None:
    """Le prévu de l'ordre, hors perte, et le taux de perte du jour, figés (P54, O5)."""
    noms = codes(s, (q.qualite_id for q in o.qualites))
    m2: dict[str, Decimal] = defaultdict(Decimal)
    for q in o.qualites:
        m2[noms[q.qualite_id]] += q.m2
    d = donnees_moteur.charger(s, avec_journal=False)
    for matiere_id, par_qualite in sorted(par_matiere(s, d, dict(m2)).items()):
        kg = arrondir(sum(par_qualite.values(), ZERO), QUANTITE)
        s.add(OrdrePrevu(ordre_id=o.id, matiere_id=matiere_id, kg_hors_perte=kg))
    o.prevu_fige, o.taux_perte_fige = True, taux_perte(s)
