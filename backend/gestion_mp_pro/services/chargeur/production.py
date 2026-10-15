"""Ordres de fabrication et dossiers d'importation, pour le moteur (CALCULS A § 4.6).

Un ordre compte une fois validé (son prévu figé à la validation, s'il l'a été) ; un dossier
annulé n'existe plus pour les calculs (K3 : gardé en base pour ne pas trouer la série).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.modeles import (
    Dossier,
    DossierFacture,
    DossierFrais,
    DossierFraisPart,
    DossierLigne,
    Facture,
    Ordre,
    OrdrePrevu,
    OrdreQualite,
    PosteFrais,
    Qualite,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import StatutDossier, StatutOrdre
from gestion_mp_pro.services.chargeur.contexte import Noms, a_l_usine, nombre


def ordres(s: Session, noms: Noms, ids: Sequence[int] | None = None) -> list[c.OrdreFabrication]:
    """Les ordres validés : (qualité, m²) et, s'il a été figé, le prévu hors perte.
    `ids` : ceux-là seulement (la fiche d'un ordre), lus exactement comme dans la liste entière."""
    codes = dict(s.execute(select(Qualite.id, Qualite.code)).all())
    qualites = select(OrdreQualite.ordre_id, OrdreQualite.qualite_id, OrdreQualite.m2)
    prevu = select(OrdrePrevu.ordre_id, OrdrePrevu.matiere_id, OrdrePrevu.kg_hors_perte)
    requete = select(Ordre).where(Ordre.statut == StatutOrdre.valide)
    if ids is not None:
        qualites = qualites.where(OrdreQualite.ordre_id.in_(ids))
        prevu = prevu.where(OrdrePrevu.ordre_id.in_(ids))
        requete = requete.where(Ordre.id.in_(ids))
    fabrications: dict[int, list[tuple[str, float]]] = defaultdict(list)
    for o, q, m2 in s.execute(qualites.order_by(OrdreQualite.id)):
        fabrications[o].append((codes[q], float(m2)))
    prevus: dict[int, dict[str, float]] = defaultdict(dict)
    for o, m, kg in s.execute(prevu.order_by(OrdrePrevu.ordre_id, OrdrePrevu.matiere_id)):
        prevus[o][noms.references[m]] = float(kg)
    return [
        c.OrdreFabrication(
            numero=b.numero or "",
            date=b.date,
            fabrications=fabrications.get(b.id, []),
            commentaire=b.commentaire,
            theorique=dict(prevus.get(b.id, {})) if b.prevu_fige else None,
            perte=float(b.taux_perte_fige) if b.taux_perte_fige is not None else None,
            valide_le=a_l_usine(b.valide_le),
        )
        for b in s.scalars(requete.order_by(Ordre.id))
    ]


def _lignes(s: Session, noms: Noms) -> dict[int, list[c.LigneImport]]:
    """Les marchandises de chaque dossier, dans l'ordre de leurs numéros."""
    resultat: dict[int, list[c.LigneImport]] = defaultdict(list)
    for x in s.scalars(select(DossierLigne).order_by(DossierLigne.dossier_id, DossierLigne.id)):
        resultat[x.dossier_id].append(
            c.LigneImport(
                id=x.id,
                reference=noms.references[x.matiere_id],
                quantite=nombre(x.quantite_kg),
                valeur_devise=nombre(x.valeur_devise),
                devise=x.devise,
                cours=nombre(x.cours),
                lot_fournisseur=noms.lots.get(x.lot_id, "") if x.lot_id else "",
                fournisseur=noms.fournisseur(x.fournisseur_id),
                ligne_reception_id=x.reception_ligne_id,
            )
        )
    return resultat


def _frais(s: Session) -> dict[int, list[c.ChargeImport]]:
    """Les frais de chaque dossier : poste, clé de répartition, parts figées."""
    postes = {p.id: p for p in s.scalars(select(PosteFrais))}
    parts: dict[int, dict[int, float]] = defaultdict(dict)
    for f, ligne, montant in s.execute(
        select(
            DossierFraisPart.frais_id, DossierFraisPart.ligne_id, DossierFraisPart.montant
        ).order_by(DossierFraisPart.frais_id, DossierFraisPart.ligne_id)
    ):
        parts[f][ligne] = float(montant)
    resultat: dict[int, list[c.ChargeImport]] = defaultdict(list)
    for x in s.scalars(select(DossierFrais).order_by(DossierFrais.dossier_id, DossierFrais.id)):
        poste = postes[x.poste_id]
        resultat[x.dossier_id].append(
            c.ChargeImport(
                poste=poste.code,
                montant=nombre(x.montant),
                ligne=x.ligne_id,
                piece=x.piece,
                commentaire=x.commentaire,
                recuperable_poste=poste.recuperable,
                cle=str(poste.cle),
                parts=dict(parts.get(x.id, {})),
                nature=str(poste.nature),
                entre_valeur_douane=poste.entre_valeur_douane,
            )
        )
    return resultat


def _factures(s: Session) -> dict[int, list[c.FactureImport]]:
    """Les factures de chaque dossier (une ou plusieurs, la première ajoutée d'abord), chacune
    avec les marchandises qu'elle a apportées (celles de ses réceptions)."""
    apportees: dict[tuple[int, int | None], list[int]] = defaultdict(list)
    for did, lid, fid in s.execute(
        select(DossierLigne.dossier_id, DossierLigne.id, Reception.facture_id)
        .join(ReceptionLigne, ReceptionLigne.id == DossierLigne.reception_ligne_id)
        .join(Reception, Reception.id == ReceptionLigne.reception_id)
        .where(Reception.facture_id.is_not(None))
        .order_by(DossierLigne.id)
    ):
        apportees[(did, fid)].append(lid)
    resultat: dict[int, list[c.FactureImport]] = defaultdict(list)
    requete = (
        select(DossierFacture.dossier_id, Facture)
        .join(Facture, Facture.id == DossierFacture.facture_id)
        .where(DossierFacture.liberee_le.is_(None))
        .order_by(DossierFacture.dossier_id, DossierFacture.ajoutee_le, Facture.id)
    )
    for did, f in s.execute(requete):
        resultat[did].append(
            c.FactureImport(
                numero=f.numero,
                montant=nombre(f.montant),
                devise=f.devise,
                lignes=apportees.get((did, f.id), []),
            )
        )
    return resultat


def dossiers(s: Session, noms: Noms) -> list[c.DossierImport]:
    """Les dossiers non annulés, dans l'ordre de leurs identifiants."""
    lignes, frais, factures = _lignes(s, noms), _frais(s), _factures(s)
    resultat = []
    requete = select(Dossier).where(Dossier.statut != StatutDossier.annule).order_by(Dossier.id)
    for d in s.scalars(requete):
        resultat.append(
            c.DossierImport(
                numero=d.numero,
                libelle=d.libelle,
                date_arrivee=d.date_arrivee,
                banque=d.banque,
                statut="Clos" if d.statut == StatutDossier.clos else "Ouvert",
                commentaire=d.commentaire,
                lignes=lignes.get(d.id, []),
                charges=frais.get(d.id, []),
                factures=factures.get(d.id, []),
            )
        )
    return resultat
