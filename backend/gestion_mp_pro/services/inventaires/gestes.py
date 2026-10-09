"""Ouvrir, compter, ajouter un lot trouvé, valider, abandonner, annuler un inventaire (REGLES
B.1.16, IR1–IR20 ; Gestion MP corrigé : C-04 à C-08, C-20, D-08 ; API-PRO 128–132, 245).

On fige le théorique (soldes > 0 du périmètre, verrouillés), on compte lot par lot, on valide :
un ajustement par écart, daté du jour de l'inventaire, par `services/stock.py`. Un lot trouvé
n'est créé qu'à la validation (un abandon ne laisse aucun lot fantôme ; « Lot interne » prend
son numéro à ce moment). Un inventaire abandonné garde son numéro, ses comptages et son motif
(aucun trou dans la série INV) ; un inventaire validé s'annule une fois, par contre-passation
de ses ajustements, avec un motif.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Inventaire,
    InventaireCritere,
    InventaireLigne,
    InventaireMatiere,
    Lot,
    Magasin,
    Motif,
    Mouvement,
)
from gestion_mp_pro.modeles.enums import (
    CritereInventaire,
    DocumentMouvement,
    SerieNumero,
    StatutInventaire,
    TypeMotif,
    TypeMouvement,
)
from gestion_mp_pro.modeles.types import TAUX, arrondir
from gestion_mp_pro.services import audit, horloge, lots, numerotation, periode, reglages, stock
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.inventaires import perimetre as p
from gestion_mp_pro.services.inventaires.comptage import compter, lot_trouve
from gestion_mp_pro.services.inventaires.document import (
    charger,
    encore_ouvert,
    noms_des_personnes,
    relire,
    retenu,
    sans_justification,
)

__all__ = [
    "Ouverture",
    "abandonner",
    "annuler",
    "charger",
    "compter",
    "lot_trouve",
    "ouvrir",
    "valider",
]

MOTIF_MINIMUM = 3
ECART_D_INVENTAIRE = "Écart d'inventaire"
CITEES_DANS_UN_REFUS = 8


@dataclass(frozen=True)
class Ouverture:
    """Ce que l'écran envoie pour ouvrir un inventaire."""

    date: date
    magasin_id: int | None = None
    libelle: str = ""
    tolerance: Decimal | None = None
    criteres: p.Criteres = p.Criteres()


def ouvrir(s: Session, qui: Acteur, e: Ouverture) -> Inventaire:
    """Route 128 : numéro dès l'ouverture, théorique figé, périmètre écrit (K2)."""
    periode.date_permise(s, e.date)
    if e.magasin_id is not None and s.get(Magasin, e.magasin_id) is None:
        raise Refus.saisie("Magasin inconnu.", code="valeur_inconnue")
    p.conflit(s, e.magasin_id)
    p.verifier(s, e.criteres)
    tolerance = e.tolerance
    if tolerance is None:
        tolerance = arrondir(reglages.nombre(s, "tolerance_inventaire"), TAUX)
    suspendues = p.matieres(s, e.criteres)
    soldes = p.soldes_a_figer(s, e.magasin_id, suspendues)
    if not soldes:
        raise Refus.etat(
            "Aucun lot en stock dans ce périmètre : rien à compter, l'inventaire n'est pas ouvert."
        )
    p.refus_si_bouge_apres(s, e.date, {(x.lot_id, x.magasin_id) for x in soldes})
    i = Inventaire(
        numero=numerotation.numero(s, SerieNumero.INV, e.date),
        libelle=e.libelle or "Inventaire",
        date=e.date,
        magasin_id=e.magasin_id,
        tolerance=tolerance,
        cree_par_id=qui.id,
        cree_le=horloge.maintenant(),
        lignes=[],
        criteres=_criteres(e.criteres),
        matieres=[],
    )
    matieres_des_lots = {x.lot.matiere_id for x in soldes}
    i.matieres.extend(
        InventaireMatiere(matiere_id=m) for m in sorted(suspendues | matieres_des_lots)
    )
    for x in soldes:
        i.lignes.append(
            InventaireLigne(
                matiere_id=x.lot.matiere_id,
                lot_id=x.lot_id,
                magasin_id=x.magasin_id,
                theorique=x.quantite,
                lot_numero=x.lot.numero,
            )
        )
    s.add(i)
    s.flush()
    audit.journal(
        s,
        qui,
        "ouverture inventaire",
        "inventaire",
        i.id,
        numero=i.numero,
        detail=f"{i.numero} · {len(i.lignes)} lot(s) figés",
    )
    return i


