"""Le registre des 57 réglages : libellé, famille, défaut, bornes, unité, aide (REGLAGES § 3).

Une seule déclaration, lue par la lecture et l'écriture des réglages (`services/reglages`), par
l'écran (route 23, bornes contrôlées à la frappe) et par les essais. Elle déclare **exactement**
les clés de `modeles.CLES_REGLAGES` (CHECK `ck_parametre_cle_connue`), dans l'ordre de l'écran.

Reprise de `gestion_mp/parametres.py` corrigé (libellés, défauts, bornes à l'identique) ; l'aide
d'écran de Gestion MP est versée dans la déclaration (une seule source, ECRANS-PRO P8) ; trois
familles nouvelles : « Période close » (`date_cloture`, écrit par la route 26 seulement),
« Technique » (`courriel_destinataires`, `adresse_publique` : direction et administrateur).
`seuil_bc_urgent` reste lisible, sans effet, et ne se modifie plus (E-16).
"""

from __future__ import annotations

from dataclasses import dataclass

from gestion_mp_pro.modeles import CLES_REGLAGES


@dataclass(frozen=True)
class Reglage:
    """La déclaration d'un réglage ; bornes dans l'unité **rangée** (fraction pour un %)."""

    cle: str
    libelle: str
    famille: str
    defaut: float | str
    bas: float | None = None
    haut: float | None = None
    unite: str = ""
    echelle: float = 1
    aide: str = ""
    technique: bool = False
    modifiable: bool = True

    @property
    def texte(self) -> bool:
        """Un réglage texte (défaut textuel) ; sinon un nombre."""
        return isinstance(self.defaut, str)


COUVERTURE = "Couverture et statuts"
APPRO = "Approvisionnement"
CLASSES = "Classification ABC / XYZ"
ACHAT = "Politique d'achat"
RECEPTION = "Réceptions et fournisseurs"
INVENTAIRE = "Stock et inventaire"
PRIX = "Prix"
TRESO = "Trésorerie"
SOCIETE = "Société"
PERIODE = "Période close"
TECHNIQUE = "Technique"
J, P, MAD = "jours", "%", "MAD"


def _n(  # noqa: PLR0917 — une ligne de déclaration par réglage, comme Gestion MP
    cle: str,
    libelle: str,
    famille: str,
    defaut: float,
    bas: float,
    haut: float,
    unite: str = "",
    echelle: float = 1,
    aide: str = "",
    **options: bool,
) -> Reglage:
    """Un réglage numérique."""
    return Reglage(cle, libelle, famille, defaut, bas, haut, unite, echelle, aide, **options)


def _t(cle: str, libelle: str, famille: str, defaut: str = "", aide: str = "") -> Reglage:
    """Un réglage texte (≤ 500 caractères)."""
    technique = famille == TECHNIQUE
    return Reglage(cle, libelle, famille, defaut, aide=aide, technique=technique)


_COUVERTURE = (
    _n("seuil_critique", "Couverture critique", COUVERTURE, 60, 1, 3650, J,
       aide="Statut classeur seulement, pour comparaison : sous cette couverture, une matière y "
            "est « critique ». Le statut du Cockpit, du plan d'achat et du courriel compare le "
            "stock projeté au seuil d'alerte."),
    _n("seuil_alerte", "Couverture d'attention", COUVERTURE, 90, 1, 3650, J,
       aide="Statut classeur seulement, pour comparaison : sous cette couverture, une matière y "
            "est en ATTENTION."),
    _n("seuil_dormant", "Stock dormant", COUVERTURE, 180, 1, 3650, J,
       aide="Sans sortie ni entrée depuis ce nombre de jours, un stock détenu dort."),
)  # fmt: skip

