"""Un dossier calculé : coût de revient, TVA et droits attendus, frais non répartis, contrôles,
puis, pour la fiche (route 189), marchandises, frais, échéancier, alertes et gestes permis
(REGLES R-IMP-04 à R-IMP-14 ; défauts B-04, B-05, B-07, B-11).

Les chiffres sont ceux du moteur (`calcul/importations.py`, prouvé à l'identique de Gestion MP) ;
ce module ne fait que lire la base et assembler.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import importations as calcul
from gestion_mp_pro.calcul.importations import LigneRevient
from gestion_mp_pro.modeles import Dossier, Facture, PieceJointe
from gestion_mp_pro.services.importations import attente, parties
from gestion_mp_pro.services.importations.lignes import Marchandises, lire_marchandises
from gestion_mp_pro.services.importations.modele import (
    DossierFiche,
    DossierResume,
    FactureDossier,
)
from gestion_mp_pro.services.importations.socle import (
    CENTIME,
    DIRHAM,
    Contexte,
    a_la_main,
    charger,
    contexte,
    repris,
    vue,
)

TVA = "TVA"
"""Le seul poste comparé à la TVA attendue : la TVA de la douane (R-IMP-05)."""
DROITS = "DD"


def facture_dossier(f: Facture, ctx: Contexte) -> FactureDossier:
    """La facture telle que le dossier la montre."""
    return FactureDossier(
        id=f.id,
        numero=f.numero,
        fournisseur_id=f.fournisseur_id,
        fournisseur=ctx.nom(f.fournisseur_id),
        date=f.date,
        montant=f.montant,
        devise=f.devise,
        echeance=f.echeance,
        payee_le=f.payee_le,
    )


def _sommes(d: Dossier, ctx: Contexte) -> tuple[float, float, float, float]:
    """Frais hors TVA, TVA (récupérables), TVA de la douane, droits saisis."""
    charges = tva = douane = droits = 0.0
    for x in d.frais:
        p = ctx.postes[x.poste_id]
        montant = float(x.montant)
        if p.recuperable:
            tva += montant
        else:
            charges += montant
        douane += montant if p.code == TVA else 0.0
        droits += montant if p.code == DROITS else 0.0
    return charges, tva, douane, droits


def _ecart_tva(saisie: float, attendue: float | None, tolere: float | None) -> float | None:
    """L'écart de la TVA saisie à l'attendue quand il dépasse la tolérance réglée (C29)."""
    if not saisie or not attendue or attendue <= 0 or tolere is None:
        return None
    ecart = saisie - attendue
    return ecart if abs(ecart) > tolere else None


def _au_dela(x: float) -> float:
    """Un reste sous le demi-centime n'en est pas un."""
    return x if abs(x) > CENTIME else 0.0


def _calcul(d: Dossier, ctx: Contexte) -> tuple[dict[int, LigneRevient], Marchandises]:
    """Le coût de revient de chaque marchandise, et les marchandises lues."""
    v = vue(d, ctx)
    repartis = calcul.revient_dossier(v, ctx.parametres)
    seuil = ctx.parametres.seuil_surcout_import
    aberrantes = {x.ligne_id for x in calcul.lignes_aberrantes(repartis, seuil)}
    negatives = {x.ligne_id for x in calcul.lignes_negatives(repartis)}
    revient = {x.ligne_id: x for x in repartis}
    return revient, lire_marchandises(d, ctx, revient, aberrantes, negatives)


def _entete(d: Dossier, ctx: Contexte) -> dict[str, Any]:
    """L'en-tête du dossier : numéro, dates, statut, facture, nature, comptes, version."""
    facture = ctx.factures.get(d.facture_id) if d.facture_id else None
    return {
        "id": d.id,
        "numero": d.numero,
        "libelle": d.libelle,
        "date_arrivee": d.date_arrivee,
        "banque": d.banque,
        "commentaire": d.commentaire,
        "statut": str(d.statut),
        "clos_le": d.clos_le,
        "clos_par": ctx.personnes.get(d.clos_par_id) if d.clos_par_id else None,
        "annule_le": d.annule_le,
        "annule_par": ctx.personnes.get(d.annule_par_id) if d.annule_par_id else None,
        "annulation_motif": d.annulation_motif,
        "facture": facture_dossier(facture, ctx) if facture else None,
        "a_la_main": a_la_main(d),
        "repris": repris(d),
        "local_confirme": d.local_confirme,
        "nb_lignes": len(d.lignes),
        "nb_frais": len(d.frais),
        "version": d.version,
    }


