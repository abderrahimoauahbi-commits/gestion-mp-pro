"""Remplir un brouillon d'opération : tout est vérifié dès la saisie (REGLES B.1.12, OR1–OR27).

« Dit tout de suite, plutôt qu'à la validation » : date permise, motif de la liste du type
(C-09), justification d'un ajustement, ordre d'un retour des machines, matière, magasin, lot,
unité (une bobine se compte entière, D-08), sens d'une matière retrouvée, quarantaine (libérer :
direction et achats ; mettre en quarantaine : avec ses observations), fournisseur d'un retour.
L'en-tête est réécrit et **toutes** les lignes remplacées.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Devise,
    Lot,
    Magasin,
    Matiere,
    Motif,
    Operation,
    OperationLigne,
    Ordre,
)
from gestion_mp_pro.modeles.enums import Role, StatutOrdre, TypeMagasin, TypeOperation
from gestion_mp_pro.modeles.types import PRIX, QUANTITE, arrondir
from gestion_mp_pro.services import conversions, periode
from gestion_mp_pro.services.operations import droits

ZERO = Decimal(0)
MOTIF_REQUIS = (
    TypeOperation.retour_machine,
    TypeOperation.retour_fournisseur,
    TypeOperation.ajustement,
)
"""Les types dont le motif dit pourquoi le stock bouge (S91)."""
MATIERE_RETROUVEE = "Matière retrouvée"
JUSTIFICATION_AJUSTEMENT = 5
"""Un ajustement se justifie en quelques mots : 5 caractères au moins (S92)."""
JUSTIFICATION_QUARANTAINE = 3
"""Une mise en quarantaine dit ce qui est douteux : 3 caractères au moins."""
UNITES = ("kg", "bobine", "palette")


@dataclass(frozen=True)
class SaisieLigne:
    """Une ligne saisie (quantité signée dans son unité ; prix et devise : ouverture seule)."""

    matiere_id: int
    magasin_id: int
    quantite: Decimal
    lot_id: int | None = None
    lot_numero: str = ""
    lot_interne: bool = False
    magasin_destination_id: int | None = None
    unite: str = "kg"
    prix: Decimal = ZERO
    devise: str = "MAD"


@dataclass(frozen=True)
class SaisieOperation:
    """Ce que l'écran envoie pour créer ou modifier un brouillon."""

    type: TypeOperation
    date: date
    lignes: tuple[SaisieLigne, ...]
    ordre_id: int | None = None
    motif_id: int | None = None
    commentaire: str = ""


@dataclass
class _Ligne:
    """Une ligne vérifiée : ce qui sera enregistré, et ce qu'on en sait."""

    ligne: OperationLigne
    matiere: Matiere
    lot: Lot | None
    source: Magasin
    destination: Magasin | None


def remplir(s: Session, o: Operation, e: SaisieOperation, role: str) -> None:
    """Vérifie la saisie (dans l'ordre de Gestion MP) puis réécrit l'en-tête et les lignes."""
    periode.date_permise(s, e.date)
    motif = _motif(s, e)
    if e.type is TypeOperation.ajustement and len(e.commentaire.strip()) < JUSTIFICATION_AJUSTEMENT:
        raise Refus.saisie(
            "Un ajustement se justifie : écrire en quelques mots ce qui a été constaté.",
            code="motif_requis",
        )
    if motif is not None and motif.impose_role and role not in {Role.direction, motif.impose_role}:
        raise Refus.droit(droits.REFUS_LIBERATION)
    ordre = _ordre_du_retour(s, e) if e.type is TypeOperation.retour_machine else None
    lignes = [_ligne(s, e, x, motif) for x in e.lignes]
    _quarantaine(e, lignes, motif, role)
    fournisseur = (
        _fournisseur_du_retour(lignes) if e.type is TypeOperation.retour_fournisseur else None
    )
    o.date, o.commentaire = e.date, e.commentaire
    o.ordre_id = ordre.id if ordre is not None else None
    o.motif_id = motif.id if motif is not None else None
    o.motif_texte = motif.libelle if motif is not None else ""
    o.fournisseur_id = fournisseur
    o.lignes.clear()
    s.flush()
    o.lignes.extend(x.ligne for x in lignes)


