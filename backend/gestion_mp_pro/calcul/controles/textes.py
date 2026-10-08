"""Les textes des contrôles : ce qu'il faut faire, pourquoi un contrôle ne peut pas sonner, et
le libellé français de chaque colonne du détail.

Portage de `QUOI_FAIRE`, `GARANTIS`, `GARANTIS_SAISIE` et `COLONNES` de
`gestion_mp/calcul/controles.py`. Les textes sont ceux de Gestion MP ; seuls les noms d'écran
suivent les titres PRO (« Qualités et recettes ») et « la personne qui entretient le serveur »
devient « l'administrateur technique ». Le lien de correction n'est plus ici : chaque contrôle
déclare le sien (`@controle(..., lien=...)`, ECRANS-PRO « Ouvrir l'écran »).
"""

from __future__ import annotations

HORS_SAISIE = (
    "Gestion MP refuse déjà cette saisie : la ligne vient d'une reprise de données ou d'une "
    "écriture faite hors de l'écran. Prévenir l'administrateur technique, puis annuler le "
    "document fautif (contre-passation) et le ressaisir."
)
"""Le « quoi faire » commun aux contrôles qui ne peuvent pas venir de la saisie
(C02, C04, C14, C16, C26, C31, C32)."""

QUOI_FAIRE: dict[str, str] = {
    "C01": "La direction ouvre la qualité (Qualités et recettes › Recette) et corrige les "
    "pourcentages du rôle signalé jusqu'à 100 % (les achats, qui la lisent seulement, le lui "
    "signalent) : tant que ce n'est pas fait, le besoin en fil de cette qualité est faux, "
    "et le plan d'achat avec lui.",
    "C02": HORS_SAISIE,
    "C03": "Ouvrir le retour et vérifier son motif : un retour des machines porte R1, R2 ou R4, "
    "un retour au fournisseur R3, R5 ou R6. S'il manque, annuler le retour "
    "(contre-passation) et le ressaisir avec son motif.",
    "C04": HORS_SAISIE,
    "C05": "Ouvrir la matière (Matières, classification, fournisseurs) et lui donner son "
    "fournisseur — ou la désactiver si elle ne s'achète plus. Sans fournisseur, le plan "
    "d'achat ne sait pas à qui la commander.",
    "C06": "Relancer le fournisseur et noter la nouvelle date d'arrivée (ETA) dans le suivi "
    "d'expédition de la commande. S'il ne livrera pas le reste, solder la commande : elle "
    "ne comptera plus dans le stock projeté.",
    "C07": "Si la matière ne sert plus, la désactiver dans sa fiche ; si elle doit servir, "
    "l'ajouter à la recette d'une qualité. Pour information seulement.",
    "C08": "Comparer la pesée au bon de livraison avec le fournisseur. Écart confirmé : le "
    "réclamer (avoir ou complément). Pesée fausse : corriger le stock par un ajustement "
    "motivé.",
    "C09": "Corriger le prix d'achat dans la fiche matière.",
    "C10": "Corriger le délai (en jours, au moins 1) dans la fiche fournisseur.",
    "C11": "Saisir le cours de la devise dans Réglages › Devises (ouvert à la direction et aux "
    "achats) : sans lui, ses prix se lisent comme des dirhams.",
    "C12": "Bloquant : le stock tenu ne retombe plus sur le journal des mouvements. Ne plus rien "
    "saisir sur ces matières et prévenir l'administrateur technique : une écriture a "
    "contourné le chemin normal.",
    "C13": "Commander tout de suite (Plan d'achat), ou faire avancer une livraison déjà "
    "commandée : la matière manquera avant que la commande n'arrive.",
    "C14": HORS_SAISIE,
    "C15": "Saisir le prix d'achat dans la fiche matière : sans lui, le coût au m² de la qualité "
    "et le budget d'achat sont sous-évalués. Une matière désactivée encore dans la "
    "recette : la remplacer dans la recette (la direction), ou la remettre en service — "
    "le plan d'achat ne la proposera plus.",
    "C16": HORS_SAISIE,
    "C17": "Chercher un second fournisseur pour cette matière, ou un fil équivalent (et lui "
    "donner son groupe d'équivalence) : elle est en alerte et ne dépend que d'un seul.",
    "C18": "Voir si la matière peut servir une autre qualité, se rendre au fournisseur ou se "
    "vendre ; sinon, la déclasser. Pour information seulement.",
    "C19": "Normal si le fournisseur facture vraiment en deux monnaies : un bon de commande part "
    "par devise. Sinon, corriger la devise de la matière dans sa fiche.",
    "C20": "Faire compter la matière (Inventaire) et corriger le stock par un ajustement motivé.",
    "C21": "Choisir la devise du prix dans la fiche matière.",
    "C22": "Ouvrir le métier (Métiers à tisser) et ramener les mètres montés à cet étage à la "
    "laize du métier.",
    "C23": "Saisir le poids d'une bobine (kg / bobine) dans la fiche matière : sans lui, le fil "
    "monté pèse zéro et manque au stock.",
    "C24": "Retirer le fil de cet étage, ou augmenter le nombre d'étages du métier.",
    "C25": "Enregistrer la sortie vers les machines de ce fil (Sorties vers les machines) : sans "
    "elle, le magasin le compte encore en stock alors qu'il est monté — et le stock le "
    "compte deux fois. Si la sortie existe, vérifier les mètres montés.",
    "C26": HORS_SAISIE,
    "C27": "Bloquant : ouvrir le lot (son numéro mène à Stock › Lots, lots épuisés compris) et "
    "cliquer « Suivre » pour trouver la sortie de trop ; l'annuler (contre-passation), ou "
    "enregistrer l'entrée oubliée.",
    "C28": "Saisir les frais du dossier (droits, fret, transit…) dans Importations : sans eux, le "
    "coût de revient n'est que le prix de la facture.",
    "C29": "Comparer la TVA saisie dans les frais du dossier à la quittance de la douane ; "
    "corriger le frais, ou la valeur en douane des marchandises.",
    "C30": "Vérifier le poids de bobine avec le fournisseur ; si le nouveau poids est le bon, le "
    "reporter dans la fiche matière (kg / bobine).",
    "C31": HORS_SAISIE,
    "C32": HORS_SAISIE,
    "C33": "Baisser le stock minimum dans la fiche matière : il immobilise plus de mois de "
    "consommation que le plafond réglé (le plan d'achat le plafonne déjà).",
    "C34": "Rattacher les marchandises au dossier (Importations › À rattacher), ou retirer les "
    "frais saisis par erreur.",
    "C35": "Reprendre les frais du dossier sur leurs pièces (quittance, facture du transitaire) : "
    "un zéro de trop, ou les frais d'un autre dossier. Tant qu'ils restent, ils entrent "
    "dans le coût moyen du stock.",
    "C36": "Rapprocher la facture du bon de livraison et de la pesée : un manque de poids se "
    "réclame au fournisseur (avoir), une facture mal saisie se corrige sur sa réception, "
    "un camion pas encore rattaché rejoint le dossier. Le coût, lui, reste à la pesée × "
    "le prix. Une facture sans montant se complète ; une marchandise dans une autre "
    "devise que sa facture se vérifie (elle ne peut pas se rapprocher).",
    "C37": "Bloquant : une écriture est datée avant l'entrée de son lot, ou a pris plus que ce "
    "que le lot portait ce jour-là — elle est partie à coût nul. Ouvrir le journal du lot, "
    "annuler l'écriture fautive (contre-passation) et la ressaisir à une date où la "
    "matière était là, ou sur un autre lot.",
    "C38": "Comparer le prix de la fiche matière au dernier achat (tous deux lus au kilo — un "
    "prix au mètre l'est par la densité ; unité du prix, densité, devise) et le corriger "
    "s'il est faux — ou confirmer le dernier prix payé avec le "
    "fournisseur. C'est au responsable du référentiel de trancher : le contrôle ne corrige "
    "rien.",
}
"""Ce qu'il faut faire quand un contrôle sonne : un contrôle qui ne le dit pas laisse
l'utilisateur devant une liste."""

