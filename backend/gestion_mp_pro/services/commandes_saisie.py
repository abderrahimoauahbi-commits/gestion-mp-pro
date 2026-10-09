"""Ce qu'une saisie de bon doit respecter : matières du fournisseur, en service, une fois
chacune ; unités de commande de la fiche ; date promise (REGLES § 2.5, 2.6 ;
`gestion_mp/api/achats.py` : `unites_permises`, `_verifier_unite`, `_verifier_lignes`,
`_changer_promesse` ; défauts A-08 et A-11 corrigés).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Commande, CommandeLigne, Fournisseur, Matiere
from gestion_mp_pro.services import horloge

ETA = (
    "Noter la nouvelle date annoncée par le fournisseur dans l'arrivée prévue (ETA) du "
    "suivi d'expédition."
)
TOLERANCE_CONTENANCE = Decimal("0.000001")


@dataclass(frozen=True)
class LigneSaisie:
    """Une ligne saisie : matière, kilos, unité de commande et sa contenance, prix éventuel."""

    matiere_id: int
    quantite: Decimal
    unite_achat: str = "kg"
    contenance: Decimal = Decimal(1)
    prix: Decimal | None = None


def nombre_fr(x: float | Decimal, decimales: int = 2) -> str:
    """« 1 234,5 » : espace des milliers, virgule décimale, zéros inutiles retirés."""
    texte = f"{float(x):,.{decimales}f}".replace(",", " ").replace(".", ",")
    if "," in texte:
        texte = texte.rstrip("0").rstrip(",")
    return texte


def unites_permises(m: Matiere) -> dict[str, Decimal]:
    """Les conditionnements où la matière se commande et leur contenance en kilos : le kilo, la
    bobine, la palette, l'unité d'achat de la fiche — jamais « ml » (R-CMD-25)."""
    permises = {"kg": Decimal(1)}
    if m.poids_bobine:
        permises["Bobine"] = Decimal(m.poids_bobine)
    if m.poids_bobine and m.bobines_palette:
        permises["Palette"] = Decimal(m.poids_bobine) * Decimal(m.bobines_palette)
    if m.unite_achat and m.unite_achat not in ("kg", "ml") and m.contenance_achat > 0:
        permises[m.unite_achat] = Decimal(m.contenance_achat)
    return permises


def _proches(a: Decimal, b: Decimal) -> bool:
    """Deux contenances égales à un millionième relatif près."""
    return abs(a - b) <= TOLERANCE_CONTENANCE * max(Decimal(1), abs(a))


def verifier_unite(m: Matiere, ligne: LigneSaisie, deja: CommandeLigne | None = None) -> None:
    """L'unité de la ligne est l'une de celles de la fiche, à sa contenance ; une ligne déjà
    sur le bon garde son conditionnement même si la fiche a changé depuis."""
    if ligne.unite_achat == "kg":
        if not _proches(ligne.contenance, Decimal(1)):
            raise Refus.saisie(
                f"« {m.reference} » : commandée en kg, la contenance vaut 1.", code="unite_invalide"
            )
        return
    if (
        deja is not None
        and deja.unite_achat == ligne.unite_achat
        and _proches(Decimal(deja.contenance), ligne.contenance)
    ):
        return
    permises = unites_permises(m)
    voulue = permises.get(ligne.unite_achat)
    if voulue is None:
        raise Refus.saisie(
            f"« {m.reference} » ne se commande pas en « {ligne.unite_achat} » : "
            f"{', '.join(permises)} (fiche de la matière).",
            code="unite_invalide",
        )
    if not _proches(voulue, ligne.contenance):
        raise Refus.saisie(
            f"« {m.reference} » : une {ligne.unite_achat} contient {nombre_fr(voulue, 3)} kg, "
            f"pas {nombre_fr(ligne.contenance, 3)} (fiche de la matière).",
            code="unite_invalide",
        )


def fournisseur_commandable(s: Session, fournisseur_id: int) -> Fournisseur:
    """Le fournisseur d'un nouveau bon : connu et en service (A-11)."""
    f = s.get(Fournisseur, fournisseur_id)
    if f is None:
        raise Refus.saisie("Fournisseur inconnu.", code="valeur_inconnue")
    if not f.actif:
        raise Refus.saisie(
            f"Le fournisseur « {f.nom} » est désactivé : on ne lui commande plus. Le "
            "réactiver d'abord (Catalogue › Fournisseurs), ou commander à un autre."
        )
    return f


