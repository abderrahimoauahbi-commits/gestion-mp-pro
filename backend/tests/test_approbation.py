"""L'approbation de la direction (lot D3) : au-delà du seuil, au montant approuvé et au cours
figé ; un bon parti qui grossit repasse par elle sans perdre son numéro ; renvoyé, il revient à
sa version partie ; les décisions sont tracées. Preuves héritées de `test_achats`,
`test_audit2_achats`, `test_commandes_receptions` (domaine 4, « Approbation » : 6 essais).
"""

from __future__ import annotations

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat, bon, cours, fiche, geste, ok, recevoir, reglage
from fastapi.testclient import TestClient

from gestion_mp_pro.db import fabrique as fabrique_de_sessions
from gestion_mp_pro.modeles import Commande
from gestion_mp_pro.modeles.enums import OrigineSolde, StatutCommande


def modifier(client: TestClient, b: dict, lignes: dict[int, float], code: int = 200) -> dict:
    """`PUT /commandes/{id}` avec la version lue."""
    corps = {
        "version": fiche(client, b["id"])["version"],
        "lignes": [{"matiere_id": m, "quantite": q} for m, q in lignes.items()],
    }
    r = client.put(f"/api/commandes/{b['id']}", json=corps)
    assert r.status_code == code, r.text
    return r.json()


def confirmer(client: TestClient, b: dict, prix: float) -> dict:
    """Confirme le prix de la première ligne (catalogue inchangé)."""
    lignes = [{"ligne_id": b["lignes"][0]["id"], "prix": prix}]
    return geste(client, b, "prix", lignes=lignes, mettre_a_jour_catalogue=False)


@pytest.fixture
def eur() -> Achat:
    """Une filature en euros."""
    return Achat.nouveau(devise="EUR", delai=45)


@pytest.fixture
def mad() -> Achat:
    """Une filature en dirhams, délai 10 jours."""
    return Achat.nouveau(devise="MAD", delai=10)


def test_au_dela_du_seuil_la_direction_approuve_ou_renvoie(
    achats: TestClient, direction: TestClient, eur: Achat
) -> None:
    """Hérité : test_achats::test_au_dela_du_seuil_la_direction_approuve_ou_renvoie."""
    with reglage("seuil_approbation", "5000"):
        b = bon(achats, eur, {eur.matiere("VERT", prix="3.2"): 4000})
        assert b["approbation_requise"] is True and b["montant_estime"] == pytest.approx(12800)
        b = geste(achats, b, "envoyer")
        assert b["statut"] == "a_approuver" and b["numero"] is None
        motif = "Couper en deux livraisons"
        assert geste(achats, b, "renvoyer", 403, motif=motif)["code"] == "droit_refuse"
        assert geste(direction, b, "renvoyer", 422, motif="")["code"] == "saisie_invalide"
        b = geste(direction, b, "renvoyer", motif=motif)
        assert b["statut"] == "brouillon" and b["renvoi"]["motif"] == motif
        assert b["renvoi"]["par"] == "Direction"
        b = geste(achats, b, "envoyer")
        assert b["statut"] == "a_approuver"
        assert geste(achats, b, "envoyer", 409)["detail"] == (
            "Ce bon attend l'approbation de la direction."
        )
        b = geste(direction, b, "approuver")
        assert b["statut"] == "envoyee" and b["numero"] and b["approuvee_par"] == "Direction"
        assert b["renvoi"] is None
        decisions = [d["decision"] for d in b["decisions"]]
        assert decisions == ["demande_approbation", "renvoi", "demande_approbation", "approbation"]
        assert b["decisions"][1]["motif"] == motif
        assert b["version_partie"]["motif"] == "approbation"
        assert b["version_partie"]["montant_reference"] == pytest.approx(12800)


