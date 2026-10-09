"""Lecture du catalogue des matières (routes 70, 71, 75, 81 ; R-REF-21…27, R-REF-48).

Tout le catalogue en une fois (l'écran filtre à la frappe), en requêtes groupées : chaque
matière avec sa classification (codes et libellés), son fournisseur, son prix ramené au kilo,
son conditionnement (déclaré ou déduit comme le plan d'achat), son stock (tous magasins,
quarantaine comprise) et ce qui empêche sa suppression (ses traces, dans l'ordre du refus).
Les prix sont retirés pour l'alimentation par le filtre des routes ; `sans_achat` retire en
plus ce qui accompagne le prix (devise, unité du prix, minimum de commande).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul import classification as cla
from gestion_mp_pro.modeles import (
    CodeDouanier,
    CommandeLigne,
    CommandeVersionLigne,
    Composition,
    Couleur,
    DossierLigne,
    Fournisseur,
    InventaireCritere,
    InventaireLigne,
    InventaireMatiere,
    Lot,
    Matiere,
    Montage,
    Mouvement,
    OperationLigne,
    OrdreLigne,
    OrdrePrevu,
    PieceJointe,
    ReceptionLigne,
    Recette,
    RecetteVersionLigne,
    RoleNomenclature,
    Signalement,
    Solde,
    Titrage,
    TypeFil,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import UnitePrix
from gestion_mp_pro.services import recherche

ROLES_LINEAIRES = ("Cuir", "Franges", "Ruban")

USAGES: tuple[tuple[Any, str], ...] = (
    (Mouvement.matiere_id, "des mouvements de stock"),
    (Lot.matiere_id, "des lots en stock ou passés"),
    (CommandeLigne.matiere_id, "des commandes"),
    (CommandeVersionLigne.matiere_id, "des commandes"),
    (ReceptionLigne.matiere_id, "des réceptions"),
    (OrdreLigne.matiere_id, "des ordres de fabrication"),
    (OrdrePrevu.matiere_id, "des ordres de fabrication"),
    (OperationLigne.matiere_id, "des opérations (brouillons compris)"),
    (DossierLigne.matiere_id, "des dossiers d'importation"),
    (InventaireLigne.matiere_id, "des inventaires"),
    (InventaireMatiere.matiere_id, "des inventaires"),
    (InventaireCritere.matiere_id, "des inventaires"),
    (Signalement.matiere_id, "des signalements de l'atelier"),
    (Recette.matiere_id, "des recettes"),
    (RecetteVersionLigne.matiere_id, "des recettes"),
    (Montage.matiere_id, "des fils montés sur les métiers"),
    (PieceJointe.matiere_id, "des pièces jointes"),
)
"""Où une matière laisse une trace : tant qu'elle y figure, elle ne se supprime pas (R-REF-34)."""

A_RETIRER = ("des recettes", "des fils montés sur les métiers", "des pièces jointes")


@dataclass(frozen=True)
class Conditionnement:
    """L'unité dans laquelle la matière se commande, et ce qu'elle contient (R-REF-25)."""

    unite: str
    contenance: Decimal
    declare: bool


def conditionnement(m: Matiere) -> Conditionnement:
    """Déclaré (unité ≠ kg, contenance > 0) ; sinon la palette, la bobine, le kilo."""
    if m.unite_achat and m.unite_achat != "kg" and m.contenance_achat > 0:
        return Conditionnement(m.unite_achat, m.contenance_achat, True)
    palette = m.poids_bobine * m.bobines_palette
    if palette:
        return Conditionnement("Palette", palette, False)
    if m.poids_bobine:
        return Conditionnement("Bobine", m.poids_bobine, False)
    return Conditionnement("kg", Decimal(1), False)


def prix_kg(prix: Decimal, unite_prix: str, densite: Decimal) -> Decimal:
    """Le prix ramené au kilo : au mètre, ÷ densité (0 sans densité) ; sinon tel quel."""
    if unite_prix == UnitePrix.ml:
        return prix / densite if densite else Decimal(0)
    return prix


def message_usage(reference: str, quoi: str) -> str:
    """Le refus de suppression d'une matière tenue par une trace (X-REF-34, X-REF-35)."""
    if quoi in A_RETIRER:
        return (
            f"« {reference} » figure dans {quoi} : l'en retirer d'abord, ou désactiver la matière."
        )
    return (
        f"« {reference} » figure dans {quoi} : elle appartient à l'historique. La désactiver "
        "plutôt que la supprimer."
    )


