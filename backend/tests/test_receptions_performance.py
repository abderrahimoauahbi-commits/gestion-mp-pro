"""La note des livraisons à partir de vraies réceptions (lot D4 ; domaine 6 de ESSAIS.md, avec
le lot D8 qui sert `/fournisseurs/performance`) : ce qui ne devait rien n'est pas noté, un bon
tout renvoyé garde sa note, une seule tolérance pour « livré » et le camion complet, le camion
de remplacement après un retour, le score sans les bons annulés. La note est celle du moteur
(`calcul.fournisseurs`), nourri par le chargeur.
"""

from __future__ import annotations

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat
from fabriques.achats import geste as geste_bon
from fabriques.receptions import (
    Quai,
    bon_relu,
    j,
    ligne_du_bon,
    parti,
    performance,
    recevoir,
    retour,
)
from fastapi.testclient import TestClient

from gestion_mp_pro.calcul.fournisseurs import scorecard_fournisseurs
from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.services import donnees_moteur


@pytest.fixture
def mad() -> Achat:
    """Une filature marocaine, délai de livraison de 10 jours."""
    return Achat.nouveau(devise="MAD", delai=10, pays="MAROC")


@pytest.fixture
def quai() -> Quai:
    """Un magasin de rangement à soi."""
    return Quai.nouveau()


def _ligne(b: dict, m: int, kg: float, lot: str, quai: Quai) -> list[dict]:
    return [ligne_du_bon(b, m, kg, lot, magasin_id=quai.courant)]


def test_une_reception_hors_commande_n_entre_pas_dans_l_otif(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_commandes_receptions::test_une_reception_hors_commande_n_entre_pas_dans_l_otif."""  # noqa: E501
    m = mad.matiere("HC")
    r = recevoir(achats, mad.fournisseur_id,
                 [{"matiere_id": m, "lot_numero": "HC-1", "quantite_pesee": 50,
                   "magasin_id": quai.courant}])  # fmt: skip
    p = performance(r["numero"])
    assert p.in_full is None and p.otif is None


def test_solder_un_bon_tout_renvoye_le_solde_et_garde_sa_note(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_audit2_achats::test_solder_un_bon_tout_renvoye_le_solde_et_garde_sa_note —
    promis à J−10, 600 kg reçus à J : (0, 0, 0) ; tout renvoyé puis soldé : soldé (pas annulé),
    la note reste."""
    m = mad.matiere("G6")
    b = parti(achats, mad, {m: 1000}, envoye=j(-20))
    assert b["date_livraison_prevue"] == j(-10)
    r = recevoir(achats, mad.fournisseur_id, _ligne(b, m, 600, "G6-1", quai))
    p = performance(r["numero"])
    assert (p.on_time, p.in_full, p.otif) == (0, 0, 0)
    retour(achats, r["lignes"][0], 600, le=j())
    assert geste_bon(achats, b, "solder")["statut"] == "soldee"
    p = performance(r["numero"])
    assert (p.in_full, p.otif) == (0, 0)


def test_une_seule_tolerance_pour_le_bon_livre_et_le_camion_complet(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_audit2_achats::test_une_seule_tolerance_pour_le_bon_livre_et_le_camion_complet
    — 500 + 485 sur 1 000 : « Livré », et le camion est complet."""
    m = mad.matiere("G10")
    b = parti(achats, mad, {m: 1000})
    recevoir(achats, mad.fournisseur_id, _ligne(b, m, 500, "G10-1", quai))
    r = recevoir(achats, mad.fournisseur_id, _ligne(b, m, 485, "G10-2", quai))
    assert bon_relu(achats, b["id"])["livraison"] == "livre"
    assert performance(r["numero"]).in_full == 1


def test_le_camion_de_remplacement_apres_un_retour_est_note(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_audit2_achats::test_le_camion_de_remplacement_apres_un_retour_est_note —
    1 000 reçus à J−12 (promis J−10), 600 renvoyés, un camion de 200 à J : (0, 0, 0)."""
    m = mad.matiere("G9")
    b = parti(achats, mad, {m: 1000}, envoye=j(-20))
    r = recevoir(achats, mad.fournisseur_id, _ligne(b, m, 1000, "G9-1", quai), date=j(-12))
    retour(achats, r["lignes"][0], 600, le=j(-1))
    r = recevoir(achats, mad.fournisseur_id, _ligne(b, m, 200, "G9-2", quai))
    p = performance(r["numero"])
    assert (p.on_time, p.in_full, p.otif) == (0, 0, 0)


def test_le_score_ne_compte_pas_les_bons_annules(achats: TestClient, mad: Achat) -> None:
    """Hérité : test_audit2_achats::test_le_score_ne_compte_pas_les_bons_annules — un bon parti
    compte ; annulé (rien reçu), il ne compte plus, ni son montant."""
    nom = bon_relu(achats, parti(achats, mad, {mad.matiere("PREMIER"): 50})["id"])["fournisseur"]

    def ligne() -> object:
        donnees_moteur.invalider()
        with sessions()() as s:
            return next(x for x in scorecard_fournisseurs(donnees_moteur.charger(s))
                        if x.fournisseur == nom)  # fmt: skip

    avant = ligne()
    b = parti(achats, mad, {mad.matiere("SCORE"): 100})
    assert ligne().nb_commandes == avant.nb_commandes + 1  # type: ignore[attr-defined]
    assert geste_bon(achats, b, "solder")["statut"] == "annulee"
    apres = ligne()
    assert apres.nb_commandes == avant.nb_commandes  # type: ignore[attr-defined]
    assert apres.montant_mad == pytest.approx(avant.montant_mad)  # type: ignore[attr-defined]