_APPRO = (
    _n("delai_defaut", "Délai par défaut", APPRO, 60, 1, 730, J,
       aide="Délai pris pour une matière sans fournisseur (ou d'un fournisseur inconnu) ; un "
            "fournisseur a toujours son propre délai, saisi dans sa fiche."),
    _n("marge_jours", "Couverture de commande", APPRO, 30, 0, 730, J,
       aide="Ce qu'une commande couvre, à défaut du pas du fournisseur."),
    _n("marge_securite", "Marge de sécurité", APPRO, 0.2, 0, 5, P, 100,
       aide="Majore la couverture minimum que porte la fiche d'une matière (en mois) : à 20 %, "
            "une couverture minimum de 2 mois en demande 2,4. Elle entre dans le seuil d'alerte, "
            "qui est le plus grand du stock minimum, de cette couverture et de la sécurité de la "
            "classe. Sans couverture minimum dans la fiche, elle ne change rien."),
    _n("taux_perte", "Taux de perte matière", APPRO, 0.02, 0, 0.5, P, 100,
       aide="Ajouté aux besoins et au coût de la matière."),
    _n("securite_a", "Sécurité classe A", APPRO, 30, 0, 365, J,
       aide="Jours de consommation à venir gardés en sécurité pour une matière de classe A. Le "
            "seuil d'alerte est le plus grand de cette sécurité, du stock minimum et de la "
            "couverture minimum : elle ne s'y ajoute pas."),
    _n("securite_b", "Sécurité classe B", APPRO, 30, 0, 365, J,
       aide="Jours de sécurité pour une matière de classe B (le seuil d'alerte en prend le plus "
            "grand, comme pour A)."),
    _n("securite_c", "Sécurité classe C", APPRO, 30, 0, 365, J,
       aide="Jours de sécurité pour une matière de classe C (le seuil d'alerte en prend le plus "
            "grand, comme pour A)."),
    _n("fenetre_realisation_jours", "Prévision — fenêtre du réalisé", APPRO, 90, 0, 730, J,
       aide="Sorties réelles comparées au plan, par mois entiers clos (les jours ramenés en mois "
            "au plus près, un demi arrondi au-dessus : 75 j = 3 mois). 0 = plan seul."),
    _n("plafond_stock_min_mois", "Stock minimum — plafond", APPRO, 3, 0, 60, "mois",
       aide="Le stock minimum du catalogue ne vaut pas plus de N mois de la consommation à venir "
            "(celle de l'horizon de commande). 0 = pas de plafond : le stock minimum du catalogue "
            "vaut tel quel. Une matière non consommée n'en a aucun."),
    _n("croissance_annuelle", "Croissance annuelle du plan", APPRO, 0, -0.9, 10, P, 100,
       aide="Ajoutée au plan de production à partir du jour où la base a été saisie : à 5 %, une "
            "base saisie en janvier vaut 5 % de plus en janvier suivant. Un mois garde la même "
            "prévision, qu'on le regarde six mois avant ou le mois même."),
)  # fmt: skip

_CLASSES = (
    _n("seuil_abc_a", "Classe A — valeur cumulée", CLASSES, 0.8, 0, 1, P, 100,
       aide="Les matières qui font ensemble cette part de la valeur consommée sont en classe A."),
    _n("seuil_abc_b", "Classe B — valeur cumulée", CLASSES, 0.95, 0, 1, P, 100,
       aide="Jusqu'à cette part cumulée, classe B ; au-delà, classe C."),
    _n("seuil_xyz_x", "Classe X — CV maximum", CLASSES, 0.25, 0, 10,
       aide="Sous ce coefficient de variation (écart-type ÷ moyenne mensuelle), la demande est "
            "régulière : classe X."),
    _n("seuil_xyz_y", "Classe Y — CV maximum", CLASSES, 0.5, 0, 10,
       aide="Sous ce coefficient de variation, la demande est variable : classe Y. Au-delà, "
            "erratique : classe Z."),
)  # fmt: skip

