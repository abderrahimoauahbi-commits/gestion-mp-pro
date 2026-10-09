"""Les classeurs de l'analyse (routes 216–220) : contrôles, valorisation, prix, opportunités,
fournisseurs. Conventions communes (`exports/classeur.py`, lot D9) : vraies dates, gravités et
classements en clair (E-12), écart en fraction au format % — **une** échelle, comme l'écran
(P8-3) —, mêmes filtres que l'écran, la date de référence dans le titre et le nom du fichier.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from gestion_mp_pro.calcul.controles import Colonne as ColonneControle
from gestion_mp_pro.calcul.controles import Controle, Synthese
from gestion_mp_pro.documents.format import kg, montant_precis
from gestion_mp_pro.exports.classeur import GRAVITES, Colonne, Feuille, classeur, filtres, titre
from gestion_mp_pro.services.pilotage import Valorisation
from gestion_mp_pro.services.pilotage_fournisseurs import PerformanceFournisseurs
from gestion_mp_pro.services.pilotage_prix import HistoriquePrix, MatricePrix, Opportunites

FORMAT_DE_L_UNITE = {
    "kg": "kg",
    "MAD": "montant",
    "%": "pourcent",
    "j": "entier",
    "date": "date",
    "nombre": "#,##0.##",
    "m": "#,##0.00",
}
"""Le format Excel d'une colonne du détail d'un contrôle, selon son unité."""


def _c(titre_: str, cle: str, format_: str = "", *, monetaire: bool = False) -> Colonne:
    """Une colonne qui lit une clé (dict) ou un attribut (objet)."""

    def lire(x: Any) -> object:
        return x.get(cle) if isinstance(x, dict) else getattr(x, cle)

    return Colonne(titre_, lire, format_, monetaire=monetaire)


# ── Contrôles (216) ───────────────────────────────────────────────────────────────────


def _etat(c: Controle) -> str:
    if c.garanti:
        return f"garanti : {c.garanti}"
    return "OK" if c.conforme else "À revoir"


def _detail(c: Controle) -> Feuille:
    """Une feuille par contrôle en anomalie : toutes ses lignes, colonnes libellées."""

    def colonne(x: ColonneControle) -> Colonne:
        return _c(x.libelle, x.cle, FORMAT_DE_L_UNITE.get(x.unite, ""), monetaire=x.unite == "MAD")

    return Feuille(
        f"{c.code} {c.libelle}"[:31],
        [colonne(x) for x in c.colonnes],
        c.detail,
        [f"{c.code} — {c.libelle}", f"Quoi faire : {c.quoi_faire}"],
    )


def controles(note: Synthese, liste: list[Controle], jour: date) -> bytes:
    """Route 216 : « Contrôles » (synthèse en tête) et une feuille par contrôle en anomalie."""
    synthese = (
        f"Score : {note.conformes} conformes sur {note.total} vérifiés · {note.garantis} "
        f"garantis · {note.anomalies} en anomalie dont {note.bloquants} bloquant(s)"
    )
    colonnes = [
        _c("Code", "code"),
        _c("Ce qui est vérifié", "libelle"),
        Colonne("Gravité", lambda c: GRAVITES.get(c.gravite, c.gravite)),
        _c("Anomalies", "anomalies", "entier"),
        Colonne("État", _etat),
        _c("Quoi faire", "quoi_faire"),
    ]
    resume = Feuille(
        "Contrôles", colonnes, liste, [titre("Contrôles de cohérence", jour), synthese]
    )
    return classeur([resume, *(_detail(c) for c in liste if not c.conforme)], voit_prix=True)


# ── Valorisation (217) ────────────────────────────────────────────────────────────────


def valorisation(v: Valorisation) -> bytes:
    """Route 217 : la valorisation, matière par matière (celles qui ont du stock)."""
    colonnes = [
        _c("Référence", "reference"),
        _c("Nature", "nature"),
        _c("Fournisseur", "fournisseur"),
        _c("Magasins (kg)", "stock_magasin", "kg"),
        _c("Sur les métiers (kg)", "stock_machine", "kg"),
        _c("Stock détenu (kg)", "stock", "kg"),
        _c("Coût moyen (MAD / kg)", "cmup_mad", "prix", monetaire=True),
        _c("Prix catalogue", "prix_catalogue", "prix", monetaire=True),
        _c("Devise", "devise"),
        _c("Valeur (MAD)", "valeur_mad", "montant", monetaire=True),
        _c("Écart au catalogue (MAD)", "ecart_mad", "montant", monetaire=True),
    ]
    lignes = [x for x in v.lignes if x.stock or x.stock_machine]
    total = (
        f"Total : {kg(v.total_kg)}, {montant_precis(v.total_mad, 'MAD')} (dont sur les métiers "
        f"{montant_precis(v.total_machine_mad, 'MAD')})"
    )
    entete = [titre("Valorisation du stock", v.date_reference), total]
    return classeur([Feuille("Valorisation", colonnes, lignes, entete)], voit_prix=True)


# ── Prix (218) ────────────────────────────────────────────────────────────────────────


def prix(h: HistoriquePrix, m: MatricePrix, jour: date, q: str) -> bytes:
    """Route 218 : l'historique des achats (vraies dates) et la matrice des prix (une ligne par
    matière et devise, une colonne par mois)."""
    historique = [
        _c("Date", "date_bc", "date"),
        _c("Bon", "numero_bc"),
        _c("Référence", "reference"),
        _c("Nature", "nature"),
        _c("Désignation", "designation"),
        _c("Fournisseur", "fournisseur"),
        _c("Quantité (kg)", "quantite", "kg"),
        _c("Prix payé", "prix_achat", "prix", monetaire=True),
        _c("Devise", "devise"),
        _c("Prix précédent", "prix_precedent", "prix", monetaire=True),
        _c("Évolution", "evolution", "pourcent"),
        _c("Montant (MAD)", "montant_mad", "montant", monetaire=True),
    ]
    matrice = [
        _c("Référence", "reference"),
        _c("Nature", "nature"),
        _c("Désignation", "designation"),
        _c("Composition", "composition"),
        _c("Titrage", "titrage"),
        _c("Fournisseur", "fournisseur"),
        _c("Devise", "devise"),
    ]
    for i, mois in enumerate(m.mois):
        matrice.append(Colonne(mois, lambda x, i=i: x["prix"][i], "prix", monetaire=True))
    entete = [titre("Prix payés", jour), filtres([("mots", q)])]
    return classeur(
        [
            Feuille("Historique des achats", historique, h.lignes, entete),
            Feuille("Matrice des prix", matrice, m.lignes, [titre("Matrice des prix", jour)]),
        ],
        voit_prix=True,
    )


# ── Opportunités (219) ────────────────────────────────────────────────────────────────


def opportunites(o: Opportunites) -> bytes:
    """Route 219 : les pistes avec ces critères, et l'avertissement."""
    colonnes = [
        _c("Référence", "reference"),
        _c("Fournisseur actuel", "fournisseur_actuel"),
        _c("Composition", "composition"),
        _c("Titrage", "titrage"),
        _c("Couleur", "couleur"),
        _c("Prix actuel (MAD / kg)", "prix_actuel_mad", "prix", monetaire=True),
        _c("Base du prix", "base_prix"),
        _c("Date du prix", "date_prix", "date"),
        _c("Comparable", "reference_alternative"),
        _c("Chez", "fournisseur_alternatif"),
        _c("Son prix (MAD / kg)", "prix_minimum_mad", "prix", monetaire=True),
        _c("Date de son prix", "date_prix_minimum", "date"),
        _c("Écart", "ecart", "pourcent"),
        _c("Écart (j)", "ecart_jours", "entier"),
        _c("Conso / an (kg)", "conso_annuelle", "kg"),
        _c("Économie / an (MAD)", "economie_mad", "montant", monetaire=True),
    ]
    criteres = filtres(
        [
            ("même couleur", "oui" if o.criteres["meme_couleur"] else "non"),
            ("autre fournisseur", "oui" if o.criteres["autre_fournisseur"] else "non"),
            ("prix de catalogue", "oui" if o.criteres["prix_catalogue"] else "non"),
            ("fenêtre", f"{o.fenetre_jours:.0f} j"),
        ]
    )
    entete = [titre("Opportunités d'économies", o.date_reference), criteres, o.avertissement]
    return classeur([Feuille("Opportunités", colonnes, o.lignes, entete)], voit_prix=True)