def _motif(s: Session, e: SaisieOperation) -> Motif | None:
    """Le motif, de la liste du type (C-09) ; obligatoire pour un ajustement et les retours."""
    if e.motif_id is None:
        if e.type in MOTIF_REQUIS:
            raise Refus.saisie(
                "Choisir le motif : il dit pourquoi le stock bouge.", code="motif_requis"
            )
        return None
    motif = s.get(Motif, e.motif_id)
    if motif is not None and str(motif.type_operation) == str(e.type):
        return motif
    permis = s.scalars(
        select(Motif.libelle).where(Motif.type_operation == e.type).order_by(Motif.ordre)
    ).all()
    nom = f"Motif « {motif.libelle} » inconnu" if motif is not None else "Motif inconnu"
    suite = (
        "choisir parmi " + ", ".join(f"« {x} »" for x in permis)
        if permis
        else "ce type d'opération n'en prend pas"
    )
    raise Refus.saisie(
        f"{nom} pour « {droits.LIBELLES[e.type]} » : {suite}.", code="valeur_inconnue"
    )


def _ordre_du_retour(s: Session, e: SaisieOperation) -> Ordre:
    """L'ordre validé d'où la matière revient, daté au plus tard du retour (OR6, OR7)."""
    ordre = s.get(Ordre, e.ordre_id) if e.ordre_id else None
    if ordre is None or ordre.statut != StatutOrdre.valide:
        raise Refus.saisie(
            "Un retour des machines se rattache à l'ordre d'où la matière revient.",
            code="valeur_inconnue",
        )
    retour_apres_l_ordre(e.date, ordre)
    return ordre


def retour_apres_l_ordre(jour: date, ordre: Ordre) -> None:
    """La matière revient d'un ordre après en être partie, jamais avant (OR7)."""
    if jour < ordre.date:
        raise Refus.saisie(
            f"Ce retour est daté du {jour:%d/%m/%Y}, avant l'ordre {ordre.numero} du "
            f"{ordre.date:%d/%m/%Y} : la matière n'était pas encore partie. Dater le retour du "
            "jour où elle est revenue.",
            code="date_invalide",
        )


def _connus(s: Session, x: SaisieLigne) -> tuple[Matiere, Magasin, Lot | None]:
    """Matière, magasin, lot (de cette matière) d'une ligne (OR8–OR10)."""
    matiere = s.get(Matiere, x.matiere_id)
    if matiere is None:
        raise Refus.saisie("Matière inconnue.", code="valeur_inconnue")
    source = s.get(Magasin, x.magasin_id)
    if source is None:
        raise Refus.saisie("Magasin inconnu.", code="valeur_inconnue")
    lot = s.get(Lot, x.lot_id) if x.lot_id else None
    if lot is not None and lot.matiere_id != matiere.id:
        raise Refus.saisie("Ce lot est d'une autre matière.", code="valeur_inconnue")
    return matiere, source, lot