_ACHAT = (
    _n("seuil_bc_urgent", "BC urgent", ACHAT, 300000, 0, 1e12, MAD, modifiable=False,
       aide="Sans effet, gardé pour mémoire : il ne servait qu'à la méthode du classeur. Au plan "
            "d'achat, un fournisseur est « urgent » quand une de ses matières est en rupture, "
            "critique ou urgente — pas pour le montant de sa commande."),
    _n("seuil_bc_groupe", "BC groupé", ACHAT, 100000, 0, 1e12, MAD,
       aide="Au plan d'achat, ce qu'il faut commander à un fournisseur sans urgence, à partir de "
            "ce montant, se passe en un bon groupé ; en deçà, c'est un bon standard."),
    _n("seuil_tier1", "Tier 1 (classe A)", ACHAT, 300000, 0, 1e12, MAD,
       aide="Une matière de classe A dont la commande atteint ce montant passe en Tier 1 (émettre "
            "cette semaine), comme toute rupture ou matière CRITIQUE."),
    _n("seuil_tier2", "Tier 2", ACHAT, 200000, 0, 1e12, MAD,
       aide="À partir de ce montant, Tier 2 (sous 7 jours). Une matière URGENTE y est de toute "
            "façon, quel que soit son montant."),
    _n("seuil_tier3", "Tier 3", ACHAT, 100000, 0, 1e12, MAD,
       aide="À partir de ce montant, Tier 3 (sous 15 jours) ; en deçà, Tier 4 (regrouper sous 30 "
            "jours) — sauf urgence."),
    _n("seuil_approbation", "Approbation des commandes au-delà de", ACHAT, 0, 0, 1e12, MAD,
       aide="Une commande plus chère attend l'approbation de la direction. 0 = jamais."),
)  # fmt: skip

_RECEPTION = (
    _n("toler_in_full", "Tolérance de livraison complète", RECEPTION, 0.02, 0, 0.2, P, 100,
       aide="Une ligne reçue à cette part près de la quantité commandée compte comme livrée en "
            "entier (elle n'attend plus rien). Au plus 20 % : au-delà, un bon à peine entamé "
            "passerait pour livré."),
    _n("toler_ecart_pesee", "Tolérance d'écart de pesée", RECEPTION, 0.02, 0, 1, P, 100,
       aide="Un écart entre la pesée et le bon de livraison au-delà de ce taux est signalé "
            "(contrôle C08). Sans bon de livraison, une pesée franchement sous le reste à livrer "
            "est une livraison partielle, pas un écart."),
    _n("toler_excedent", "Excédent de livraison toléré", RECEPTION, 0.1, 0, 10, P, 100,
       aide="Une ligne de bon reçoit au plus son reste à livrer plus cette part de la ligne ; "
            "au-delà, la réception est refusée (le surplus se reçoit hors commande)."),
    _n("toler_poids_bobine", "Tolérance du poids de bobine", RECEPTION, 0.05, 0, 1, P, 100,
       aide="Un poids de bobine reçu éloigné du catalogue de plus de ce taux est signalé "
            "(contrôle C30)."),
    _n("toler_retard_jours", "Retard toléré dans la ponctualité", RECEPTION, 0, 0, 60, J,
       aide="Une livraison en retard de N jours ou moins reste « à l'heure » ; et une commande "
            "n'est dite « en retard » (écran, contrôle C06, courriel du lundi) qu'au-delà de ces "
            "N jours."),
    _n("cible_otif", "Cible OTIF", RECEPTION, 0.95, 0, 1, P, 100,
       aide="Sous cette part de livraisons parfaites, un fournisseur est signalé « sous la "
            "cible »."),
    _n("score_strategique", "Score — Stratégique", RECEPTION, 85, 0, 100, "/100",
       aide="À partir de ce score, un fournisseur est classé « Stratégique » : fidéliser et "
            "négocier le volume."),
    _n("score_standard", "Score — Standard", RECEPTION, 65, 0, 100, "/100",
       aide="À partir de ce score (et sous « Stratégique »), un fournisseur est « Standard » : "
            "maintenir la relation."),
    _n("score_surveiller", "Score — ATTENTION", RECEPTION, 45, 0, 100, "/100",
       aide="À partir de ce score (et sous « Standard »), un fournisseur est classé « À "
            "surveiller » ; en deçà, « À challenger »."),
)  # fmt: skip

