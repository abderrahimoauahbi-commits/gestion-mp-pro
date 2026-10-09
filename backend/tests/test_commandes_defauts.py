"""Les bons de commande (lot D3) : défauts de Gestion MP corrigés (A-05, A-11, A-17, A-27) et
ce que le moteur lit d'un bon (brouillon attendu de personne, retard toléré et C06). Preuves
héritées de `test_defauts_a`, `test_commandes_receptions`.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat, bon, fiche, geste, recevoir, reglage
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.calcul.controles import controler
from gestion_mp_pro.calcul.stock import etat_stock
from gestion_mp_pro.db import fabrique as fabrique_de_sessions
from gestion_mp_pro.modeles import Matiere
from gestion_mp_pro.services import donnees_moteur

JOUR = date(2026, 10, 8)


def j(n: int = 0) -> str:
    """Le jour des essais décalé de `n` jours, en ISO."""
    return (JOUR + timedelta(days=n)).isoformat()


def modifier(client: TestClient, b: dict, lignes: dict[int, float], code: int = 200, **autres):
    """`PUT /commandes/{id}` avec la version lue."""
    version = fiche(client, b["id"])["version"]
    corps = {
        "version": version,
        "lignes": [{"matiere_id": m, "quantite": q} for m, q in lignes.items()],
    }
    r = client.put(f"/api/commandes/{b['id']}", json=corps | autres)
    assert r.status_code == code, r.text
    return r.json()


def prix(client: TestClient, b: dict, valeurs: dict[int, float], code: int = 200, **autres):
    """Confirmer des prix (ligne → prix), sans toucher au catalogue."""
    lignes = [{"ligne_id": i, "prix": p} for i, p in valeurs.items()]
    return geste(client, b, "prix", code, lignes=lignes, mettre_a_jour_catalogue=False, **autres)


@pytest.fixture
def eur() -> Achat:
    """Une filature turque en euros, délai 45 jours."""
    return Achat.nouveau(devise="EUR", delai=45, pays="TURKEY")


@pytest.fixture
def mad() -> Achat:
    """Une filature marocaine en dirhams, délai 10 jours."""
    return Achat.nouveau(devise="MAD", delai=10, pays="MAROC")


def test_confirmer_les_prix_d_un_bon_qui_n_est_pas_parti_ou_solde_est_refuse(
    achats: TestClient, eur: Achat
) -> None:
    """Hérité : test_defauts_a::test_confirmer_les_prix_d_un_brouillon_est_refuse,
    test_defauts_a::test_confirmer_les_prix_d_un_bon_solde_est_refuse (A-05)."""
    m = eur.matiere("CONF", prix="3")
    b = bon(achats, eur, {m: 100})
    r = prix(achats, b, {b["lignes"][0]["id"]: 3}, 409)
    assert "pas encore parti" in r["detail"] and fiche(achats, b["id"])["cours"] is None
    b = geste(achats, b, "envoyer")
    recevoir(b["lignes"][0]["id"], 100)
    assert fiche(achats, b["id"])["statut"] == "soldee"
    assert "soldé" in prix(achats, b, {b["lignes"][0]["id"]: 3}, 409)["detail"]


def test_un_bon_a_approuver_avant_son_envoi_ne_confirme_pas_ses_prix(
    achats: TestClient, eur: Achat
) -> None:
    """Hérité : test_defauts_a::test_un_bon_a_approuver_avant_son_envoi_ne_confirme_pas_ses_prix."""
    with reglage("seuil_approbation", "100"):
        b = geste(achats, bon(achats, eur, {eur.matiere("CONF APPROB", prix="3"): 1000}), "envoyer")
        assert b["statut"] == "a_approuver" and b["numero"] is None
        assert prix(achats, b, {b["lignes"][0]["id"]: 3}, 409)["code"] == "etat_incompatible"


def test_une_matiere_ou_un_fournisseur_desactive_ne_se_commande_pas(
    achats: TestClient, eur: Achat
) -> None:
    """Hérité : test_defauts_a::test_une_matiere_desactivee_ne_se_commande_pas (A-11, partie
    commande ; la réception est au lot D4) — une ligne déjà sur le bon reste."""
    garde, m = eur.matiere("GARDEE", prix="3"), eur.matiere("DESACTIVEE", prix="3")
    b = bon(achats, eur, {garde: 10})
    with fabrique_de_sessions()() as s, s.begin():
        for ident in (m, garde):
            x = s.get(Matiere, ident)
            assert x is not None
            x.actif = False
    r = achats.post(
        "/api/commandes",
        json={"fournisseur_id": eur.fournisseur_id, "lignes": [{"matiere_id": m, "quantite": 10}]},
    )
    assert r.status_code == 409 and "désactivée" in r.json()["detail"]
    assert modifier(achats, b, {garde: 20})["quantite"] == 20
    assert "désactivée" in modifier(achats, b, {garde: 20, m: 5}, 409)["detail"]
    endormi = Achat.nouveau(devise="EUR", actif=False)
    r = achats.post(
        "/api/commandes",
        json={
            "fournisseur_id": endormi.fournisseur_id,
            "lignes": [{"matiere_id": m, "quantite": 10}],
        },
    )
    assert r.status_code == 409 and "désactivé" in r.json()["detail"]


def test_un_bon_solde_n_annonce_pas_d_approbation(achats: TestClient, eur: Achat) -> None:
    """Hérité : test_defauts_a::test_un_bon_solde_n_annonce_pas_d_approbation (A-17)."""
    b = geste(achats, bon(achats, eur, {eur.matiere("APPROB", prix="3"): 1000}), "envoyer")
    geste(achats, b, "solder")
    with reglage("seuil_approbation", "100"):
        assert fiche(achats, b["id"])["approbation_requise"] is False


def test_un_brouillon_n_est_attendu_de_personne(achats: TestClient, mad: Achat) -> None:
    """Hérité : test_commandes_receptions::test_un_brouillon_n_est_attendu_de_personne (stock
    et C06 lus par le moteur ; le cockpit est au lot D8)."""
    m = mad.matiere("BROUILLON")
    b = bon(achats, mad, {m: 500}, date_livraison_prevue=j(0))
    assert b["livraison"] == "pas_envoye"
    with fabrique_de_sessions()() as s:
        ref = s.scalar(select(Matiere.reference).where(Matiere.id == m))
        d = donnees_moteur.charger_au(s, JOUR)
        lignes = etat_stock(d, JOUR)
        ligne = next(x for x in lignes if x.reference == ref)
        c06 = next(x for x in controler(d, lignes, JOUR, aujourdhui=JOUR) if x.code == "C06")
    assert ligne.bc_en_cours == 0 and ligne.bc_hors_horizon == 0
    assert ligne.bc_en_preparation == 500
    assert f"BC-brouillon-{b['id']}" not in {x["numero"] for x in c06.detail}


def test_le_retard_tolere_vaut_a_l_ecran_et_dans_c06(achats: TestClient, mad: Achat) -> None:
    """Hérité : test_commandes_receptions::test_le_retard_tolere_vaut_a_l_ecran_et_dans_c06."""
    m = mad.matiere("TOL")
    b = bon(achats, mad, {m: 100})
    b = geste(achats, b, "envoyer", date=j(-5))
    b = modifier(achats, b, {m: 100}, date_livraison_prevue=j(-2))

    def c06() -> set[str]:
        with fabrique_de_sessions()() as s:
            d = donnees_moteur.charger_au(s, JOUR)
            c = next(
                x
                for x in controler(d, etat_stock(d, JOUR), JOUR, aujourdhui=JOUR)
                if x.code == "C06"
            )
            return {str(x["numero"]) for x in c.detail}

    assert fiche(achats, b["id"])["livraison"] == "en_retard" and b["numero"] in c06()
    with reglage("toler_retard_jours", "5"):
        assert fiche(achats, b["id"])["livraison"] == "attendu" and b["numero"] not in c06()


def test_l_approbation_date_le_bon_du_jour_d_envoi_saisi(
    achats: TestClient, direction: TestClient, eur: Achat
) -> None:
    """Hérité : test_defauts_a::test_l_approbation_date_le_bon_du_jour_d_envoi_saisi (A-27)."""
    with reglage("seuil_approbation", "100"):
        b = geste(achats, bon(achats, eur, {eur.matiere("APPROB DATE", prix="3"): 1000}), "envoyer")
        assert "futur" in geste(direction, b, "approuver", 422, date=j(1))["detail"]
        b = geste(direction, b, "approuver", date=j(-1))
        assert b["date_commande"] == j(-1) and b["numero"]