def test_un_bon_parti_qui_franchit_le_seuil_repasse_par_la_direction(
    achats: TestClient, direction: TestClient, eur: Achat
) -> None:
    """Hérité : test_achats::test_un_bon_parti_qui_franchit_le_seuil_repasse_par_la_direction
    (la réception avertie pendant l'approbation est au lot D4)."""
    gris = eur.matiere("GRIS", prix="2.8")
    with cours("EUR", "10"), reglage("seuil_approbation", "50000"):
        b = geste(achats, bon(achats, eur, {gris: 1000}), "envoyer")  # 28 000 MAD
        numero = b["numero"]
        assert b["statut"] == "envoyee" and numero
        b = modifier(achats, b, {gris: 20000})
        assert b["statut"] == "a_approuver" and b["numero"] == numero and not b["approuvee_par"]
        assert b["livraison"] == "attendu" and b["parti"]
        b = modifier(achats, b, {gris: 21000})
        assert b["statut"] == "a_approuver" and b["numero"] == numero
        assert geste(achats, b, "envoyer", 409)["code"] == "etat_incompatible"
        b = geste(direction, b, "approuver")
        assert b["statut"] == "envoyee" and b["numero"] == numero
        assert b["montant_approuve"] == pytest.approx(588000)
        assert modifier(achats, b, {gris: 19000})["statut"] == "envoyee"
        assert modifier(achats, b, {gris: 21000})["statut"] == "envoyee"
        assert modifier(achats, b, {gris: 21500})["statut"] == "a_approuver"
        b = geste(direction, b, "renvoyer", motif="Rester à 19 t")
        assert b["statut"] == "envoyee" and b["numero"] == numero
        assert b["lignes"][0]["quantite"] == 21000 and b["renvoi"]["motif"] == "Rester à 19 t"
        assert [d["decision"] for d in b["decisions"]][-2:] == ["renvoi", "version_retablie"]


def test_un_prix_confirme_un_peu_plus_cher_ne_rouvre_pas_l_approbation(
    achats: TestClient, direction: TestClient, eur: Achat
) -> None:
    """Hérité : test_achats::test_un_prix_confirme_un_peu_plus_cher_ne_rouvre_pas_l_approbation."""
    with reglage("seuil_approbation", "5000"):
        b = geste(achats, bon(achats, eur, {eur.matiere("VERT3", prix="3.2"): 3000}), "envoyer")
        b = geste(direction, b, "approuver")
        catalogue = b["lignes"][0]["prix_catalogue"]
        assert confirmer(achats, b, round(catalogue * 1.03, 3))["statut"] == "confirmee"
        assert confirmer(achats, b, round(catalogue * 1.2, 3))["statut"] == "a_approuver"
        assert geste(direction, b, "approuver")["statut"] == "confirmee"


def test_l_approbation_ne_se_contourne_pas_par_paliers(
    achats: TestClient, direction: TestClient, mad: Achat
) -> None:
    """Hérité : test_commandes_receptions::test_l_approbation_ne_se_contourne_pas_par_paliers."""
    with reglage("seuil_approbation", "5000"):
        b = geste(achats, bon(achats, mad, {mad.matiere("PALIER"): 600}), "envoyer")
        b = geste(direction, b, "approuver")  # 6 000 MAD
        assert confirmer(achats, b, 10.49)["statut"] == "confirmee"  # +4,9 %
        assert confirmer(achats, b, 11.0)["statut"] == "a_approuver"  # +4,9 % de la veille


def test_solder_un_bon_a_approuver_est_refuse_et_rouvrir_repasse_par_la_direction(
    achats: TestClient, mad: Achat
) -> None:
    """Hérité : test_audit2_achats::test_solder_un_bon_a_approuver_est_refuse_et_rouvrir_repasse_par_la_direction."""  # noqa: E501
    m = mad.matiere("B1")
    with reglage("seuil_approbation", "5000"):
        b = geste(achats, bon(achats, mad, {m: 400}), "envoyer")  # 4 000 MAD : part seul
        assert b["statut"] == "envoyee"
        b = modifier(achats, b, {m: 2000})
        assert b["statut"] == "a_approuver"
        assert "approbation" in geste(achats, b, "solder", 409)["detail"]
        with fabrique_de_sessions()() as s, s.begin():  # clos pendant l'approbation (autrefois)
            c = s.get(Commande, b["id"])
            assert c is not None
            c.statut, c.solde_origine = StatutCommande.annulee, OrigineSolde.manuel
        b = geste(achats, b, "rouvrir")
        assert b["statut"] == "a_approuver" and not b["approuvee_par"]


