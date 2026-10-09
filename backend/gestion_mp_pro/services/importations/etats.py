"""L'en-tête d'un dossier (route 191) et sa vie : clôture (202), réouverture (203), annulation
(204) — REGLES R-IMP-27, R-IMP-51 à R-IMP-55 ; défauts B-02, B-03, B-04, B-08.

- **Clore**, c'est figer le coût : une marchandise en devise sans cours prend le cours du jour,
  marqué `cours_origine = clos_au_jour` ; les alertes (cours vides, cours du bon, frais hors
  norme, facture, droits, TVA…) se lisent avant (`alertes_lues`).
- **Rouvrir** rend vides les cours que la clôture avait figés d'office (B-08) ; un cours saisi,
  ou figé par la clôture d'une période (`periode_close`), reste.
- **Annuler** remplace la suppression (B-02) : le dossier garde son numéro (série sans trou),
  sa facture est libérée, ses marchandises sont détachées de leurs lignes reçues
  (`reception_ligne_id = NULL`) pour qu'un nouveau dossier les reprenne, ses frais restent en
  lecture, hors de tout coût (un frais réglé reste réglé).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Devise, Dossier, Facture
from gestion_mp_pro.modeles.enums import OrigineCours, StatutDossier
from gestion_mp_pro.modeles.types import COURS, arrondir
from gestion_mp_pro.services import audit, horloge, periode
from gestion_mp_pro.services.importations import parties
from gestion_mp_pro.services.importations.fiche import resume
from gestion_mp_pro.services.importations.ouverture import (
    arrivee_constatee,
    avant_la_mise_en_service,
)
from gestion_mp_pro.services.importations.socle import (
    ANNULE,
    CLOS,
    DIRHAM,
    Contexte,
    a_la_main,
    charger,
    contexte,
    mad,
    noter,
    ouvert,
    verifier,
)

MOTIF_MIN = 3


@dataclass(frozen=True)
class EnTete:
    """Le corps de la route 191 : ce que l'en-tête permet de modifier (fiche entière)."""

    version: int
    libelle: str
    banque: str
    commentaire: str
    date_arrivee: dt.date | None


def modifier(s: Session, qui: audit.Qui, did: int, e: EnTete) -> Dossier:
    """Libellé, banque, observations, date d'arrivée (qui peut se vider) — R-IMP-27, B-03."""
    d = ouvert(s, did, e.version)
    arrivee_constatee(e.date_arrivee)
    if e.date_arrivee != d.date_arrivee:
        dates = [x for x in (e.date_arrivee, d.date_arrivee) if x]
        periode.cout_hors_periode_close(s, d, "date d'arrivée", dates)
        if a_la_main(d) and e.date_arrivee is not None:
            avant_la_mise_en_service(s, e.date_arrivee)
    with audit.suivre(s, qui, "modification dossier", d, numero=d.numero, detail=d.numero):
        d.libelle, d.banque = e.libelle.strip(), e.banque.strip()
        d.commentaire, d.date_arrivee = e.commentaire.strip(), e.date_arrivee
    return d


def _references(d: Dossier, ctx: Contexte) -> dict[int, str]:
    """La référence de chaque marchandise."""
    return {x.id: ctx.matieres[x.matiere_id].reference for x in d.lignes}


