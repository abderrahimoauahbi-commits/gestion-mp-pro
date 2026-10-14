"""La fiche matière : règles, création, modification, suppression (routes 72–74 ; R-REF-28…34).

Les règles d'une fiche (`verifier`) sont les mêmes pour l'écran et le tableur, dans l'ordre de
Gestion MP corrigé : rôle connu ; valeurs de classification connues (et en service si elles
changent, A-11) ; unité du prix ; densité d'un rôle au mètre et d'un prix au mètre ; une
matière en service a un fournisseur (C05), en service s'il change ; devise connue ; unité
d'achat (jamais « ml ») et sa contenance ; code douanier connu ; **le rôle d'une matière qui est
dans une recette ne change pas** (A-02). La référence est unique sans tenir compte de la casse.

Désactiver ne revalide que ce qui change (H-28) : une ancienne fiche sans fournisseur sort du
catalogue sans être d'abord complétée. `commandable` dit aux achats et aux réceptions qu'une
matière ou son fournisseur désactivés ne se commandent plus (A-11).
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    CodeDouanier,
    Composition,
    Couleur,
    Fournisseur,
    Matiere,
    Recette,
    RoleNomenclature,
    Titrage,
    TypeFil,
)
from gestion_mp_pro.modeles.enums import UnitePrix
from gestion_mp_pro.modeles.types import (
    MESURE,
    MOIS,
    PRIORITE,
    PRIX,
    QUANTITE,
    UNITES,
    Nombre,
    arrondir,
)
from gestion_mp_pro.services import audit, horloge
from gestion_mp_pro.services.fournisseurs import devise_connue
from gestion_mp_pro.services.matieres_lecture import (
    ROLES_LINEAIRES,
    matiere,
    message_usage,
    usages,
)

__all__ = ["commandable", "creer", "matiere", "modifier", "supprimer", "verifier"]

CLASSIFICATION: tuple[tuple[str, type[Composition | TypeFil | Titrage | Couleur], str], ...] = (
    ("composition_id", Composition, "Composition inconnue"),
    ("type_fil_id", TypeFil, "Type de fil inconnu"),
    ("titrage_id", Titrage, "Titrage inconnu"),
    ("couleur_id", Couleur, "Couleur inconnue"),
)
NOMBRES: dict[str, Nombre] = {
    "densite": MESURE,
    "prix": PRIX,
    "contenance_achat": QUANTITE,
    "minimum_commande": QUANTITE,
    "poids_bobine": MESURE,
    "bobines_palette": UNITES,
    "stock_min": QUANTITE,
    "couv_min_mois": MOIS,
    "priorite_equiv": PRIORITE,
}
TEXTES = ("designation", "couleur_code", "groupe_equiv")

BORNES: dict[str, tuple[float, float]] = {
    "densite": (0, 1000),
    "prix": (0, 1e7),
    "contenance_achat": (0, 1e7),
    "minimum_commande": (0, 1e9),
    "poids_bobine": (0, 1000),
    "bobines_palette": (0, 10000),
    "stock_min": (0, 1e9),
    "couv_min_mois": (0, 60),
    "priorite_equiv": (0, 100),
}
"""Bornes des nombres d'une fiche (R-REF-28) : une déclaration pour l'écran, l'API, le tableur."""


def _refus(message: str, champ: str, code: str = "saisie_invalide") -> Refus:
    """Un refus de saisie sur un champ de la fiche."""
    return Refus.saisie(message, code=code, champs={champ: message})


def _change(actuel: Matiere | None, champ: str, valeur: object) -> bool:
    """La fiche change-t-elle ce champ (toujours vrai pour une fiche nouvelle) ?"""
    return actuel is None or getattr(actuel, champ) != valeur


def _classification(s: Session, e: dict[str, Any], actuel: Matiere | None) -> None:
    """Valeurs connues ; une valeur désactivée ne se pose pas (elle se garde) (A-11)."""
    for champ, modele, inconnue in CLASSIFICATION:
        ident = e.get(champ)
        if ident is None:
            continue
        v = cast(Composition | TypeFil | Titrage | Couleur | None, s.get(modele, ident))
        if v is None:
            raise _refus(
                f"{inconnue} : « {ident} ». L'ajouter d'abord dans la classification.",
                champ,
                "valeur_inconnue",
            )
        if not v.actif and _change(actuel, champ, ident):
            raise _refus(
                f"« {v.code} » est désactivée dans la classification : choisir une valeur en "
                "service, ou la réactiver d'abord.",
                champ,
            )