def en_kg(matiere: Matiere, lot: Lot | None, quantite: Decimal, unite: str) -> Decimal:
    """La quantité saisie (kg, bobines, palettes) ramenée aux kilos, signe gardé (S96, D-08)."""
    unite = (unite or "kg").lower()
    if unite not in UNITES:
        raise Refus.saisie(
            "Unité : kg, bobine ou palette — le cuir, les franges et le ruban se comptent "
            "aussi en kilos.",
            code="unite_invalide",
        )
    if unite == "bobine" and quantite != quantite.to_integral_value():
        raise Refus.saisie(
            f"« {matiere.reference} » : une bobine se compte entière — saisir un nombre entier "
            "de bobines, ou le poids en kg.",
            code="unite_invalide",
        )
    c = conversions.conditionnement(matiere, lot)
    k = conversions.contenance(c, unite)
    if k is None:
        if unite == "palette" and c.bobines_palette <= 0:
            raise Refus.saisie(
                f"« {matiere.reference} » : le nombre de bobines par palette n'est pas connu, "
                "saisir en bobines ou en kg.",
                code="unite_invalide",
            )
        raise Refus.saisie(
            f"« {matiere.reference} » : le poids de bobine n'est pas connu, saisir en kg.",
            code="unite_invalide",
        )
    return arrondir(quantite * k, QUANTITE)


def _ligne(s: Session, e: SaisieOperation, x: SaisieLigne, motif: Motif | None) -> _Ligne:
    """Une ligne vérifiée (OR8–OR23), prête à enregistrer (S102)."""
    matiere, source, lot = _connus(s, x)
    if e.type is TypeOperation.ouverture and (x.unite or "kg").lower() != "kg":
        raise Refus.saisie(
            "Un stock d'ouverture se saisit en kg : il fixe le prix au kilo.",
            code="unite_invalide",
        )
    quantite = en_kg(matiere, lot, x.quantite, x.unite)
    interne = x.lot_interne and lot is None and e.type in _AVEC_LOT_NOUVEAU
    numero = "" if interne else x.lot_numero.strip()
    _verifier_par_type(
        s,
        e=e,
        x=x,
        matiere=matiere,
        lot=lot,
        quantite=quantite,
        numero=numero,
        interne=interne,
        motif=motif,
    )
    destination = _destination(s, x) if e.type is TypeOperation.transfert else None
    ouverture = e.type is TypeOperation.ouverture
    return _Ligne(
        OperationLigne(
            matiere_id=matiere.id,
            lot_id=lot.id if lot is not None else None,
            lot_numero=numero or (lot.numero if lot is not None else ""),
            lot_interne=interne,
            magasin_id=source.id,
            magasin_destination_id=destination.id if destination is not None else None,
            quantite=quantite,
            prix=arrondir(x.prix, PRIX) if ouverture else ZERO,
            devise=(x.devise or "MAD").upper() if ouverture else None,
        ),
        matiere,
        lot,
        source,
        destination,
    )


_AVEC_LOT_NOUVEAU = (TypeOperation.ouverture, TypeOperation.ajustement)
"""Les types qui créent leur lot à la validation (nommé, ou « Lot interne »)."""


def _verifier_par_type(
    s: Session,
    *,
    e: SaisieOperation,
    x: SaisieLigne,
    matiere: Matiere,
    lot: Lot | None,
    quantite: Decimal,
    numero: str,
    interne: bool,
    motif: Motif | None,
) -> None:
    """Les règles de chaque type sur une ligne (OR15–OR21, matière retrouvée)."""
    ref = matiere.reference
    if e.type is TypeOperation.ouverture:
        devise = (x.devise or "MAD").upper()
        if devise != "MAD" and s.get(Devise, devise) is None:
            raise Refus.saisie(
                f"« {ref} » : devise inconnue (« {x.devise} »). L'ajouter d'abord dans "
                "Réglages › Devises, avec son cours.",
                code="valeur_inconnue",
            )
        if not numero and not interne:
            raise Refus.saisie(
                f"« {ref} » : le numéro de lot du stock d'ouverture manque (ou cocher « Lot "
                "interne »).",
                champs={"lot_numero": "numéro du lot manquant"},
            )
        if quantite <= 0:
            raise Refus.saisie("Un stock d'ouverture est positif.", code="quantite_invalide")
    elif e.type is TypeOperation.ajustement:
        if lot is None and not numero and not interne:
            raise Refus.saisie(
                "Désigner le lot ajusté (ou en nommer un, pour une matière retrouvée)."
            )
        if quantite == 0:
            raise Refus.saisie("Un ajustement ne peut pas être nul.", code="quantite_invalide")
        retrouvee = lot is None or (motif is not None and motif.libelle == MATIERE_RETROUVEE)
        if retrouvee and quantite < 0:
            raise Refus.saisie(
                "Une matière retrouvée s'ajoute au stock : sens « + ».", code="quantite_invalide"
            )
    else:
        if lot is None:
            raise Refus.saisie(f"« {ref} » : choisir le lot.")
        if quantite <= 0:
            raise Refus.saisie("La quantité est positive.", code="quantite_invalide")
    if lot is None and numero and re.search(r"\s", numero):
        raise Refus.saisie(
            f"Un numéro de lot s'écrit sans espace : « {numero} ».",
            champs={"lot_numero": "numéro du lot avec un espace"},
        )


