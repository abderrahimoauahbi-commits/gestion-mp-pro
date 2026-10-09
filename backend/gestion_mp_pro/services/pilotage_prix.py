"""Les prix payés et les pistes d'économies (routes 211, 213, 214, 218, 219).

- Historique (213) : chaque prix payé, son précédent (même matière, même fournisseur, même
  devise), son évolution ; cherché (tous les mots, sans accents) et borné par dates.
- Matrice (214) : le prix moyen pondéré par mois, **dans la devise de la facture** (E-04 :
  une moyenne de dollars et d'euros n'est aucun prix).
- Opportunités (211) : même composition, type et titrage — même couleur par défaut (T6) —,
  chez un autre fournisseur, à des prix de la même époque, sur des coûts **rendus usine**
  (M84) ; matière désactivée ignorée, dernier prix d'un jour = dernier saisi (E-05).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul.opportunites import comparer_les_prix
from gestion_mp_pro.calcul.prix import PRIX_STABLE, historique_prix, matrice_prix
from gestion_mp_pro.modeles import Commande
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.services import donnees_moteur
from gestion_mp_pro.services.pilotage import couts_d_achat, ids_fournisseurs, ids_matieres, lire

FENETRE_MIN, FENETRE_MAX = 1, 3650
"""Bornes de la fenêtre de comparaison des prix (jours)."""


def _correspond(mots: list[str], *champs: object) -> bool:
    """Tous les mots dans l'un des champs (sans accents)."""
    texte = normaliser(" ".join(str(c) for c in champs if c is not None))
    return all(m in texte for m in mots)


@dataclass
class HistoriquePrix:
    """Les prix payés, le plus récent d'abord, et leurs indicateurs (sur les lignes rendues)."""

    lignes: list[dict[str, Any]]
    total_achats_mad: float
    hausses: int
    fortes_hausses: int
    baisses: int
    seuils: dict[str, float]


def _seuils(forte: float) -> dict[str, float]:
    return {"stable": PRIX_STABLE, "forte": forte}


def historique(
    s: Session, q: str = "", du: date | None = None, au: date | None = None
) -> HistoriquePrix:
    """Route 213 : chaque prix payé (date = celle de la réception), filtré."""
    d = donnees_moteur.charger(s)
    mots = normaliser(q).split()
    ids, fournisseurs = ids_matieres(s), ids_fournisseurs(s)
    bons = dict(
        s.execute(select(Commande.numero, Commande.id).where(Commande.numero.is_not(None))).all()
    )
    lignes = [
        {
            **asdict(x),
            "matiere_id": ids.get(x.reference),
            "fournisseur_id": fournisseurs.get(x.fournisseur),
            "commande_id": bons.get(x.numero_bc),
        }
        for x in historique_prix(d)
        if (du is None or (x.date_bc is not None and x.date_bc >= du))
        and (au is None or (x.date_bc is not None and x.date_bc <= au))
        and _correspond(mots, x.reference, x.nature, x.designation, x.fournisseur, x.numero_bc)
    ]
    forte = d.parametres.seuil_hausse_forte
    evolutions = [x["evolution"] or 0.0 for x in lignes]
    return HistoriquePrix(
        lignes=lignes,
        total_achats_mad=sum(x["montant_mad"] for x in lignes),
        hausses=sum(1 for e in evolutions if e > PRIX_STABLE),
        fortes_hausses=sum(1 for e in evolutions if e > forte),
        baisses=sum(1 for e in evolutions if e < -PRIX_STABLE),
        seuils=_seuils(forte),
    )


@dataclass
class MatricePrix:
    """Les 36 derniers mois vus et le prix moyen de chaque (matière, devise)."""

    mois: list[str]
    lignes: list[dict[str, Any]]
    seuils: dict[str, float]


def matrice(s: Session, q: str = "") -> MatricePrix:
    """Route 214 : la matrice des prix, chaque cellule dans la devise de ses factures."""
    d = donnees_moteur.charger(s)
    mois, lignes = matrice_prix(d)
    mots = normaliser(q).split()
    ids = ids_matieres(s)
    rendues = [
        {**asdict(x), "matiere_id": ids.get(x.reference)}
        for x in lignes
        if _correspond(
            mots,
            x.reference,
            x.nature,
            x.designation,
            x.composition,
            x.type_fil,
            x.titrage,
            x.couleur,
            x.fournisseur,
            x.devise,
        )
    ]
    return MatricePrix(mois=mois, lignes=rendues, seuils=_seuils(d.parametres.seuil_hausse_forte))


@dataclass(frozen=True)
class Criteres:
    """Les critères de comparaison des opportunités (défauts : décision T6)."""

    meme_couleur: bool = True
    autre_fournisseur: bool = True
    prix_catalogue: bool = False
    fenetre_jours: int | None = None


@dataclass
class Opportunites:
    """Les pistes, l'avertissement, les seuils et les pistes écartées."""

    date_reference: date
    avertissement: str
    criteres: dict[str, bool]
    fenetre_jours: float
    seuils: dict[str, float]
    ecartees: dict[str, int]
    total_mad: float
    lignes: list[dict[str, Any]] = field(default_factory=list)


def avertissement(c: Criteres, fenetre: float) -> str:
    """Ce que la comparaison compare, et ce qu'elle ne dit pas."""
    return (
        "Comparaison entre fils de même composition, même type et même titrage"
        + (", de même couleur" if c.meme_couleur else "")
        + (", chez un autre fournisseur" if c.autre_fournisseur else "")
        + f", sur des prix payés à moins de {fenetre:.0f} jours l'un de l'autre"
        + (" — ou des prix de catalogue, non datés" if c.prix_catalogue else "")
        + ". Chaque prix est un coût rendu usine quand l'achat est passé par un dossier "
        "d'importation (droits, fret, transit compris, hors TVA), sinon le prix de la facture "
        "au cours de la commande. Ni la qualité réelle du fil ni la disponibilité ne se lisent "
        "ici : c'est une opportunité à négocier, pas une décision."
    )


def opportunites(s: Session, jour: date, c: Criteres) -> Opportunites:
    """Route 211 : où une matière comparable s'achète moins cher, à la même époque."""
    lecture = lire(s, jour)
    d = lecture.donnees
    fenetre = float(c.fenetre_jours or d.parametres.fenetre_prix_jours)
    resultats, ecartees = comparer_les_prix(
        d,
        lecture.lignes,
        meme_couleur=c.meme_couleur,
        autre_fournisseur=c.autre_fournisseur,
        prix_catalogue=c.prix_catalogue,
        fenetre_jours=fenetre,
        couts=couts_d_achat(s, lecture),
    )
    ids = ids_matieres(s)
    return Opportunites(
        date_reference=jour,
        avertissement=avertissement(c, fenetre),
        criteres={
            "meme_couleur": c.meme_couleur,
            "autre_fournisseur": c.autre_fournisseur,
            "prix_catalogue": c.prix_catalogue,
        },
        fenetre_jours=fenetre,
        seuils=_seuils(d.parametres.seuil_hausse_forte),
        ecartees=ecartees,
        total_mad=sum(o.economie_mad for o in resultats),
        lignes=[
            {
                **asdict(o),
                "matiere_id": ids.get(o.reference),
                "matiere_alternative_id": ids.get(o.reference_alternative),
            }
            for o in resultats
        ],
    )