# ── Pourquoi un contrôle ne peut pas sonner (`garanti=`) ─────────────────────
# La base les rend impossibles (contrainte, clé étrangère) : rejoués quand même (une reprise
# ou une contrainte retirée les ferait sonner), mais leur zéro ne prouve rien (décision T11).
GARANTI_C09 = "La base refuse un prix négatif (contrainte article_prix_check)."
"""C09 : contrainte sur le prix."""
GARANTI_C10 = "La base refuse un délai fournisseur nul ou négatif (fournisseur_delai_jours_check)."
"""C10 : contrainte sur le délai."""
GARANTI_C11 = "La base refuse un cours de change nul ou négatif (devise_taux_check)."
"""C11 : contrainte sur le cours."""
GARANTI_C16 = (
    "Les mouvements pointent leur matière et leur fournisseur (par le lot) par des clés "
    "étrangères : un mouvement orphelin ne peut pas s'écrire."
)
"""C16 : clés étrangères du journal."""
GARANTI_C21 = (
    "La devise d'un prix est une clé étrangère vers les devises : un prix sans devise "
    "connue ne peut pas s'écrire."
)
"""C21 : clé étrangère de la devise."""

# La saisie les rend impossibles : chaque écriture passe par un chemin qui refuse la ligne.
GARANTI_C02 = (
    "Un ordre de fabrication reçoit son numéro en même temps qu'il écrit ses sorties : une "
    "sortie vers les machines porte toujours le sien (garanti par la saisie)."
)
"""C02 : l'ordre numéroté avec ses sorties."""
GARANTI_C04 = (
    "Chaque écriture de stock porte le nom du compte connecté qui la valide (garanti par "
    "la saisie)."
)
"""C04 : l'auteur de chaque écriture."""
GARANTI_C14 = (
    "Une écriture datée après aujourd'hui est refusée (« Date dans le futur ») ; une "
    "annulation prend la date de l'écriture qu'elle défait (garanti par la saisie)."
)
"""C14 : pas de date future."""
GARANTI_C24 = (
    "Un fil ne se monte qu'à un étage du métier, et le métier ne perd pas un étage garni "
    "(garanti par la saisie)."
)
"""C24 : l'étage existe."""
GARANTI_C26 = (
    "Une sortie se fait toujours d'un lot, et un lot a toujours un numéro (garanti par la saisie)."
)
"""C26 : la sortie nomme son lot."""
GARANTI_C31 = (
    "Un ordre de fabrication porte une seule date et un numéro qui n'est qu'à lui "
    "(garanti par la saisie)."
)
"""C31 : une date par ordre."""
GARANTI_C32 = (
    "Un ordre ne se valide pas à une date antérieure au dernier ordre validé : les "
    "numéros suivent les dates (garanti par la saisie)."
)
"""C32 : les numéros suivent les dates."""

