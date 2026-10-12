"""Un cas par CHECK : la valeur interdite qui le fait refuser (lot S1, MODELE-DONNEES § 3).

`CAS[nom] = (table, mutation)` : la ligne valide de `modele_monde.LIGNES[table]`, modifiée par
`mutation` (un dictionnaire, ou une fonction des identifiants du monde), doit être refusée par
le CHECK `nom`. Les CHECK génériques (`…_enum` : valeur hors liste ; `…_nombre` : NaN) ont leur
cas calculé par `cas_generique`.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from modele_monde import INSTANT, JOUR, Ids

Mutation = dict[str, Any] | Callable[[Ids], dict[str, Any]]
VEILLE = JOUR - timedelta(days=1)
N = Decimal(-1)


def _jalons() -> dict[str, tuple[str, Mutation]]:
    """Les six jalons d'un bon : jamais avant la date du bon."""
    jalons = ("proforma_le", "acompte_le", "embarquee_le", "au_port_le", "dedouanee_le")
    return {
        f"ck_commande_{j}_apres_commande": ("commande", {j: VEILLE})
        for j in (*jalons, "arrivee_usine_le")
    }


def _negatifs(table: str, colonnes: dict[str, str]) -> dict[str, tuple[str, Mutation]]:
    """`nom du CHECK → colonne` : une valeur négative suffit à le faire refuser."""
    return {f"ck_{table}_{nom}": (table, {col: N}) for nom, col in colonnes.items()}


