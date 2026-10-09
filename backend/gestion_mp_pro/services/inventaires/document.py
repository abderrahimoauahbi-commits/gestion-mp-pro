"""Un inventaire et ses lignes, tels que les gestes et les lectures les manipulent : relecture
verrouillée à la version lue, état qui permet encore de compter, comptage retenu, lignes pour
le calcul des écarts (`calcul.inventaire`), justification manquante (IR17).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import flag_modified

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul import inventaire as calcul
from gestion_mp_pro.modeles import Inventaire, InventaireLigne, Matiere, Utilisateur
from gestion_mp_pro.modeles.enums import StatutInventaire
from gestion_mp_pro.services import audit

JUSTIFICATION_MINIMUM = 3
"""Un écart hors tolérance se justifie en 3 caractères au moins (IR17)."""


def charger(s: Session, ident: int, *, verrou: bool = False) -> Inventaire:
    """L'inventaire, ses lignes, critères et matières (`FOR UPDATE` si `verrou`), ou 404 (IR1)."""
    requete = (
        select(Inventaire)
        .where(Inventaire.id == ident)
        .options(
            selectinload(Inventaire.lignes),
            selectinload(Inventaire.criteres),
            selectinload(Inventaire.matieres),
        )
        .execution_options(populate_existing=True)
    )
    if verrou:
        requete = requete.with_for_update(of=Inventaire)
    i = s.scalars(requete).first()
    if i is None:
        raise Refus.introuvable("Inventaire introuvable.")
    return i


def relire(s: Session, ident: int, version: int) -> Inventaire:
    """L'inventaire verrouillé, à sa version lue (409 qui nomme l'auteur sinon)."""
    i = charger(s, ident, verrou=True)
    audit.verifier_version(s, i, version, "Cet inventaire", feminin=False)
    return i


def encore_ouvert(i: Inventaire) -> None:
    """Un inventaire qu'on peut encore compter ou valider (IR8)."""
    if i.statut == StatutInventaire.abandonne:
        raise Refus.etat(f"L'inventaire {i.numero} a été abandonné : en ouvrir un nouveau.")
    if i.statut != StatutInventaire.ouvert:
        raise Refus.etat("Cet inventaire est déjà validé.", code="deja_valide")


def toucher(i: Inventaire) -> None:
    """La version de l'inventaire avance aussi quand seules ses lignes changent."""
    flag_modified(i, "libelle")


def ligne_de_calcul(x: InventaireLigne, reference: str) -> calcul.LigneInventaire:
    """Une ligne pour le calcul des écarts (en nombres flottants, comme le moteur)."""
    return calcul.LigneInventaire(
        id=x.id,
        reference=reference,
        theorique=float(x.theorique),
        compte=None if x.compte is None else float(x.compte),
        second_compte=None if x.second_compte is None else float(x.second_compte),
        lot_id=x.lot_id,
        magasin_id=x.magasin_id,
    )


def retenu(x: InventaireLigne) -> Decimal | None:
    """Le comptage qui ajuste : le second (recompté) s'il existe, sinon le premier (S140)."""
    return x.second_compte if x.second_compte is not None else x.compte


def references(s: Session, i: Inventaire) -> dict[int, str]:
    """La référence de chaque matière des lignes."""
    ids = {x.matiere_id for x in i.lignes}
    return dict(s.execute(select(Matiere.id, Matiere.reference).where(Matiere.id.in_(ids))).all())


def sans_justification(s: Session, i: Inventaire) -> list[str]:
    """Les références dont l'écart hors tolérance n'est pas justifié (IR17)."""
    refs = references(s, i)
    return [
        refs[x.matiere_id]
        for x in i.lignes
        if calcul.ecart_hors_tolerance(ligne_de_calcul(x, refs[x.matiere_id]), float(i.tolerance))
        and len(x.justification.strip()) < JUSTIFICATION_MINIMUM
    ]


def noms_des_personnes(s: Session, ids: set[int]) -> dict[int, str]:
    """Le nom de chaque personne citée."""
    if not ids:
        return {}
    return dict(
        s.execute(select(Utilisateur.id, Utilisateur.nom).where(Utilisateur.id.in_(ids))).all()
    )