def _criteres(c: p.Criteres) -> list[InventaireCritere]:
    """Les critères tels qu'ils ont été choisis (le périmètre dit à l'écran)."""
    rangs = [InventaireCritere(genre=CritereInventaire.matiere, matiere_id=x) for x in c.matieres]
    rangs += [InventaireCritere(genre=CritereInventaire.role, role_id=x) for x in c.roles]
    rangs += [
        InventaireCritere(genre=CritereInventaire.composition, composition_id=x)
        for x in c.compositions
    ]
    rangs += [
        InventaireCritere(genre=CritereInventaire.classe_abc, classe_abc=x) for x in c.classes_abc
    ]
    return rangs


def valider(s: Session, qui: Acteur, ident: int, version: int) -> Inventaire:
    """Route 131 : un ajustement par écart (lots trouvés créés maintenant)."""
    i = relire(s, ident, version)
    encore_ouvert(i)
    comptees = [x for x in i.lignes if x.compte is not None]
    if not comptees:
        raise Refus.saisie("Aucun lot compté : saisir les comptages avant de valider.")
    sans = sans_justification(s, i)
    if sans:
        raise Refus.saisie(
            "Écart hors tolérance sans justification : "
            + ", ".join(sans[:CITEES_DANS_UN_REFUS])
            + ".",
            code="motif_requis",
        )
    periode.date_permise(s, i.date)
    ecarts = [x for x in comptees if retenu(x) != x.theorique]
    for x in ecarts:
        if x.lot_id is None:
            nouveau = (
                lots.lot_interne(s, x.matiere_id, i.date)
                if x.lot_interne
                else stock.lot_ou_creer(s, x.matiere_id, x.lot_numero, i.date)
            )
            x.lot_id, x.lot_numero, x.lot_interne = nouveau.id, nouveau.numero, False
    s.flush()
    p.refus_si_bouge_apres(s, i.date, {(x.lot_id, x.magasin_id) for x in ecarts if x.lot_id})
    _ajuster(s, qui, i, ecarts)
    i.statut, i.valide_par_id, i.valide_le = StatutInventaire.valide, qui.id, horloge.maintenant()
    s.flush()
    audit.journal(
        s,
        qui,
        "validation inventaire",
        "inventaire",
        i.id,
        numero=i.numero,
        detail=f"{i.numero} · {len(comptees)} lot(s) comptés · {len(ecarts)} ajustement(s)",
    )
    return i


def _ajuster(s: Session, qui: Acteur, i: Inventaire, ecarts: list[InventaireLigne]) -> None:
    """Un `AJUSTEMENT` par écart, motif « Écart d'inventaire », justification et recompteur en
    commentaire (S159)."""
    motif = s.scalars(
        select(Motif).where(
            Motif.type_operation == TypeMotif.inventaire, Motif.libelle == ECART_D_INVENTAIRE
        )
    ).first()
    noms = noms_des_personnes(s, {x.second_par_id for x in ecarts if x.second_par_id is not None})
    piece = stock.Piece(DocumentMouvement.inventaire, i.id, i.numero)
    for x in ecarts:
        ecart = (retenu(x) or Decimal(0)) - x.theorique
        recompte = (
            f"recompté par {noms.get(x.second_par_id or 0, '')}"
            if x.second_compte is not None
            else ""
        )
        commentaire = " · ".join(filter(None, [x.justification.strip(), recompte]))[:300]
        stock.ecrire(
            s,
            type=TypeMouvement.AJUSTEMENT,
            lot=s.get_one(Lot, x.lot_id),
            magasin_id=x.magasin_id,
            quantite=ecart,
            jour=i.date,
            piece=piece,
            auteur_id=qui.id,
            liens=stock.Liens(
                motif_id=motif.id if motif is not None else None,
                motif_texte=ECART_D_INVENTAIRE,
                commentaire=commentaire,
            ),
        )


