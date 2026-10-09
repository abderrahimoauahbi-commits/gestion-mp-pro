"""Le chargeur du moteur (`services/donnees_moteur.py`, lot S4) : une petite usine écrite en
base par les fabriques (`fabriques/moteur.py`) est relue **exactement** comme les `Donnees`
écrites ici à la main (CALCULS A § 4), et le moteur PRO rend les mêmes sorties sur les deux, à
plusieurs dates (`charger_au`).
"""

from __future__ import annotations

from datetime import date

import pytest
from fabriques.comparaison import en_ordre, types_de
from fabriques.moteur import Monde, batir
from fabriques.moteur_attendu import AUJOURDHUI, attendu
from fabriques.stock import s
from moteur.jeux_outils import differences, propre
from moteur.sorties_pro import sorties_du_moteur
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.a_la_date import a_la_date
from gestion_mp_pro.services import donnees_moteur

__all__ = ["s"]


@pytest.fixture
def usine(s: Session) -> tuple[Monde, c.Donnees]:
    """La petite usine en base, et ce que le chargeur doit en lire."""
    w = batir(s)
    return w, attendu(s, w)


def test_le_chargeur_relit_la_base_exactement(s: Session, usine: tuple[Monde, c.Donnees]) -> None:
    """Chaque champ de chaque structure, dans l'ordre (CALCULS A § 4.6, § 4.7)."""
    _, voulu = usine
    lu = donnees_moteur.lire(s)
    assert differences(en_ordre(propre(voulu)), en_ordre(propre(lu))) == []
    assert types_de(lu) == types_de(voulu)


@pytest.mark.parametrize(
    "jour", [date(2026, 9, 1), date(2026, 9, 22), date(2026, 9, 25), date(2026, 9, 30), AUJOURDHUI]
)
def test_charger_au_rend_les_sorties_du_moteur_sur_les_donnees_attendues(
    s: Session, usine: tuple[Monde, c.Donnees], jour: date
) -> None:
    """Le moteur PRO, nourri par le chargeur à une date, rend exactement ce qu'il rend sur les
    `Donnees` écrites à la main (stock, plan d'achat, valorisation, cockpit, contrôles…)."""
    _, voulu = usine
    donnees_moteur.invalider()
    charge = donnees_moteur.charger_au(s, jour)
    assert en_ordre(propre(charge)) == en_ordre(propre(a_la_date(voulu, jour, AUJOURDHUI)))
    obtenu = propre(sorties_du_moteur(donnees_moteur.charger(s), jour, AUJOURDHUI))
    assert differences(propre(sorties_du_moteur(voulu, jour, AUJOURDHUI)), obtenu) == []


def test_sans_journal(s: Session, usine: tuple[Monde, c.Donnees]) -> None:
    """`avec_journal=False` : ni journal ni soldes, le reste identique."""
    _, voulu = usine
    lu = donnees_moteur.charger(s, avec_journal=False)
    assert (lu.mouvements, lu.soldes) == ([], None)
    assert propre(lu.commandes) == propre(voulu.commandes)
