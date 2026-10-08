"""Propriétés du moteur (PLAN-DE-RECETTE-PRO § 4) : sur des suites aléatoires de gestes
VALIDES (entrées, sorties, retours des machines et au fournisseur, transferts, ajustements,
annulations), le moteur tient ses invariants :

- les soldes par lot et par magasin retombent sur le stock de chaque matière (journal) ;
- aucun lot n'est jamais sous zéro, à aucune date (C27, C37 conformes) ;
- la valeur est conservée : Σ des flux valorisés = valeur du stock au CMUP ;
- une annulation coûte ce que coûtait l'écriture qu'elle défait ;
- une sortie puis son annulation remettent le stock et le CMUP à l'état d'avant ;
- l'état à une date passée ne dépend pas des écritures postérieures.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from gestion_mp_pro.calcul.a_la_date import a_la_date
from gestion_mp_pro.calcul.controles import controler, stock_negatif_passe
from gestion_mp_pro.calcul.lots import stock_par_lot
from gestion_mp_pro.calcul.modele import (
    Article,
    Donnees,
    Fournisseur,
    Magasin,
    Mouvement,
    Parametres,
)
from gestion_mp_pro.calcul.stock import etat_stock
from gestion_mp_pro.calcul.valorisation import couts_du_journal

DEBUT = date(2026, 1, 5)
REFERENCES = ("FIL A", "FIL B")
MAGASINS = ("M1", "M2")
LOTS = ("L1", "L2", "L3")
GESTES = (
    "entree",
    "sortie",
    "retour_machine",
    "retour_fournisseur",
    "transfert",
    "ajustement",
    "annulation",
)
REGLAGE = settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)

Cle = tuple[str, str, str]


@dataclass
class _Journal:
    """Le journal en construction, et ce que chaque lot porte dans chaque magasin."""

    mouvements: list[Mouvement] = field(default_factory=list)
    soldes: dict[Cle, float] = field(default_factory=lambda: defaultdict(float))
    jour: date = DEBUT

    def ecrire(self, type_: str, cle: Cle, quantite: float, **autres: object) -> Mouvement:
        reference, lot, magasin = cle
        signe = -1 if type_ in ("SORTIE_PROD", "RETOUR_FOURNISSEUR") else 1
        m = Mouvement(
            date=autres.pop("jour", self.jour),
            type=type_,
            reference=reference,  # type: ignore[arg-type]
            quantite=quantite,
            lot_fournisseur=lot,
            utilisateur="Essai",
            fournisseur="FOURNISSEUR",
            id=len(self.mouvements) + 1,
            magasin_source=magasin if signe < 0 else "",
            magasin_destination=magasin if signe > 0 else "",
            **autres,
        )  # type: ignore[arg-type]
        self.mouvements.append(m)
        self.soldes[cle] += quantite * signe
        return m


def _geste(data: st.DataObject, journal: _Journal) -> None:
    geste = data.draw(st.sampled_from(GESTES))
    journal.jour += timedelta(days=data.draw(st.integers(0, 4)))
    pleins = sorted(c for c, q in journal.soldes.items() if q > 1)
    if geste == "entree" or not pleins:
        cle = (
            data.draw(st.sampled_from(REFERENCES)),
            data.draw(st.sampled_from(LOTS)),
            data.draw(st.sampled_from(MAGASINS)),
        )
        journal.ecrire(
            "ENTREE_RECEPTION",
            cle,
            float(data.draw(st.integers(10, 900))),
            prix_unite=float(data.draw(st.integers(1, 60))),
        )
        return
    cle = data.draw(st.sampled_from(pleins))
    part = data.draw(st.sampled_from((0.1, 0.25, 0.5, 1.0)))
    quantite = journal.soldes[cle] * part
    if geste in ("sortie", "retour_machine"):
        sortie = journal.ecrire("SORTIE_PROD", cle, quantite, numero_of="OF-2026-0001")
        if geste == "retour_machine":
            journal.ecrire(
                "RETOUR_PRODUCTION", cle, quantite / 2, numero_of="OF-2026-0001", motif_retour="R1"
            )
        _ = sortie
    elif geste == "retour_fournisseur":
        journal.ecrire("RETOUR_FOURNISSEUR", cle, quantite, motif_retour="R3")
    elif geste == "transfert":
        _transferer(journal, cle, quantite)
    elif geste == "ajustement":
        signe = data.draw(st.sampled_from((-1, 1)))
        journal.ecrire("AJUSTEMENT_INVENTAIRE", cle, signe * quantite)
    else:
        _annuler(journal, data)


def _transferer(journal: _Journal, cle: Cle, quantite: float) -> None:
    reference, lot, source = cle
    destination = "M2" if source == "M1" else "M1"
    journal.mouvements.append(
        Mouvement(
            date=journal.jour,
            type="TRANSFERT_MAGASIN",
            reference=reference,
            quantite=quantite,
            lot_fournisseur=lot,
            magasin_source=source,
            magasin_destination=destination,
            utilisateur="Essai",
            fournisseur="FOURNISSEUR",
            id=len(journal.mouvements) + 1,
        )
    )
    journal.soldes[cle] -= quantite
    journal.soldes[(reference, lot, destination)] += quantite


def _annuler(journal: _Journal, data: st.DataObject) -> None:
    """Annule une sortie (toujours possible : elle rend la matière), datée comme elle."""
    annulees = {m.contrepasse_id for m in journal.mouvements}
    sorties = [
        m
        for m in journal.mouvements
        if m.type == "SORTIE_PROD"
        and m.quantite > 0
        and m.contrepasse_id is None
        and m.id not in annulees
    ]
    if not sorties:
        return
    m = data.draw(st.sampled_from(sorties))
    journal.ecrire(
        "SORTIE_PROD",
        (m.reference, m.lot_fournisseur, m.magasin_source),
        -m.quantite,
        jour=m.date,
        contrepasse_id=m.id,
        numero_of=m.numero_of,
    )


def _donnees(mouvements: list[Mouvement]) -> Donnees:
    return Donnees(
        parametres=Parametres(cours={"MAD": 1.0}),
        fournisseurs=[Fournisseur(nom="FOURNISSEUR", delai_jours=30)],
        articles=[
            Article(reference=r, fournisseur="FOURNISSEUR", prix_unite=20.0) for r in REFERENCES
        ],
        magasins=[Magasin(code=c) for c in MAGASINS],
        mouvements=mouvements,
    )


@st.composite
def journaux(draw: st.DrawFn) -> _Journal:
    """Une suite de 3 à 40 gestes valides."""
    journal = _Journal()
    data = draw(st.data())
    for _ in range(draw(st.integers(3, 40))):
        _geste(data, journal)
    return journal


@REGLAGE
@given(journaux())
def test_les_lots_retombent_sur_le_stock_et_jamais_sous_zero(journal: _Journal) -> None:
    donnees = _donnees(journal.mouvements)
    lignes = {x.reference: x for x in etat_stock(donnees, journal.jour)}
    par_lot: dict[str, float] = defaultdict(float)
    for lot in stock_par_lot(donnees):
        par_lot[lot.reference] += lot.stock
        assert lot.stock > -1e-6
        for magasin, quantite in lot.par_magasin.items():
            assert abs(quantite - journal.soldes[(lot.reference, lot.lot, magasin)]) < 1e-6
    for reference, ligne in lignes.items():
        assert abs(par_lot[reference] - ligne.stock_net) < 1e-3
        assert abs(sum(ligne.par_magasin.values()) - par_lot[reference]) < 1e-6
    assert stock_negatif_passe(donnees) == []
    codes = {c.code: c for c in controler(donnees, list(lignes.values()), journal.jour)}
    assert codes["C27"].conforme and codes["C37"].conforme


@REGLAGE
@given(journaux())
def test_la_valeur_est_conservee_et_une_annulation_coute_l_original(journal: _Journal) -> None:
    donnees = _donnees(journal.mouvements)
    couts = couts_du_journal(donnees)
    flux: dict[str, float] = defaultdict(float)
    for m in donnees.mouvements:
        flux[m.reference] += m.quantite_signee * couts.unitaire[m.id or 0]
        if m.contrepasse_id is not None:
            assert couts.unitaire[m.id or 0] == couts.unitaire[m.contrepasse_id]
    for reference, (quantite, valeur) in couts.stock.items():
        echelle = max(1.0, abs(valeur), abs(flux[reference]))
        assert abs(flux[reference] - valeur) <= 1e-6 * echelle
        assert quantite >= 0 and valeur >= 0


@REGLAGE
@given(journaux(), st.sampled_from((0.1, 0.5, 1.0)))
def test_une_sortie_puis_son_annulation_ne_changent_rien(journal: _Journal, part: float) -> None:
    avant = couts_du_journal(_donnees(journal.mouvements))
    pleins = sorted(c for c, q in journal.soldes.items() if q > 1)
    if not pleins:
        return
    sortie = journal.ecrire("SORTIE_PROD", pleins[0], journal.soldes[pleins[0]] * part)
    journal.ecrire("SORTIE_PROD", pleins[0], -sortie.quantite, contrepasse_id=sortie.id)
    apres = couts_du_journal(_donnees(journal.mouvements))
    for reference, (quantite, valeur) in avant.stock.items():
        q2, v2 = apres.stock[reference]
        assert abs(q2 - quantite) <= 1e-6 * max(1.0, quantite)
        assert abs(v2 - valeur) <= 1e-6 * max(1.0, valeur)


@REGLAGE
@given(journaux(), st.integers(0, 80))
def test_une_date_passee_ne_depend_pas_de_ce_qui_suit(journal: _Journal, recul: int) -> None:
    jour = journal.jour - timedelta(days=recul)
    complet = _donnees(journal.mouvements)
    tronque = _donnees([m for m in journal.mouvements if m.date <= jour])
    aujourdhui = journal.jour + timedelta(days=1)
    d1, d2 = a_la_date(complet, jour, aujourdhui), a_la_date(tronque, jour, aujourdhui)
    assert etat_stock(d1, jour) == etat_stock(d2, jour)
    c1, c2 = couts_du_journal(d1), couts_du_journal(d2)
    assert (c1.unitaire, c1.stock) == (c2.unitaire, c2.stock)
    assert replace(d1, mouvements=[]) == replace(d2, mouvements=[])
