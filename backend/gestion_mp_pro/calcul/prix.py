"""Prix payés : prix constatés, achats datés, historique, pistes d'économies (CALCULS B § 2).

Portage de `moteur.prix_constates`, `CoutDate`, `achats_dates`, `LigneHistoriquePrix`,
`historique_prix`, et des calculs de route `couts_rendus` (pour sa partie pure) et
`matrice_prix` (`api/pilotage.py`). Les opportunités sont dans `opportunites.py`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from gestion_mp_pro.calcul.importations import LigneRevient
from gestion_mp_pro.calcul.modele import Donnees, LignePrix

CoutDate = tuple[date, float, str]
"""Un coût d'achat daté, en dirhams le kilo, et ce sur quoi il repose."""
COUT_RENDU = "coût rendu"
PRIX_FACTURE = "prix facture"
MOIS_DE_LA_MATRICE = 36
"""La matrice des prix montre les 36 derniers mois vus."""
PRIX_STABLE = 0.005
"""Sous cette variation, le prix de la matrice n'a pas bougé (`seuils.stable`)."""


def prix_constates(donnees: Donnees) -> dict[str, tuple[float, str, date | None]]:
    """Ce que chaque fil coûte, en MAD : le dernier prix payé, sinon le catalogue."""
    parametres = donnees.parametres
    prix: dict[str, tuple[float, str, date | None]] = {
        a.reference: (a.prix_kg * parametres.taux(a.devise), "catalogue", None)
        for a in donnees.articles
    }
    achats = sorted(
        (x for x in donnees.historique_prix if x.prix_achat > 0),
        key=lambda x: (x.date_bc or date.min, x.numero_bc),
    )
    for achat in achats:  # le dernier écrase les précédents
        if achat.reference in prix:
            prix[achat.reference] = (
                achat.prix_achat * parametres.taux(achat.devise),
                "payé",
                achat.date_bc,
            )
    return prix


def achats_dates(
    donnees: Donnees, couts: dict[str, list[CoutDate]] | None = None
) -> dict[str, list[tuple[date, float]]]:
    """Les prix payés de chaque fil, en MAD, dans l'ordre du temps (à date égale, l'ordre de
    saisie : E-05) ; avec `couts`, le coût rendu usine de chaque achat (M84)."""
    if couts is not None:
        return {
            reference: sorted(
                ((jour, prix) for jour, prix, _ in serie if prix > 0), key=lambda x: x[0]
            )
            for reference, serie in couts.items()
            if any(prix > 0 for _, prix, _ in serie)
        }
    parametres = donnees.parametres
    achats: dict[str, list[tuple[date, float]]] = defaultdict(list)
    for achat in donnees.historique_prix:
        if achat.prix_achat > 0 and achat.date_bc is not None:
            achats[achat.reference].append(
                (achat.date_bc, achat.prix_achat * parametres.taux(achat.devise))
            )
    for serie in achats.values():
        serie.sort(key=lambda x: x[0])
    return achats


@dataclass
class LigneAchatRecu:
    """Une ligne de réception validée et payée, telle que la lit le coût rendu."""

    ligne_id: int
    jour: date
    reference: str
    prix: float
    devise: str
    cours_commande: float | None = None
    devise_commande: str | None = None


def couts_rendus(
    donnees: Donnees, lignes: list[LigneAchatRecu], revient: dict[int, LigneRevient]
) -> dict[str, list[CoutDate]]:
    """Le coût rendu usine de chaque achat, MAD/kg (route `couts_rendus`, M84) : le coût hors
    TVA du dossier, sinon le prix au cours figé de la commande (même devise), sinon au cours
    du jour. `lignes` : réceptions validées, non refusées, pesées et payées, triées par
    (date, n° de ligne) ; `revient` : `importations.revient_par_reception`."""
    couts: dict[str, list[CoutDate]] = {}
    for ligne in lignes:
        dossier = revient.get(ligne.ligne_id)
        if dossier is not None and dossier.revient_unite > 0:
            cout, base = dossier.revient_unite, COUT_RENDU
        elif ligne.cours_commande and ligne.devise == ligne.devise_commande:
            cout, base = ligne.prix * ligne.cours_commande, PRIX_FACTURE
        else:
            cout, base = ligne.prix * donnees.parametres.taux(ligne.devise), PRIX_FACTURE
        couts.setdefault(ligne.reference, []).append((ligne.jour, cout, base))
    return couts


