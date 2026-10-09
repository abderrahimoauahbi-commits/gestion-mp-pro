"""Parité par l'API : les paires de routes des documents (lus dans la base, pas dans le moteur).

Commandes, réceptions, dossiers, factures, inventaires, ordres, mouvements, lots, soldes,
échéancier, pesées, matières, analyse du coût de revient, bilan du mois. Là où Gestion MP
rendait les lignes dans la liste et PRO sur la fiche (API-PRO : listes légères, fiches
complètes), la liste de Gestion MP est comparée aux fiches de PRO, une par document.
"""

from __future__ import annotations

import parite_api_formes as f
from parite_api import Liste, Route
from parite_api_routes import Appel, RouteMoteur

INSTANTS = (
    "cree_le",
    "validee_le",
    "valide_le",
    "approuvee_le",
    "confirme_le",
    "clos_le",
    "saisi_le",
    "modifie_le",
)
PERSONNES = (
    "cree_par",
    "valide_par",
    "validee_par",
    "approuvee_par",
    "confirme_par",
    "controle_par",
    "auteur",
    "modifie_par",
    "second_par",
)


def _formes(**autres: f.Forme) -> dict[str, f.Forme]:
    """Les formes communes (instants, personnes) et celles de la route."""
    formes: dict[str, f.Forme] = {c: f.instant for c in INSTANTS}
    formes |= {c: f.personne for c in PERSONNES}
    return formes | autres


LIGNE_COMMANDE = Liste(("id",), renommes={"article_id": "matiere_id"}, formes=_formes())
LIGNE_RECEPTION = Liste(
    ("id",),
    renommes={"article_id": "matiere_id"},
    formes=_formes(),
    deplaces={
        "devise": "devise de la ligne : PRO tient une devise par réception (I35), "
        "vérifiée contre l'en-tête par `parite_api_passe.verifier_devises`"
    },
)
LIGNE_DOSSIER = Liste(
    ("id",),
    renommes={
        "article_id": "matiere_id",
        "quantite": "quantite_kg",
        "valeur_unite": "valeur_kg",
        "revient_unite": "revient_kg",
        "detail": "frais_par_poste",
    },
    formes={"cours": f.nul, "commentaire": f.note_de_cloture},
    deplaces={"poids_kg": "poids en kg d'une marchandise : `quantite_kg` (le stock est en kg)"},
)
FAMILLE = Liste(("famille",), renommes={"valeur_unite": "valeur_kg", "revient_unite": "revient_kg"})
FRAIS = Liste(("id",), renommes={}, formes=_formes())
ECHEANCE = Liste(("objet", "id"), formes={"date": f.jour})


def _documents_1() -> list[Route]:
    """Partie 1 de `documents`."""

    return [
        Route(
            "commandes",
            "/api/commandes",
            "/api/commandes",
            fiche_pro="/api/commandes/{id}",
            liste=Liste(
                ("id",),
                formes=_formes(livraison=f.code, cours=f.nul),
                sous={
                    "lignes": LIGNE_COMMANDE,
                    "receptions": Liste(("id",), formes={"date": f.jour}),
                },
            ),
        ),
        Route(
            "receptions",
            "/api/receptions",
            "/api/receptions",
            fiche_pro="/api/receptions/{id}",
            liste=Liste(
                ("id",),
                renommes={"commandes_ids": "commandes", "en_dossier": "dossier"},
                formes=_formes(commandes=f.numeros, commandes_ids=f.ids, en_dossier=f.presence),
                deplaces={"devise_fournisseur": DEVISE_FOURNISSEUR},
                sous={"lignes": LIGNE_RECEPTION},
            ),
        ),
        Route("factures", "/api/factures", "/api/factures", liste=Liste(("id",), formes=_formes())),
        Route(
            "dossiers",
            "/api/dossiers",
            "/api/dossiers",
            fiche_gmp="/api/dossiers/{id}",
            fiche_pro="/api/dossiers/{id}",
            liste=Liste(
                ("id",),
                renommes={"charges": "frais", "nb_charges": "nb_frais"},
                formes=_formes(
                    receptions=f.numeros,
                    matieres_sans_code=f.references,
                    matieres_code_inactif=f.references,
                ),
                sous={
                    "lignes": LIGNE_DOSSIER,
                    "familles": FAMILLE,
                    "charges": FRAIS,
                    "echeancier": ECHEANCE_DOSSIER,
                },
            ),
        ),
    ]