def _motif(motif: str, quoi: str) -> str:
    """Un motif d'au moins 3 caractères (422 sinon)."""
    texte = motif.strip()
    if len(texte) < MOTIF_MINIMUM:
        raise Refus.saisie(f"Dire pourquoi l'inventaire est {quoi}.", code="motif_requis")
    return texte


def abandonner(s: Session, qui: Acteur, ident: int, version: int, motif: str) -> Inventaire:
    """Route 132 : rien n'est ajusté, les mouvements reprennent ; il reste, « abandonné », avec
    son numéro, ses comptages et son motif (C-05)."""
    i = relire(s, ident, version)
    if i.statut == StatutInventaire.abandonne:
        raise Refus.etat(f"L'inventaire {i.numero} est déjà abandonné.")
    if i.statut == StatutInventaire.annule:
        raise Refus.etat(f"L'inventaire {i.numero} est déjà annulé.", code="deja_annule")
    if i.statut != StatutInventaire.ouvert:
        raise Refus.etat("Un inventaire validé reste : ses ajustements sont au journal.")
    texte = _motif(motif, "abandonné")
    i.statut, i.abandonne_par_id, i.abandonne_le = (
        StatutInventaire.abandonne,
        qui.id,
        horloge.maintenant(),
    )
    i.annulation_motif = texte
    s.flush()
    audit.journal(
        s,
        qui,
        "abandon inventaire",
        "inventaire",
        i.id,
        numero=i.numero,
        detail=f"{i.numero} · {texte}",
    )
    return i


def annuler(s: Session, qui: Acteur, ident: int, version: int, motif: str) -> Inventaire:
    """Route 245 : un inventaire validé, une fois ; ses ajustements contre-passés à leur date
    (refusé en période close, si la matière est repartie, si un inventaire ouvert la suspend)."""
    i = relire(s, ident, version)
    if i.statut == StatutInventaire.annule:
        raise Refus.etat(f"L'inventaire {i.numero} est déjà annulé.", code="deja_annule")
    if i.statut != StatutInventaire.valide:
        raise Refus.etat("Seul un inventaire validé s'annule ; un inventaire en cours s'abandonne.")
    texte = _motif(motif, "annulé")
    piece = stock.Piece(DocumentMouvement.inventaire, i.id, i.numero)
    ajustements = stock.a_contrepasser(s, piece)
    _aucun_inventaire_ouvert(s, ajustements)
    if ajustements:
        stock.contrepasser_mouvements(s, ajustements, qui.id)
    i.statut, i.annule_par_id, i.annule_le = StatutInventaire.annule, qui.id, horloge.maintenant()
    i.annulation_motif = texte
    s.flush()
    audit.journal(
        s,
        qui,
        "annulation inventaire",
        "inventaire",
        i.id,
        numero=i.numero,
        detail=f"{i.numero} · {texte}",
    )
    return i


def _aucun_inventaire_ouvert(s: Session, ajustements: list[Mouvement]) -> None:
    """Les écritures d'un inventaire ne sont pas suspendues par un autre : on vérifie ici
    qu'aucun inventaire ouvert ne compte une matière ajustée dans son magasin (K2)."""
    for x in ajustements:
        ouvert = stock.inventaire_qui_suspend(s, s.get_one(Lot, x.lot_id), x.magasin_id)
        if ouvert is not None:
            raise Refus.etat(
                f"L'inventaire {ouvert.numero} est en cours : les mouvements sont suspendus "
                "jusqu'à sa validation.",
                code="inventaire_en_cours",
            )
