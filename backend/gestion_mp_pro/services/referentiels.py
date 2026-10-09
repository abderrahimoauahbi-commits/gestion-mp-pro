"""Magasins, codes douaniers et motifs (routes 31–33, 38–42 ; héritage R-REF-71…73, 93…95).

- **Magasins** (direction) : deux types, « Stock courant » et « Quarantaine » ; jamais
  supprimés ; un magasin qui détient de la matière ne se désactive pas et ne change pas de type ;
  il reste toujours un magasin en service de chaque type (R-REF-04).
- **Codes douaniers** (direction ; lecture achats) : position du tarif (chiffres et points) et
  taux de droits ; un code porté par des matières ne se supprime pas (le désactiver).
- **Motifs** (lecture) : la liste semée des motifs de mouvement, les types d'opération et les
  rôles qui les font, les motifs et issues des réclamations — une seule source pour l'écran.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import CodeDouanier, Magasin, Matiere, Motif, Solde
from gestion_mp_pro.modeles.enums import (
    IssueReclamation,
    MotifReclamation,
    Role,
    TypeMagasin,
    TypeMotif,
)
from gestion_mp_pro.modeles.types import TAUX, arrondir
from gestion_mp_pro.services import audit

POUSSIERE = Decimal("0.001")
"""Sous le gramme, un stock est nul."""

TYPES_MAGASIN = {
    "stock_courant": TypeMagasin.stock_courant,
    "stock courant": TypeMagasin.stock_courant,
    "quarantaine": TypeMagasin.quarantaine,
}
LIBELLES_MAGASIN = {
    TypeMagasin.stock_courant: "Stock courant",
    TypeMagasin.quarantaine: "Quarantaine",
}
CODE_DOUANIER = re.compile(r"\d[\d.]{1,19}")


def kg(valeur: Decimal | float) -> str:
    """« 1 234 » : milliers séparés d'une espace (une seule graphie, I-15)."""
    return f"{float(valeur):,.0f}".replace(",", " ")


# --- Magasins --------------------------------------------------------------------------------


@dataclass(frozen=True)
class MagasinSaisi:
    """Ce qu'on saisit d'un magasin."""

    code: str
    nom: str
    type: str
    contenu: str
    actif: bool


def detenus(s: Session) -> dict[int, Decimal]:
    """Les kilos détenus par magasin (somme des soldes de ses lots)."""
    requete = select(Solde.magasin_id, func.sum(Solde.quantite)).group_by(Solde.magasin_id)
    return {mid: q or Decimal(0) for mid, q in s.execute(requete).all()}


def magasins(s: Session) -> list[Magasin]:
    """Les magasins triés par type puis code."""
    return list(s.scalars(select(Magasin).order_by(Magasin.type, Magasin.code)))


def magasin(s: Session, ident: int, *, verrou: bool = False) -> Magasin:
    """Un magasin (404 sinon)."""
    g = s.get(Magasin, ident, with_for_update=verrou)
    if g is None:
        raise Refus.introuvable("Magasin introuvable.")
    return g


def _type_magasin(brut: str) -> TypeMagasin:
    """« stock_courant » / « Stock courant » / « quarantaine » (X-REF-54)."""
    t = TYPES_MAGASIN.get(brut.strip().lower())
    if t is None:
        raise Refus.saisie(
            "Type de magasin : « Stock courant » ou « Quarantaine ».", champs={"type": "inconnu"}
        )
    return t


def _code_magasin_libre(s: Session, code: str, ident: int | None) -> None:
    """Un code ne désigne qu'un magasin, quelle que soit sa casse (X-REF-55, A-12)."""
    autre = s.scalar(
        select(Magasin.code).where(
            func.lower(Magasin.code) == code.lower(), Magasin.id != (ident or 0)
        )
    )
    if autre is not None:
        raise Refus.etat(f"Le magasin « {code} » existe déjà.", code="doublon")


