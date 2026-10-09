"""Postes de frais d'importation (routes 34–37 ; héritage R-REF-85…92, commits f216509, 58f507c).

Un poste dit s'il est **récupérable** (la TVA : hors du coût) et sa **clé de répartition** : à
la valeur (défaut, M51) ou au poids. Les postes système (DD, TPI, TVA, FRET, ASSUR) sont lus par
les calculs du dossier : ils gardent leur nature et ne se suppriment pas.

Changer la clé recalcule les dossiers **ouverts**, jamais les **clos** : avant le changement,
chaque frais global non figé de ce poste dans un dossier clos garde sa répartition à l'ancienne
clé, marchandise par marchandise (`dossier_frais_part`, origine `changement_cle`, Σ parts =
montant aux plus forts restes) ; le frais reste une seule pièce (un montant, un règlement).
Un dossier ouvert dont la marchandise est entrée en période close refuse le changement (D4).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Devise, Dossier, DossierFrais, DossierFraisPart, PosteFrais
from gestion_mp_pro.modeles.enums import (
    CleRepartition,
    NatureFrais,
    ObjetJournal,
    OriginePart,
    StatutDossier,
)
from gestion_mp_pro.modeles.types import MONTANT
from gestion_mp_pro.services import audit, periode

CLES = {CleRepartition.valeur: "à la valeur", CleRepartition.poids: "au poids"}
CODE_POSTE = re.compile(r"[A-Z0-9_]{1,16}")
ORDRE_MAX = 999


@dataclass
class Usage:
    """Ce qui pèse sur un poste : ses frais, et les dossiers qui les portent, par statut."""

    frais_ouverts: int = 0
    frais_clos: int = 0
    dossiers: dict[str, set[int]] = field(default_factory=lambda: defaultdict(set))

    @property
    def dossiers_ouverts(self) -> int:
        """Dossiers ouverts qui portent un frais de ce poste."""
        return len(self.dossiers[StatutDossier.ouvert])

    @property
    def dossiers_clos(self) -> int:
        """Dossiers clos qui portent un frais de ce poste."""
        return len(self.dossiers[StatutDossier.clos])

    @property
    def frais(self) -> int:
        """Tous les frais de ce poste, dossiers annulés compris."""
        return self.frais_ouverts + self.frais_clos + len(self.dossiers[StatutDossier.annule])


@dataclass(frozen=True)
class PosteSaisi:
    """Ce qu'on saisit d'un poste (le code ne change plus après la création)."""

    libelle: str
    recuperable: bool
    cle: str
    ordre: int | None
    nature: str = NatureFrais.autre
    entre_valeur_douane: bool = False


def usages(s: Session) -> dict[int, Usage]:
    """L'usage de chaque poste par les dossiers."""
    requete = select(DossierFrais.poste_id, Dossier.statut, Dossier.id).join(
        Dossier, Dossier.id == DossierFrais.dossier_id
    )
    resultat: dict[int, Usage] = defaultdict(Usage)
    for poste, statut, dossier in s.execute(requete):
        u = resultat[poste]
        u.dossiers[statut].add(dossier)
        if statut == StatutDossier.ouvert:
            u.frais_ouverts += 1
        elif statut == StatutDossier.clos:
            u.frais_clos += 1
    return resultat


def postes(s: Session) -> list[PosteFrais]:
    """Les postes dans leur ordre."""
    return list(s.scalars(select(PosteFrais).order_by(PosteFrais.ordre, PosteFrais.code)))


def poste(s: Session, ident: int, *, verrou: bool = False) -> PosteFrais:
    """Un poste (404 sinon)."""
    p = s.get(PosteFrais, ident, with_for_update=verrou)
    if p is None:
        raise Refus.introuvable("Poste de frais introuvable.")
    return p


def _cle(brut: str) -> CleRepartition:
    """« valeur » ou « poids »."""
    try:
        return CleRepartition(brut)
    except ValueError:
        raise Refus.saisie(
            "Clé de répartition : à la valeur (valeur) ou au poids (poids).",
            champs={"cle": "valeur ou poids"},
        ) from None


