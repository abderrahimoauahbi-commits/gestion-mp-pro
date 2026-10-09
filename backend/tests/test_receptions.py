"""Les réceptions (lot D4) : un camion sur ses bons, partiel, sous réserve, refusé, hors commande,
le lot interne numéroté à la validation, l'annulation tracée. Preuves héritées de `test_achats`,
`test_parcours` (domaine 5 de ESSAIS.md).
"""

from __future__ import annotations

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat
from fabriques.receptions import (
    JOUR,
    Quai,
    bon_relu,
    camion,
    fiche,
    geste,
    j,
    liberer,
    ligne_du_bon,
    menage,  # noqa: F401 — fixture du module
    motif_operation,
    ok,
    parti,
)
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Lot, Mouvement

pytestmark = pytest.mark.usefixtures("menage")


@pytest.fixture
def eur() -> Achat:
    """Une filature en euros, paiement à 60 jours."""
    return Achat.nouveau(devise="EUR", delai=45, pays="TURKEY", delai_paiement_jours=60)


@pytest.fixture
def quai() -> Quai:
    """Un magasin de rangement à soi."""
    return Quai.nouveau()


def test_on_ne_recoit_pas_sur_un_bon_qui_n_est_pas_parti(achats: TestClient, eur: Achat) -> None:
    """Hérité : test_achats::test_on_ne_recoit_pas_sur_un_bon_qui_n_est_pas_parti."""
    from fabriques.achats import bon

    m = eur.matiere("GRIS")
    b = bon(achats, eur, {m: 100})
    r = camion(achats, eur.fournisseur_id, [ligne_du_bon(b, m, 100, "G1")], 409)
    assert "envoyé" in r["detail"] and r["code"] == "etat_incompatible"


def test_reception_partielle_avec_une_ligne_sous_reserve(
    achats: TestClient, eur: Achat, quai: Quai
) -> None:
    """Hérité : test_achats::test_reception_partielle_avec_une_ligne_sous_reserve — reçu 1 438,
    reste 482 ; le second camion dit le déjà reçu ; la ligne sous réserve attend en quarantaine
    (D-02 : le bon ne se solde pas) ; libérée, le bon se solde de lui-même."""
    bleu, vert = eur.matiere("BLEU", bobines_palette="96"), eur.matiere("VERT")
    b = parti(achats, eur, {bleu: 960, vert: 960}, prix=3.05)
    r = camion(
        achats,
        eur.fournisseur_id,
        [
            ligne_du_bon(
                b, bleu, 478, "B-1", quantite_bl=480, nb_palettes=2, magasin_id=quai.courant
            ),
            ligne_du_bon(b, vert, 960, "V-1", quantite_bl=960, qualite="reserve",
                         observations="cartons mouillés"),
        ],
        numero_bl="BL-77",
        controle_par="Karim",
    )  # fmt: skip
    assert r["numero"] is None and r["controle_par"] == "Karim" and r["blocages"] == []
    assert [x["numero"] for x in r["commandes"]] == [b["numero"]]
    assert r["lignes"][0]["nb_bobines"] == 192 and r["lignes"][0]["prix"] == 3.05
    r = geste(achats, r, "valider")
    assert r["numero"].startswith("REC-2025-") and r["statut"] == "validee"
    c = bon_relu(achats, b["id"])
    assert c["statut"] == "confirmee" and c["recu"] == pytest.approx(1438)
    assert c["livree_le"] is None and c["reste_kg"] == pytest.approx(482)
    r2 = camion(
        achats,
        eur.fournisseur_id,
        [ligne_du_bon(b, bleu, 482, "B-2", magasin_id=quai.courant)],
    )
    assert r2["lignes"][0]["deja_recu"] == pytest.approx(478)
    assert r2["lignes"][0]["quantite_attendue"] == pytest.approx(482)
    geste(achats, r2, "valider")
    c = bon_relu(achats, b["id"])
    assert c["statut"] == "confirmee" and c["livraison"] == "sous_reserve"
    assert c["lignes"][1]["en_quarantaine"] == pytest.approx(960)
    ligne_vert = r["lignes"][1]
    lot = ok(achats.get(f"/api/lots/{ligne_vert['lot_id']}"))
    assert lot["quarantaine"] == pytest.approx(960) and lot["disponible"] == 0
    liberer(achats, ligne_vert, quai.courant, 960, le=j())
    c = bon_relu(achats, b["id"])
    assert c["statut"] == "soldee" and c["livraison"] == "livre"