def _un_de_chaque_type(s: Session, g: Magasin, type_: TypeMagasin, actif: bool) -> None:
    """Il reste toujours un magasin en service de chaque type (R-REF-04)."""
    if g.actif and (not actif or type_ != g.type):
        restants = s.scalar(
            select(func.count()).where(Magasin.type == g.type, Magasin.actif, Magasin.id != g.id)
        )
        if not restants:
            raise Refus.etat(
                f"Il doit toujours rester un magasin « {LIBELLES_MAGASIN[g.type]} » en service : "
                "en créer ou en réactiver un autre d'abord."
            )


def creer_magasin(s: Session, qui: audit.Qui, e: MagasinSaisi) -> Magasin:
    """Un magasin nouveau (route 32)."""
    code = e.code.strip()
    type_ = _type_magasin(e.type)
    _code_magasin_libre(s, code, None)
    g = Magasin(code=code, nom=e.nom.strip(), type=type_, contenu=e.contenu.strip(), actif=e.actif)
    s.add(g)
    audit.creation(s, qui, "création magasin", g, numero=code, detail=code)
    return g


def modifier_magasin(
    s: Session, qui: audit.Qui, ident: int, e: MagasinSaisi, version: int
) -> Magasin:
    """Un magasin modifié (route 33) : ni désactivé ni retypé s'il détient de la matière."""
    g = magasin(s, ident, verrou=True)
    audit.verifier_version(s, g, version, "Ce magasin", feminin=False)
    code, type_ = e.code.strip(), _type_magasin(e.type)
    _code_magasin_libre(s, code, ident)
    detenu = detenus(s).get(ident, Decimal(0))
    if g.actif and not e.actif and detenu > POUSSIERE:
        raise Refus.etat(
            f"« {g.code} » détient encore {kg(detenu)} kg : transférer le stock avant de "
            "désactiver le magasin."
        )
    if g.type != type_ and detenu > POUSSIERE:
        raise Refus.etat("Un magasin qui détient de la matière ne change pas de type.")
    _un_de_chaque_type(s, g, type_, e.actif)
    with audit.suivre(s, qui, "modification magasin", g, numero=code, detail=code):
        g.code, g.nom, g.type, g.contenu, g.actif = (
            code,
            e.nom.strip(),
            type_,
            e.contenu.strip(),
            e.actif,
        )
    s.flush()
    return g


# --- Codes douaniers ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CodeSaisi:
    """Ce qu'on saisit d'un code douanier (taux en fraction : 0,10 = 10 %)."""

    code: str
    libelle: str
    taux_droits: float
    actif: bool


def pourcent(taux: Decimal | float) -> str:
    """« 10,00 % »."""
    return f"{float(taux) * 100:.2f} %".replace(".", ",")


def matieres_par_code(s: Session) -> dict[int, int]:
    """Le nombre de matières qui portent chaque code douanier."""
    requete = (
        select(Matiere.code_douanier_id, func.count())
        .where(Matiere.code_douanier_id.is_not(None))
        .group_by(Matiere.code_douanier_id)
    )
    return {cid: n for cid, n in s.execute(requete).all() if cid is not None}


def codes_douaniers(s: Session) -> list[CodeDouanier]:
    """Les codes douaniers triés par code."""
    return list(s.scalars(select(CodeDouanier).order_by(CodeDouanier.code)))


def code_douanier(s: Session, ident: int, *, verrou: bool = False) -> CodeDouanier:
    """Un code douanier (404 sinon)."""
    c = s.get(CodeDouanier, ident, with_for_update=verrou)
    if c is None:
        raise Refus.introuvable("Code douanier introuvable.")
    return c


def _code_valide(s: Session, brut: str, ident: int | None) -> str:
    """Chiffres éventuellement séparés de points, sans espace, libre (X-REF-83, X-REF-84)."""
    code = re.sub(r"\s+", "", brut)
    if not CODE_DOUANIER.fullmatch(code):
        raise Refus.saisie(
            "Un code douanier s'écrit en chiffres, éventuellement séparés de points "
            "(ex. 5402.47.00.00).",
            champs={"code": "chiffres et points"},
        )
    if s.scalar(
        select(CodeDouanier.id).where(CodeDouanier.code == code, CodeDouanier.id != (ident or 0))
    ):
        raise Refus.etat(f"Le code douanier « {code} » existe déjà.", code="doublon")
    return code


