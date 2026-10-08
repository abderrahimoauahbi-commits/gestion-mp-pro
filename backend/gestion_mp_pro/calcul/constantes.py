"""Les constantes du moteur (REGLAGES § 8 de l'héritage) : chacune nommée et documentée.

Aucune ne devient un réglage sans décision : la parité avec Gestion MP en dépend
(ARCHITECTURE § 7). Les valeurs sont celles de `gestion_mp/calcul/modele.py`, `moteur.py` et
`controles.py`, méthode « corrigée » (le mode « classeur » n'est pas repris, DECISIONS P17).
"""

from __future__ import annotations

# ── Calendrier du plan ────────────────────────────────────────────────────────
MOIS = 12
"""Le plan glissant compte douze mois, M0 = le mois de la date de référence."""
JOURS_PAR_MOIS = 30
"""Le classeur approxime le mois à 30 jours dans ses fenêtres de demande."""
JOURS_PAR_AN = 365
"""L'année des rotations (DIO, DPO)."""
CROISSANCE_MINIMUM = -0.9
"""La croissance du plan ne descend pas plus bas (borne du réglage)."""

# ── Seuils numériques ─────────────────────────────────────────────────────────
POUSSIERE = 1e-3
"""Sous le gramme, un stock est nul : ce sont des restes d'arrondi, pas de la matière."""
EPSILON = 1e-9
"""Le zéro des quantités et des valeurs flottantes (« plus que rien »)."""
CENTIME = 0.005
"""Sous le demi-centime, un montant est nul (frais non répartis, avoirs, parts figées)."""
SOUS_LE_MILLIEME = 1e-6
"""Le zéro des quantités comptées entières (une bobine)."""
EGALITE_RELATIVE = 1e-9
"""Deux kg/m² de recette sont égaux à ce rapport près (`besoins_passes`)."""

# ── Rôles de nomenclature ─────────────────────────────────────────────────────
ROLES = ("Poil", "Chaîne", "Trame", "Colle", "Cuir", "Franges", "Ruban", "Plastique")
"""Les huit rôles de nomenclature du classeur."""
ROLES_LINEAIRES = ("Cuir", "Franges", "Ruban")
"""Les rôles dont la qualité dit des ml/m² ; × densité (kg/ml) = kg/m²."""
TOLERANCE_RECETTE = 0.01
"""L'écart à 100 % toléré dans un rôle de la recette (en points) : enregistrement et C01."""

# ── Types de mouvement du moteur ──────────────────────────────────────────────
TYPES_MOUVEMENT: dict[str, tuple[str, int]] = {
    "STOCK_INITIAL": ("📥 Stock Initial", 1),
    "ENTREE_RECEPTION": ("📦 Entrée Réception", 1),
    "SORTIE_PROD": ("📤 Sortie Prod", -1),
    "RETOUR_PRODUCTION": ("🔄 Retour Production", 1),
    "RETOUR_FOURNISSEUR": ("↩️ Retour Fournisseur", -1),
    "AJUSTEMENT_INVENTAIRE": ("⚖️ Ajustement Inventaire", 1),
    "TRANSFERT_MAGASIN": ("🔀 Transfert Magasin", 0),
    "QUARANTAINE": ("🚫 Quarantaine", 0),
}
"""Code stable → (libellé du classeur, signe sur le stock). Signe inconnu : +1."""
ACHATS_JOURNAL = ("STOCK_INITIAL", "ENTREE_RECEPTION")
"""Les écritures qui achètent de la matière (elles fixent le coût d'un lot)."""

# ── Statuts d'une matière ─────────────────────────────────────────────────────
STATUTS = {
    "RUPTURE": "⚫ RUPTURE",
    "CRITIQUE": "🔴 CRITIQUE",
    "URGENT": "🟠 URGENT",
    "ATTENTION": "🟡 ATTENTION",
    "OK": "🟢 OK",
    "SANS_CONSO": "⚪ NON CONSOMMÉE",
}
"""Le statut d'une matière : les libellés sont les valeurs (comparées telles quelles)."""
STATUTS_EN_ALERTE = (
    STATUTS["RUPTURE"],
    STATUTS["CRITIQUE"],
    STATUTS["URGENT"],
    STATUTS["ATTENTION"],
)
"""Les statuts qui appellent une action d'achat (« NON CONSOMMÉE » n'en est pas un)."""
SEUIL_CRITIQUE = 0.5
"""Stock projeté ≤ la moitié du seuil : CRITIQUE."""
SEUIL_ATTENTION = 1.2
"""Stock projeté ≤ 1,2 × le seuil : ATTENTION."""
MONO_SOURCE = "🔴 MONO-SOURCE"
"""Le sourcing d'une matière dont le groupe n'a qu'un fournisseur."""
HORS_CATALOGUE = "❓ Hors catalogue"
"""Le sourcing d'une matière sans groupe d'équivalence."""

