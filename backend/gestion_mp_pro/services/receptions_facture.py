"""La facture d'une réception validée (route 174) : elle se complète ou se corrige sans toucher
au stock ; champ absent = inchangé, un numéro vide la détache (R-RCP-30 à 33, A-04). Le numéro
d'une facture dont la réception est dans un dossier d'importation ne change pas : on l'en détache
d'abord (X-RCP-24). Les garde-fous de la facture elle-même (réglée, dossier clos, période close)
sont dans `services/factures.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Facture, Reception
from gestion_mp_pro.modeles.enums import StatutDocument
from gestion_mp_pro.services import audit, factures
from gestion_mp_pro.services.receptions_socle import (
    charger,
    detacher_d_abord,
    dossier_de,
    nom_reception,
    toucher,
    verifier,
)


@dataclass(frozen=True)
class FactureCorrigee:
    """Le corps de la route 174 : la version de la réception, les champs envoyés."""

    version: int
    valeurs: dict[str, object] = field(default_factory=dict)


def completer_facture(s: Session, qui: audit.Qui, rid: int, e: FactureCorrigee) -> Reception:
    """Complète ou corrige la facture d'une réception validée, sans toucher au stock ; un
    numéro vide la détache (R-RCP-30 à 33, A-04)."""
    r = charger(s, rid, verrou=True)
    verifier(s, r, e.version)
    if r.statut == StatutDocument.annulee:
        raise Refus.etat("Cette réception est annulée : sa facture ne se modifie plus.")
    if r.statut == StatutDocument.brouillon:
        raise Refus.etat(
            "Un brouillon porte sa facture dans sa saisie : « Corriger » la réception pour la "
            "changer."
        )
    actuelle = s.get(Facture, r.facture_id, with_for_update=True) if r.facture_id else None
    numero = e.valeurs.get("numero")
    change_de_numero = (
        isinstance(numero, str) and actuelle is not None and (numero.strip() != actuelle.numero)
    )
    dossier = dossier_de(s, r) if change_de_numero else None
    if dossier is not None and actuelle is not None:
        raise Refus.etat(
            f"La date, le montant et l'échéance de la facture {actuelle.numero} se corrigent "
            "ici ; son numéro, non. " + detacher_d_abord(dossier, "changer le numéro"),
            code="documents_lies",
        )
    if isinstance(numero, str) and not numero.strip():
        if actuelle is not None:
            with audit.suivre(
                s,
                qui,
                "facture détachée",
                r,
                numero=r.numero or "",
                detail=f"{nom_reception(r)} · facture {actuelle.numero}",
            ):
                r.facture_id = None
                s.flush()
            factures.oublier_si_orpheline(s, qui, actuelle.id, reception_id=r.id)
        return r
    cible = factures.preparer_cible(s, r, actuelle, numero)
    factures.corriger(s, qui, r, cible, factures.Correction(e.version, e.valeurs))
    with audit.suivre(
        s,
        qui,
        "facture complétée",
        r,
        numero=r.numero or "",
        detail=f"{nom_reception(r)} · {factures.detail_facture(cible)}",
    ):
        if r.facture_id != cible.id:
            r.facture_id = cible.id
        toucher(r)
        s.flush()
    if actuelle is not None and actuelle.id != cible.id:
        factures.oublier_si_orpheline(s, qui, actuelle.id, reception_id=r.id)
    return r