def _destination(s: Session, x: SaisieLigne) -> Magasin:
    """Le magasin d'arrivée d'un transfert, autre que celui de départ (OR22, OR23)."""
    if not x.magasin_destination_id or x.magasin_destination_id == x.magasin_id:
        raise Refus.saisie("Un transfert va d'un magasin à un autre.")
    destination = s.get(Magasin, x.magasin_destination_id)
    if destination is None:
        raise Refus.saisie("Magasin de destination inconnu.", code="valeur_inconnue")
    return destination


def est_quarantaine(g: Magasin | None) -> bool:
    """Un magasin de type « Quarantaine »."""
    return g is not None and g.type == TypeMagasin.quarantaine


def _quarantaine(e: SaisieOperation, lignes: list[_Ligne], motif: Motif | None, role: str) -> None:
    """Sortir d'une quarantaine : direction et achats, motif dédié ; y entrer : motif dédié et
    observations (OR24–OR26, décision de Mohamed)."""
    if e.type is not TypeOperation.transfert:
        return
    nom_motif = motif.libelle if motif is not None else ""
    libere = any(est_quarantaine(x.source) and not est_quarantaine(x.destination) for x in lignes)
    met = any(not est_quarantaine(x.source) and est_quarantaine(x.destination) for x in lignes)
    if libere:
        if not droits.peut_liberer(role):
            raise Refus.droit(droits.REFUS_LIBERATION)
        if nom_motif != droits.LIBERATION:
            raise Refus.saisie(
                f"Une sortie de quarantaine se fait avec le motif « {droits.LIBERATION} ».",
                code="motif_requis",
            )
    if met:
        if nom_motif != droits.MISE_EN_QUARANTAINE:
            raise Refus.saisie(
                "Une entrée en quarantaine se fait avec le motif "
                f"« {droits.MISE_EN_QUARANTAINE} ».",
                code="motif_requis",
            )
        if len(e.commentaire.strip()) < JUSTIFICATION_QUARANTAINE:
            raise Refus.saisie(
                "Une mise en quarantaine se justifie : écrire ce qui est douteux.",
                code="motif_requis",
            )


def _fournisseur_du_retour(lignes: list[_Ligne]) -> int | None:
    """Le fournisseur à qui l'on rend : celui du lot, sinon celui de la matière ; un seul
    (OR27, C-10)."""
    fournisseurs: set[int] = set()
    for x in lignes:
        if x.lot is None:
            continue
        fournisseur = x.lot.fournisseur_id or x.matiere.fournisseur_id
        if fournisseur is None:
            raise Refus.saisie(
                f"Le lot {x.lot.numero} n'a pas de fournisseur connu : on ne sait pas à qui "
                "le rendre.",
                code="valeur_inconnue",
            )
        fournisseurs.add(fournisseur)
    if len(fournisseurs) > 1:
        raise Refus.saisie("Un retour au fournisseur ne mêle pas deux fournisseurs.")
    return next(iter(fournisseurs), None)