def _nature(brut: str, recuperable: bool) -> NatureFrais:
    """Une nature connue ; une TVA est récupérable."""
    try:
        nature = NatureFrais(brut)
    except ValueError:
        raise Refus.saisie("Nature de frais inconnue.", champs={"nature": "inconnue"}) from None
    if nature == NatureFrais.tva and not recuperable:
        raise Refus.saisie(
            "Une TVA à l'importation est récupérable : cocher « récupérable ».",
            champs={"recuperable": "obligatoire pour une TVA"},
        )
    return nature


def _libelle(brut: str) -> str:
    """Le libellé, obligatoire (X-REF-75)."""
    libelle = brut.strip()
    if not libelle:
        raise Refus.saisie("Le libellé est obligatoire.", champs={"libelle": "obligatoire"})
    return libelle


def _detail(p: PosteFrais) -> str:
    """« MANUT · Manutention · au poids · récupérable »."""
    return f"{p.code} · {p.libelle} · {CLES[p.cle]}" + (" · récupérable" if p.recuperable else "")


def creer(s: Session, qui: audit.Qui, code: str, e: PosteSaisi) -> PosteFrais:
    """Un poste nouveau (route 35) : code en capitales, ordre à la suite par défaut."""
    code = code.strip().upper()
    if not CODE_POSTE.fullmatch(code):
        raise Refus.saisie(
            "Le code d'un poste : lettres, chiffres ou « _ », sans espace (ex. MANUT).",
            champs={"code": "lettres, chiffres ou _"},
        )
    if s.scalar(select(PosteFrais.id).where(PosteFrais.code == code)):
        raise Refus.etat(f"Le poste « {code} » existe déjà.", code="doublon")
    ordre = e.ordre
    if ordre is None:
        ordre = min(ORDRE_MAX, int(s.scalar(select(func.max(PosteFrais.ordre))) or 0) + 1)
    p = PosteFrais(
        code=code,
        libelle=_libelle(e.libelle),
        recuperable=e.recuperable,
        nature=_nature(e.nature, e.recuperable),
        entre_valeur_douane=e.entre_valeur_douane,
        cle=_cle(e.cle),
        ordre=ordre,
    )
    s.add(p)
    audit.creation(s, qui, "création poste de frais", p, numero=code, detail=_detail(p))
    return p


def _verifier_nature(p: PosteFrais, e: PosteSaisi, nature: NatureFrais, u: Usage) -> None:
    """Un poste système garde sa nature ; un poste des dossiers clos aussi (X-REF-78, 79)."""
    change = (e.recuperable, nature, e.entre_valeur_douane) != (
        p.recuperable,
        p.nature,
        p.entre_valeur_douane,
    )
    if not change:
        return
    if p.systeme:
        nature_lue = "récupérable" if p.recuperable else "un coût"
        raise Refus.etat(
            f"« {p.libelle} » est {nature_lue} par nature : les calculs du dossier (TVA "
            "attendue) le lisent ainsi."
        )
    if u.dossiers_clos:
        raise Refus.etat(
            f"Ce poste porte des frais dans {u.dossiers_clos} dossier(s) clos : changer sa "
            "nature changerait leur coût. Créer un autre poste."
        )


def _proteger_periode_close(s: Session, p: PosteFrais, cle: CleRepartition, nature: bool) -> None:
    """Un dossier ouvert entré en période close refuse un changement de répartition (D4)."""
    if cle == p.cle and not nature:
        return
    requete = (
        select(Dossier)
        .join(DossierFrais, DossierFrais.dossier_id == Dossier.id)
        .where(DossierFrais.poste_id == p.id, Dossier.statut == StatutDossier.ouvert)
        .options(selectinload(Dossier.frais).selectinload(DossierFrais.parts))
        .distinct()
    )
    for d in s.scalars(requete):
        touches = [
            x
            for x in d.frais
            if x.poste_id == p.id and (nature or (x.ligne_id is None and not x.parts))
        ]
        if touches:
            periode.cout_hors_periode_close(s, d, f"changement du poste « {p.libelle} »")