# ── Commandes ─────────────────────────────────────────────────────────────────
STATUTS_BC_CLOS = ("Soldée", "Annulée")
"""Un bon clos n'attend plus rien."""

# ── Stock ─────────────────────────────────────────────────────────────────────
REALISATION_MINI, REALISATION_MAXI = 0.5, 1.5
"""Le coefficient de réalisation (réel / plan) est borné : un trimestre atypique ne double
ni ne divise par deux ce qu'on commande."""
RECUL_DEBUT_JOURS = 7
"""Un mois ne juge le plan que si l'atelier sortait déjà du fil dans sa première semaine."""
SANS_LOT = "(sans lot)"
"""L'étiquette des mouvements qui ne nomment pas leur lot."""
QUARANTAINE = "Quarantaine"
"""Le type de magasin qui retient la marchandise sous réserve."""

# ── Classement ABC / XYZ et plan d'achat ──────────────────────────────────────
POIDS_CLASSE = {"A": 3, "B": 2}
"""Le montant pondéré du plan d'achat : × 3 en classe A, × 2 en B, × 1 sinon."""
TIER_1, TIER_2, TIER_3, TIER_4 = "🔥 TIER 1", "🟠 TIER 2", "🟡 TIER 3", "⚪ TIER 4"
"""Les quatre urgences d'émission d'un bon."""
ACTIONS_TIER = {
    TIER_1: "Émettre cette semaine",
    TIER_2: "Émettre sous 7j",
    TIER_3: "Émettre sous 15j",
    TIER_4: "Regrouper sous 30j",
}
"""Ce que dit chaque tier."""

# ── Fournisseurs ──────────────────────────────────────────────────────────────
POINTS_OTIF = 60
"""Le score fournisseur sur 100 : la livraison parfaite d'abord."""
POINTS_RETOURS = 20
"""20 points à 0 % de matière renvoyée."""
POINTS_DELAI = 20
"""20 points jusqu'à 15 jours de délai, un de moins par 5 jours au-delà."""
DELAI_SANS_PENALITE = 15
"""Le délai (jours) jusqu'auquel le score garde ses 20 points de délai."""
JOURS_PAR_POINT_DE_DELAI = 5
"""Un point de délai perdu par tranche de 5 jours au-delà de 15."""
RETOURS_SANS_POINT = 0.05
"""À cette part de matière renvoyée (et au-delà), plus aucun point de retours."""

# ── Importations ──────────────────────────────────────────────────────────────
POSTES_IMPORT: dict[str, tuple[str, bool]] = {
    "DD": ("Droits de douane", False),
    "TPI": ("Taxe parafiscale à l'importation", False),
    "TVA": ("TVA à l'importation", True),
    "PORT": ("Port Med", False),
    "FRET": ("Fret", False),
    "ASSUR": ("Assurance", False),
    "TRANSIT": ("Transitaire", False),
    "TIMBRE": ("Timbre", False),
    "INT_OC": ("Intérêts / ordre de change", False),
    "TMSA": ("TMSA", False),
    "AUTRE": ("Autre frais", False),
}
"""Postes de charge d'un dossier : code → (libellé, récupérable)."""
RECUPERABLES = frozenset(code for code, (_, recuperable) in POSTES_IMPORT.items() if recuperable)
"""Les postes que l'État rend : ils pèsent sur la trésorerie, pas sur le coût."""
POSTES_VALEUR_EN_DOUANE = ("FRET", "ASSUR")
"""Ce qui s'ajoute à la marchandise dans la valeur en douane (CAF)."""
TOLERANCE_TVA_IMPORT = 0.05
"""Au-delà de 5 % d'écart entre la TVA saisie et l'attendue : une saisie à vérifier."""
TOLERANCE_DROITS_IMPORT = 0.02
"""Droits saisis contre droits attendus : écart toléré (2 %)…"""
ECART_DROITS_MINIMUM = 50.0
"""… et d'au moins 50 MAD (décision I11)."""

# ── Contrôles ─────────────────────────────────────────────────────────────────
RAPPORT_PRIX_ELOIGNE = 3.0
"""C38 : au-delà de ce rapport entre catalogue et dernier prix payé, l'un des deux est faux."""