_INVENTAIRE = (
    _n("tolerance_inventaire", "Tolérance d'écart d'inventaire", INVENTAIRE, 0.02, 0, 1, P, 100,
       aide="Proposée à l'ouverture d'un inventaire : au-delà, un écart de comptage se justifie "
            "avant la validation."),
)  # fmt: skip

_PRIX = (
    _n("seuil_hausse_forte", "Forte hausse de prix à partir de", PRIX, 0.05, 0.005, 10, P, 100,
       aide="Une hausse de prix à partir de ce taux est colorée « forte hausse » dans la matrice "
            "et l'historique des prix ; sous 0,5 %, un prix est dit stable."),
    _n("fenetre_prix_jours", "Écart maximal entre deux prix comparés", PRIX, 90, 1, 3650, J,
       aide="Deux prix ne se comparent qu'à la même époque."),
    _n("taux_tva_import", "TVA à l'importation", PRIX, 0.2, 0, 1, P, 100,
       aide="Le taux appliqué à la valeur en douane (marchandise, fret, assurance) augmentée des "
            "droits et de la TPI, pour la TVA attendue d'un dossier (contrôle C29)."),
    _n("taux_tpi_import", "Taxe parafiscale à l'importation (TPI)", PRIX, 0.0025, 0, 0.1, P, 100,
       aide="Sur la valeur en douane ; elle entre dans la base de la TVA attendue."),
    _n("seuil_surcout_import", "Frais d'un dossier d'importation à vérifier au-delà de", PRIX,
       1.0, 0.05, 100, P, 100,
       aide="Des frais hors TVA plus lourds que cette part de la marchandise sont signalés sur le "
            "dossier et dans les contrôles (C35) : ils fausseraient le coût moyen du stock."),
    _n("toler_facture_import", "Facture d'un dossier à rapprocher au-delà de", PRIX, 0.02, 0, 1,
       P, 100,
       aide="Une facture qui s'éloigne de plus de cette part de la marchandise reçue (pesée × "
            "prix) est signalée sur le dossier et dans les contrôles (C36)."),
    _n("toler_tva_import", "TVA d'importation à vérifier au-delà de", PRIX, 0.05, 0, 1, P, 100,
       aide="Une TVA saisie qui s'éloigne de plus de cette part de la TVA attendue est signalée "
            "sur le dossier et dans les contrôles (C29). En deçà : le cours de la douane, une "
            "assurance non saisie."),
    _n("delai_frais_import_jours", "Dossier sans frais à signaler après", PRIX, 30, 1, 365, J,
       aide="Un dossier ouvert, arrivé depuis plus longtemps et sans aucun frais hors TVA "
            "(droits, fret, transit…), est signalé dans les contrôles (C28)."),
)  # fmt: skip

_TRESO = (
    _n("dso", "Délai client moyen (DSO)", TRESO, 60, 0, 3650, J,
       aide="Le délai moyen de paiement des clients : il entre dans le cycle de trésorerie du "
            "Cockpit (stock + clients − fournisseurs)."),
)  # fmt: skip

