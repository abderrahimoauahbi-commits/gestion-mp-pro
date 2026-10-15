"""Enregistrer un comptage ne fait plus relire tout le moteur (lot CONFORT-LENTEURS ; stress
« 3 ans », A5) : la ligne de journal « comptage » ne change pas la signature du cache, parce
qu'un comptage n'écrit rien de ce que le moteur lit. Tout autre geste la change toujours.
"""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal

import pytest
from fabriques import stock as fabriques_stock
from fabriques.operations import Monde, acteur, monde
from fabriques.stock import JOUR, autre_magasin
from sqlalchemy.orm import Session

from gestion_mp_pro.services import audit, donnees_moteur
from gestion_mp_pro.services import inventaires as inv
from gestion_mp_pro.services.inventaires import Comptage, Criteres, LotTrouve, Ouverture

s = fabriques_stock.s
"""La session de l'essai, annulée à la fin (fixture du lot S4)."""


def _monde(s: Session) -> Monde:
    return monde(s, courant=autre_magasin(s))


def _interdit(*_a: object, **_k: object) -> None:
    raise AssertionError("le moteur entier a été relu après un comptage")


def test_un_comptage_ne_relit_pas_le_moteur_et_rend_les_memes_chiffres(
    s: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fiche lue (cache chaud), comptage et recomptage hors tolérance : la signature ne bouge
    pas, la fiche se relit sans le moteur entier et dit exactement ce que dirait un moteur
    relu de la base (écarts, valeurs, à recompter)."""
    m = _monde(s)
    achats = acteur(s)
    i = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id, criteres=Criteres(matieres=(m.a2.id,))))
    s.flush()
    inv.fiche(s, i.id)
    avant = donnees_moteur.signature(s)
    ligne = i.lignes[0].id
    i = inv.compter(s, achats, i.id, i.version, [Comptage(ligne, {"compte": Decimal(360)})])
    s.flush()
    assert donnees_moteur.signature(s) == avant
    with monkeypatch.context() as patch:
        patch.setattr(donnees_moteur, "lire", _interdit)
        lu = inv.fiche(s, i.id)
        i = inv.compter(
            s, achats, i.id, i.version, [Comptage(ligne, {"second_compte": Decimal(399)})]
        )
        s.flush()
        recompte = inv.fiche(s, i.id)
    assert lu.a_recompter == 1 and recompte.lignes[0].retenu == 399
    donnees_moteur.invalider()
    assert asdict(inv.fiche(s, i.id)) == asdict(recompte)


def test_les_autres_gestes_changent_toujours_la_signature(s: Session) -> None:
    """Ouvrir un inventaire, y ajouter un lot trouvé, le valider, ou une ligne « comptage »
    d'un autre objet : la signature change (le moteur sera relu)."""
    m = _monde(s)
    achats = acteur(s)
    vues = [donnees_moteur.signature(s)]
    i = inv.ouvrir(s, achats, Ouverture(JOUR, m.courant.id, criteres=Criteres(matieres=(m.a2.id,))))
    s.flush()
    vues.append(donnees_moteur.signature(s))
    trouve = LotTrouve(
        m.a2.id,
        lot_numero="TROUVE-1",
        compte=Decimal(5),
        justification="lot retrouvé sans étiquette",
    )
    i = inv.lot_trouve(s, achats, i.id, i.version, trouve)
    s.flush()
    vues.append(donnees_moteur.signature(s))
    comptages = [Comptage(x.id, {"compte": x.theorique}) for x in i.lignes if not x.lot_trouve]
    i = inv.compter(s, achats, i.id, i.version, comptages)
    i = inv.valider(s, achats, i.id, i.version)
    s.flush()
    vues.append(donnees_moteur.signature(s))
    audit.journal(s, None, "comptage", "ordre")
    s.flush()
    vues.append(donnees_moteur.signature(s))
    assert len(set(vues)) == len(vues)