def usages(s: Session, ident: int | None = None) -> dict[int, list[str]]:
    """Les traces de chaque matière (ou d'une seule), sans doublon, dans l'ordre du refus."""
    trouve: dict[int, list[str]] = {}
    for colonne, quoi in USAGES:
        requete = select(colonne).where(colonne.is_not(None)).distinct()
        if ident is not None:
            requete = requete.where(colonne == ident)
        for (mid,) in s.execute(requete):
            liste = trouve.setdefault(mid, [])
            if quoi not in liste:
                liste.append(quoi)
    return trouve


@dataclass(frozen=True)
class Ligne:
    """Une matière telle que le catalogue la montre (`MatiereResume`, `MatiereFiche`)."""

    id: int
    version: int
    reference: str
    designation: str
    role_id: int
    role: str
    lineaire: bool
    composition_id: int | None
    composition: str | None
    composition_libelle: str | None
    type_fil_id: int | None
    type_fil: str | None
    titrage_id: int | None
    titrage: str | None
    titrage_unite: str | None
    couleur_id: int | None
    couleur: str | None
    couleur_libelle: str | None
    couleur_code: str
    fournisseur_id: int | None
    fournisseur: str | None
    prix: Decimal | None
    unite_prix: str | None
    prix_kg: Decimal | None
    devise: str | None
    densite: Decimal
    kg_par_ml: Decimal
    unite_achat: str
    contenance_achat: Decimal
    conditionnement: Conditionnement
    contenance_palette: Decimal
    minimum_commande: Decimal | None
    poids_bobine: Decimal
    bobines_palette: Decimal
    stock_min: Decimal
    couv_min_mois: Decimal
    groupe_equiv: str
    priorite_equiv: Decimal | None
    code_douanier_id: int | None
    code_douanier: str | None
    actif: bool
    stock: Decimal
    utilisee: bool
    usages: list[str] = field(default_factory=list)
    modifie_le: datetime | None = None
    modifie_par: str | None = None


@dataclass
class _Tables:
    """Les référentiels lus une fois pour toute la liste."""

    roles: dict[int, RoleNomenclature]
    compositions: dict[int, Composition]
    types: dict[int, TypeFil]
    titrages: dict[int, Titrage]
    couleurs: dict[int, Couleur]
    fournisseurs: dict[int, str]
    codes: dict[int, str]
    personnes: dict[int, str]
    stocks: dict[int, Decimal]
    usages: dict[int, list[str]]


def _tables(s: Session, ident: int | None) -> _Tables:
    """Les référentiels, les stocks et les usages (une requête par table)."""
    stocks = select(Lot.matiere_id, func.sum(Solde.quantite)).join(Solde, Solde.lot_id == Lot.id)
    if ident is not None:
        stocks = stocks.where(Lot.matiere_id == ident)
    return _Tables(
        roles={r.id: r for r in s.scalars(select(RoleNomenclature))},
        compositions={x.id: x for x in s.scalars(select(Composition))},
        types={x.id: x for x in s.scalars(select(TypeFil))},
        titrages={x.id: x for x in s.scalars(select(Titrage))},
        couleurs={x.id: x for x in s.scalars(select(Couleur))},
        fournisseurs=dict(s.execute(select(Fournisseur.id, Fournisseur.nom)).all()),
        codes=dict(s.execute(select(CodeDouanier.id, CodeDouanier.code)).all()),
        personnes=dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).all()),
        stocks={
            mid: q or Decimal(0) for mid, q in s.execute(stocks.group_by(Lot.matiere_id)).all()
        },
        usages=usages(s, ident),
    )


def matiere(s: Session, ident: int, *, verrou: bool = False) -> Matiere:
    """Une matière (404 « Matière introuvable. »)."""
    m = s.get(Matiere, ident, with_for_update=verrou)
    if m is None:
        raise Refus.introuvable("Matière introuvable.")
    return m


def _code(table: dict[int, Any], ident: int | None) -> str | None:
    """Le code d'une valeur de classification (ou `None`)."""
    return table[ident].code if ident is not None and ident in table else None


