"""La fiche d'une réception (route 168) : lignes recalées sans rien écrire, blocages,
avertissements, dossier, annulation, tolérances, réclamations, et les **gestes permis**
(`actions` : geste → `None` s'il est permis, sinon la phrase du refus, la même que le service
rend — ECRANS-PRO § 4.17 « refus annoncés avant le clic »).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Lot,
    Matiere,
    Reception,
    ReceptionLigne,
    Reclamation,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import StatutDocument
from gestion_mp_pro.services import reglages
from gestion_mp_pro.services.receptions_blocages import avertissements, blocages
from gestion_mp_pro.services.receptions_lecture import (
    Annulation,
    DossierCite,
    ReceptionFiche,
    Tolerances,
    charger_receptions,
    lire_lignes,
    resume,
)
from gestion_mp_pro.services.receptions_socle import detacher_d_abord, dossier_de

GESTES = ("modifier", "supprimer", "valider", "annuler", "facture", "reclamer", "etiquettes")
"""Les gestes d'une réception (la table de transitions des essais les rejoue)."""

REFUS_ANNULEE = {
    "modifier": "Cette réception est annulée : elle ne se modifie plus.",
    "supprimer": "Une réception annulée ne se supprime pas : elle reste la trace du camion.",
    "valider": "Cette réception est annulée : elle ne se valide plus.",
    "annuler": "Cette réception est déjà annulée.",
    "facture": "Cette réception est annulée : sa facture ne se modifie plus.",
    "reclamer": "On réclame sur ce que le fournisseur a livré : cette réception est annulée.",
    "etiquettes": "Réception annulée : ses entrées ont été contre-passées.",
}
REFUS_VALIDEE = {
    "modifier": "Une réception validée est entrée en stock : elle ne se modifie plus. L'annuler "
    "(elle se contre-passe), puis en saisir une nouvelle.",
    "supprimer": "Une réception validée ne se supprime pas : l'annuler.",
    "valider": "Cette réception est déjà validée.",
}
REFUS_BROUILLON = {
    "annuler": "Seule une réception validée s'annule ; un brouillon se supprime.",
    "facture": "Un brouillon porte sa facture dans sa saisie : « Corriger » la réception pour la "
    "changer.",
    "reclamer": "On réclame sur ce que le fournisseur a livré : cette réception n'est pas encore "
    "validée.",
    "etiquettes": "Aucun lot : la réception n'est pas encore validée.",
}


@dataclass
class ReclamationCourte:
    """Une réclamation sur la réception (onglet « Réclamations »)."""

    id: int
    numero: str
    ouverte_le: date
    statut: str
    motif: str
    reception_ligne_id: int | None
    lot: str
    reference: str
    quantite: Decimal
    issue: str | None


@dataclass
class ReceptionDetaillee(ReceptionFiche):
    """La fiche et ses réclamations."""

    reclamations: list[ReclamationCourte] = field(default_factory=list)


def actions(
    r: Reception, premier_blocage: str | None, dossier: str | None
) -> dict[str, str | None]:
    """Chaque geste → `None` s'il est permis, sinon la raison (même phrase que le refus)."""
    if r.statut == StatutDocument.annulee:
        return dict(REFUS_ANNULEE)
    if r.statut == StatutDocument.brouillon:
        refus: dict[str, str | None] = dict.fromkeys(GESTES)
        refus.update(REFUS_BROUILLON)
        refus["valider"] = premier_blocage
        return refus
    refus = dict.fromkeys(GESTES)
    refus.update(REFUS_VALIDEE)
    refus["annuler"] = dossier
    if not any(x.lot_id for x in r.lignes):
        refus["etiquettes"] = "Aucun lot : toutes les lignes sont refusées."
    return refus


def _reclamations(s: Session, rid: int) -> list[ReclamationCourte]:
    """Les réclamations de la réception (référence gardée même sans lot : ligne refusée)."""
    requete = (
        select(Reclamation, Lot.numero, Matiere.reference)
        .outerjoin(ReceptionLigne, ReceptionLigne.id == Reclamation.reception_ligne_id)
        .outerjoin(Lot, Lot.id == Reclamation.lot_id)
        .outerjoin(Matiere, Matiere.id == func.coalesce(ReceptionLigne.matiere_id, Lot.matiere_id))
        .where(Reclamation.reception_id == rid)
        .order_by(Reclamation.id)
    )
    return [
        ReclamationCourte(
            x.id,
            x.numero,
            x.ouverte_le,
            str(x.statut),
            str(x.motif),
            x.reception_ligne_id,
            lot or "",
            reference or "",
            x.quantite,
            str(x.issue) if x.issue else None,
        )  # fmt: skip
        for x, lot, reference in s.execute(requete).tuples()
    ]


def fiche(s: Session, rid: int) -> ReceptionDetaillee:
    """Route 168 : la fiche entière (une lecture)."""
    trouvees = charger_receptions(s, [rid])
    if not trouvees:
        raise Refus.introuvable("Réception introuvable.")
    r = trouvees[0]
    lu, lignes = lire_lignes(s, trouvees)
    base = resume(s, r, lu)
    d = dossier_de(s, r)
    annulee_par = s.get(Utilisateur, r.annulee_par_id) if r.annulee_par_id else None
    brouillon = r.statut == StatutDocument.brouillon
    premiers = blocages(s, r, lu.ctx) if brouillon else []
    return ReceptionDetaillee(
        **vars(base),
        cree_le=r.cree_le,
        delai_paiement_jours=lu.fournisseurs[r.fournisseur_id].delai_paiement_jours,
        lignes=lignes[r.id],
        avertissements=avertissements(r, lu.ctx) if brouillon else [],
        dossier=DossierCite(d.id, d.numero, str(d.statut)) if d is not None else None,
        annulation=Annulation(
            annulee_par.nom if annulee_par else "", r.annulee_le, r.annulation_motif
        )
        if r.annulee_le is not None
        else None,
        tolerances=Tolerances(
            reglages.nombre(s, "toler_ecart_pesee"),
            reglages.nombre(s, "toler_poids_bobine"),
            reglages.nombre(s, "toler_excedent"),
        ),
        actions=actions(
            r,
            premiers[0].message if premiers else None,
            detacher_d_abord(d, "l'annuler") if d is not None else None,
        ),
        reclamations=_reclamations(s, r.id),
    )
