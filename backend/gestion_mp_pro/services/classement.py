"""Classement automatique du catalogue (routes 76–77 ; R-REF-35…41).

Chaque référence est lue (`calcul.classification.decomposer`) : composition, type de fil,
titrage, couleur et code couleur en sont déduits. L'aperçu n'écrit rien ; l'application ne
touche que les matières choisies, à la version lue (409 sinon), crée les valeurs de
classification qui manquent et journalise chaque fiche. **Une valeur déjà renseignée n'est
jamais écrasée** : la lecture comble les vides, elle ne corrige pas un choix humain. La couleur
se prend de la désignation quand elle existe (« la désignation dit la couleur comme l'atelier
la nomme ») ; les codes se retrouvent sans tenir compte de la casse (A-12).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul import classification as cla
from gestion_mp_pro.modeles import Composition, Couleur, Matiere, Titrage, TypeFil
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import ObjetJournal
from gestion_mp_pro.services import audit

DESIGNATION_MAX = 40
"""Au-delà, une désignation n'est plus un nom de couleur."""

LISTES: dict[str, tuple[type[Composition | TypeFil | Titrage | Couleur], int]] = {
    "composition": (Composition, L.CODE_CLASSIFICATION),
    "type_fil": (TypeFil, L.CODE_CLASSIFICATION),
    "titrage": (Titrage, L.CODE_TITRAGE),
    "couleur": (Couleur, L.CODE_COULEUR),
}


@dataclass(frozen=True)
class Proposition:
    """Ce que la référence d'une matière dit, pour les seuls champs vides."""

    matiere_id: int
    reference: str
    version: int
    changements: dict[str, str]


@dataclass
class Apercu:
    """Les propositions et les valeurs de classification à créer, par liste."""

    propositions: list[Proposition] = field(default_factory=list)
    a_creer: dict[str, list[str]] = field(default_factory=dict)


def _existants(s: Session) -> dict[str, dict[str, int]]:
    """Les codes connus de chaque liste, en minuscules → id."""
    return {
        nom: {code.lower(): ident for ident, code in s.execute(select(m.id, m.code))}
        for nom, (m, _) in LISTES.items()
    }


def _lire(m: Matiere, composition: str) -> dict[str, str]:
    """Les champs vides que la référence (et la désignation) comblent."""
    lu = cla.decomposer(m.reference, composition)
    couleur = re.sub(r"\([^)]*\)", "", m.designation or "").strip()
    if couleur and len(couleur) <= DESIGNATION_MAX:
        lu.couleur = couleur
    trouve = {
        "composition": lu.composition.upper(),
        "type_fil": lu.type_fil.upper(),
        "titrage": lu.titrage_complet,
        "couleur": lu.couleur,
    }
    change = {
        nom: valeur[: LISTES[nom][1]]
        for nom, valeur in trouve.items()
        if valeur and getattr(m, f"{nom}_id") is None
    }
    if lu.couleur_code and not m.couleur_code:
        change["couleur_code"] = lu.couleur_code[: L.COULEUR_CODE]
    return change


def apercu(s: Session, ids: list[int] | None = None) -> Apercu:
    """Ce que le classement ferait (rien n'est écrit) ; `ids` : seulement ces matières."""
    existants = _existants(s)
    libelles = dict(s.execute(select(Composition.id, Composition.libelle)).all())
    requete = select(Matiere).order_by(Matiere.reference)
    if ids is not None:
        requete = requete.where(Matiere.id.in_(ids))
    resultat = Apercu(a_creer={nom: [] for nom in LISTES})
    for m in s.scalars(requete):
        change = _lire(m, libelles.get(m.composition_id, "") if m.composition_id else "")
        if not change:
            continue
        resultat.propositions.append(Proposition(m.id, m.reference, m.version, change))
        for nom in LISTES:
            code = change.get(nom)
            if code and code.lower() not in existants[nom] and code not in resultat.a_creer[nom]:
                resultat.a_creer[nom].append(code)
    for codes in resultat.a_creer.values():
        codes.sort()
    return resultat


def _creer_valeur(s: Session, nom: str, code: str) -> int:
    """Une valeur de classification qui manque, avec ses libellés connus (R-REF-40)."""
    if nom == "composition":
        libelle, famille = cla.libelle_composition(code)
        valeur: Composition | TypeFil | Titrage | Couleur = Composition(
            code=code, libelle=libelle, famille=famille
        )
    elif nom == "type_fil":
        valeur = TypeFil(code=code, libelle=cla.TYPES_CONNUS.get(code, code))
    elif nom == "titrage":
        nombre, _, unite = code.partition(" ")
        valeur = Titrage(
            code=code, valeur=nombre[: L.VALEUR_TITRAGE], unite=unite[: L.UNITE_TITRAGE]
        )
    else:
        valeur = Couleur(code=code, libelle=code)
    s.add(valeur)
    s.flush()
    return valeur.id


def appliquer(s: Session, qui: audit.Qui, ids: list[int], versions: list[int]) -> Apercu:
    """Classe les matières choisies, à leur version lue (route 77)."""
    if len(ids) != len(versions) or len(set(ids)) != len(ids):
        raise Refus.saisie(
            "Une version par matière choisie, chacune une fois.", champs={"versions": "à aligner"}
        )
    lues = dict(zip(ids, versions, strict=True))
    fiches = {
        m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(ids)).with_for_update())
    }
    for ident in ids:
        if ident not in fiches:
            raise Refus.introuvable("Matière introuvable.")
        audit.verifier_version(
            s, fiches[ident], lues[ident], f"La matière « {fiches[ident].reference} »"
        )
    resultat = apercu(s, ids)
    existants = _existants(s)
    for p in resultat.propositions:
        m = fiches[p.matiere_id]
        with audit.suivre(s, qui, "classement du catalogue", m, detail=m.reference):
            for nom, valeur in p.changements.items():
                if nom == "couleur_code":
                    m.couleur_code = valeur
                    continue
                if valeur.lower() not in existants[nom]:
                    existants[nom][valeur.lower()] = _creer_valeur(s, nom, valeur)
                setattr(m, f"{nom}_id", existants[nom][valeur.lower()])
            m.modifie_par_id = qui.id
    audit.journal(
        s,
        qui,
        "classement du catalogue",
        ObjetJournal.matiere,
        detail=f"{len(resultat.propositions)} matière(s) complétée(s)",
    )
    s.flush()
    return resultat