def cloturer(s: Session, qui: audit.Qui, did: int, version: int, alertes_lues: bool) -> Dossier:
    """Clore le dossier : son coût se fige (R-IMP-51, 52 ; B-04)."""
    d = ouvert(s, did, version)
    ctx = contexte(s, [d])
    r, _ = resume(d, ctx)
    if not r.nb_lignes:
        raise Refus.saisie(parties.SANS_MARCHANDISE)
    if r.charges_non_reparties_mad or r.tva_non_repartie_mad:
        raise Refus.etat(parties.NON_REPARTIS)
    sans_cours = [x for x in d.lignes if x.devise != DIRHAM and x.cours is None]
    devises = any(x.devise != DIRHAM for x in d.lignes)
    alertes = parties.alertes(r, len(sans_cours), devises)
    if alertes and not alertes_lues:
        raise Refus.saisie(
            "Clore ce dossier se confirme après lecture de ses alertes : " + " ".join(alertes),
            code="confirmation_requise",
        )
    references = _references(d, ctx)
    figes = []
    for x in sans_cours:
        devise = s.get(Devise, x.devise)
        if devise is None or not devise.cours:
            continue
        x.cours = arrondir(devise.cours, COURS)
        x.cours_origine = OrigineCours.clos_au_jour
        figes.append(f"{references[x.id]} à {x.cours:g}")
    d.statut, d.clos_le, d.clos_par_id = StatutDossier.clos, horloge.maintenant(), qui.id
    detail = d.numero + (f" · cours du jour figé : {', '.join(figes)}" if figes else "")
    if r.lignes_cours_bon:
        detail += f" · {r.lignes_cours_bon} ligne(s) au cours du bon"
    noter(s, qui, d, "clôture dossier", detail, apres={"statut": "clos"})
    return d


def rouvrir(s: Session, qui: audit.Qui, did: int, version: int, motif: str) -> Dossier:
    """Rouvrir un dossier clos pour corriger (R-IMP-54 ; B-08)."""
    d = charger(s, did, verrou=True)
    verifier(s, d, version)
    if d.statut == StatutDossier.annule:
        raise Refus.etat(ANNULE)
    if d.statut == StatutDossier.ouvert:
        raise Refus.etat(parties.DEJA_OUVERT)
    periode.cout_hors_periode_close(s, d, "réouverture")
    references = _references(d, contexte(s, [d]))
    rendus = []
    for x in d.lignes:
        if x.cours_origine == OrigineCours.clos_au_jour:
            rendus.append(f"{references[x.id]} ({x.cours:g})")
            x.cours, x.cours_origine = None, None
    d.statut, d.clos_le, d.clos_par_id = StatutDossier.ouvert, None, None
    detail = d.numero + (f" · {motif.strip()}" if motif.strip() else "")
    if rendus:
        detail += f" · cours du jour figé à la clôture retiré : {', '.join(rendus)}"
    noter(s, qui, d, "réouverture dossier", detail, avant={"statut": "clos"})
    return d


def annuler(s: Session, qui: audit.Qui, did: int, version: int, motif: str) -> Dossier:
    """Annuler le dossier : il garde son numéro, sa facture et sa marchandise sont libérées,
    ses frais sortent du coût (B-02, ECRANS-PRO 5.6)."""
    d = charger(s, did, verrou=True)
    verifier(s, d, version)
    if d.statut == StatutDossier.annule:
        raise Refus.etat(parties.DEJA_ANNULE, code="deja_annule")
    if d.statut == StatutDossier.clos:
        raise Refus.etat(CLOS, code="dossier_clos")
    motif = motif.strip()
    if len(motif) < MOTIF_MIN:
        raise Refus.saisie(
            "Le motif est obligatoire : 3 caractères au moins.",
            code="motif_requis",
            champs={"motif": "3 caractères au moins"},
        )
    periode.cout_hors_periode_close(s, d, "annulation")
    facture = s.get(Facture, d.facture_id) if d.facture_id else None
    for x in d.lignes:
        x.reception_ligne_id = None
    d.statut, d.annule_le, d.annule_par_id = StatutDossier.annule, horloge.maintenant(), qui.id
    d.annulation_motif = motif
    total = sum((f.montant for f in d.frais), Decimal(0))
    detail = f"{d.numero} · {motif}" + (f" · facture {facture.numero} libérée" if facture else "")
    if d.frais:
        detail += f" · {len(d.frais)} frais ({mad(total)}) sortis du coût"
    noter(s, qui, d, "annulation dossier", detail, avant={"statut": "ouvert"})
    return d