@dataclass
class LigneHistoriquePrix:
    """Un prix réellement payé, et ce qu'il devient face au précédent."""

    date_bc: date | None
    numero_bc: str
    reference: str
    nature: str
    designation: str
    fournisseur: str
    quantite: float
    prix_achat: float
    devise: str
    prix_mad: float
    montant_mad: float
    prix_precedent: float | None
    evolution: float | None
    origine: str


def historique_prix(donnees: Donnees) -> list[LigneHistoriquePrix]:
    """Chaque achat avec son prix précédent (même fournisseur, même devise), le plus récent
    d'abord (`Tbl_HistoriquePrix`)."""
    parametres = donnees.parametres
    lignes = sorted(
        donnees.historique_prix, key=lambda p: (p.date_bc or date.min, p.reference, p.numero_bc)
    )
    dernier: dict[tuple[str, str, str], float] = {}
    resultat = []
    for prix in lignes:
        article = donnees.article(prix.reference)
        cle = (prix.reference, prix.fournisseur, prix.devise)
        precedent = dernier.get(cle)
        taux = parametres.taux(prix.devise)
        resultat.append(
            LigneHistoriquePrix(
                date_bc=prix.date_bc,
                numero_bc=prix.numero_bc,
                reference=prix.reference,
                nature=article.nature if article else "",
                designation=article.designation if article else "",
                fournisseur=prix.fournisseur,
                quantite=prix.quantite,
                prix_achat=prix.prix_achat,
                devise=prix.devise,
                prix_mad=prix.prix_achat * taux,
                montant_mad=prix.quantite * prix.prix_achat * taux,
                prix_precedent=precedent,
                evolution=(prix.prix_achat - precedent) / precedent if precedent else None,
                origine="",
            )
        )
        dernier[cle] = prix.prix_achat
    resultat.reverse()
    return resultat


@dataclass
class LigneMatrice:
    """Le prix moyen pondéré d'une référence, mois par mois, dans la devise de ses factures."""

    reference: str
    nature: str
    designation: str
    titrage: float | str | None
    titrage_unite: str
    composition: str
    type_fil: str
    couleur: str
    fournisseur: str
    devise: str
    prix: list[float | None]


def _par_mois(
    historique: list[LignePrix],
) -> tuple[dict[tuple[str, str], dict[str, list[tuple[float, float]]]], list[str]]:
    par_reference: dict[tuple[str, str], dict[str, list[tuple[float, float]]]] = {}
    mois_vus: set[str] = set()
    for prix in historique:
        if prix.date_bc is None:
            continue
        mois = f"{prix.date_bc.year:04d}-{prix.date_bc.month:02d}"
        mois_vus.add(mois)
        par_reference.setdefault((prix.reference, prix.devise or "MAD"), {}).setdefault(
            mois, []
        ).append((prix.quantite, prix.prix_achat))
    return par_reference, sorted(mois_vus)[-MOIS_DE_LA_MATRICE:]


def _moyenne(achats: list[tuple[float, float]] | None) -> float | None:
    if not achats:
        return None
    quantite = sum(q for q, _ in achats)
    if quantite:
        return sum(q * p for q, p in achats) / quantite
    return sum(p for _, p in achats) / len(achats)


def matrice_prix(donnees: Donnees) -> tuple[list[str], list[LigneMatrice]]:
    """Les 36 derniers mois vus et, par (référence, devise), le prix moyen pondéré de chaque
    mois (non converti : une moyenne de dollars et d'euros ne serait aucun prix)."""
    par_reference, mois = _par_mois(donnees.historique_prix)
    lignes = []
    for (reference, devise), mesures in sorted(par_reference.items()):
        a = donnees.article(reference)
        lignes.append(
            LigneMatrice(
                reference=reference,
                nature=a.nature if a else "",
                designation=a.designation if a else "",
                titrage=a.titrage if a else None,
                titrage_unite=a.titrage_unite if a else "",
                composition=(a.composition or a.nature) if a else "",
                type_fil=a.type_fil if a else "",
                couleur=(a.couleur or a.designation) if a else "",
                fournisseur=a.fournisseur if a else "",
                devise=devise,
                prix=[_moyenne(mesures.get(m)) for m in mois],
            )
        )
    return mois, lignes
