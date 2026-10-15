"""« Mettre au rebut » un fond de lot (lot FOND-DE-LOT ; décision de Mohamed du 15/10/2026).

Un **ajustement en moins** au motif « Rebut », sur **tout** ce que le lot porte dans ce magasin,
créé et validé dans une seule transaction par le chemin ordinaire des opérations
(`gestes.creer(valider=True)`) : numéro `AJU-…`, journal, période close, inventaire en cours,
valorisation au coût moyen comme tout ajustement ; le mouvement se voit dans la traçabilité du
lot et dans la ligne « ajustements » du bilan du mois.

Qui, et sur quoi :

- un **fond de lot** (reste > 0 et sous le seuil de rebut) : direction et achats au bureau,
  alimentation au téléphone depuis la fiche du lot — **sauf** un lot en quarantaine, que
  l'atelier ne met pas au rebut (c'est une décision de la direction ou des achats) ;
- **au-dessus du seuil** (« ce n'est pas un fond de lot ») : refus 409 `pas_un_fond_de_lot`,
  sauf pour la direction, avec un motif écrit (cinq caractères au moins) ;
- la version du lot lue par l'écran est vérifiée (409 `conflit_version`) ; le lot porte une
  ligne de journal « rebut fond de lot », qui fait avancer sa version.

Le motif « Rebut » est semé par la révision 0009 ; s'il manque (base plus ancienne, référentiel
retouché), il est recréé ici, à la suite des motifs d'ajustement.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Lot, Magasin, Motif, Operation, Solde
from gestion_mp_pro.modeles.enums import ObjetJournal, Role, TypeMagasin, TypeMotif, TypeOperation
from gestion_mp_pro.services import audit, fonds_de_lot, horloge, lots_fiche
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.operations import gestes
from gestion_mp_pro.services.operations.saisie import (
    JUSTIFICATION_AJUSTEMENT,
    SaisieLigne,
    SaisieOperation,
)

MOTIF_REBUT = "Rebut"
"""Le libellé du motif d'ajustement (révision 0009) ; l'écran le lit dans `GET /motifs`."""

REFUS_QUARANTAINE = (
    "Un lot en quarantaine ne se met pas au rebut depuis l'atelier : c'est une décision de la "
    "direction ou des achats, après contrôle de la matière."
)
ZERO = Decimal(0)


@dataclass(frozen=True)
class DemandeRebut:
    """Route 258 : le lot, le magasin, la version lue, le motif (exigé au-dessus du seuil)."""

    lot_id: int
    magasin_id: int
    version: int
    motif: str = ""


def motif_rebut(s: Session) -> Motif:
    """Le motif d'ajustement « Rebut », recréé s'il manque."""
    trouve = s.scalars(
        select(Motif).where(
            Motif.type_operation == TypeMotif.ajustement, Motif.libelle == MOTIF_REBUT
        )
    ).first()
    if trouve is not None:
        return trouve
    rang = s.scalar(
        select(func.coalesce(func.max(Motif.ordre) + 1, 0)).where(
            Motif.type_operation == TypeMotif.ajustement
        )
    )
    motif = Motif(type_operation=TypeMotif.ajustement, libelle=MOTIF_REBUT, ordre=rang or 0)
    s.add(motif)
    s.flush()
    return motif


def _solde_verrouille(s: Session, lot: Lot, magasin: Magasin) -> Decimal:
    """Ce que le lot porte dans ce magasin, sous verrou (un seul rebut à la fois)."""
    solde = s.scalars(
        select(Solde)
        .where(Solde.lot_id == lot.id, Solde.magasin_id == magasin.id)
        .with_for_update()
    ).first()
    quantite = solde.quantite if solde is not None else ZERO
    if quantite <= 0:
        raise Refus.etat(
            f"Le lot {lot.numero} ne porte plus rien dans « {magasin.code} » : rien à mettre au "
            "rebut.",
            code="stock_insuffisant",
        )
    return quantite


def _permis(
    qui: Acteur, lot: Lot, magasin: Magasin, *, q: Decimal, seuil: Decimal, motif: str
) -> None:
    """Qui met quoi au rebut : fond de lot pour tous (quarantaine : pas l'atelier) ; au-dessus
    du seuil, la direction seule, avec un motif."""
    if fonds_de_lot.est_fond(q, seuil):
        if qui.role == Role.alimentation and magasin.type == TypeMagasin.quarantaine:
            raise Refus.droit(REFUS_QUARANTAINE)
        return
    poids = fonds_de_lot.poids_lisible(q)
    regle = (
        f"le seuil de rebut est {fonds_de_lot.seuil_lisible(seuil)}"
        if seuil > 0
        else "le seuil de rebut est désactivé (0)"
    )
    if qui.role != Role.direction:
        raise Refus.etat(
            f"Ce n'est pas un fond de lot : le lot {lot.numero} porte {poids} dans "
            f"« {magasin.code} », {regle}. Seule la direction met au rebut au-dessus du seuil, "
            "avec un motif.",
            code="pas_un_fond_de_lot",
        )
    if len(motif.strip()) < JUSTIFICATION_AJUSTEMENT:
        raise Refus.saisie(
            f"Ce n'est pas un fond de lot ({poids} dans « {magasin.code} », {regle}) : la "
            "direction écrit pourquoi elle le met au rebut (cinq caractères au moins).",
            code="motif_requis",
        )


def _commentaire(q: Decimal, seuil: Decimal, magasin: Magasin, motif: str) -> str:
    """« Fond de lot mis au rebut : 56 g dans Morocco (seuil 100 g). » + le motif écrit."""
    nature = "Fond de lot mis au rebut" if fonds_de_lot.est_fond(q, seuil) else "Mis au rebut"
    seuil_dit = fonds_de_lot.seuil_lisible(seuil) if seuil > 0 else "désactivé"
    poids = fonds_de_lot.poids_lisible(q)
    debut = f"{nature} : {poids} dans « {magasin.code} » (seuil {seuil_dit})."
    return " ".join(filter(None, [debut, motif.strip()]))[:500]


def mettre_au_rebut(s: Session, qui: Acteur, e: DemandeRebut) -> Operation:
    """Route 258 : l'ajustement « Rebut » validé, sur tout le reste du lot dans ce magasin."""
    lot = s.get(Lot, e.lot_id)
    if lot is None:
        raise Refus.introuvable("Lot introuvable.")
    magasin = s.get(Magasin, e.magasin_id)
    if magasin is None:
        raise Refus.saisie("Magasin inconnu.", code="valeur_inconnue")
    if lots_fiche.version(s, lot.id) != e.version:
        raise Refus.etat(
            f"Le lot {lot.numero} a bougé entre-temps : rouvrez-le pour repartir de sa dernière "
            "version.",
            code="conflit_version",
        )
    q = _solde_verrouille(s, lot, magasin)
    seuil = fonds_de_lot.seuil(s)
    _permis(qui, lot, magasin, q=q, seuil=seuil, motif=e.motif)
    saisie = SaisieOperation(
        type=TypeOperation.ajustement,
        date=horloge.aujourd_hui(),
        lignes=(SaisieLigne(lot.matiere_id, magasin.id, -q, lot_id=lot.id),),
        motif_id=motif_rebut(s).id,
        commentaire=_commentaire(q, seuil, magasin, e.motif),
    )
    o = gestes.creer(s, qui, saisie, valider=True, droit_tranche=True)
    audit.journal(
        s, qui, "rebut fond de lot", ObjetJournal.lot, lot.id, numero=o.numero or "",
        detail=f"{lot.numero} · {fonds_de_lot.poids_lisible(q)} dans {magasin.code} · {o.numero}",
    )  # fmt: skip
    s.flush()  # la version du lot avance tout de suite (la fiche relue la voit)
    return o
