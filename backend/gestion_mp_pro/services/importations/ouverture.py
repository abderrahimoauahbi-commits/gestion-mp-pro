"""Ouvrir un dossier (route 190) et y rattacher le second camion d'une de ses factures (route
192) — REGLES R-IMP-19 à R-IMP-30 ; défauts B-02, B-03. Une facture s'ajoute ensuite à un dossier
ouvert (route 253, `factures_du_dossier`) : un dossier en porte une ou plusieurs (décision de
Mohamed du 12/10/2026), une facture n'est que dans un seul dossier.

Depuis une facture : toute sa marchandise libre entre, à sa pesée × son prix, au cours figé de
son bon s'il y en a un (`cours_origine = bon`), sinon sans cours (« cours du jour »). Le numéro
suit la série `NN/AA` de l'année d'arrivée, sans trou (`services/numerotation`). Seul un dossier
d'avant la mise en service se saisit à la main, avec son vrai numéro s'il en avait un.

**Deux postes** qui ouvrent ensemble le dossier d'une facture (ou l'ajoutent chacun à un
dossier, ou rattachent la même marchandise) : les index uniques départagent, l'insertion se
fait dans un point de reprise, et le perdant reçoit un 409 qui nomme le dossier gagnant —
jamais une erreur du serveur.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Dossier,
    DossierFacture,
    DossierLigne,
    Facture,
    Fournisseur,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import OrigineCours, SerieNumero, StatutDocument
from gestion_mp_pro.modeles.types import MONTANT, arrondir
from gestion_mp_pro.services import audit, horloge, numerotation, periode
from gestion_mp_pro.services.fournisseurs import est_local
from gestion_mp_pro.services.importations.fiche import resumer
from gestion_mp_pro.services.importations.libres import (
    factures_acceptees,
    lignes_libres,
    porteurs,
)
from gestion_mp_pro.services.importations.parties import A_LA_MAIN
from gestion_mp_pro.services.importations.socle import (
    DIRHAM,
    a_la_main,
    bons,
    contexte,
    noter,
    ouvert,
)

Paires = Sequence[tuple[ReceptionLigne, Reception]]
SERIE = re.compile(r"(\d{1,3})/(\d{2})")


@dataclass(frozen=True)
class Ouverture:
    """Le corps de la route 190 : depuis une facture, ou à la main (d'avant la mise en service)."""

    facture_id: int | None = None
    numero: str = ""
    libelle: str = ""
    date_arrivee: date | None = None
    banque: str = ""
    commentaire: str = ""
    local_confirme: bool = False


def arrivee_constatee(jour: date | None) -> None:
    """Une arrivée se constate, elle ne se prévoit pas (B-03)."""
    if jour is not None and jour > horloge.aujourd_hui():
        raise Refus.saisie(
            f"Date d'arrivée dans le futur ({jour:%d/%m/%Y}) : une arrivée se constate, elle ne "
            "se prévoit pas.",
            code="date_future",
            champs={"date_arrivee": "dans le futur"},
        )


def avant_la_mise_en_service(s: Session, arrivee: date) -> None:
    """Seul un dossier d'avant la mise en service (la première réception validée) se saisit à
    la main (I3, B-03)."""
    service = s.scalar(
        select(func.min(Reception.date)).where(Reception.statut == StatutDocument.validee)
    )
    if service is not None and arrivee >= service:
        raise Refus.saisie(
            f"Un dossier saisi à la main est d'avant la mise en service (avant le "
            f"{service:%d/%m/%Y}) : après, la marchandise entre par sa facture.",
            champs={"date_arrivee": "après la mise en service"},
        )


def _pris(s: Session, numero: str) -> bool:
    """Ce numéro de dossier est-il déjà porté (annulés compris : ils le gardent) ?"""
    return s.scalar(select(Dossier.id).where(Dossier.numero == numero)) is not None


def numero_suivant(s: Session, arrivee: date) -> tuple[int, int, str]:
    """Le numéro suivant de la série `NN/AA` de l'année d'arrivée (année, rang, texte), en
    sautant les numéros saisis à la main (R-IMP-23)."""
    texte = numerotation.numero(s, SerieNumero.DOS, arrivee, deja_pris=lambda n: _pris(s, n))
    return arrivee.year, int(texte.split("/")[0]), texte


def numero_saisi(s: Session, brut: str) -> str:
    """Le vrai numéro d'un dossier d'avant la mise en service : « 7/19 » est « 07/19 »."""
    serie = SERIE.fullmatch(brut.strip())
    if serie is None:
        raise Refus.saisie(
            "Un numéro de dossier s'écrit NN/AA (« 07/19 ») : vide, il prend le suivant de la "
            "série.",
            champs={"numero": "NN/AA"},
        )
    voulu = f"{int(serie[1]):02d}/{serie[2]}"
    if _pris(s, voulu):
        raise Refus.etat(f"Le dossier « {voulu} » existe déjà.", code="numero_pris")
    return voulu


def deja_porte(s: Session, f: Facture, porteur: tuple[int, str]) -> str:
    """Le refus d'un second dossier pour une facture : il dit où va ce qui en reste."""
    did, numero = porteur
    lien = s.get(DossierFacture, (did, f.id))
    if lien is not None and lien.liberee_le is None:
        return (
            f"Cette facture a déjà son dossier, {numero} : un dossier par facture. Ce qui en "
            "reste à rattacher (un second camion) s'y ajoute."
        )
    return (
        f"La facture {f.numero} est déjà dans le dossier {numero} (repris de l'ancien ERP) : une "
        "facture ne se partage pas entre deux dossiers. Ce qui en reste à rattacher s'y ajoute."
    )


def de_la_facture(s: Session, f: Facture) -> list[tuple[ReceptionLigne, Reception]]:
    """Toute la marchandise libre de la facture, ses réceptions verrouillées en partage."""
    libres = lignes_libres(s, facture_id=f.id, verrou=True)
    if not libres:
        raise Refus.etat(
            f"La facture « {f.numero} » n'a plus de marchandise à rattacher : elle est déjà "
            "dans un dossier, ou ses réceptions ne sont pas validées."
        )
    return libres


def marchandises(s: Session, paires: Paires) -> list[DossierLigne]:
    """Chaque ligne reçue devient une marchandise : pesée × prix, au cours figé de son bon s'il
    est dans sa devise, sinon sans cours (R-IMP-24)."""
    figes = bons(s, (x.id for x, _ in paires))
    resultat = []
    for x, r in paires:
        bon = figes.get(x.id)
        cours = bon.cours if bon and bon.devise == r.devise and r.devise != DIRHAM else None
        resultat.append(
            DossierLigne(
                reception_ligne_id=x.id,
                matiere_id=x.matiere_id,
                lot_id=x.lot_id,
                fournisseur_id=r.fournisseur_id,
                quantite_kg=x.quantite_pesee,
                valeur_devise=arrondir(x.quantite_pesee * x.prix, MONTANT),
                devise=r.devise,
                cours=cours,
                cours_origine=OrigineCours.bon if cours else None,
            )
        )
    return resultat


def refus_concurrent(s: Session, facture_id: int | None) -> Refus:
    """Un autre poste a enregistré la même chose entre-temps (X-IMP-09, 10)."""
    gagnants = porteurs(s, [facture_id]).get(facture_id) if facture_id else None
    if gagnants:
        return Refus.etat(
            f"Un autre poste vient d'enregistrer cette facture dans le dossier {gagnants[0][1]} : "
            "l'ouvrir pour la suite (rien n'est perdu).",
            code="doublon",
        )
    return Refus.etat(
        "Un autre poste vient d'enregistrer la même chose (même numéro de dossier, ou même "
        "marchandise) : recharger la page, puis reprendre.",
        code="doublon",
    )


def inserer(
    s: Session,
    d: Dossier,
    lignes: list[DossierLigne],
    facture_id: int | None,
    lien: DossierFacture | None = None,
) -> None:
    """Le dossier, sa facture nouvelle et ses marchandises, dans un point de reprise : les index
    uniques (`uq_dossier_facture`, la ligne reçue) départagent deux postes."""
    try:
        with s.begin_nested():
            if d.id is None:
                s.add(d)
            if lien is not None:
                d.factures.append(lien)
            d.lignes.extend(lignes)
            s.flush()
    except IntegrityError:
        raise refus_concurrent(s, facture_id) from None


def facture_libre(s: Session, facture_id: int | None) -> Facture:
    """La facture qui ouvre un dossier ou s'y ajoute : connue, et dans aucun dossier (une
    facture n'est que dans un seul dossier)."""
    f = s.get(Facture, facture_id) if facture_id else None
    if f is None:
        raise Refus.introuvable("Facture inconnue.")
    deja = porteurs(s, [f.id]).get(f.id)
    if deja:
        raise Refus.etat(deja_porte(s, f, deja[0]), code="doublon")
    return f


def fournisseur_confirme(s: Session, f: Facture, confirme: bool, geste: str) -> tuple[str, bool]:
    """Le nom du fournisseur de la facture, et s'il est marocain : alors le geste se confirme
    (I16, ni douane ni fret international)."""
    fournisseur = s.get(Fournisseur, f.fournisseur_id)
    if fournisseur is None:
        return "", False
    local = est_local(fournisseur.pays, fournisseur.devise)
    if local and not confirme:
        raise Refus.etat(
            f"{fournisseur.nom} est un fournisseur marocain : ni douane, ni fret international, "
            f"sa facture {f.numero} n'a normalement pas de dossier d'importation. {geste} quand "
            "même se confirme."
        )
    return fournisseur.nom, local


def _depuis_facture(s: Session, qui: audit.Qui, e: Ouverture) -> Dossier:
    """Le dossier d'une facture : toute sa marchandise libre (R-IMP-19, 21 à 25)."""
    f = facture_libre(s, e.facture_id)
    if e.numero.strip():
        raise Refus.saisie(
            "Le dossier d'une facture prend le numéro suivant de la série (NN/AA) : un numéro "
            "choisi ne vaut que pour un dossier d'avant la mise en service, saisi à la main.",
            champs={"numero": "automatique"},
        )
    nom, local = fournisseur_confirme(s, f, e.local_confirme, "L'ouvrir")
    paires = de_la_facture(s, f)
    periode.cout_hors_periode_close(s, None, "ouverture du dossier", [r.date for _, r in paires])
    arrivee = e.date_arrivee or min((r.date for _, r in paires), default=horloge.aujourd_hui())
    annee, rang, numero = numero_suivant(s, arrivee)
    d = Dossier(
        numero=numero,
        annee=annee,
        rang=rang,
        libelle=e.libelle.strip() or f"{nom} — facture {f.numero}",
        date_arrivee=arrivee,
        banque=e.banque.strip(),
        commentaire=e.commentaire.strip(),
        local_confirme=local,
        cree_par_id=qui.id,
    )
    lien = DossierFacture(facture_id=f.id, ajoutee_par_id=qui.id)
    inserer(s, d, marchandises(s, paires), f.id, lien)
    detail = f"{numero} · {len(paires)} ligne(s) · facture {f.numero}"
    journaliser(s, qui, d, detail + (" · fournisseur marocain, confirmé" if local else ""))
    return d


def _a_la_main(s: Session, qui: audit.Qui, e: Ouverture) -> Dossier:
    """Un dossier d'avant la mise en service, vide, à remplir ligne par ligne (B-03)."""
    if e.date_arrivee is None:
        raise Refus.saisie(
            "Un dossier saisi à la main est d'avant la mise en service : dire sa date d'arrivée.",
            champs={"date_arrivee": "obligatoire sans facture"},
        )
    avant_la_mise_en_service(s, e.date_arrivee)
    if e.numero.strip():
        annee, rang, numero = None, None, numero_saisi(s, e.numero)
    else:
        annee, rang, numero = numero_suivant(s, e.date_arrivee)
    d = Dossier(
        numero=numero,
        annee=annee,
        rang=rang,
        libelle=e.libelle.strip(),
        date_arrivee=e.date_arrivee,
        banque=e.banque.strip(),
        commentaire=e.commentaire.strip(),
        saisi_a_la_main=True,
        cree_par_id=qui.id,
    )
    inserer(s, d, [], None)
    journaliser(s, qui, d, f"{numero} · 0 ligne(s) · saisi à la main")
    return d


def journaliser(s: Session, qui: audit.Qui, d: Dossier, detail: str) -> None:
    """« ouverture dossier » au journal, la fiche entière en `apres` (R-IMP-25)."""
    audit.creation(s, qui, "ouverture dossier", d, numero=d.numero, detail=detail)


def creer(s: Session, qui: audit.Qui, e: Ouverture) -> Dossier:
    """Ouvre un dossier (route 190)."""
    arrivee_constatee(e.date_arrivee)
    if e.facture_id is not None:
        return _depuis_facture(s, qui, e)
    return _a_la_main(s, qui, e)


def _refus_autre_facture(s: Session, d: Dossier, facture_id: int) -> Refus:
    """Le second camion d'une facture qui n'est pas dans ce dossier : l'y ajouter d'abord, ou
    elle ouvre son propre dossier (X-IMP-13, 14)."""
    autre = s.get(Facture, facture_id)
    nom = autre.numero if autre else "choisie"
    if not d.saisi_a_la_main:
        return Refus.etat(
            f"La facture {nom} n'est pas dans le dossier {d.numero} : l'y ajouter d'abord "
            "(« Ajouter une facture », toute sa marchandise entre), ou elle ouvre son propre "
            "dossier."
        )
    return Refus.etat(
        f"Le dossier {d.numero}, repris de l'ancien ERP, ne prend que la suite des factures "
        f"qu'il porte déjà. La facture {nom} ouvre son propre dossier."
    )


def rattacher(s: Session, qui: audit.Qui, did: int, version: int, facture_id: int) -> Dossier:
    """Le second camion d'une facture rejoint son dossier (route 192 ; R-IMP-28 à 30)."""
    d = ouvert(s, did, version)
    if facture_id not in factures_acceptees(s, d):
        raise Refus.etat(A_LA_MAIN) if a_la_main(d) else _refus_autre_facture(s, d, facture_id)
    f = s.get(Facture, facture_id)
    if f is None:
        raise Refus.introuvable("Facture inconnue.")
    paires = de_la_facture(s, f)
    periode.cout_hors_periode_close(s, d, "rattachement", [r.date for _, r in paires])
    inserer(s, d, marchandises(s, paires), f.id)
    disparates = ", ".join(
        f"{x.devise} à " + " et ".join(f"{c:g}" for c in x.cours)
        for x in resumer(d, contexte(s, [d])).cours_disparates
    )
    detail = f"{d.numero} · {len(paires)} ligne(s) · facture {f.numero}"
    noter(
        s,
        qui,
        d,
        "marchandises dossier",
        detail + (f" · plusieurs cours : {disparates}" if disparates else ""),
    )
    return d