def _role(s: Session, e: dict[str, Any]) -> RoleNomenclature:
    """Le rôle de la matière (X-REF-20)."""
    r = s.get(RoleNomenclature, e["role_id"])
    if r is None:
        raise _refus(f"Rôle inconnu : « {e['role_id']} ».", "role_id", "valeur_inconnue")
    return r


def _densite(r: RoleNomenclature, e: dict[str, Any]) -> None:
    """Unité du prix, densité d'un rôle au mètre et d'un prix au mètre (X-REF-22…24)."""
    if e["unite_prix"] not in tuple(UnitePrix):
        raise _refus("Unité du prix : au kilo (kg) ou au mètre (ml).", "unite_prix")
    if r.code in ROLES_LINEAIRES and not e["densite"]:
        raise _refus(
            f"Une matière du rôle {r.code} (cuir, franges, ruban : comptés au mètre dans les "
            "recettes) a besoin de sa densité (kg/ml) : le stock est en kilos.",
            "densite",
        )
    if e["unite_prix"] == UnitePrix.ml and not e["densite"]:
        raise _refus(
            "Un prix au mètre a besoin de la densité (kg/ml) pour se ramener au kilo.", "densite"
        )


def _fournisseur(s: Session, e: dict[str, Any], actuel: Matiere | None) -> None:
    """En service ⇒ fournisseur (C05), connu, et en service s'il change (X-REF-25, 26)."""
    fid = e.get("fournisseur_id")
    if e["actif"] and not fid:
        raise _refus(
            "Une matière en service a un fournisseur : sans lui, le plan d'achat ne sait pas à "
            "qui la commander (contrôle C05).",
            "fournisseur_id",
        )
    if not fid:
        return
    f = s.get(Fournisseur, fid)
    if f is None:
        raise _refus("Fournisseur inconnu.", "fournisseur_id", "valeur_inconnue")
    if not f.actif and e["actif"] and _change(actuel, "fournisseur_id", fid):
        raise _refus(
            f"Le fournisseur « {f.nom} » est désactivé : en choisir un en service, ou le "
            "réactiver d'abord.",
            "fournisseur_id",
        )


def _achat(e: dict[str, Any]) -> None:
    """Unité d'achat (vide = kg, jamais « ml ») et sa contenance (X-REF-28, 29)."""
    e["unite_achat"] = (e.get("unite_achat") or "").strip() or "kg"
    if e["unite_achat"].lower() == "kg":
        e["unite_achat"] = "kg"  # « Kg », « KG » (tableur) : le kilo, pas une unité déclarée
    if e["unite_achat"].lower() == "ml":
        raise _refus(
            "La commande se compte en kilos (ou en palettes, fûts… de tant de kilos). Un "
            "fournisseur qui facture au mètre : choisir le prix « au mètre ».",
            "unite_achat",
        )
    if e["unite_achat"] != "kg" and not e["contenance_achat"]:
        raise _refus(
            "Une unité d'achat autre que le kilo a besoin de sa contenance (kg par unité).",
            "contenance_achat",
        )
    if e["unite_achat"] == "kg":
        e["contenance_achat"] = arrondir(1, QUANTITE)


def _code_douanier(s: Session, e: dict[str, Any], actuel: Matiere | None) -> None:
    """Un code douanier connu ; désactivé, il ne se pose pas (X-REF-30, P7-15)."""
    cid = e.get("code_douanier_id")
    if cid is None:
        return
    c = s.get(CodeDouanier, cid)
    if c is None:
        raise _refus(
            f"Code douanier inconnu : « {cid} ». Demander à la direction de l'ajouter "
            "(Réglages › Codes douaniers) ; en attendant, laisser le code vide.",
            "code_douanier_id",
            "valeur_inconnue",
        )
    if not c.actif and _change(actuel, "code_douanier_id", cid):
        raise _refus(
            f"Le code douanier « {c.code} » est désactivé : en choisir un en service.",
            "code_douanier_id",
        )


