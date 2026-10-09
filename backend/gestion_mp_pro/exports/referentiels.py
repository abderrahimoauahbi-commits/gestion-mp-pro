"""Classeurs des référentiels : matières, fiches fournisseurs, modèle du tableur (69, 78, 81).

Conventions communes (`exports/classeur.py`, R-REF-96) : une feuille titrée, « {titre} — exporté
le JJ/MM/AAAA » en tête, les intitulés en gras, les nombres en vrais nombres avec leur format, la
ligne d'en-tête figée et filtrable, `=` gardé en texte. Ces classeurs sont lus par la direction
et les achats (prix compris) ; la route les refuse à l'alimentation. Le modèle du tableur est le
catalogue actuel, relu tel quel par `services/tableur_matieres` (colonnes de
`services/tableur_referentiels`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from gestion_mp_pro.exports import classeur as conventions
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services.fournisseurs import Usages, est_local
from gestion_mp_pro.services.matieres_lecture import Ligne
from gestion_mp_pro.services.tableur_referentiels import COLONNES, SE_COMMANDE, VERSION, VIDER

TYPE_XLSX = conventions.TYPE_XLSX
ENTIER, KG, PRIX = "#,##0", "#,##0.0", "#,##0.000"

Colonne = tuple[str, str | None]


def _lire(rang: int) -> Any:
    """La valeur de la colonne `rang` d'une rangée."""
    return lambda rangee: rangee[rang]


def classeur(
    titre: str, colonnes: Sequence[Colonne], lignes: Sequence[Sequence[Any]], *, entete: bool = True
) -> bytes:
    """Un classeur d'une feuille aux conventions communes (`exports/classeur.py`) : titre
    « … — exporté le JJ/MM/AAAA » (si `entete`), intitulés, lignes. Lu par D et A seulement."""
    feuille = conventions.Feuille(
        titre,
        [
            conventions.Colonne(nom, _lire(i), format_ or "")
            for i, (nom, format_) in enumerate(colonnes)
        ],
        lignes,
        [conventions.exporte_le(titre, horloge.aujourd_hui())] if entete else [],
    )
    return conventions.classeur([feuille], voit_prix=True)


def nom_de_fichier(nom: str) -> str:
    """« matieres-2026-10-08.xlsx »."""
    return conventions.nom_de_fichier(nom, horloge.aujourd_hui())


def matieres(lignes: Sequence[Ligne]) -> bytes:
    """Le catalogue : classification, achat, conditionnement, stock (route 81)."""
    colonnes: list[Colonne] = [
        ("Référence", None), ("Désignation", None), ("Rôle", None), ("Composition", None),
        ("Type de fil", None), ("Titrage", None), ("Couleur", None), ("Code couleur", None),
        ("Fournisseur", None), ("Prix", PRIX), ("Devise", None), ("Unité du prix", None),
        ("Prix / kg", PRIX), ("Densité (kg/ml)", "0.00000"), ("Unité d'achat", None),
        ("Contenance", KG), ("Unité d'achat déclarée ou déduite", None),
        ("Minimum de commande", KG), ("kg / bobine", PRIX), ("Bobines / palette", ENTIER),
        ("Stock minimum", KG), ("Couverture minimum (mois)", KG), ("Groupe", None),
        ("Priorité dans le groupe", KG), ("Code douanier", None), ("En stock", KG),
        ("Active", None),
    ]  # fmt: skip
    rangees = [
        [
            x.reference,
            x.designation,
            x.role,
            x.composition,
            x.type_fil,
            x.titrage,
            x.couleur,
            x.couleur_code,
            x.fournisseur or "",
            x.prix,
            x.devise,
            x.unite_prix,
            x.prix_kg,
            x.densite or None,
            x.conditionnement.unite,
            x.conditionnement.contenance,
            "déclarée" if x.conditionnement.declare else "déduite",
            x.minimum_commande,
            x.poids_bobine,
            x.bobines_palette,
            x.stock_min,
            x.couv_min_mois,
            x.groupe_equiv,
            x.priorite_equiv,
            x.code_douanier or "",
            x.stock,
            "oui" if x.actif else "non",
        ]  # fmt: skip
        for x in lignes
    ]
    return classeur("Matières", colonnes, rangees)


def fournisseurs(liste: Sequence[Any], usages: dict[int, Usages]) -> bytes:
    """Les fiches des fournisseurs : contact, délais, paiement, port, banque (route 69)."""
    colonnes: list[Colonne] = [
        ("Fournisseur", None), ("Code", None), ("Pays", None), ("Local", None),
        ("Contact", None), ("Téléphone", None), ("E-mail", None), ("Devise par défaut", None),
        ("Devises", None), ("Délai déclaré (j)", ENTIER), ("Délai mesuré (j)", "#,##0.0"),
        ("Couverture (j)", ENTIER), ("Mode de paiement", None), ("Paiement à (j)", ENTIER),
        ("Conditions", None), ("Incoterm", None), ("Port de chargement", None),
        ("Banque", None), ("Matières", ENTIER), ("Actif", None),
    ]  # fmt: skip
    rangees = []
    for f in liste:
        u = usages.get(f.id, Usages())
        rangees.append([
            f.nom, f.code, f.pays, "oui" if est_local(f.pays, f.devise) else "non", f.contact,
            f.telephone, f.email, f.devise,
            " · ".join(f"{d} {n}" for d, n in sorted(u.devises.items())), f.delai_jours,
            u.delai_mesure, f.couverture_commande_jours or None, f.mode_paiement,
            f.delai_paiement_jours, f.conditions_paiement, f.incoterm, f.port_chargement,
            f.banque, u.nombre("matieres"), "oui" if f.actif else "non",
        ])  # fmt: skip
    return classeur("Fournisseurs", colonnes, rangees)


def _se_commande(x: Ligne) -> str:
    """« Palette de 1 080 kg (déduit) », « kg » : information, jamais relue."""
    c = x.conditionnement
    if c.contenance == 1:
        return c.unite
    contenance = f"{c.contenance.normalize():f}".replace(".", ",")
    return f"{c.unite} de {contenance} kg" + ("" if c.declare else " (déduit)")


def modele_tableur(lignes: Sequence[Ligne]) -> bytes:
    """Le catalogue actuel en tableur, à corriger puis relire (route 78), feuille « Matières »."""
    colonnes: list[Colonne] = [(intitule, None) for intitule, _, _ in COLONNES]
    colonnes += [(VIDER, None), (VERSION, None), (SE_COMMANDE, None)]
    rangees = [
        [
            x.reference,
            x.designation,
            x.role,
            x.composition,
            x.type_fil,
            x.titrage,
            x.couleur,
            x.couleur_code,
            x.densite,
            x.fournisseur or "",
            x.prix,
            x.unite_prix,
            x.devise,
            x.unite_achat,
            x.contenance_achat,
            x.minimum_commande,
            x.poids_bobine,
            x.bobines_palette,
            x.stock_min,
            x.couv_min_mois,
            x.groupe_equiv,
            x.priorite_equiv,
            x.code_douanier or "",
            "oui" if x.actif else "non",
            "",
            x.version,
            _se_commande(x),
        ]  # fmt: skip
        for x in lignes
    ]
    return classeur("Matières", colonnes, rangees, entete=False)