def resume(d: Dossier, ctx: Contexte) -> tuple[DossierResume, Marchandises]:
    """Le dossier calculé, sans le détail (route 187), et ses marchandises lues."""
    p = ctx.parametres
    revient, m = _calcul(d, ctx)
    marchandise = sum(x.valeur_mad for x in revient.values())
    reparties = sum(x.charges_mad for x in revient.values())
    tva_repartie = sum(x.tva_mad for x in revient.values())
    poids = sum(x.poids_kg for x in revient.values())
    charges, tva, tva_douane, droits = _sommes(d, ctx)
    v = vue(d, ctx)
    attendue = calcul.tva_attendue(v, p) if d.lignes else None
    tolere = abs(attendue) * p.toler_tva_import if attendue else None
    attendus = m.droits_attendus if d.lignes and not m.sans_code else None
    revient_mad = marchandise + reparties
    r = DossierResume(
        **_entete(d, ctx),
        poids=poids,
        marchandise_mad=marchandise,
        charges_mad=reparties,
        tva_mad=tva_repartie,
        tva_saisie_mad=tva_douane,
        tva_attendue_mad=attendue,
        tva_ecart_tolere_mad=tolere,
        tva_ecart_mad=_ecart_tva(tva_douane, attendue, tolere),
        droits_mad=droits,
        droits_attendus_mad=attendus,
        droits_ecart_mad=calcul.ecart_droits(droits, attendus),
        revient_mad=revient_mad,
        revient_kg=revient_mad / poids if poids else None,
        decaisse_mad=revient_mad + tva_repartie,
        surcout=reparties / marchandise if marchandise else 0.0,
        seuil_surcout=p.seuil_surcout_import,
        surcout_aberrant=bool(marchandise > 0 and reparties > marchandise * p.seuil_surcout_import),
        lignes_aberrantes=sorted({x.reference for x in m.lignes if x.aberrante}),
        lignes_negatives=sorted({x.reference for x in m.lignes if x.negative}),
        ecart_facture=calcul.ecart_facture(v, p),
        lignes_cours_bon=m.au_cours_du_bon,
        cours_disparates=m.cours_disparates,
        cours_eloignes=m.cours_eloignes,
        charges_non_reparties_mad=_au_dela(charges - reparties),
        tva_non_repartie_mad=_au_dela(tva - tva_repartie),
        fournisseurs=sorted({x.fournisseur for x in m.lignes} - {""}),
        factures=sorted(k for k in m.pieces if k),
        receptions=m.liste_receptions(),
        pieces=m.liste_pieces(),
        familles=m.familles(),
        a_verifier=[],
    )
    r.a_verifier = parties.a_verifier(r)
    return r, m


def resumer(d: Dossier, ctx: Contexte) -> DossierResume:
    """Le dossier calculé, sans le détail."""
    return resume(d, ctx)[0]


def nb_pieces(s: Session, did: int) -> int:
    """Les pièces jointes du dossier (non retirées)."""
    requete = select(func.count()).where(
        PieceJointe.dossier_id == did, PieceJointe.retiree_le.is_(None)
    )
    return int(s.scalar(requete) or 0)


def fiche(s: Session, did: int) -> DossierFiche:
    """La fiche complète d'un dossier (route 189)."""
    d = charger(s, did)
    ctx = contexte(s, [d])
    r, m = resume(d, ctx)
    devises = [x.devise for x in d.lignes]
    sans_cours = sum(1 for x in d.lignes if x.devise != DIRHAM and x.cours is None)
    p = ctx.parametres
    return DossierFiche(
        **{f.name: getattr(r, f.name) for f in fields(r)},
        taux_tva_import=p.taux_tva_import,
        taux_tpi_import=p.taux_tpi_import,
        toler_tva_import=p.toler_tva_import,
        matieres_sans_code=m.matieres_sans_code,
        matieres_code_inactif=m.matieres_code_inactif,
        lignes=m.lignes,
        frais=parties.frais_lus(d, ctx),
        echeancier=parties.echeancier(d, ctx, m),
        alertes=parties.alertes(r, sans_cours, any(x != DIRHAM for x in devises)),
        actions=parties.actions(d, r, devises),
        a_rattacher=attente.du_dossier(s, d),
        nb_pieces=nb_pieces(s, d.id),
    )