def _role_en_recette(s: Session, r: RoleNomenclature, actuel: Matiere | None) -> None:
    """Le rôle d'une matière qui figure dans des recettes ne change pas (A-02, F13)."""
    if actuel is None or actuel.role_id == r.id:
        return
    recettes = s.scalar(select(func.count()).where(Recette.matiere_id == actuel.id)) or 0
    if recettes:
        ancien = s.get(RoleNomenclature, actuel.role_id)
        raise Refus.etat(
            f"« {actuel.reference} » figure dans {recettes} recette(s) comme "
            f"{ancien.code if ancien else '?'} : son rôle ne change pas tant qu'elle y est. La "
            "retirer d'abord de ces recettes (Qualités et recettes), ou créer une autre matière."
        )


def verifier(s: Session, champs: dict[str, Any], actuel: Matiere | None) -> dict[str, Any]:
    """Les règles d'une fiche matière ; rend les champs nettoyés, prêts à écrire."""
    e = dict(champs)
    e["reference"] = str(e["reference"]).strip()
    for k in TEXTES:
        e[k] = str(e.get(k) or "").strip()
    for k, categorie in NOMBRES.items():
        if e.get(k) is not None:
            e[k] = arrondir(e[k], categorie)
    r = _role(s, e)
    _classification(s, e, actuel)
    _densite(r, e)
    _fournisseur(s, e, actuel)
    e["devise"] = devise_connue(s, str(e.get("devise") or "MAD"), actuel.devise if actuel else None)
    _achat(e)
    _code_douanier(s, e, actuel)
    _role_en_recette(s, r, actuel)
    e["unite_prix"] = UnitePrix(e["unite_prix"])
    return e


def reference_libre(s: Session, reference: str, ident: int | None) -> None:
    """Une référence ne désigne qu'une matière, quelle que soit sa casse (X-REF-31, A-12)."""
    autre = s.scalar(
        select(Matiere.reference).where(
            func.lower(Matiere.reference) == reference.lower(), Matiere.id != (ident or 0)
        )
    )
    if autre is not None:
        en_plus = f" (« {reference} »)" if autre != reference else ""
        raise Refus.etat(f"La matière « {autre} » existe déjà{en_plus}.", code="doublon")


def creer(s: Session, qui: audit.Qui, champs: dict[str, Any]) -> Matiere:
    """Une matière nouvelle (route 72)."""
    e = verifier(s, champs, None)
    reference_libre(s, e["reference"], None)
    m = Matiere(**e, modifie_par_id=qui.id, modifie_le=horloge.maintenant())
    s.add(m)
    audit.creation(s, qui, "création matière", m, detail=m.reference)
    return m


def modifier(
    s: Session, qui: audit.Qui, ident: int, champs: dict[str, Any], version: int
) -> Matiere:
    """Une matière modifiée (route 73), sous verrou, à sa version lue."""
    m = matiere(s, ident, verrou=True)
    audit.verifier_version(s, m, version, "Cette matière")
    e = verifier(s, champs, m)
    reference_libre(s, e["reference"], ident)
    avant = m.reference
    with audit.suivre(s, qui, "modification matière", m) as geste:
        for k, v in e.items():
            setattr(m, k, v)
        m.modifie_par_id = qui.id
        geste.detail = m.reference if avant == m.reference else f"{avant} → {m.reference}"
    s.flush()
    return m


def supprimer(s: Session, qui: audit.Qui, ident: int, version: int | None) -> None:
    """Une matière sans aucune trace (route 74 ; X-REF-34, X-REF-35)."""
    m = matiere(s, ident, verrou=True)
    if version is not None:
        audit.verifier_version(s, m, version, "Cette matière")
    traces = usages(s, ident).get(ident)
    if traces:
        raise Refus.etat(message_usage(m.reference, traces[0]), code="fiche_utilisee")
    audit.suppression(s, qui, "suppression matière", m, detail=m.reference)
    s.delete(m)
    s.flush()


def commandable(s: Session, ident: int) -> Matiere:
    """Une matière qui se commande : en service, et son fournisseur aussi (A-11, pour D3, D4)."""
    m = matiere(s, ident)
    if not m.actif:
        raise Refus.etat(
            f"« {m.reference} » est désactivée : la réactiver avant de la commander.",
            code="fiche_inactive",
        )
    f = s.get(Fournisseur, m.fournisseur_id) if m.fournisseur_id else None
    if f is not None and not f.actif:
        raise Refus.etat(
            f"« {f.nom} » est désactivé : le réactiver avant de lui commander.",
            code="fiche_inactive",
        )
    return m