CAS: dict[str, tuple[str, Mutation]] = {
    "ck_utilisateur_identifiant_minuscules": ("utilisateur", {"identifiant": "Essai"}),
    "ck_utilisateur_role_requis": ("utilisateur", {"role": None}),
    "ck_utilisateur_historique_inactif": ("utilisateur", {"historique": True}),
    "ck_tentative_echecs_positifs": ("tentative", {"echecs": -1}),
    "ck_parametre_cle_connue": ("parametre", {"cle": "cle_inconnue"}),
    "ck_compteur_annee_plausible": ("compteur", {"annee": 1999}),
    "ck_compteur_dernier_positif": ("compteur", {"dernier": -1}),
    "ck_notification_destinataire": (
        "notification",
        lambda i: {"utilisateur_id": i["utilisateur"]},
    ),
    "ck_courriel_essais_positifs": ("courriel", {"essais": -1}),
    "ck_courriel_envoi_date": ("courriel", {"statut": "envoye"}),
    "ck_tache_execution_duree_positive": ("tache_execution", {"duree_ms": -1}),
    "ck_sauvegarde_taille_positive": ("sauvegarde", {"taille": -1}),
    "ck_sauvegarde_tables_positives": ("sauvegarde", {"tables": -1}),
    "ck_devise_code_iso": ("devise", {"code": "usd"}),
    "ck_devise_cours_borne": ("devise", {"cours": Decimal(10001)}),
    "ck_devise_mad_unite": ("devise", {"code": "MAD", "cours": Decimal(2)}),
    "ck_devise_mad_actif": ("devise", {"code": "MAD", "cours": 1, "actif": False}),
    "ck_devise_cours_cours_positif": ("devise_cours", {"cours": 0}),
    "ck_composition_code_non_vide": ("composition", {"code": ""}),
    "ck_type_fil_code_non_vide": ("type_fil", {"code": ""}),
    "ck_titrage_code_non_vide": ("titrage", {"code": ""}),
    "ck_unite_titrage_code_un_mot": ("unite_titrage", {"code": "g km"}),
    "ck_unite_titrage_ordre_positif": ("unite_titrage", {"ordre": -1}),
    "ck_couleur_code_non_vide": ("couleur", {"code": ""}),
    "ck_role_nomenclature_lineaire_de_base": ("role_nomenclature", {"lineaire": True}),
    "ck_role_nomenclature_ordre_positif": ("role_nomenclature", {"ordre": -1}),
    "ck_fournisseur_pays_majuscules": ("fournisseur", {"pays": "Maroc"}),
    "ck_fournisseur_delai_positif": ("fournisseur", {"delai_jours": 0}),
    "ck_fournisseur_couverture_positive": ("fournisseur", {"couverture_commande_jours": -1}),
    "ck_fournisseur_delai_paiement_positif": ("fournisseur", {"delai_paiement_jours": -1}),
    "ck_code_douanier_taux_borne": ("code_douanier", {"taux_droits": Decimal("1.5")}),
    "ck_matiere_prix_au_metre": ("matiere", {"unite_prix": "ml"}),
    "ck_matiere_unite_achat_pas_ml": ("matiere", {"unite_achat": "ML"}),
    "ck_matiere_contenance_positive": ("matiere", {"contenance_achat": 0}),
    "ck_matiere_priorite_bornee": ("matiere", {"priorite_equiv": Decimal(101)}),
    **_negatifs(
        "matiere",
        {
            "densite_positive": "densite",
            "prix_positif": "prix",
            "minimum_positif": "minimum_commande",
            "poids_bobine_positif": "poids_bobine",
            "bobines_palette_positives": "bobines_palette",
            "stock_min_positif": "stock_min",
            "couv_min_positive": "couv_min_mois",
        },
    ),
    "ck_poste_frais_ordre_borne": ("poste_frais", {"ordre": 1000}),
    "ck_poste_frais_tva_recuperable": ("poste_frais", {"nature": "tva"}),
    "ck_motif_code_r_format": ("motif", {"code_r": "R7"}),
    "ck_motif_ordre_positif": ("motif", {"ordre": -1}),
    "ck_qualite_base_positive": ("qualite", {"base_mensuelle": N}),
    "ck_qualite_poids_poids_positif": ("qualite_poids", {"poids": N}),
    "ck_qualite_saison_mois_valide": ("qualite_saison", {"mois": 13}),
    "ck_qualite_saison_coefficient_borne": ("qualite_saison", {"coefficient": Decimal(21)}),
    "ck_recette_pourcentage_borne": ("recette", {"pourcentage": Decimal(101)}),
    "ck_recette_version_numero_positif": ("recette_version", {"numero": 0}),
    "ck_recette_version_motif_de_restauration": ("recette_version", {"origine": "restauration"}),
    "ck_recette_version_ligne_pourcentage_borne": ("recette_version_ligne", {"pourcentage": N}),
    "ck_recette_version_poids_poids_positif": ("recette_version_poids", {"poids": N}),
    "ck_plan_version_base_positive": ("plan_version", {"base_mensuelle": N}),
    "ck_plan_version_motif_de_restauration": ("plan_version", {"origine": "restauration"}),
    "ck_plan_version_saison_mois_valide": ("plan_version_saison", {"mois": 0}),
    "ck_plan_version_saison_coefficient_borne": ("plan_version_saison", {"coefficient": N}),
    "ck_metier_laize_positive": ("metier", {"laize": N}),
    "ck_metier_bobines_par_metre_positives": ("metier", {"bobines_par_metre": N}),
    "ck_metier_etages_bornes": ("metier", {"etages": 41}),
    "ck_metier_etage_etage_borne": ("metier_etage", {"etage": 0}),
    "ck_montage_metres_positifs": ("montage", {"metres": N}),
    "ck_montage_pourcentage_borne": ("montage", {"pourcentage": Decimal(101)}),
    "ck_montage_evenement_etage_borne": ("montage_evenement", {"etage": 41}),
    "ck_lot_numero_sans_blanc": ("lot", {"numero": "L 1"}),
    "ck_lot_poids_bobine_positif": ("lot", {"poids_bobine": N}),
    "ck_solde_positif": ("solde", {"quantite": Decimal("-0.001")}),
    "ck_mouvement_date_plausible": ("mouvement", {"date_effet": date(1999, 12, 31)}),
    "ck_mouvement_quantite_non_nulle": ("mouvement", {"quantite": 0}),
    "ck_mouvement_prix_positif": ("mouvement", {"prix": N}),
    "ck_mouvement_cours_positif": ("mouvement", {"devise": "USD", "cours": 0}),
    "ck_mouvement_cours_mad": ("mouvement", {"cours": Decimal(10)}),
    "ck_mouvement_document": ("mouvement", {"document": "operation"}),
    "ck_mouvement_ordre": ("mouvement", {"type": "SORTIE"}),
    "ck_mouvement_prix_entree": ("mouvement", {"type": "TRANSFERT", "prix": 1}),
    "ck_commande_numero_statut": ("commande", {"numero": "BC-2026-0001"}),
    "ck_commande_numero_parti": ("commande", {"statut": "envoyee"}),
    "ck_commande_livraison_apres": ("commande", {"date_livraison_prevue": VEILLE}),
    "ck_commande_cours_positif": ("commande", {"cours": 0}),
    "ck_commande_cours_mad": ("commande", {"devise": "MAD", "cours": 10}),
    "ck_commande_cours_fige": ("commande", {"cours": 10}),
    "ck_commande_montant_approuve_positif": ("commande", {"montant_approuve": 0}),
    "ck_commande_solde": ("commande", {"statut": "soldee"}),
    **_jalons(),
    "ck_commande_ligne_quantite_positive": ("commande_ligne", {"quantite": 0}),
    "ck_commande_ligne_unite_achat_pas_ml": ("commande_ligne", {"unite_achat": "ml"}),
    "ck_commande_ligne_contenance_positive": ("commande_ligne", {"contenance": 0}),
    "ck_commande_ligne_prix_positif": ("commande_ligne", {"prix": N}),
    "ck_commande_ligne_confirmation": ("commande_ligne", {"prix_confirme": True}),
    "ck_commande_version_montant_positif": ("commande_version", {"montant_reference": N}),
    "ck_commande_version_ligne_quantite_positive": ("commande_version_ligne", {"quantite": 0}),
    "ck_commande_version_ligne_contenance_positive": ("commande_version_ligne", {"contenance": 0}),
    "ck_commande_version_ligne_prix_positif": ("commande_version_ligne", {"prix": N}),
    "ck_commande_decision_motif_du_renvoi": (
        "commande_decision",
        {"decision": "renvoi", "motif": "ok"},
    ),
    "ck_facture_montant_positif": ("facture", {"montant": 0}),
    "ck_facture_echeance_apres": ("facture", {"date": JOUR, "echeance": VEILLE}),
    "ck_facture_reglement": ("facture", lambda i: {"payee_par_id": i["utilisateur"]}),
    "ck_reception_numero_statut": ("reception", {"statut": "brouillon"}),
    "ck_reception_validation_date": ("reception", {"validee_le": None}),
    "ck_reception_annulation_date": ("reception", {"annulee_le": INSTANT}),
    "ck_reception_ligne_lot_interne_accepte": (
        "reception_ligne",
        {"lot_interne": True, "qualite": "refuse"},
    ),
    "ck_reception_ligne_lot_range": ("reception_ligne", {"magasin_id": None}),
    "ck_reception_ligne_refus_sans_lot": ("reception_ligne", {"qualite": "refuse"}),
    **_negatifs(
        "reception_ligne",
        {
            "attendu_positif": "quantite_attendue",
            "bl_positif": "quantite_bl",
            "pese_positif": "quantite_pesee",
            "palettes_positives": "nb_palettes",
            "bobines_en_plus_positives": "bobines_en_plus",
            "bobines_positives": "nb_bobines",
            "prix_positif": "prix",
        },
    ),
    "ck_ordre_numero_statut": ("ordre", {"numero": "OF-2026-0001"}),
    "ck_ordre_validation_date": ("ordre", {"valide_le": INSTANT}),
    "ck_ordre_annulation_date": ("ordre", {"annule_le": INSTANT}),
    "ck_ordre_prevu_fige": ("ordre", {"prevu_fige": True}),
    "ck_ordre_taux_perte_borne": ("ordre", {"taux_perte_fige": Decimal(2)}),
    "ck_ordre_qualite_m2_positifs": ("ordre_qualite", {"m2": 0}),
    "ck_ordre_ligne_quantite_positive": ("ordre_ligne", {"quantite": 0}),
    "ck_ordre_prevu_kg_positifs": ("ordre_prevu", {"kg_hors_perte": N}),
    "ck_operation_numero_statut": ("operation", {"numero": "AJU-2026-0001"}),
    "ck_operation_validation_date": ("operation", {"validee_le": INSTANT}),
    "ck_operation_annulation_date": ("operation", {"annulee_le": INSTANT}),
    "ck_operation_ordre": ("operation", {"type": "retour_machine"}),
    "ck_operation_fournisseur": ("operation", {"type": "retour_fournisseur"}),
    "ck_operation_ajustement_justifie": (
        "operation",
        {"statut": "validee", "commentaire": " abc "},
    ),
    "ck_operation_ligne_destination_distincte": (
        "operation_ligne",
        lambda i: {"magasin_destination_id": i["courant"]},
    ),
    "ck_operation_ligne_quantite_non_nulle": ("operation_ligne", {"quantite": 0}),
    "ck_operation_ligne_prix_positif": ("operation_ligne", {"prix": N}),
    "ck_operation_ligne_prix_en_devise": ("operation_ligne", {"prix": 1}),
    "ck_inventaire_tolerance_bornee": ("inventaire", {"tolerance": Decimal(2)}),
    "ck_inventaire_validation_date": ("inventaire", {"statut": "valide"}),
    "ck_inventaire_abandon_date": ("inventaire", {"abandonne_le": INSTANT}),
    "ck_inventaire_annulation_date": ("inventaire", {"annule_le": INSTANT}),
    "ck_inventaire_critere_classe_abc_valide": ("inventaire_critere", {"classe_abc": "D"}),
    "ck_inventaire_critere_un_critere": ("inventaire_critere", lambda i: {"role_id": i["poil"]}),
    **_negatifs(
        "inventaire_ligne",
        {
            "theorique_positif": "theorique",
            "compte_positif": "compte",
            "palettes_positives": "nb_palettes",
            "bobines_positives": "nb_bobines",
            "second_compte_positif": "second_compte",
        },
    ),
    "ck_inventaire_ligne_second_apres_premier": ("inventaire_ligne", {"second_compte": 1}),
    "ck_inventaire_ligne_lot_designe": ("inventaire_ligne", {"lot_id": None}),
    "ck_inventaire_ligne_lot_a_creer_trouve": (
        "inventaire_ligne",
        {"lot_id": None, "lot_numero": "L9"},
    ),
    "ck_inventaire_ligne_lot_trouve_sans_theorique": (
        "inventaire_ligne",
        {"lot_trouve": True, "theorique": 1},
    ),
    "ck_dossier_numero_format": ("dossier", {"numero": "DOS-1"}),
    "ck_dossier_annee_et_rang": ("dossier", {"rang": None}),
    "ck_dossier_numero_automatique": ("dossier", {"annee": None, "rang": None}),
    "ck_dossier_annee_plausible": ("dossier", {"annee": 1999}),
    "ck_dossier_rang_borne": ("dossier", {"rang": 0}),
    "ck_dossier_cloture_date": ("dossier", {"clos_le": INSTANT}),
    "ck_dossier_annulation_date": ("dossier", {"annule_le": INSTANT}),
    "ck_dossier_ligne_quantite_positive": ("dossier_ligne", {"quantite_kg": N}),
    "ck_dossier_ligne_valeur_positive": ("dossier_ligne", {"valeur_devise": N}),
    "ck_dossier_ligne_cours_positif": ("dossier_ligne", {"cours": 0}),
    "ck_dossier_ligne_cours_mad": ("dossier_ligne", {"devise": "MAD"}),
    "ck_dossier_ligne_cours_origine": ("dossier_ligne", {"cours_origine": None}),
    "ck_dossier_frais_montant_non_nul": ("dossier_frais", {"montant": 0}),
    "ck_dossier_frais_taux_borne": ("dossier_frais", {"taux": 0}),
    "ck_dossier_frais_reglement": ("dossier_frais", lambda i: {"payee_par_id": i["utilisateur"]}),
    "ck_reclamation_ligne_de_reception": ("reclamation", {"reception_id": None}),
    "ck_reclamation_quantite_positive": ("reclamation", {"quantite": N}),
    "ck_reclamation_montant_demande_positif": ("reclamation", {"montant_demande": N}),
    "ck_reclamation_montant_obtenu_positif": ("reclamation", {"montant_obtenu": N}),
    "ck_reclamation_close": ("reclamation", {"statut": "close"}),
    "ck_signalement_texte_utile": ("signalement", {"texte": " a "}),
    "ck_signalement_traitement": ("signalement", {"traite_le": INSTANT}),
    "ck_piece_jointe_un_objet": ("piece_jointe", {"objet": "dossier"}),
    "ck_piece_jointe_taille_bornee": ("piece_jointe", {"taille": 20 * 1024 * 1024 + 1}),
    "ck_piece_jointe_retrait": ("piece_jointe", {"retiree_le": INSTANT}),
    "ck_indicateur_jour_ruptures_positives": ("indicateur_jour", {"ruptures": -1}),
    "ck_indicateur_jour_critiques_positifs": ("indicateur_jour", {"critiques": -1}),
    "ck_indicateur_jour_urgents_positifs": ("indicateur_jour", {"urgents": -1}),
    "ck_reprise_execution_fin": ("reprise_execution", {"fin": INSTANT}),
}


def cas_generique(nom: str, table: str) -> tuple[str, Mutation] | None:
    """Le cas d'un CHECK générique : `ck_<table>_<colonne>_enum` ou `…_nombre`."""
    prefixe = f"ck_{table}_"
    if not nom.startswith(prefixe):
        return None
    reste = nom.removeprefix(prefixe)
    if reste.endswith("_enum"):
        return table, {reste.removesuffix("_enum"): "zz"}
    if reste.endswith("_nombre"):
        return table, {reste.removesuffix("_nombre"): Decimal("NaN")}
    return None