# ── Fournisseurs (220) ────────────────────────────────────────────────────────────────


def fournisseurs(p: PerformanceFournisseurs, jour: date) -> bytes:
    """Route 220 : le classement (sans émoji) et les réceptions notées."""
    classement = [
        _c("Fournisseur", "fournisseur"),
        _c("Pays", "pays"),
        _c("Devise", "devise"),
        _c("Délai (j)", "delai_jours", "entier"),
        _c("Commandes", "nb_commandes", "entier"),
        _c("Acheté (MAD)", "montant_mad", "montant", monetaire=True),
        _c("Réceptions", "receptions", "entier"),
        _c("À l'heure", "on_time", "pourcent"),
        _c("Complètes", "in_full", "pourcent"),
        _c("Conformes", "in_spec", "pourcent"),
        _c("OTIF", "otif", "pourcent"),
        _c("Retours", "taux_retours", "pourcent"),
        _c("Écart de pesée", "ecart_pesee_moyen", "pourcent"),
        _c("Score", "score", "#,##0.0"),
        _c("Classement", "classement"),
        _c("Action", "action"),
    ]
    receptions = [
        _c("Réception", "numero"),
        _c("Fournisseur", "fournisseur"),
        _c("Date", "date_reception", "date"),
        _c("À l'heure", "on_time", "entier"),
        _c("Complète", "in_full", "entier"),
        _c("Conforme", "in_spec", "entier"),
        _c("Parfaite (OTIF)", "otif", "entier"),
        _c("Lignes hors tolérance", "lignes_hors_tolerance", "entier"),
        _c("Écart de pesée", "ecart_pesee", "pourcent"),
    ]
    entete = [titre("Classement des fournisseurs", jour), filtres([("du", p.du), ("au", p.au)])]
    return classeur(
        [
            Feuille("Fournisseurs", classement, p.lignes, entete),
            Feuille("Réceptions notées", receptions, p.receptions, entete),
        ],
        voit_prix=True,
    )