def test_un_bon_parti_qui_attend_la_direction_reste_attendu_et_se_recoit(
    achats: TestClient, direction: TestClient, mad: Achat
) -> None:
    """Hérité : test_audit2_achats::test_un_bon_parti_qui_attend_la_direction_reste_attendu_et_se_recoit
    (réception écrite par la fabrique : le domaine des réceptions est au lot D4)."""  # noqa: E501
    m = mad.matiere("G1")
    with reglage("seuil_approbation", "5000"):
        b = geste(achats, bon(achats, mad, {m: 400}), "envoyer")
        b = modifier(achats, b, {m: 600})
        assert b["statut"] == "a_approuver" and b["numero"] and b["livraison"] == "attendu"
        r = achats.delete(f"/api/commandes/{b['id']}", params={"version": b["version"]})
        assert r.status_code == 409
        recevoir(b["lignes"][0]["id"], 400)
        assert fiche(achats, b["id"])["statut"] == "a_approuver"  # c'est la direction qui décide
        b = geste(direction, b, "renvoyer", motif="Pas de hausse")
        assert b["numero"] and b["lignes"][0]["quantite"] == 400 and b["statut"] == "soldee"
        assert b["solde_origine"] == "automatique"


def test_reduire_un_bon_usd_quand_le_dollar_monte_ne_repasse_pas_par_la_direction(
    achats: TestClient, mad: Achat
) -> None:
    """Hérité : test_audit2_achats::test_reduire_un_bon_usd_quand_le_dollar_monte_ne_repasse_pas_par_la_direction."""  # noqa: E501
    a = mad.matiere("USD", prix="2.67", devise="USD")
    with cours("USD", "9.5"), reglage("seuil_approbation", "100000"):
        b = geste(achats, bon(achats, mad, {a: 3900}), "envoyer")
        b = confirmer(achats, b, 2.67)
        assert b["statut"] == "confirmee" and b["cours"] == 9.5  # 98 923 MAD au cours figé
        with cours("USD", "10"):
            b = modifier(achats, b, {a: 3800})
            assert b["statut"] == "confirmee"
            assert b["montant_estime_mad"] == pytest.approx(3800 * 2.67 * 9.5)


def test_un_brouillon_soumis_que_l_on_modifie_revient_en_brouillon(
    achats: TestClient, mad: Achat
) -> None:
    """R-CMD-16 a : la direction ne relit pas un bon qui bouge sous ses yeux."""
    m = mad.matiere("RELU")
    with reglage("seuil_approbation", "100"):
        b = geste(achats, bon(achats, mad, {m: 100}), "envoyer")
        assert b["statut"] == "a_approuver" and b["approbation_requise"]
        b = modifier(achats, b, {m: 120})
        assert b["statut"] == "brouillon" and b["numero"] is None
        assert b["decisions"][-1]["decision"] == "retour_brouillon"


def test_la_pastille_et_la_cloche_de_la_direction(
    achats: TestClient, direction: TestClient, mad: Achat
) -> None:
    """Le compteur `a_approuver` du contexte (pastille « Commandes », direction seule) et la
    notification de la demande ; les achats apprennent la décision."""
    avant = ok(direction.get("/api/contexte"))["compteurs"]["a_approuver"]
    assert "a_approuver" not in ok(achats.get("/api/contexte"))["compteurs"]
    with reglage("seuil_approbation", "100"):
        b = geste(achats, bon(achats, mad, {mad.matiere("CLOCHE"): 100}), "envoyer")
        assert ok(direction.get("/api/contexte"))["compteurs"]["a_approuver"] == avant + 1
        cloche = ok(direction.get("/api/notifications"))["elements"]
        assert any(n["lien"] == f"/commandes/{b['id']}" for n in cloche)
        geste(direction, b, "approuver")
        assert ok(direction.get("/api/contexte"))["compteurs"]["a_approuver"] == avant
        cloche = ok(achats.get("/api/notifications"))["elements"]
        assert any(
            n["lien"] == f"/commandes/{b['id']}" and "approuvé" in n["texte"] for n in cloche
        )
