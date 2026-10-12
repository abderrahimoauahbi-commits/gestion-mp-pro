"""Les frais d'un dossier (routes 199–201) : en MAD, négatifs pour un avoir, répartis à la clé
de leur poste, ou visés sur une seule marchandise — REGLES R-IMP-41 à R-IMP-45 ; défaut B-01.

Le `taux` d'un frais (révision 0006, lot TAUX-FRAIS) est gardé pour mémoire : l'écran en tire
un montant proposé, que l'utilisateur garde ou corrige (la douane arrondit). Le serveur enregistre
le montant reçu **tel quel** et ne le recalcule jamais depuis le taux, ni à l'écriture ni à la
lecture.

Un frais **réglé** est un décaissement constaté (I20) : son poste, son montant et sa
marchandise ne changent plus, il ne se retire pas, et il ne disparaît pas avec son dossier
(un dossier s'annule, il ne se supprime plus). L'annulation d'un règlement est réservée à la
direction, avec un motif (`services/factures.verifier_annulation_reglement`, lot D8).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul import importations as calcul
from gestion_mp_pro.modeles import Dossier, DossierFrais, PosteFrais
from gestion_mp_pro.services import audit, periode
from gestion_mp_pro.services.importations.socle import (
    contexte,
    mad,
    noter,
    ouvert,
    vue,
)


@dataclass(frozen=True)
class FraisSaisi:
    """Le corps des routes 199 et 200."""

    poste_id: int
    montant: Decimal
    taux: Decimal | None = None
    ligne_id: int | None = None
    piece: str = ""
    prestataire: str = ""
    date_piece: dt.date | None = None
    echeance: dt.date | None = None
    commentaire: str = ""


def _poste(s: Session, poste_id: int) -> PosteFrais:
    """Le poste du frais ; inconnu, le refus liste les postes (X-IMP-35)."""
    p = s.get(PosteFrais, poste_id)
    if p is None:
        connus = ", ".join(s.scalars(select(PosteFrais.code).order_by(PosteFrais.ordre)))
        raise Refus.saisie(
            f"Poste de frais inconnu : « {poste_id} » (attendu : {connus}).",
            code="valeur_inconnue",
            champs={"poste_id": "inconnu"},
        )
    return p


def _verifier(s: Session, d: Dossier, e: FraisSaisi) -> PosteFrais:
    """Poste connu, montant non nul, marchandise de ce dossier (X-IMP-35 à 37)."""
    p = _poste(s, e.poste_id)
    if not e.montant:
        raise Refus.saisie(
            "Un frais a un montant (un avoir se saisit en négatif).",
            champs={"montant": "non nul"},
        )
    if e.ligne_id is not None and not any(x.id == e.ligne_id for x in d.lignes):
        raise Refus.saisie(
            "La marchandise visée n'appartient pas à ce dossier.",
            champs={"ligne_id": "hors du dossier"},
        )
    return p


def refuser_negatif(s: Session, d: Dossier) -> None:
    """Un avoir ne rend aucune marchandise négative (R-IMP-44)."""
    ctx = contexte(s, [d])
    negatives = calcul.lignes_negatives(calcul.revient_dossier(vue(d, ctx), ctx.parametres))
    if negatives:
        x = negatives[0]
        raise Refus.etat(
            f"Ce frais rendrait {x.reference} négatif ({mad(x.revient_mad)}) : un avoir ne "
            "dépasse pas ce que la marchandise a coûté. Le porter sur tout le dossier, ou revoir "
            "son montant."
        )


def _ecrire(x: DossierFrais, e: FraisSaisi) -> None:
    """Les champs du frais (textes sans blancs autour)."""
    x.poste_id, x.montant, x.ligne_id, x.taux = e.poste_id, e.montant, e.ligne_id, e.taux
    x.piece, x.prestataire = e.piece.strip(), e.prestataire.strip()
    x.date_piece, x.echeance, x.commentaire = e.date_piece, e.echeance, e.commentaire.strip()


def _detail(d: Dossier, p: PosteFrais, e: FraisSaisi) -> str:
    """« 01/26 · TVA 62 104,41 MAD (20 %) » : la ligne du journal d'un frais."""
    taux = f" ({format(e.taux.normalize(), 'f').replace('.', ',')} %)" if e.taux else ""
    return f"{d.numero} · {p.code} {mad(e.montant)}{taux}"


