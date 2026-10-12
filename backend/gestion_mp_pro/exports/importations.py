"""Les classeurs des importations (routes 205 et 208 ; `gestion_mp/api/importations.py` et
`analyse_import.py`), aux conventions communes (`exports/classeur.py`) : les dossiers en quatre
feuilles (Dossiers, Marchandises, Frais, Échéancier), et le coût de revient (par axe avec son
total, puis lot par lot). Mêmes filtres que l'écran ; statuts en clair, vraies dates (B-09).
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from gestion_mp_pro.calcul.analyse_revient import AnalyseRevient
from gestion_mp_pro.exports.classeur import Colonne, Feuille, classeur, exporte_le, filtres
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services.analyse_revient import FiltresAnalyse
from gestion_mp_pro.services.importations.lecture import DossierDetaille, FiltresDossiers

STATUTS = {"ouvert": "Ouvert", "clos": "Clos", "annule": "Annulé"}
TITRES = {"ouvert": "ouverts", "clos": "clos", "annule": "annulés"}


def _m(titre: str, lire: Any, format_: str = "montant") -> Colonne:
    """Une colonne monétaire."""
    return Colonne(titre, lire, format_, monetaire=True)


def _par_kg(revient: float, poids: float) -> float | None:
    """Le coût au kilo (rien sans poids)."""
    return revient / poids if poids else None


COLONNES_DOSSIERS = (
    Colonne("Dossier", lambda d: d.numero),
    Colonne("Libellé", lambda d: d.libelle),
    Colonne("Arrivée", lambda d: d.date_arrivee, "date"),
    Colonne("Statut", lambda d: STATUTS.get(d.statut, d.statut)),
    Colonne("Clos le", lambda d: d.clos_le, "horodatage"),
    Colonne("Factures", lambda d: " · ".join(f.numero for f in d.factures)),
    Colonne("Réceptions", lambda d: " · ".join(x.numero for x in d.receptions)),
    Colonne("Poids (kg)", lambda d: d.poids, "kg"),
    _m("Achat MAD", lambda d: d.marchandise_mad),
    _m("Charges hors TVA", lambda d: d.charges_mad),
    _m("Charges / achat", lambda d: d.surcout, "pourcent"),
    _m("Coût hors TVA", lambda d: d.revient_mad),
    _m("Coût hors TVA / kg", lambda d: d.revient_kg, "prix"),
    _m("TVA", lambda d: d.tva_mad),
    _m("Coût TTC", lambda d: d.decaisse_mad),
    _m("Frais non répartis", lambda d: d.charges_non_reparties_mad + d.tva_non_repartie_mad),
    _m("Droits de douane saisis", lambda d: d.droits_mad),
    _m("Droits de douane attendus", lambda d: d.droits_attendus_mad),
    Colonne("Banque", lambda d: d.banque),
    Colonne("Annulé le", lambda d: d.annule_le, "horodatage"),
    Colonne("Motif d'annulation", lambda d: d.annulation_motif),
    Colonne("Observations", lambda d: d.commentaire),
)

COLONNES_MARCHANDISES = (
    Colonne("Dossier", lambda x: x[0].numero),
    Colonne("Référence", lambda x: x[1].reference),
    Colonne("Lot", lambda x: x[1].lot),
    Colonne("Fournisseur", lambda x: x[1].fournisseur),
    Colonne("Facture", lambda x: x[1].facture or ""),
    Colonne("Réception", lambda x: x[1].reception or ""),
    Colonne("Quantité (kg)", lambda x: x[1].quantite_kg, "kg"),
    _m("Valeur facture", lambda x: x[1].valeur_devise),
    Colonne("Devise", lambda x: x[1].devise),
    _m("Cours", lambda x: x[1].cours_applique, "cours"),
    _m("Achat MAD", lambda x: x[1].valeur_mad),
    _m("Charges hors TVA", lambda x: x[1].charges_mad),
    _m("Coût hors TVA", lambda x: x[1].revient_mad),
    _m("Coût hors TVA / kg", lambda x: x[1].revient_kg, "prix"),
    _m("TVA", lambda x: x[1].tva_mad),
    Colonne("Code douanier", lambda x: x[1].code_douanier or ""),
    _m("Droits de douane attendus", lambda x: x[1].droits_attendus_mad),
    Colonne("Observations", lambda x: x[1].commentaire),
)


def _porte_sur(x: tuple[Any, Any, dict[int, str]]) -> str:
    """La marchandise visée, sinon la répartition (« figée (clé d'avant son changement) »)."""
    _, frais, references = x
    if frais.ligne_id:
        return references.get(frais.ligne_id, "?")
    return str(frais.repartition)


def _taux(x: tuple[Any, Any, dict[int, str]]) -> Decimal | None:
    """Le taux saisi avec le frais, en fraction pour le format « % » d'Excel (vide sans taux)."""
    taux = x[1].taux
    return None if taux is None else taux / 100


COLONNES_FRAIS = (
    Colonne("Dossier", lambda x: x[0].numero),
    Colonne("Poste", lambda x: x[1].libelle),
    _m("Taux", _taux, "0.00##%"),
    _m("Montant MAD", lambda x: x[1].montant),
    Colonne("Récupérable", lambda x: x[1].recuperable),
    Colonne("Répartition", _porte_sur),
    Colonne("Prestataire", lambda x: x[1].prestataire),
    Colonne("Pièce", lambda x: x[1].piece),
    Colonne("Date de la pièce", lambda x: x[1].date_piece, "date"),
    Colonne("Échéance", lambda x: x[1].echeance, "date"),
    Colonne("Réglé le", lambda x: x[1].payee_le, "date"),
    Colonne("Observations", lambda x: x[1].commentaire),
)

COLONNES_ECHEANCIER = (
    Colonne("Échéance", lambda x: x[1].echeance, "date"),
    Colonne("Dossier", lambda x: x[0].numero),
    Colonne("Quoi", lambda x: x[1].quoi),
    Colonne("Tiers", lambda x: x[1].tiers),
    Colonne("Pièce", lambda x: x[1].piece),
    _m("Montant", lambda x: x[1].montant),
    Colonne("Devise", lambda x: x[1].devise),
    Colonne("Estimé", lambda x: x[1].estime),
    Colonne("Réglé le", lambda x: x[1].payee_le, "date"),
)


def dossiers(detail: list[DossierDetaille], f: FiltresDossiers) -> bytes:
    """Route 205 : feuilles Dossiers, Marchandises, Frais, Échéancier."""
    nom = "Dossiers d'importation" + (f" — {TITRES[f.statut]}" if f.statut in TITRES else "")
    entete = [
        exporte_le(nom, horloge.aujourd_hui()),
        filtres([("recherche", f.q), ("fournisseur", f.fournisseur)]),
    ]
    resumes = [x.resume for x in detail]
    lignes = [(x.resume, y) for x in detail for y in x.lignes]
    frais = [(x.resume, y, {z.id: z.reference for z in x.lignes}) for x in detail for y in x.frais]
    echeances = [(x.resume, y) for x in detail for y in x.echeancier]
    return classeur(
        [
            Feuille("Dossiers", COLONNES_DOSSIERS, resumes, entete),
            Feuille("Marchandises", COLONNES_MARCHANDISES, lignes, entete),
            Feuille("Frais", COLONNES_FRAIS, frais, entete),
            Feuille("Échéancier", COLONNES_ECHEANCIER, echeances, entete),
        ],
        voit_prix=True,
    )


def _colonnes_groupe(libelle_axe: str) -> tuple[Colonne, ...]:
    """Les colonnes de la feuille « Par {axe} »."""
    return (
        Colonne(libelle_axe, lambda g: g.valeur),
        Colonne("Lots", lambda g: g.lignes, "entier"),
        Colonne("Poids (kg)", lambda g: g.poids, "kg"),
        _m("Achat MAD", lambda g: g.marchandise_mad),
        _m("Charges hors TVA", lambda g: g.charges_mad),
        _m("Charges / achat", lambda g: g.surcout, "pourcent"),
        _m("Coût hors TVA", lambda g: g.revient_mad),
        _m("Coût hors TVA / kg", lambda g: g.revient_kg, "prix"),
        _m("TVA", lambda g: g.tva_mad),
        _m("Coût TTC", lambda g: g.decaisse_mad),
        Colonne("Dossiers", lambda g: " · ".join(g.dossiers)),
    )


COLONNES_LOTS = (
    Colonne("Dossier", lambda x: x.dossier),
    Colonne("Arrivée", lambda x: x.date_arrivee, "date"),
    Colonne("Statut", lambda x: x.statut),
    Colonne("Référence", lambda x: x.reference),
    Colonne("Lot", lambda x: x.lot_fournisseur),
    Colonne("Fournisseur", lambda x: x.fournisseur),
    Colonne("Titrage", lambda x: x.titrage),
    Colonne("Poids (kg)", lambda x: x.poids, "kg"),
    _m("Achat MAD", lambda x: x.marchandise_mad),
    _m("Charges hors TVA", lambda x: x.charges_mad),
    _m("Coût hors TVA", lambda x: x.revient_mad),
    _m("Coût hors TVA / kg", lambda x: x.revient_kg, "prix"),
    _m("TVA", lambda x: x.tva_mad),
    _m("Coût TTC", lambda x: x.decaisse_mad),
)


def revient(r: AnalyseRevient, f: FiltresAnalyse) -> bytes:
    """Route 208 : la feuille « Par {axe} » (et son total), puis « Lot par lot »."""
    total = SimpleNamespace(
        valeur="Total",
        lignes=r.total_lignes,
        poids=r.total_poids,
        marchandise_mad=r.total_marchandise_mad,
        charges_mad=r.total_charges_mad,
        surcout=r.total_charges_mad / r.total_marchandise_mad if r.total_marchandise_mad else None,
        revient_mad=r.total_revient_mad,
        revient_kg=_par_kg(r.total_revient_mad, r.total_poids),
        tva_mad=r.total_tva_mad,
        decaisse_mad=r.total_decaisse_mad,
        dossiers=[],
    )
    entete = [
        exporte_le("Coût de revient des matières importées", horloge.aujourd_hui()),
        filtres(
            [("recherche", f.q), ("statut", f.statut), ("du", f.du), ("au", f.au),
             ("composition", f.composition), ("titrage", f.titrage), ("type", f.type_fil),
             ("couleur", f.couleur), ("fournisseur", f.fournisseur)]
        ),
    ]  # fmt: skip
    return classeur(
        [
            Feuille(
                f"Par {r.libelle_axe.lower()}",
                _colonnes_groupe(r.libelle_axe),
                [*r.lignes, total],
                entete,
            ),
            Feuille("Lot par lot", COLONNES_LOTS, r.detail_lignes, entete),
        ],
        voit_prix=True,
    )
