"""Les factures d'un dossier (routes 253 et 254) : en ajouter une, en retirer une.

Décision de Mohamed du 12/10/2026, qui amende I3 : un dossier d'importation — une déclaration en
douane, un arrivage — peut regrouper **plusieurs factures** (deux factures du même fournisseur
dans le même conteneur, ou de fournisseurs différents groupés). Le reste de I3 tient : une
facture n'appartient qu'à **un seul** dossier non annulé, toute sa marchandise libre entre avec
elle, une ligne reçue ne sort qu'avec toute sa réception.

- **Ajouter** une facture reçue qui n'est dans aucun dossier : comme à l'ouverture, toute sa
  marchandise libre entre (pesée × prix, au cours figé de son bon), un fournisseur marocain se
  confirme (I16), le coût d'un mois clos ne bouge pas. Une autre devise ou un autre fournisseur
  est permis : chaque marchandise garde sa devise, rien ne s'additionne entre devises. Deux
  postes qui prennent la même facture : l'index unique `uq_dossier_facture` départage, le
  perdant reçoit un 409 qui nomme le dossier gagnant.
- **Retirer** une facture : sa marchandise sort du dossier et attend de nouveau (les frais
  restent, répartis sur ce qui reste) ; refusé si un frais vise une marchandise qu'elle a
  apportée (il sortirait avec elle, I19).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Dossier, DossierFacture, Facture, Reception, ReceptionLigne
from gestion_mp_pro.services import audit, periode
from gestion_mp_pro.services.importations import parties
from gestion_mp_pro.services.importations.fiche import resumer
from gestion_mp_pro.services.importations.marchandises import sans_parts_sur
from gestion_mp_pro.services.importations.ouverture import (
    de_la_facture,
    facture_libre,
    fournisseur_confirme,
    inserer,
    marchandises,
)
from gestion_mp_pro.services.importations.socle import (
    a_la_main,
    contexte,
    factures_vives,
    mad,
    noter,
    ouvert,
)


def _disparates(s: Session, d: Dossier) -> str:
    """« · plusieurs cours : USD à 10 et 10.5 » quand une devise a plusieurs cours."""
    texte = ", ".join(
        f"{x.devise} à " + " et ".join(f"{c:g}" for c in x.cours)
        for x in resumer(d, contexte(s, [d])).cours_disparates
    )
    return f" · plusieurs cours : {texte}" if texte else ""


def ajouter(
    s: Session, qui: audit.Qui, did: int, version: int, facture_id: int, *, local_confirme: bool
) -> Dossier:
    """Ajoute au dossier une facture reçue qui n'est dans aucun dossier : toute sa marchandise
    libre y entre (route 253)."""
    d = ouvert(s, did, version)
    if a_la_main(d):
        raise Refus.etat(parties.A_LA_MAIN_AJOUT)
    f = facture_libre(s, facture_id)
    nom, local = fournisseur_confirme(s, f, local_confirme, "L'ajouter")
    paires = de_la_facture(s, f)
    periode.cout_hors_periode_close(s, d, "ajout d'une facture", [r.date for _, r in paires])
    lien = DossierFacture(facture_id=f.id, ajoutee_par_id=qui.id)
    inserer(s, d, marchandises(s, paires), f.id, lien)
    if local:
        d.local_confirme = True
    detail = f"{d.numero} · facture {f.numero} · {nom} · {len(paires)} ligne(s)"
    detail += " · fournisseur marocain, confirmé" if local else ""
    noter(s, qui, d, "facture ajoutée", detail + _disparates(s, d), apres={"facture": f.numero})
    return d


def _apportees(s: Session, d: Dossier, facture_id: int) -> set[int]:
    """Les marchandises du dossier que la facture a apportées (celles de ses réceptions)."""
    ids = [x.reception_ligne_id for x in d.lignes if x.reception_ligne_id]
    if not ids:
        return set()
    siennes = set(
        s.scalars(
            select(ReceptionLigne.id)
            .join(Reception, Reception.id == ReceptionLigne.reception_id)
            .where(ReceptionLigne.id.in_(ids), Reception.facture_id == facture_id)
        )
    )
    return {x.id for x in d.lignes if x.reception_ligne_id in siennes}


def retirer(s: Session, qui: audit.Qui, did: int, version: int, facture_id: int) -> Dossier:
    """Retire une facture du dossier : sa marchandise attend de nouveau son dossier, les frais
    restent et se répartissent sur ce qui reste (route 254)."""
    d = ouvert(s, did, version)
    lien = next((x for x in factures_vives(d) if x.facture_id == facture_id), None)
    f = s.get(Facture, facture_id)
    if lien is None or f is None:
        raise Refus.introuvable(f"Cette facture n'est pas dans le dossier {d.numero}.")
    sortants = _apportees(s, d, facture_id)
    refus = parties.refus_retrait(d, f.numero, sortants)
    if refus:
        raise Refus.etat(refus)
    periode.cout_hors_periode_close(s, d, "retrait d'une facture")
    sans_parts_sur(d, sortants)
    s.flush()
    for x in [y for y in d.lignes if y.id in sortants]:
        d.lignes.remove(x)
    d.factures.remove(lien)
    s.flush()
    total = sum((x.montant for x in d.frais), Decimal(0))
    detail = (
        f"{d.numero} · facture {f.numero} · {len(sortants)} ligne(s) sortie(s) · "
        f"{len(d.frais)} frais gardés ({mad(total)})"
    )
    noter(s, qui, d, "facture retirée", detail, avant={"facture": f.numero})
    return d