def creer_code(s: Session, qui: audit.Qui, e: CodeSaisi) -> CodeDouanier:
    """Un code douanier nouveau (route 39)."""
    code = _code_valide(s, e.code, None)
    c = CodeDouanier(
        code=code, libelle=e.libelle.strip(), taux_droits=arrondir(e.taux_droits, TAUX)
    )
    c.actif = e.actif
    s.add(c)
    audit.creation(
        s,
        qui,
        "création code douanier",
        c,
        numero=code,
        detail=f"{code} · {pourcent(c.taux_droits)}",
    )
    return c


def modifier_code(
    s: Session, qui: audit.Qui, ident: int, e: CodeSaisi, version: int
) -> CodeDouanier:
    """Un code douanier modifié (route 40) ; le code lui-même se corrige, les matières suivent."""
    c = code_douanier(s, ident, verrou=True)
    audit.verifier_version(s, c, version, "Ce code douanier", feminin=False)
    code = _code_valide(s, e.code, ident)
    avant = f"{c.code} · {pourcent(c.taux_droits)}"
    with audit.suivre(s, qui, "modification code douanier", c, numero=code) as geste:
        c.code, c.libelle, c.actif = code, e.libelle.strip(), e.actif
        c.taux_droits = arrondir(e.taux_droits, TAUX)
        geste.detail = f"{avant} → {c.code} · {pourcent(c.taux_droits)}" + (
            "" if c.actif else " · désactivé"
        )
    s.flush()
    return c


def supprimer_code(s: Session, qui: audit.Qui, ident: int, version: int | None) -> None:
    """Un code que nulle matière ne porte (route 41) ; sinon le désactiver (X-REF-86)."""
    c = code_douanier(s, ident, verrou=True)
    if version is not None:
        audit.verifier_version(s, c, version, "Ce code douanier", feminin=False)
    n = matieres_par_code(s).get(ident, 0)
    if n:
        raise Refus.etat(
            f"{n} matière(s) portent ce code : le leur retirer d'abord, ou le désactiver.",
            code="fiche_utilisee",
        )
    audit.suppression(s, qui, "suppression code douanier", c, numero=c.code, detail=c.code)
    s.delete(c)
    s.flush()


# --- Motifs -----------------------------------------------------------------------------------

D, A, L = Role.direction, Role.achats, Role.alimentation
TYPES_MOTIF: dict[TypeMotif, tuple[str, tuple[Role, ...]]] = {
    TypeMotif.ouverture: ("Stock d'ouverture", (D, A)),
    TypeMotif.retour_machine: ("Retour des machines", (D, L)),
    TypeMotif.transfert: ("Transfert entre magasins", (D, A, L)),
    TypeMotif.ajustement: ("Ajustement justifié", (D, A)),
    TypeMotif.retour_fournisseur: ("Retour au fournisseur", (D, A)),
    TypeMotif.inventaire: ("Inventaire", (D, A)),
}
"""Libellé de chaque type et les rôles qui le font (S80, S82 ; ECRANS-PRO « droits par type »).
Un motif peut exiger un rôle de plus (`impose_role` : « Libération de quarantaine » → achats)."""

MOTIFS_RECLAMATION: dict[MotifReclamation, str] = {
    MotifReclamation.qualite: "Qualité (défaut du fil)",
    MotifReclamation.quantite_manquante: "Quantité manquante",
    MotifReclamation.poids_bobines: "Poids des bobines",
    MotifReclamation.bobines_endommagees: "Bobines endommagées",
    MotifReclamation.retard: "Retard de livraison",
    MotifReclamation.documents: "Documents (facture, BL, certificat)",
    MotifReclamation.autre: "Autre",
}
ISSUES_RECLAMATION: dict[IssueReclamation, str] = {
    IssueReclamation.avoir: "Avoir",
    IssueReclamation.remplacement: "Remplacement",
    IssueReclamation.remise: "Remise sur la prochaine commande",
    IssueReclamation.refusee: "Refusée",
    IssueReclamation.abandonnee: "Abandonnée",
}


def motifs(s: Session) -> list[Motif]:
    """Les motifs semés, par type puis dans leur ordre."""
    return list(s.scalars(select(Motif).order_by(Motif.type_operation, Motif.ordre, Motif.id)))