def test_un_brouillon_annonce_ce_qui_bloquerait(achats: TestClient, eur: Achat) -> None:
    """Hérité : test_achats::test_un_brouillon_annonce_ce_qui_bloquerait — pesée à zéro, lot,
    magasin : trois blocages ; la validation refuse avec le premier, à son code."""
    m = eur.matiere("GRIS")
    r = camion(achats, eur.fournisseur_id, [{"matiere_id": m, "quantite_pesee": 0}])
    assert len(r["blocages"]) == 3
    assert r["actions"]["valider"] == r["blocages"][0]
    refus = geste(achats, r, "valider", 422)
    assert refus["detail"] == r["blocages"][0] and refus["code"] == "quantite_invalide"
    ok(achats.delete(f"/api/receptions/{r['id']}", params={"version": r["version"]}), 204)


def test_le_prix_paye_hors_commande_est_retenu(achats: TestClient, eur: Achat, quai: Quai) -> None:
    """Hérité : test_achats::test_le_prix_paye_hors_commande_est_retenu — 2,65 EUR le kilo, sur
    la ligne puis sur l'entrée en stock (cours du jour figé)."""
    m = eur.matiere("GRIS")
    r = camion(
        achats,
        eur.fournisseur_id,
        [{"matiere_id": m, "lot_numero": "G-HC", "quantite_pesee": 50, "magasin_id": quai.courant,
          "prix": 2.65}],
    )  # fmt: skip
    assert r["lignes"][0]["prix"] == pytest.approx(2.65) and r["devise"] == "EUR"
    r = geste(achats, r, "valider")
    with sessions()() as s:
        mvt = s.scalars(select(Mouvement).where(Mouvement.reception_id == r["id"])).one()
        assert float(mvt.prix) == pytest.approx(2.65) and mvt.devise == "EUR"
        assert mvt.cours is not None and mvt.auteur_id is not None


def test_une_reception_toute_refusee_reste_une_trace(achats: TestClient, eur: Achat) -> None:
    """Hérité : test_achats::test_une_reception_toute_refusee_reste_une_trace — numérotée,
    validée, rien en stock."""
    m = eur.matiere("GRIS")
    r = camion(
        achats,
        eur.fournisseur_id,
        [{"matiere_id": m, "qualite": "refuse", "observations": "fil taché"}],
    )
    assert r["blocages"] == []
    r = geste(achats, r, "valider")
    assert r["statut"] == "validee" and r["numero"] and r["pese"] == 0
    with sessions()() as s:
        assert s.scalars(select(Mouvement).where(Mouvement.reception_id == r["id"])).all() == []
    assert r["actions"]["etiquettes"] == "Aucun lot : toutes les lignes sont refusées."


def test_une_reception_toute_refusee_s_annule(achats: TestClient, eur: Achat) -> None:
    """A-01 (Gestion MP corrigé, test_defauts_a) : une réception toute refusée s'annule, sans
    mouvement à contre-passer, et le bon attend de nouveau sa marchandise."""
    m = eur.matiere("REFUS")
    b = parti(achats, eur, {m: 300})
    r = geste(achats, camion(achats, eur.fournisseur_id,
                             [ligne_du_bon(b, m, 0, "", qualite="refuse")]), "valider")  # fmt: skip
    assert r["actions"]["annuler"] is None
    r = geste(achats, r, "annuler", motif="camion renvoyé, saisi deux fois")
    assert r["statut"] == "annulee" and r["annulation"]["motif"].startswith("camion renvoyé")
    with sessions()() as s:
        assert s.scalars(select(Mouvement).where(Mouvement.reception_id == r["id"])).all() == []
    assert bon_relu(achats, b["id"])["statut"] == "envoyee"