def _documents_2() -> list[Route]:
    """Partie 2 de `documents`."""

    return [
        Route(
            "inventaires",
            "/api/inventaires",
            "/api/inventaires",
            fiche_gmp="/api/inventaires/{id}",
            fiche_pro="/api/inventaires/{id}",
            liste=Liste(
                ("id",),
                formes=_formes(),
                sous={
                    "lignes": Liste(
                        ("id",), renommes={"article_id": "matiere_id"}, formes=_formes()
                    )
                },
            ),
        ),
        Route(
            "ordres",
            "/api/bons",
            "/api/ordres",
            fiche_pro="/api/ordres/{id}",
            liste=Liste(
                ("id",),
                renommes={
                    "fabrications": "qualites",
                    "theorique": "prevu",
                    "par_fil": "par_matiere",
                    "retours_detail": "retours",
                },
                formes=_formes(retours=f.numeros),
                sous={
                    "lignes": Liste(("id",), renommes={"article_id": "matiere_id"}),
                    "fabrications": Liste(("qualite",)),
                    "par_fil": Liste(("reference",), renommes={"theorique": "prevu"}),
                    "retours_detail": Liste(("numero", "date")),
                },
            ),
        ),
    ]


def _documents_3() -> list[Route]:
    """Partie 3 de `documents`."""

    return [
        Route(
            "échéancier",
            "/api/echeancier",
            "/api/echeancier",
            liste=Liste(("objet", "id"), formes={"date": f.jour}),
            entete=Liste((), sous={"a_dater": ECHEANCE, "reglees": ECHEANCE, "ecartees": ECHEANCE}),
        ),
        Route(
            "matières",
            "/api/articles",
            "/api/matieres",
            liste=Liste(
                ("id",),
                renommes={"historique": "utilisee"},
                formes=_formes(titrage_unite=f.nul),
                deplaces=MATIERE_DEPLACES,
            ),
        ),
        Route(
            "pesées",
            "/api/receptions/pesees",
            "/api/receptions/pesees",
            page_pro=True,
            champ_pro="elements",
            liste=Liste(
                ("date_reception", "reference", "lot_fournisseur", "quantite_pesee"),
                cle_pro=("date", "reference", "lot", "quantite_pesee"),
                renommes={
                    "lot_fournisseur": "lot",
                    "date_reception": "date",
                    "statut_qualite": "qualite_libelle",
                },
                formes={
                    "statut_reception": f.code,
                    "statut_qualite": f.table({"Réserve": "Sous réserve"}),
                },
                deplaces=PESEE_DEPLACES,
                vue_pro=f.pesee_comme_gestion_mp,
            ),
        ),
    ]


def _documents_4() -> list[Route]:
    """Partie 4 de `documents`."""
    return [
        Route(
            "mouvements",
            "/api/mouvements",
            "/api/mouvements",
            page_gmp=True,
            page_pro=True,
            champ_pro="elements",
            liste=Liste(
                ("id",),
                renommes={"article_id": "matiere_id", "paire": "paire_id"},
                formes=_formes(cours=f.nul, document=f.table({"sortie": "ordre"})),
            ),
        ),
        Route(
            "soldes",
            "/api/soldes",
            "/api/lots",
            liste=Liste(
                ("lot_id",),
                renommes={"article_id": "matiere_id"},
                sous={"magasins": Liste(("magasin_id",), formes={"type": f.type_magasin})},
            ),
        ),
    ]


def documents() -> list[Route]:
    """Les routes des documents."""
    return _documents_1() + _documents_2() + _documents_3() + _documents_4()


def bilans(mois: list[str]) -> list[RouteMoteur]:
    """Le bilan de chaque mois : la fonction de Gestion MP (sa route rend du HTML) contre
    `GET /bilan?mois=` de PRO."""
    return [
        RouteMoteur(
            Route(
                f"bilan {m}",
                "",
                f"/api/bilan?mois={m}",
                entete=Liste((), sous={"ecarts_ordres": Liste(("numero",))}),
            ),
            Appel("gestion_mp.api.suivi", "bilan", {"annee": int(m[:4]), "mois": int(m[5:])}),
        )
        for m in mois
    ]


DEVISE_FOURNISSEUR = "devise du fournisseur : fiche du fournisseur (route 60, `devise`)"
ECHEANCE_DOSSIER = Liste(
    ("nature", "piece", "quoi"), renommes={"charge_id": "frais_id"}, formes={"date_piece": f.jour}
)
MATIERE_DEPLACES = {
    "modifie_par": "dernière modification d'une matière : historique de la fiche "
    "(route `historique/matiere/{id}`, journal en tables)",
    "modifie_le": "idem (historique de la fiche)",
    "historique_raison": "raison du refus de suppression : dite par le refus (REGLES) ; "
    "la liste dit `utilisee`",
    "version": "compteur de verrou propre à chaque base (T5) : non comparable",
}
PESEE_DEPLACES = {
    "nature": "libellé de la composition : fiche de la matière (route 66, `composition_libelle`)",
    "quantite_commandee": "quantité du bon : fiche de la réception (`lignes[].quantite_commandee`)",
}