COLONNES: dict[str, str] = {
    "apres": "Après",
    "arrivee": "Arrivée",
    "attendu": "Attendu",
    "catalogue": "Catalogue (kg / bobine)",
    "conso_mensuelle": "Conso / mois",
    "constate": "Constaté (kg / bobine)",
    "date": "Date",
    "date_apres": "Date de l'ordre suivant",
    "date_bc": "Date de la commande",
    "dates": "Dates",
    "delai": "Délai (j)",
    "devise_par_defaut": "Devise par défaut",
    "devise": "Devise",
    "devises": "Devises",
    "dossier": "Dossier",
    "ecart": "Écart (%)",
    "ecart_mad": "Écart (MAD)",
    "entrees": "Entré",
    "etage": "Étage",
    "etages": "Étages du métier",
    # C22 compte les matières montées à l'étage (ECRANS-PRO : « Fils » → « Matières »).
    "fils": "Matières",
    "fournisseur": "Fournisseur",
    "frais": "Frais hors TVA (MAD)",
    "tva": "TVA (MAD)",
    "jours_commande": "Jours depuis la commande",
    "jours_arrivee": "Jours depuis l'arrivée",
    "nb_dates": "Nombre de dates",
    "jours_sans_mouvement": "Jours sans mouvement",
    "laize": "Laize (m)",
    "lot": "Lot",
    "magasin": "Magasin",
    "manque": "Manque",
    "marchandises": "Marchandises",
    "motif": "Motif",
    "metier": "Métier",
    "metres": "Mètres",
    "metres_montes": "Mètres montés",
    "mois": "Mois",
    "montant_a_commander_mad": "À commander (MAD)",
    "numero": "N°",
    "numero_of": "Ordre (n° OF)",
    "pesee": "Pesé",
    "poids": "Poids (kg)",
    "prix": "Prix",
    "qualite": "Qualité",
    "prix_catalogue": "Prix du catalogue",
    "prix_paye": "Dernier prix payé",
    "rapport": "Catalogue / payé",
    "quantite": "Quantité",
    "reception": "Réception",
    "reference": "Référence",
    "retard_jours": "Retard (j)",
    "retenu": "Retenu",
    "roles": "Rôles",
    "echeance": "Livraison attendue",
    "monte": "Monté (kg)",
    "somme_magasins": "Somme des magasins",
    "sorties": "Sorti",
    "stock": "Stock",
    "stock_min_catalogue": "Stock minimum",
    "stock_net": "Stock net",
    "stock_projete": "Stock projeté",
    "taux": "Cours",
    "marchandise_mad": "Marchandise (MAD)",
    "frais_mad": "Frais hors TVA (MAD)",
    # C35 : la fraction frais / marchandise (échelle unique P8-3), plus « surcout_pct » × 100.
    "surcout": "Frais / marchandise (%)",
    "facture": "Facture",
    "facture_montant": "Facture (devise)",
    "recu": "Reçu, pesée × prix (devise)",
    "tva_attendue": "TVA attendue (MAD)",
    "tva_saisie": "TVA saisie (MAD)",
    "type": "Type",
    "utilisateur": "Par",
    "valeur": "Valeur (MAD)",
}
"""Les colonnes du détail, en français : la clé technique ne s'affiche jamais. Une quantité
de matière est toujours en kilos, cuir, franges et ruban compris."""