def ajouter(s: Session, qui: audit.Qui, did: int, version: int, e: FraisSaisi) -> Dossier:
    """Un frais de plus (route 199)."""
    d = ouvert(s, did, version)
    p = _verifier(s, d, e)
    periode.cout_hors_periode_close(s, d, "frais")
    x = DossierFrais(parts=[])
    _ecrire(x, e)
    d.frais.append(x)
    s.flush()
    refuser_negatif(s, d)
    noter(s, qui, d, "frais", _detail(d, p, e), apres=audit.photo(x))
    return d


def _frais(d: Dossier, fid: int) -> DossierFrais:
    """Le frais du dossier (404 sinon, X-IMP-39)."""
    x = next((y for y in d.frais if y.id == fid), None)
    if x is None:
        raise Refus.introuvable("Frais introuvable dans ce dossier.")
    return x


def _a_sa_version(s: Session, d: Dossier, x: DossierFrais, version: int) -> None:
    """409 `conflit_version` si le frais a changé depuis sa lecture (l'auteur : la dernière
    ligne du journal du dossier, où tout geste d'un frais s'écrit)."""
    if x.version == version:
        return
    ligne = audit.derniere_ligne(s, "dossier", d.id)
    nom = ligne.utilisateur_nom if ligne is not None else "un autre poste"
    heure = audit.horodatage(ligne.quand) if ligne is not None else "à l'instant"
    raise Refus.etat(
        f"Ce frais a été modifié entre-temps par {nom} ({heure}) : rouvrez-le pour repartir de "
        "sa dernière version.",
        code="conflit_version",
    )


def _regle_inchange(x: DossierFrais, e: FraisSaisi) -> None:
    """Un frais réglé garde son poste, son montant, sa marchandise ; sa pièce ne se date pas
    après son règlement (B-01)."""
    if x.payee_le is None:
        return
    change = (x.poste_id, x.montant, x.ligne_id) != (e.poste_id, e.montant, e.ligne_id)
    if change:
        raise Refus.etat(
            f"Ce frais est réglé (le {x.payee_le:%d/%m/%Y}, {mad(x.montant)}) : son poste, son "
            "montant et sa marchandise ne changent plus. Un remboursement se saisit en avoir "
            "(montant négatif)."
        )
    if e.date_piece and e.date_piece > x.payee_le:
        raise Refus.saisie(
            f"La pièce ({e.date_piece:%d/%m/%Y}) ne peut pas être datée après son règlement "
            f"({x.payee_le:%d/%m/%Y}).",
            champs={"date_piece": "après le règlement"},
        )


def modifier(
    s: Session, qui: audit.Qui, did: int, fid: int, *, version: int, e: FraisSaisi
) -> Dossier:
    """Un frais corrigé (route 200) ; `version` est celle du frais."""
    d = ouvert(s, did, None)
    x = _frais(d, fid)
    _a_sa_version(s, d, x, version)
    p = _verifier(s, d, e)
    _regle_inchange(x, e)
    change = (x.poste_id, x.montant, x.ligne_id) != (e.poste_id, e.montant, e.ligne_id)
    if change:
        periode.cout_hors_periode_close(s, d, "frais")
        x.parts.clear()
    avant = audit.photo(x)
    _ecrire(x, e)
    s.flush()
    refuser_negatif(s, d)
    a, b = audit.differences(avant, audit.photo(x))
    noter(s, qui, d, "frais modifié", _detail(d, p, e), avant=a, apres=b)
    return d


def retirer(s: Session, qui: audit.Qui, did: int, fid: int, version: int) -> Dossier:
    """Un frais retiré (route 201) ; `version` est celle du frais."""
    d = ouvert(s, did, None)
    x = _frais(d, fid)
    _a_sa_version(s, d, x, version)
    if x.payee_le is not None:
        raise Refus.etat(
            f"Ce frais est réglé (le {x.payee_le:%d/%m/%Y}, {mad(x.montant)}) : il ne se "
            "retire pas, l'argent est sorti. Saisir un avoir (montant négatif)."
        )
    periode.cout_hors_periode_close(s, d, "frais")
    code = s.get(PosteFrais, x.poste_id)
    avant = audit.photo(x)
    d.frais.remove(x)
    s.flush()
    refuser_negatif(s, d)
    detail = f"{d.numero} · {code.code if code else ''} {mad(x.montant)}"
    noter(s, qui, d, "frais retiré", detail, avant=avant)
    return d