def modifier(s: Session, qui: audit.Qui, ident: int, e: PosteSaisi, version: int) -> int:
    """Un poste modifié (route 36) ; rend le nombre de dossiers clos à répartition figée."""
    p = poste(s, ident, verrou=True)
    audit.verifier_version(s, p, version, "Ce poste de frais", feminin=False)
    libelle, cle = _libelle(e.libelle), _cle(e.cle)
    nature = _nature(e.nature, e.recuperable) if not p.systeme else p.nature
    _verifier_nature(p, e, nature, usages(s).get(p.id, Usage()))
    nature_change = (e.recuperable, nature) != (p.recuperable, p.nature)
    _proteger_periode_close(s, p, cle, nature_change)
    figes = figer_clos(s, qui, p) if cle != p.cle else 0
    avant = f"{p.libelle} · {CLES[p.cle]}"
    with audit.suivre(s, qui, "modification poste de frais", p, numero=p.code) as geste:
        p.libelle, p.cle, p.recuperable, p.nature = libelle, cle, e.recuperable, nature
        p.entre_valeur_douane = e.entre_valeur_douane if not p.systeme else p.entre_valeur_douane
        if e.ordre is not None:
            p.ordre = e.ordre
        geste.detail = f"{p.code} : {avant} → {p.libelle} · {CLES[p.cle]}" + (
            f" · {figes} dossier(s) clos figé(s)" if figes else ""
        )
    s.flush()
    return figes


def supprimer(s: Session, qui: audit.Qui, ident: int, version: int) -> None:
    """Un poste ni système ni porté par un frais (route 37 ; X-REF-81, 82)."""
    p = poste(s, ident, verrou=True)
    audit.verifier_version(s, p, version, "Ce poste de frais", feminin=False)
    if p.systeme:
        raise Refus.etat(f"« {p.libelle} » sert aux calculs du dossier : il ne se supprime pas.")
    if usages(s).get(p.id, Usage()).frais:
        raise Refus.etat(
            "Ce poste porte des frais dans des dossiers : il ne se supprime pas.",
            code="fiche_utilisee",
        )
    audit.suppression(s, qui, "suppression poste de frais", p, numero=p.code, detail=_detail(p))
    s.delete(p)
    s.flush()


def repartir(montant: Decimal, poids: dict[int, Decimal]) -> dict[int, Decimal]:
    """Le montant au prorata des poids, au centime, Σ = montant (plus forts restes)."""
    total = sum(poids.values(), Decimal(0))
    signe = Decimal(-1) if montant < 0 else Decimal(1)
    exacts = {k: abs(montant) * v / total for k, v in poids.items() if v}
    parts = {k: x.quantize(MONTANT.pas, rounding=ROUND_DOWN) for k, x in exacts.items()}
    reste = int((abs(montant) - sum(parts.values(), Decimal(0))) / MONTANT.pas)
    for k in sorted(exacts, key=lambda k: (exacts[k] - parts[k], -k), reverse=True)[:reste]:
        parts[k] += MONTANT.pas
    return {k: signe * v for k, v in parts.items()}


def figer_clos(s: Session, qui: audit.Qui, p: PosteFrais) -> int:
    """Avant un changement de clé : les dossiers clos gardent leur répartition (58f507c)."""
    cours = {d.code: d.cours for d in s.scalars(select(Devise))}
    requete = (
        select(Dossier)
        .where(Dossier.statut == StatutDossier.clos)
        .order_by(Dossier.id)
        .options(
            selectinload(Dossier.lignes),
            selectinload(Dossier.frais).selectinload(DossierFrais.parts),
        )
        .with_for_update(of=Dossier)
    )
    figes = 0
    for d in s.scalars(requete):
        globaux = [x for x in d.frais if x.poste_id == p.id and x.ligne_id is None and not x.parts]
        if not globaux or len(d.lignes) < 2:  # noqa: PLR2004 — une seule ligne prend tout
            continue
        poids = {
            x.id: x.quantite_kg
            if p.cle == CleRepartition.poids
            else x.valeur_devise
            * (Decimal(1) if x.devise == "MAD" else (x.cours or cours.get(x.devise, Decimal(1))))
            for x in d.lignes
        }
        if not sum(poids.values(), Decimal(0)):
            continue
        for frais in globaux:
            for ligne, montant in repartir(frais.montant, poids).items():
                frais.parts.append(
                    DossierFraisPart(
                        ligne_id=ligne, montant=montant, origine=OriginePart.changement_cle
                    )
                )
        audit.journal(
            s,
            qui,
            "frais figés",
            ObjetJournal.dossier,
            d.id,
            numero=d.numero,
            detail=f"{d.numero} · {p.code} {CLES[p.cle]} : dossier clos, sa répartition est "
            f"gardée ({len(globaux)} frais, une pièce chacun)",
        )
        figes += 1
    return figes