def verifier_lignes(
    s: Session,
    fournisseur_id: int,
    lignes: list[LigneSaisie],
    anciennes: dict[int, CommandeLigne] | None = None,
) -> dict[int, Matiere]:
    """Chaque matière existe, vient de ce fournisseur, une seule fois, en service (une ligne
    déjà sur le bon reste), dans une unité de sa fiche (R-CMD-24, R-CMD-25, A-11)."""
    anciennes = anciennes or {}
    ids = [x.matiere_id for x in lignes]
    fiches = {m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(ids)))}
    vues: set[int] = set()
    for ligne in lignes:
        m = fiches.get(ligne.matiere_id)
        if m is None:
            raise Refus.saisie("Matière inconnue dans la commande.", code="valeur_inconnue")
        if m.fournisseur_id != fournisseur_id:
            raise Refus.saisie(f"« {m.reference} » n'est pas fournie par ce fournisseur.")
        if m.id in vues:
            raise Refus.saisie(
                f"« {m.reference} » figure deux fois : regrouper les quantités.",
                code="ligne_en_double",
            )
        if not m.actif and m.id not in anciennes:
            raise Refus.saisie(
                f"« {m.reference} » est désactivée : elle ne se commande plus. La réactiver "
                "d'abord (Catalogue › Matières), ou commander une autre matière."
            )
        verifier_unite(m, ligne, anciennes.get(m.id))
        vues.add(m.id)
    return fiches


def changer_promesse(c: Commande, nouvelle: date | None, *, vider: bool = False) -> None:
    """La date promise : libre sur un brouillon (vidée : elle se comptera à l'envoi, A-08) ;
    sur un bon parti, figée avec les prix, jamais repoussée une fois passée, jamais avant la
    date du bon, jamais vidée — une nouvelle annonce va dans l'ETA (R-CMD-29)."""
    if nouvelle is None:
        if not vider or c.date_livraison_prevue is None:
            return
        if c.numero:
            raise Refus.saisie(
                "La livraison promise d'un bon parti ne se vide pas : noter la nouvelle date "
                "annoncée par le fournisseur dans l'arrivée prévue (ETA) du suivi d'expédition.",
                code="date_figee",
            )
        c.date_livraison_prevue = None
        return
    if nouvelle == c.date_livraison_prevue:
        return
    if c.numero:
        _verifier_promesse_partie(c, nouvelle)
    c.date_livraison_prevue = nouvelle


def _verifier_promesse_partie(c: Commande, nouvelle: date) -> None:
    """Les refus X-CMD-12 à X-CMD-14 (bon parti)."""
    ancienne = c.date_livraison_prevue
    if c.cours:
        raise Refus.saisie(
            f"La livraison promise ({ancienne:%d/%m/%Y}) est figée depuis la confirmation des "
            f"prix : elle mesure la ponctualité. {ETA}"
            if ancienne
            else f"La date promise est figée depuis la confirmation des prix. {ETA}",
            code="date_figee",
        )
    if ancienne and ancienne < horloge.aujourd_hui() and nouvelle > ancienne:
        raise Refus.saisie(
            f"La livraison était promise pour le {ancienne:%d/%m/%Y}, date passée : elle ne "
            f"se repousse plus. {ETA}",
            code="date_figee",
        )
    if nouvelle < c.date_commande:
        raise Refus.saisie(
            f"La livraison prévue ({nouvelle:%d/%m/%Y}) précède la date du bon "
            f"({c.date_commande:%d/%m/%Y}).",
            code="date_invalide",
        )
