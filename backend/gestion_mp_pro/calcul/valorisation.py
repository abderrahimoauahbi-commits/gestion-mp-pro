"""Valorisation au coût moyen unitaire pondéré (CMUP glissant), en dirhams (CALCULS B § 1).

Portage de `moteur.CoutsDuJournal`, `couts_du_journal`, `cmup_glissant`, `cmup_par_reference`,
`LigneValorisation`, `valorisation`. Le journal est rejoué dans l'ordre : chaque entrée achetée
entre à son coût de revient (dossier d'importation) sinon à son prix au cours figé ; les
sorties partent au coût moyen du moment ; une annulation défait l'écriture à son coût, un
retour au fournisseur part au coût d'entrée de son lot, une ré-entrée sans stock reprend ce
qu'elle a coûté.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from gestion_mp_pro.calcul.constantes import ACHATS_JOURNAL, EPSILON
from gestion_mp_pro.calcul.importations import revient_par_lot, revient_par_reception
from gestion_mp_pro.calcul.modele import Article, Donnees, Mouvement
from gestion_mp_pro.calcul.stock import LigneStock


@dataclass
class CoutsDuJournal:
    """Le journal rejoué au coût moyen : la seule source du CMUP."""

    # Le coût unitaire (MAD) de chaque écriture au moment où elle a eu lieu, par son n°.
    unitaire: dict[int, float] = field(default_factory=dict)
    # Ce qui reste, par référence : [quantité, valeur en MAD].
    stock: dict[str, list[float]] = field(default_factory=dict)
    # Ce qui est parti vers les machines, net des retours : (date, valeur MAD).
    consommation: list[tuple[date, float]] = field(default_factory=list)

    def cmup(self) -> dict[str, float]:
        """Le coût moyen des matières qui ont du stock (un coût nul est un vrai coût)."""
        return {ref: b[1] / b[0] for ref, b in self.stock.items() if b[0] > EPSILON}


def _ordre(mouvement: Mouvement) -> tuple[date, int, int, int]:
    """Une annulation se rejoue juste après son original (les sorties du jour ne la voient
    pas) ; les autres écritures par date puis numéro."""
    if mouvement.contrepasse_id is not None:
        return (mouvement.date, mouvement.contrepasse_id, 1, mouvement.id or 0)
    return (mouvement.date, mouvement.id or 0, 0, 0)


class _Rejeu:
    """L'état du rejeu : stock valorisé, coût d'entrée des lots, coûts des sorties d'ordre."""

    def __init__(self, donnees: Donnees) -> None:
        self.donnees = donnees
        self.revient_ligne = revient_par_reception(donnees)
        self.revient_lot = revient_par_lot(donnees)
        self.resultat = CoutsDuJournal()
        self.etat: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
        self.entrees_lot: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
        self.sortie_ordre: dict[tuple[str, ...], float] = {}
        self.dernier_moyen: dict[str, float] = {}

    def _taux(self, devise: str) -> float:
        return self.donnees.parametres.taux(devise)

    def cout_d_entree(self, mouvement: Mouvement, article: Article) -> float:
        """Le coût de revient du dossier (par la ligne de réception, ou par le lot pour une
        entrée sans réception), sinon le prix saisi — même nul — au cours figé."""
        if mouvement.ligne_reception_id is not None:
            dedouane = self.revient_ligne.get(mouvement.ligne_reception_id)
            if dedouane is not None and dedouane.revient_unite > 0:
                return dedouane.revient_unite
        else:
            par_lot = self.revient_lot.get((mouvement.reference, mouvement.lot_fournisseur))
            if par_lot is not None and par_lot > 0:
                return par_lot
        if mouvement.prix_unite or mouvement.prix_unite is not None:
            devise = mouvement.devise or article.devise
            return mouvement.prix_unite * (mouvement.cours or self._taux(devise))
        return article.prix_kg * self._taux(article.devise)

    def cout_de_reentree(self, mouvement: Mouvement, article: Article) -> float:
        """Une matière non achetée qui rentre dans un stock vide : le coût de la sortie
        qu'elle rend, sinon celui d'entrée de son lot, sinon le dernier coût moyen, sinon le
        catalogue."""
        if mouvement.type == "RETOUR_PRODUCTION" and mouvement.numero_of:
            for cle in (
                (mouvement.numero_of, mouvement.reference, mouvement.lot_fournisseur),
                (mouvement.numero_of, mouvement.reference),
            ):
                if cle in self.sortie_ordre:
                    return self.sortie_ordre[cle]
        lot = self.entrees_lot.get((mouvement.reference, mouvement.lot_fournisseur))
        if lot and lot[0] > EPSILON and lot[1] > 0:
            return lot[1] / lot[0]
        if mouvement.reference in self.dernier_moyen:
            return self.dernier_moyen[mouvement.reference]
        return article.prix_kg * self._taux(article.devise)

    def _cout_entrant(
        self, mouvement: Mouvement, article: Article, signee: float, moyen: float
    ) -> float:
        bloc = self.etat[mouvement.reference]
        if mouvement.type in ACHATS_JOURNAL and mouvement.quantite > 0:
            cout = self.cout_d_entree(mouvement, article)
            lot = self.entrees_lot[(mouvement.reference, mouvement.lot_fournisseur)]
            lot[0] += signee
            lot[1] += signee * cout
            return cout
        if bloc[0] > EPSILON:
            return moyen
        return self.cout_de_reentree(mouvement, article)

    def _cout_sortant(self, mouvement: Mouvement, moyen: float) -> float:
        cout = moyen
        lot = self.entrees_lot.get((mouvement.reference, mouvement.lot_fournisseur))
        if mouvement.type == "RETOUR_FOURNISSEUR" and lot and lot[0] > EPSILON:
            cout = lot[1] / lot[0]
        if mouvement.type == "SORTIE_PROD" and mouvement.numero_of:
            ordre = mouvement.numero_of
            self.sortie_ordre[(ordre, mouvement.reference, mouvement.lot_fournisseur)] = cout
            self.sortie_ordre[(ordre, mouvement.reference)] = cout
        return cout

    def _cout(self, mouvement: Mouvement, article: Article, signee: float, moyen: float) -> float:
        annule = mouvement.contrepasse_id
        if annule is not None and annule in self.resultat.unitaire:
            cout = self.resultat.unitaire[annule]
            if mouvement.type in ACHATS_JOURNAL:  # l'entrée annulée ne compte plus pour son lot
                lot = self.entrees_lot[(mouvement.reference, mouvement.lot_fournisseur)]
                lot[0] += signee
                lot[1] += signee * cout
            return cout
        if signee > 0:
            return self._cout_entrant(mouvement, article, signee, moyen)
        return self._cout_sortant(mouvement, moyen)

    def _appliquer(self, bloc: list[float], signee: float, cout: float) -> None:
        if signee > 0:
            bloc[0] += signee
            bloc[1] += signee * cout
            return
        sortie = min(-signee, bloc[0]) if bloc[0] > 0 else 0.0
        bloc[0] -= sortie
        bloc[1] -= sortie * cout
        # Le stock ne vaut jamais moins que rien, et rien ne vaut rien.
        if bloc[0] <= EPSILON:
            bloc[0], bloc[1] = max(bloc[0], 0.0), 0.0
        elif bloc[1] < 0:
            bloc[1] = 0.0

    def rejouer(self, mouvement: Mouvement) -> None:
        """Une écriture rejouée : son coût, le stock valorisé, la consommation."""
        article = self.donnees.article(mouvement.reference)
        if article is None:
            return
        bloc = self.etat[mouvement.reference]
        moyen = bloc[1] / bloc[0] if bloc[0] > EPSILON else 0.0
        if mouvement.signe == 0:  # un transfert change de magasin, pas de valeur
            if mouvement.id is not None:
                self.resultat.unitaire[mouvement.id] = moyen
            return
        signee = mouvement.quantite * mouvement.signe
        cout = self._cout(mouvement, article, signee, moyen)
        avant = bloc[1]
        self._appliquer(bloc, signee, cout)
        if bloc[0] > EPSILON:
            self.dernier_moyen[mouvement.reference] = bloc[1] / bloc[0]
        if mouvement.id is not None:
            self.resultat.unitaire[mouvement.id] = cout
        if mouvement.type in ("SORTIE_PROD", "RETOUR_PRODUCTION"):
            self.resultat.consommation.append((mouvement.date, avant - bloc[1]))


