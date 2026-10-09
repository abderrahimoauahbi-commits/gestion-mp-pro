"""Les ordres de fabrication (lot D6) : ce qu'on tisse, et la matière qui part aux machines.

Brouillon (corrigeable, supprimable, sans numéro, sans effet sur le stock) → validé (numéro
`OF-AAAA-NNNN` dans l'ordre des dates, prévu et taux de perte figés, sorties écrites) → annulé
(contre-passé avec ses retours, une fois ; son numéro reste). Modules : `regles` (messages et
contrôles communs), `saisie` (remplir un brouillon), `proposition` (FIFO à la date), `prevu`
(nomenclature, prévu figé), `blocages` (ce qui empêcherait de valider), `gestes` (créer…
annuler), `brouillon` (« À valider »), `consommation` (sorti net, retours, lots sortis, route
143), `lecture` (fiche), `liste` (liste paginée 135, aperçu, accès borné, classeur).
"""

from __future__ import annotations

from gestion_mp_pro.services.ordres.brouillon import GENRE_BROUILLON
from gestion_mp_pro.services.ordres.consommation import (
    ConsommationLue,
    LotSorti,
    consommation_des_ordres,
    lots_sortis,
)
from gestion_mp_pro.services.ordres.gestes import (
    annuler,
    charger,
    creer,
    modifier,
    supprimer,
    valider,
)
from gestion_mp_pro.services.ordres.lecture import FiltresOrdres, OrdreLu, fiche
from gestion_mp_pro.services.ordres.liste import (
    ApercuOrdres,
    OptionOrdres,
    PageOrdres,
    apercu,
    lister,
    ouverts,
    toutes,
)
from gestion_mp_pro.services.ordres.proposition import Demande, Proposition, proposer
from gestion_mp_pro.services.ordres.saisie import SaisieLigne, SaisieOrdre, SaisieQualite

__all__ = [
    "GENRE_BROUILLON",
    "ApercuOrdres",
    "ConsommationLue",
    "Demande",
    "FiltresOrdres",
    "LotSorti",
    "OptionOrdres",
    "OrdreLu",
    "PageOrdres",
    "Proposition",
    "SaisieLigne",
    "SaisieOrdre",
    "SaisieQualite",
    "annuler",
    "apercu",
    "charger",
    "consommation_des_ordres",
    "creer",
    "fiche",
    "lister",
    "lots_sortis",
    "modifier",
    "ouverts",
    "proposer",
    "supprimer",
    "toutes",
    "valider",
]
