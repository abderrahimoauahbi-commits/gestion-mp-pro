"""`Donnees` : l'instantané complet sur lequel le moteur travaille (CALCULS § 1.20).

Construit par `services/donnees_moteur.py` (lot S4) — jamais par le moteur, qui ne lit
aucune base. Les index (`article`, `fournisseur`, `qualite`) et la dernière date connue
(`a_la_date`) ne sont pas des champs d'entrée : `dataclasses.replace` les recalcule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from gestion_mp_pro.calcul.modele.flux import (
    Commande,
    DossierImport,
    LignePrix,
    Mouvement,
    OrdreFabrication,
    Reception,
)
from gestion_mp_pro.calcul.modele.referentiels import (
    Article,
    Fournisseur,
    LigneRecette,
    Magasin,
    Metier,
    Parametres,
    PlanQualite,
    Qualite,
    VersionPlan,
    VersionRecette,
)

CleSolde = tuple[str, str, str]
"""(référence, lot, magasin) : la clé d'un solde tenu."""


@dataclass
class Donnees:
    """Référentiels, plan, journal et documents, tels que le moteur les lit."""

    parametres: Parametres = field(default_factory=Parametres)
    fournisseurs: list[Fournisseur] = field(default_factory=list)
    articles: list[Article] = field(default_factory=list)
    qualites: list[Qualite] = field(default_factory=list)
    recettes: list[LigneRecette] = field(default_factory=list)
    plan: list[PlanQualite] = field(default_factory=list)
    mouvements: list[Mouvement] = field(default_factory=list)
    commandes: list[Commande] = field(default_factory=list)
    historique_prix: list[LignePrix] = field(default_factory=list)
    receptions: list[Reception] = field(default_factory=list)
    magasins: list[Magasin] = field(default_factory=list)
    metiers: list[Metier] = field(default_factory=list)
    dossiers_import: list[DossierImport] = field(default_factory=list)
    ordres: list[OrdreFabrication] = field(default_factory=list)
    # L'histoire du plan et des recettes, qualité par qualité, dans l'ordre : un mois passé
    # se juge sur ce qui était prévu à l'époque.
    versions_plan: dict[str, list[VersionPlan]] = field(default_factory=dict)
    versions_recette: dict[str, list[VersionRecette]] = field(default_factory=dict)
    # Les soldes tenus (référence, lot, magasin) → kg, que C12 confronte au journal ; None
    # quand on ne les connaît pas (une date passée).
    soldes: dict[CleSolde, float] | None = None
    # Le montage des métiers n'a pas d'historique : à une date passée, il ne compte pas.
    montage_connu: bool = True
    derniere_date: date | None = field(default=None, init=False, repr=False, compare=False)
    _articles: dict[str, Article] = field(init=False, repr=False, compare=False)
    _fournisseurs: dict[str, Fournisseur] = field(init=False, repr=False, compare=False)
    _qualites: dict[str, Qualite] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.reindexer()

    def reindexer(self) -> None:
        """Recalcule les index (après une modification des listes en place)."""
        self._articles = {a.reference: a for a in self.articles}
        self._fournisseurs = {f.nom: f for f in self.fournisseurs}
        self._qualites = {q.code: q for q in self.qualites}

    def article(self, reference: str) -> Article | None:
        """La matière de cette référence, ou None."""
        return self._articles.get(reference)

    def fournisseur(self, nom: str) -> Fournisseur | None:
        """Le fournisseur de ce nom, ou None."""
        return self._fournisseurs.get(nom)

    def qualite(self, code: str) -> Qualite | None:
        """La qualité de ce code, ou None."""
        return self._qualites.get(code)

    def devise_article(self, article: Article) -> str:
        """La devise du prix de la matière fait foi (et non celle du fournisseur)."""
        return article.devise or "MAD"

    def delai_fournisseur(self, nom: str) -> float:
        """Délai du fournisseur ; le délai par défaut ne sert qu'aux inconnus (un connu à 0
        reste à 0, l'`IFERROR` du classeur)."""
        fournisseur = self.fournisseur(nom)
        if fournisseur is None:
            return self.parametres.delai_defaut
        return fournisseur.delai_jours

    def couverture_commande(self, nom: str) -> float:
        """Pas de réappro du fournisseur, à défaut la marge de couverture générale."""
        fournisseur = self.fournisseur(nom)
        valeur = fournisseur.couverture_commande_jours if fournisseur else 0
        return valeur if valeur else self.parametres.marge_jours