def test_le_lot_interne_est_numerote_a_la_validation(
    achats: TestClient, eur: Achat, quai: Quai
) -> None:
    """Hérité : test_achats::test_le_lot_interne_est_numerote_a_la_validation — LOT-AAAA-NNNN
    (année de la réception, 4 chiffres) à la validation ; la ligne refusée n'en prend pas ; le
    suivant est +1 (aucun numéro pris d'avance, M65)."""
    m = eur.matiere("GRIS")
    lignes = [
        {"matiere_id": m, "lot_interne": True, "quantite_pesee": 7, "magasin_id": quai.courant},
        {"matiere_id": m, "lot_numero": "LOT INTERNE", "qualite": "refuse"},
    ]
    r = camion(achats, eur.fournisseur_id, lignes)
    assert r["lignes"][0]["lot_interne"] and r["lignes"][0]["lot_numero"] == ""
    assert not r["lignes"][1]["lot_interne"]
    r = geste(achats, r, "valider")
    pris = r["lignes"][0]["lot_numero"]
    assert pris.startswith(f"LOT-{JOUR.year}-") and len(pris.rsplit("-", 1)[1]) == 4
    assert r["lignes"][1]["lot_id"] is None
    r2 = geste(achats, camion(achats, eur.fournisseur_id, lignes[:1]), "valider")
    suivant = r2["lignes"][0]["lot_numero"]
    assert int(suivant.rsplit("-", 1)[1]) == int(pris.rsplit("-", 1)[1]) + 1
    with sessions()() as s:
        assert s.get(Lot, r["lignes"][0]["lot_id"]).interne  # type: ignore[union-attr]


def test_l_annulation_dit_qui_quand_et_pourquoi(achats: TestClient, eur: Achat, quai: Quai) -> None:
    """Hérité : test_achats::test_l_annulation_dit_qui_quand_et_pourquoi — et le motif est exigé
    (ECRANS-PRO 4.17)."""
    m = eur.matiere("GRIS")
    r = camion(achats, eur.fournisseur_id,
               [{"matiere_id": m, "lot_numero": "AN-1", "quantite_pesee": 3,
                 "magasin_id": quai.courant}])  # fmt: skip
    r = geste(achats, r, "valider")
    assert geste(achats, r, "annuler", 422, motif="")["code"] == "saisie_invalide"
    r = geste(achats, r, "annuler", motif="lot saisi deux fois")
    assert r["annulation"]["par"] == "Achats" and r["annulation"]["motif"] == "lot saisi deux fois"
    assert r["annulation_motif"] == "lot saisi deux fois"


def test_la_reception_entre_en_stock(achats: TestClient, eur: Achat, quai: Quai) -> None:
    """Hérité : test_parcours::test_la_reception_entre_en_stock — 998 kg en 5 palettes de 100
    bobines : poids de bobine mesuré 998 ÷ 500 ; la ligne sous réserve est en quarantaine
    (détenue, pas disponible), et le bon le dit."""
    rouge = eur.matiere("ROUGE", bobines_palette="100")
    noir = eur.matiere("NOIR")
    b = parti(achats, eur, {rouge: 1000, noir: 600})
    r = camion(achats, eur.fournisseur_id, [
        ligne_du_bon(b, rouge, 998, "R-1", nb_palettes=5, magasin_id=quai.courant),
        ligne_du_bon(b, noir, 600, "N-1", qualite="reserve"),
    ])  # fmt: skip
    r = geste(achats, r, "valider")
    assert r["lignes"][0]["poids_moyen_bobine"] == pytest.approx(998 / 500)
    with sessions()() as s:
        lot = s.get(Lot, r["lignes"][0]["lot_id"])
        assert lot is not None and float(lot.poids_bobine) == pytest.approx(1.996)
    assert r["lignes"][1]["magasin"] and r["lignes"][1]["qualite_libelle"] == "Sous réserve"
    noir_lot = ok(achats.get(f"/api/lots/{r['lignes'][1]['lot_id']}"))
    assert noir_lot["quarantaine"] == 600 and noir_lot["disponible"] == 0
    assert bon_relu(achats, b["id"])["livraison"] == "sous_reserve"