def couts_du_journal(donnees: Donnees) -> CoutsDuJournal:
    """Le CMUP glissant, recalculé à chaque entrée, en dirhams, à partir du journal."""
    rejeu = _Rejeu(donnees)
    for mouvement in sorted(donnees.mouvements, key=_ordre):
        rejeu.rejouer(mouvement)
    rejeu.resultat.stock = dict(rejeu.etat)
    return rejeu.resultat


def cmup_glissant(donnees: Donnees) -> dict[str, float]:
    """Le CMUP de chaque référence qui a du stock, en dirhams."""
    return couts_du_journal(donnees).cmup()


def cmup_par_reference(
    donnees: Donnees, glissant: dict[str, float] | None = None
) -> dict[str, float]:
    """Le coût unitaire (MAD) de chaque matière : le CMUP du journal ; sans stock, la moyenne
    des prix payés (chacun dans sa devise) ; sans achat, le prix du catalogue."""
    if glissant is None:
        glissant = cmup_glissant(donnees)
    taux = donnees.parametres.taux
    achats: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for prix in donnees.historique_prix:
        bloc = achats[prix.reference]
        bloc[0] += prix.quantite
        bloc[1] += prix.quantite * prix.prix_achat * taux(prix.devise)
    resultat = {}
    for article in donnees.articles:
        if article.reference in glissant:
            resultat[article.reference] = glissant[article.reference]
            continue
        quantite, montant = achats.get(article.reference, (0.0, 0.0))
        resultat[article.reference] = (
            montant / quantite if quantite else article.prix_kg * taux(article.devise)
        )
    return resultat