_SOCIETE = (
    _t("nom_entreprise", "Raison sociale", SOCIETE),
    _t("forme_juridique", "Forme juridique et capital", SOCIETE,
       aide="Sous la raison sociale, en tête des bons : « SOCIETE ANONYME AU CAPITAL DE "
            "20 000 000 MAD »."),
    _t("secteur", "Secteur", SOCIETE, "Fabrication de tapis mécaniques",
       aide="L'activité de l'usine (fiche de la société) ; l'en-tête des bons suit le papier à "
            "en-tête : raison sociale, forme et capital, siège, ville."),
    _t("adresse", "Siège social", SOCIETE,
       aide="En tête des bons (« SIEGE SOCIAL … ») et adresse de livraison."),
    _t("ville", "Ville", SOCIETE),
    _t("telephone", "Téléphone", SOCIETE),
    _t("banques", "Banques", SOCIETE,
       aide="En pied des bons, par exemple « ATTWAFA BANK : 90D012433 · B.M.C.I : 01063 000619 "
            "001 82 » (séparer les banques par « · »)."),
    _t("ice", "ICE", SOCIETE),
    _t("rc", "R.C", SOCIETE),
    _t("identifiant_fiscal", "N.I.F (identifiant fiscal)", SOCIETE),
    _t("cnss", "C.N.S.S", SOCIETE),
    _t("patente", "Patente", SOCIETE),
    Reglage("date_cloture", "Période close jusqu'au", PERIODE, "", modifiable=False,
            aide="Rien ne s'écrit plus à cette date ni avant. Se règle par la clôture de période "
                 "(Réglages › Période close), avec un motif."),
    _t("courriel_destinataires", "Courriel du lundi : à qui", TECHNIQUE,
       aide="Adresses séparées par des virgules. Vide : pas de courriel. Il part le lundi matin, "
            "dès que le serveur d'envoi est réglé (voir la notice)."),
    _t("adresse_publique", "Adresse du serveur pour les téléphones", TECHNIQUE,
       aide="Ce que contiennent les QR des étiquettes, par exemple http://mac-usine:8050 (nom "
            "Tailscale, qui marche en Wi-Fi comme en 4G/5G). Vide : l'adresse du serveur sur le "
            "réseau de l'usine."),
)  # fmt: skip

REGLAGES: tuple[Reglage, ...] = (
    *_COUVERTURE, *_APPRO, *_CLASSES, *_ACHAT, *_RECEPTION, *_INVENTAIRE, *_PRIX, *_TRESO,
    *_SOCIETE,
)  # fmt: skip
"""Les 57 réglages, dans l'ordre de l'écran."""

PAR_CLE: dict[str, Reglage] = {r.cle: r for r in REGLAGES}

if set(PAR_CLE) != set(CLES_REGLAGES) or len(PAR_CLE) != len(REGLAGES):
    raise RuntimeError("Le registre des réglages doit déclarer exactement CLES_REGLAGES.")

ORDRES_STRICTS: tuple[tuple[str, str, str], ...] = (
    ("seuil_critique", "seuil_alerte",
     "La couverture critique doit rester inférieure à la couverture d'ATTENTION : sinon plus "
     "aucune matière ne serait en ATTENTION."),
    ("seuil_abc_a", "seuil_abc_b",
     "La part cumulée de la classe A doit rester sous celle de la classe B."),
    ("seuil_tier3", "seuil_tier2",
     "Le montant du Tier 3 doit rester sous celui du Tier 2 : sinon plus aucune ligne ne serait "
     "en Tier 3."),
    ("seuil_xyz_x", "seuil_xyz_y",
     "Le CV maximum de la classe X doit rester sous celui de la classe Y."),
    ("score_surveiller", "score_standard",
     "Le score « ATTENTION » doit rester sous le score « standard »."),
    ("score_standard", "score_strategique",
     "Le score « standard » doit rester sous le score « stratégique »."),
)  # fmt: skip
"""(plus petit, plus grand, refus) : l'égalité est refusée (Gestion MP corrigé, K65)."""

ORDRES_LARGES: tuple[tuple[str, str, str], ...] = (
    ("seuil_tier2", "seuil_tier1",
     "Le montant du Tier 1 (classe A) ne peut pas être inférieur à celui du Tier 2."),
)  # fmt: skip
"""(plus petit, plus grand, refus) : l'égalité est permise."""