def test_un_brouillon_se_modifie_puis_se_supprime(
    achats: TestClient, eur: Achat, quai: Quai
) -> None:
    """Hérité : test_parcours::test_un_brouillon_se_modifie_puis_se_supprime — pesée 10 → 12,
    puis suppression ; une version périmée est refusée."""
    m = eur.matiere("GRIS")
    ligne = {"matiere_id": m, "lot_numero": "M-1", "quantite_pesee": 10, "magasin_id": quai.courant}
    r = camion(achats, eur.fournisseur_id, [ligne])
    corps = {
        "date": j(),
        "fournisseur_id": eur.fournisseur_id,
        "lignes": [ligne | {"quantite_pesee": 12}],
    }
    r2 = ok(achats.put(f"/api/receptions/{r['id']}", json=corps | {"version": r["version"]}))
    assert r2["lignes"][0]["quantite_pesee"] == 12 and r2["version"] > r["version"]
    perime = achats.put(f"/api/receptions/{r['id']}", json=corps | {"version": r["version"]})
    assert perime.status_code == 409 and perime.json()["code"] == "conflit_version"
    ok(achats.delete(f"/api/receptions/{r['id']}", params={"version": r2["version"]}), 204)
    assert achats.get(f"/api/receptions/{r['id']}").status_code == 404


def test_une_annulation_contrepasse_tout(achats: TestClient, eur: Achat, quai: Quai) -> None:
    """Hérité : test_parcours::test_une_annulation_contrepasse_tout — lot à 0, journal [+40, −40]
    daté de l'original ; une seconde annulation est refusée."""
    m = eur.matiere("ANN")
    r = camion(achats, eur.fournisseur_id,
               [{"matiere_id": m, "lot_numero": "J-ANN", "quantite_pesee": 40,
                 "magasin_id": quai.courant}], date=j(-3))  # fmt: skip
    r = geste(achats, r, "valider")
    r = geste(achats, r, "annuler", motif="saisie en double")
    with sessions()() as s:
        mvts = s.scalars(
            select(Mouvement).where(Mouvement.reception_id == r["id"]).order_by(Mouvement.id)
        ).all()
        assert [float(x.quantite) for x in mvts] == [40, -40]
        assert {x.date_effet for x in mvts} == {JOUR.replace(day=28)}
    lot = ok(achats.get(f"/api/lots/{r['lignes'][0]['lot_id']}"))
    assert lot["disponible"] == 0
    refus = geste(achats, r, "annuler", 409, motif="encore")
    assert refus["detail"] == "Cette réception est déjà annulée."
    assert fiche(achats, r["id"])["actions"]["annuler"] == "Cette réception est déjà annulée."


def test_la_liberation_de_la_quarantaine_est_reservee_a_la_direction_et_aux_achats(
    achats: TestClient, alimentation: TestClient, eur: Achat, quai: Quai
) -> None:
    """D-02 : la ligne sous réserve reste attendue sur son bon tant qu'elle est en quarantaine ;
    l'alimentation ne la libère pas (403, lot D5) ; les achats la libèrent et le bon se solde."""
    m = eur.matiere("RESERVE")
    b = parti(achats, eur, {m: 200})
    r = camion(achats, eur.fournisseur_id, [ligne_du_bon(b, m, 200, "Q-1", qualite="reserve")])
    r = geste(achats, r, "valider")
    c = bon_relu(achats, b["id"])
    assert c["statut"] == "envoyee" and c["livraison"] == "sous_reserve"
    ligne = r["lignes"][0]
    refus = alimentation.post(
        "/api/operations",
        json={
            "type": "transfert",
            "date": j(),
            "motif_id": motif_operation("transfert", "Libération de quarantaine"),
            "valider": True,
            "lignes": [
                {
                    "matiere_id": m,
                    "lot_id": ligne["lot_id"],
                    "magasin_id": ligne["magasin_id"],
                    "magasin_destination_id": quai.courant,
                    "quantite": 200,
                }
            ],
        },
    )
    assert refus.status_code == 403
    assert bon_relu(achats, b["id"])["statut"] == "envoyee"
    liberer(achats, ligne, quai.courant, 200, le=j())
    assert bon_relu(achats, b["id"])["statut"] == "soldee"