@dataclass
class LigneValorisation:
    """La valeur d'une matière : magasins (quarantaine comprise) + machine, au CMUP."""

    reference: str
    nature: str
    fournisseur: str
    devise: str
    prix_catalogue: float
    cmup_mad: float
    stock_magasin: float
    stock_machine: float
    stock: float
    valeur_magasin_mad: float
    valeur_machine_mad: float
    valeur_mad: float
    ecart_mad: float


def valorisation(donnees: Donnees, lignes_stock: list[LigneStock]) -> list[LigneValorisation]:
    """💎 Valorisation : le stock des magasins et celui des métiers (U8), au CMUP."""
    magasins = {x.reference: x.stock_net for x in lignes_stock}
    machines = {x.reference: x.stock_machine for x in lignes_stock}
    couts = cmup_par_reference(donnees)
    resultat = []
    for article in donnees.articles:
        taux = donnees.parametres.taux(article.devise)
        cmup = couts[article.reference]
        magasin = magasins.get(article.reference, 0.0)
        machine = machines.get(article.reference, 0.0)
        stock = magasin + machine
        valeur = cmup * stock
        resultat.append(
            LigneValorisation(
                reference=article.reference,
                nature=article.nature,
                fournisseur=article.fournisseur,
                devise=article.devise,
                prix_catalogue=article.prix_kg,
                cmup_mad=cmup,
                stock_magasin=magasin,
                stock_machine=machine,
                stock=stock,
                valeur_magasin_mad=cmup * magasin,
                valeur_machine_mad=cmup * machine,
                valeur_mad=valeur,
                ecart_mad=valeur - stock * article.prix_kg * taux,
            )
        )
    return resultat