def _ligne(m: Matiere, t: _Tables) -> Ligne:
    """Une matière et tout ce qui l'accompagne."""
    role = t.roles[m.role_id]
    compo = t.compositions.get(m.composition_id) if m.composition_id else None
    titrage = t.titrages.get(m.titrage_id) if m.titrage_id else None
    couleur = t.couleurs.get(m.couleur_id) if m.couleur_id else None
    cond = conditionnement(m)
    traces = t.usages.get(m.id, [])
    return Ligne(
        id=m.id, version=m.version, reference=m.reference, designation=m.designation,
        role_id=m.role_id, role=role.code, lineaire=role.lineaire,
        composition_id=m.composition_id, composition=compo.code if compo else None,
        composition_libelle=compo.libelle if compo else None,
        type_fil_id=m.type_fil_id, type_fil=_code(t.types, m.type_fil_id),
        titrage_id=m.titrage_id, titrage=titrage.code if titrage else None,
        titrage_unite=titrage.unite if titrage else None,
        couleur_id=m.couleur_id, couleur=couleur.code if couleur else None,
        couleur_libelle=couleur.libelle if couleur else None, couleur_code=m.couleur_code,
        fournisseur_id=m.fournisseur_id,
        fournisseur=t.fournisseurs.get(m.fournisseur_id) if m.fournisseur_id else None,
        prix=m.prix, unite_prix=m.unite_prix, prix_kg=prix_kg(m.prix, m.unite_prix, m.densite),
        devise=m.devise, densite=m.densite,
        kg_par_ml=m.densite if role.code in ROLES_LINEAIRES else Decimal(0),
        unite_achat=m.unite_achat, contenance_achat=m.contenance_achat, conditionnement=cond,
        contenance_palette=m.poids_bobine * m.bobines_palette,
        minimum_commande=m.minimum_commande, poids_bobine=m.poids_bobine,
        bobines_palette=m.bobines_palette, stock_min=m.stock_min, couv_min_mois=m.couv_min_mois,
        groupe_equiv=m.groupe_equiv, priorite_equiv=m.priorite_equiv,
        code_douanier_id=m.code_douanier_id, code_douanier=_code_douanier(t, m),
        actif=m.actif, stock=t.stocks.get(m.id, Decimal(0)), utilisee=bool(traces),
        usages=traces, modifie_le=m.modifie_le,
        modifie_par=t.personnes.get(m.modifie_par_id) if m.modifie_par_id else None,
    )  # fmt: skip


def _code_douanier(t: _Tables, m: Matiere) -> str | None:
    """Le code douanier porté (ou `None`)."""
    return t.codes.get(m.code_douanier_id) if m.code_douanier_id else None


@dataclass(frozen=True)
class Filtres:
    """Les filtres de la liste : mots (sans accents), rôle, fournisseur, état."""

    q: str | None = None
    role: int | None = None
    fournisseur: int | None = None
    actif: bool | None = None


def lister(s: Session, f: Filtres | None = None) -> list[Ligne]:
    """Le catalogue trié par référence (route 70)."""
    f = f or Filtres()
    requete = select(Matiere).order_by(Matiere.reference)
    if f.q:
        requete = requete.where(*recherche.conditions(Matiere.texte_recherche, f.q))
    if f.role is not None:
        requete = requete.where(Matiere.role_id == f.role)
    if f.fournisseur is not None:
        requete = requete.where(Matiere.fournisseur_id == f.fournisseur)
    if f.actif is not None:
        requete = requete.where(Matiere.actif == f.actif)
    t = _tables(s, None)
    return [_ligne(m, t) for m in s.scalars(requete)]


def lire(s: Session, ident: int) -> Ligne:
    """Une matière et ses usages (route 71)."""
    return _ligne(matiere(s, ident), _tables(s, ident))


def sans_achat(ligne: Ligne) -> Ligne:
    """Pour l'alimentation : ce qui accompagne le prix part avec lui (devise, unité, minimum)."""
    return replace(ligne, devise=None, unite_prix=None, minimum_commande=None)


@dataclass(frozen=True)
class ReferenceComposee:
    """La référence écrite à partir de ses parties (route 75)."""

    reference: str
    designation: str
    existe: bool


def composer(
    s: Session,
    *,
    composition_id: int | None = None,
    type_fil_id: int | None = None,
    titrage_id: int | None = None,
    couleur_id: int | None = None,
    couleur_code: str = "",
    suffixe: str = "",
) -> ReferenceComposee:
    """« PP FRZ-2900 Dtex-Gold 3423-Hs » : composition, type, titrage, couleur, suffixe."""
    compo = s.get(Composition, composition_id) if composition_id else None
    type_fil = s.get(TypeFil, type_fil_id) if type_fil_id else None
    titrage = s.get(Titrage, titrage_id) if titrage_id else None
    couleur = s.get(Couleur, couleur_id) if couleur_id else None
    teinte = (couleur.libelle or couleur.code) if couleur else ""
    reference = cla.composer(
        compo.code if compo else "",
        type_fil=type_fil.code if type_fil else "",
        titrage=titrage.valeur if titrage else "",
        titrage_unite=titrage.unite if titrage else "",
        couleur=teinte,
        couleur_code=couleur_code,
        suffixe=suffixe,
    )
    existe = s.scalar(select(Matiere.id).where(func.lower(Matiere.reference) == reference.lower()))
    return ReferenceComposee(reference, cla.designation(teinte, couleur_code), existe is not None)
