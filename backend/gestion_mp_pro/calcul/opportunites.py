"""Pistes d'économies : où un fil comparable s'achète moins cher (CALCULS B § 2.6-2.7).

Portage de `moteur.Opportunite`, `comparer_les_prix`, `opportunites` (méthode corrigée) :
même composition, type, titrage (et unité) — même couleur sur demande —, chez un autre
fournisseur par défaut, à des prix de la même époque (`fenetre_prix_jours`) ; un prix de
catalogue n'entre que sur demande ; ce qui est écarté est compté.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from gestion_mp_pro.calcul.constantes import MOIS
from gestion_mp_pro.calcul.modele import Article, Donnees
from gestion_mp_pro.calcul.prix import COUT_RENDU, PRIX_FACTURE, CoutDate, achats_dates
from gestion_mp_pro.calcul.stock import LigneStock

Offre = tuple[float, str, date | None, str]
"""(prix, origine, date, motif d'écart éventuel)."""


@dataclass
class Opportunite:
    """Une piste : le prix actuel, le meilleur prix comparable, l'économie annuelle."""

    reference: str
    nature: str
    titrage: float | str | None
    fournisseur_actuel: str
    prix_actuel_mad: float
    prix_minimum_mad: float
    fournisseur_alternatif: str
    conso_annuelle: float
    economie_mad: float
    composition: str = ""
    type_fil: str = ""
    couleur: str = ""
    reference_alternative: str = ""
    couleur_alternative: str = ""
    origine_prix: str = "catalogue"
    origine_prix_minimum: str = "catalogue"
    ecart: float = 0.0
    date_prix: date | None = None
    date_prix_minimum: date | None = None
    ecart_jours: int | None = None
    base_prix: str = PRIX_FACTURE
    base_prix_minimum: str = PRIX_FACTURE


@dataclass
class _Comparaison:
    """Ce que la comparaison lit une fois pour toutes."""

    donnees: Donnees
    meme_couleur: bool
    autre_fournisseur: bool
    prix_catalogue: bool
    fenetre: float
    achats: dict[str, list[tuple[date, float]]]
    bases: dict[tuple[str, date], str]
    catalogue: dict[str, float]

    def famille(self, article: Article) -> tuple[str, ...]:
        """Ce qui doit être égal pour comparer deux fils."""
        cle: tuple[str, ...] = (
            (article.composition or article.nature or "").strip().lower(),
            (article.type_fil or "").strip().lower(),
            str(article.titrage or "").strip().lower(),
            (article.titrage_unite or "").strip().lower(),
        )
        if self.meme_couleur:
            cle += ((article.couleur or article.designation or "").strip().lower(),)
        return cle

    def base_de(self, reference: str, jour: date | None, origine: str) -> str:
        """Coût rendu, prix facture, ou catalogue."""
        if origine == "catalogue" or jour is None:
            return "catalogue"
        return self.bases.get((reference, jour), PRIX_FACTURE)

    def offre(self, rival: Article, jour: date | None) -> Offre | None:
        """Le prix du rival : l'achat le plus proche de `jour` dans la fenêtre ; hors fenêtre,
        son prix le plus bas (écarté, compté) ; sans date, son dernier prix ou son catalogue."""
        serie = self.achats.get(rival.reference)
        sans_date = "" if self.prix_catalogue else "sans_date"
        if serie and jour is not None:
            proche = min(serie, key=lambda x: (abs((x[0] - jour).days), -x[0].toordinal()))
            if abs((proche[0] - jour).days) <= self.fenetre:
                return (proche[1], "payé", proche[0], "")
            moins_cher = min(serie, key=lambda x: (x[1], -x[0].toordinal()))
            return (moins_cher[1], "payé", moins_cher[0], "hors_fenetre")
        if serie:
            return (serie[-1][1], "payé", serie[-1][0], sans_date)
        if self.catalogue[rival.reference] > 0:
            return (self.catalogue[rival.reference], "catalogue", None, sans_date)
        return None


def _comparaison(
    donnees: Donnees,
    options: tuple[bool, bool, bool],
    fenetre_jours: float | None,
    couts: dict[str, list[CoutDate]] | None,
) -> _Comparaison:
    bases: dict[tuple[str, date], str] = {}
    for reference, serie in (couts or {}).items():
        for jour, _, base in serie:
            if bases.get((reference, jour)) != COUT_RENDU:
                bases[(reference, jour)] = base
    parametres = donnees.parametres
    meme_couleur, autre_fournisseur, prix_catalogue = options
    return _Comparaison(
        donnees=donnees,
        meme_couleur=meme_couleur,
        autre_fournisseur=autre_fournisseur,
        prix_catalogue=prix_catalogue,
        fenetre=parametres.fenetre_prix_jours if fenetre_jours is None else fenetre_jours,
        achats=achats_dates(donnees, couts),
        bases=bases,
        catalogue={a.reference: a.prix_kg * parametres.taux(a.devise) for a in donnees.articles},
    )


Retenu = tuple[float, str, date | None, Article]


def _meilleur(
    cmp: _Comparaison,
    article: Article,
    rivaux: list[Article],
    prix: tuple[date | None, float, bool],
) -> tuple[Retenu | None, set[str]]:
    jour, actuel, propre_sans_date = prix
    retenu: Retenu | None = None
    motifs: set[str] = set()
    for rival in rivaux:
        if rival.reference == article.reference:
            continue
        if cmp.autre_fournisseur and rival.fournisseur == article.fournisseur:
            continue
        proposition = cmp.offre(rival, jour)
        if proposition is None or proposition[0] >= actuel:
            continue
        prix_rival, origine_rival, jour_rival, motif = proposition
        if propre_sans_date:
            motif = "sans_date"
        if motif:
            motifs.add(motif)
            continue
        if retenu is None or prix_rival < retenu[0]:
            retenu = (prix_rival, origine_rival, jour_rival, rival)
    return retenu, motifs


def _opportunite(
    cmp: _Comparaison,
    article: Article,
    quantite: float,
    actuel: tuple[date | None, float, str],
    retenu: Retenu,
) -> Opportunite:
    jour, prix, origine = actuel
    minimum, origine_minimum, jour_minimum, meilleur = retenu
    return Opportunite(
        reference=article.reference,
        nature=article.nature,
        titrage=article.titrage,
        fournisseur_actuel=article.fournisseur,
        prix_actuel_mad=prix,
        prix_minimum_mad=minimum,
        fournisseur_alternatif=meilleur.fournisseur,
        conso_annuelle=quantite,
        economie_mad=(prix - minimum) * quantite,
        composition=article.composition or article.nature,
        type_fil=article.type_fil,
        couleur=article.couleur or article.designation,
        reference_alternative=meilleur.reference,
        couleur_alternative=meilleur.couleur or meilleur.designation,
        origine_prix=origine,
        origine_prix_minimum=origine_minimum,
        ecart=(prix - minimum) / prix,
        date_prix=jour,
        date_prix_minimum=jour_minimum,
        ecart_jours=abs((jour - jour_minimum).days) if jour and jour_minimum else None,
        base_prix=cmp.base_de(article.reference, jour, origine),
        base_prix_minimum=cmp.base_de(meilleur.reference, jour_minimum, origine_minimum),
    )


def comparer_les_prix(
    donnees: Donnees,
    lignes_stock: list[LigneStock],
    *,
    meme_couleur: bool = False,
    autre_fournisseur: bool = True,
    prix_catalogue: bool = False,
    fenetre_jours: float | None = None,
    couts: dict[str, list[CoutDate]] | None = None,
) -> tuple[list[Opportunite], dict[str, int]]:
    """Les pistes triées par économie décroissante, et les pistes écartées par motif."""
    cmp = _comparaison(
        donnees, (meme_couleur, autre_fournisseur, prix_catalogue), fenetre_jours, couts
    )
    conso = {x.reference: x.conso_mensuelle * MOIS for x in lignes_stock}
    familles: dict[tuple[str, ...], list[Article]] = defaultdict(list)
    for article in donnees.articles:
        if article.actif and (
            cmp.achats.get(article.reference) or cmp.catalogue[article.reference] > 0
        ):
            familles[cmp.famille(article)].append(article)
    resultat: list[Opportunite] = []
    ecartees = {"sans_date": 0, "hors_fenetre": 0}
    for article in donnees.articles:
        quantite = conso.get(article.reference, 0.0)
        if quantite <= 0 or not article.actif:
            continue
        serie = cmp.achats.get(article.reference)
        jour, actuel, origine = (
            (serie[-1][0], serie[-1][1], "payé")
            if serie
            else (None, cmp.catalogue[article.reference], "catalogue")
        )
        if actuel <= 0:
            continue
        propre_sans_date = not serie and not prix_catalogue
        retenu, motifs = _meilleur(
            cmp, article, familles.get(cmp.famille(article), []), (jour, actuel, propre_sans_date)
        )
        if retenu is None:
            if "sans_date" in motifs:
                ecartees["sans_date"] += 1
            elif motifs:
                ecartees["hors_fenetre"] += 1
            continue
        resultat.append(_opportunite(cmp, article, quantite, (jour, actuel, origine), retenu))
    resultat.sort(key=lambda o: -o.economie_mad)
    return resultat, ecartees


def opportunites(
    donnees: Donnees,
    lignes_stock: list[LigneStock],
    *,
    meme_couleur: bool = False,
    autre_fournisseur: bool = True,
    prix_catalogue: bool = False,
    couts: dict[str, list[CoutDate]] | None = None,
) -> list[Opportunite]:
    """Les pistes d'économies (voir `comparer_les_prix`)."""
    return comparer_les_prix(
        donnees,
        lignes_stock,
        meme_couleur=meme_couleur,
        autre_fournisseur=autre_fournisseur,
        prix_catalogue=prix_catalogue,
        couts=couts,
    )[0]
