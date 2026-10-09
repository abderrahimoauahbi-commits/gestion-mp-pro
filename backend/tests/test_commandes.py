"""Les bons de commande (lot D3) : un brouillon sans numéro jusqu'à son envoi, le cours fige à la
première confirmation, la date promise, les jalons, l'unité de la fiche, les défauts de Gestion
MP corrigés (A-05, A-08, A-11, A-15, A-16, A-17, A-27). Preuves héritées de `test_achats`,
`test_audit2_achats`, `test_commandes_receptions`, `test_defauts_a`.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat, bon, cours, fiche, geste, ok, recevoir, reglage
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from gestion_mp_pro.calcul.controles import controler
from gestion_mp_pro.calcul.stock import etat_stock
from gestion_mp_pro.db import fabrique as fabrique_de_sessions
from gestion_mp_pro.modeles import Journal, Matiere
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


def test_un_brouillon_n_a_pas_de_numero_et_se_date_a_l_envoi(
    achats: TestClient, eur: Achat
) -> None:
    """Hérité : test_achats::test_un_brouillon_n_a_pas_de_numero_et_se_date_a_l_envoi."""
    b = bon(achats, eur, {eur.matiere("BLEU", prix="3"): 1000})
    assert b["numero"] is None and b["statut"] == "brouillon" and b["livraison"] == "pas_envoye"
    r = geste(achats, b, "envoyer", 422, date=j(1))
    assert "futur" in r["detail"]
    b = geste(achats, b, "envoyer", date=j(-1))
    assert b["statut"] == "envoyee" and b["date_commande"] == j(-1)
    assert b["numero"].startswith("BC-2026-")
    r = achats.delete(f"/api/commandes/{b['id']}", params={"version": b["version"]})
    assert r.status_code == 409 and "annuler" in r.json()["detail"]
    b = geste(achats, b, "solder")
    assert b["statut"] == "annulee" and b["solde_origine"] == "manuel"
    b = geste(achats, b, "rouvrir")
    assert b["statut"] == "envoyee" and b["solde_origine"] is None


def test_un_brouillon_se_supprime_il_ne_se_solde_pas(achats: TestClient, eur: Achat) -> None:
    """Hérité : test_achats::test_un_brouillon_se_supprime_il_ne_se_solde_pas."""
    b = bon(achats, eur, {eur.matiere("GRIS", prix="2.8"): 200})
    assert "supprime" in geste(achats, b, "solder", 409)["detail"]
    r = achats.put(
        f"/api/commandes/{b['id']}/expedition", json={"version": b["version"], "eta": j(1)}
    )
    assert r.status_code == 409
    assert (
        achats.delete(f"/api/commandes/{b['id']}", params={"version": b["version"]}).status_code
        == 204
    )
    assert achats.get(f"/api/commandes/{b['id']}").status_code == 404


def test_le_cours_se_fige_a_la_premiere_confirmation(achats: TestClient, eur: Achat) -> None:
    """Hérité : test_achats::test_le_cours_se_fige_a_la_premiere_confirmation."""
    b = bon(
        achats, eur, {eur.matiere("BLEU2", prix="3"): 500, eur.matiere("VERT2", prix="3.2"): 500}
    )
    b = geste(achats, b, "envoyer")
    premiere, seconde = b["lignes"]
    b = prix(achats, b, {premiere["id"]: 3.1})
    fige = b["cours"]
    assert fige and b["statut"] == "envoyee" and b["prix_a_confirmer"] == 1
    assert b["lignes"][0]["confirme_le"] and b["lignes"][0]["confirme_par"] == "Achats"
    with cours("EUR", str(fige + 1)):
        b = prix(achats, b, {seconde["id"]: 3.3})
        assert b["cours"] == pytest.approx(fige) and b["statut"] == "confirmee"
        assert b["montant_mad"] == pytest.approx((500 * 3.1 + 500 * 3.3) * fige)


def test_les_jalons_de_l_expedition(achats: TestClient, mad: Achat) -> None:
    """Hérité : test_achats::test_les_jalons_de_l_expedition ; A-16 : un champ absent garde sa
    valeur, un bon annulé ne se suit plus (test_defauts_a::test_l_expedition_d_un_bon_annule…)."""
    b = geste(achats, bon(achats, mad, {mad.matiere("JALON"): 300}), "envoyer", date=j(-3))

    def suivre(code: int = 200, **jalons: object) -> dict:
        r = achats.put(
            f"/api/commandes/{b['id']}/expedition",
            json={"version": fiche(achats, b["id"])["version"], **jalons},
        )
        assert r.status_code == code, r.text
        return r.json()

    assert "ETA" in suivre(422, embarquee_le=j(1))["detail"]
    assert "précède" in suivre(422, proforma_le=j(-4))["detail"]
    x = suivre(acompte_le=j(-1), embarquee_le=j(-1), eta=j(1), conteneur="MSCU1234567")
    assert x["expedition"]["acompte_le"] == j(-1) and x["expedition"]["eta"] == j(1)
    x = suivre(proforma_le=j(-2))
    assert x["expedition"]["conteneur"] == "MSCU1234567" and x["expedition"]["acompte_le"] == j(-1)
    x = suivre(acompte_le=None)
    assert x["expedition"]["acompte_le"] is None and x["expedition"]["proforma_le"] == j(-2)
    geste(achats, b, "solder")
    assert "annulé" in suivre(409, eta=j(2))["detail"]


def test_un_prix_confirme_change_par_la_modification_redemande_confirmation(
    achats: TestClient, mad: Achat
) -> None:
    """Hérité : test_audit2_achats::test_un_prix_confirme_change_par_la_modification_redemande_confirmation."""  # noqa: E501
    m = mad.matiere("PRIXC")
    b = geste(achats, bon(achats, mad, {m: 100}), "envoyer")
    b = prix(achats, b, {b["lignes"][0]["id"]: 21})
    version = fiche(achats, b["id"])["version"]
    b = ok(
        achats.put(
            f"/api/commandes/{b['id']}",
            json={"version": version, "lignes": [{"matiere_id": m, "quantite": 100, "prix": 2}]},
        )
    )
    assert not b["lignes"][0]["prix_confirme"] and b["statut"] == "envoyee"
    assert b["lignes"][0]["confirme_par"] is None
    assert prix(achats, b, {b["lignes"][0]["id"]: 0}, 422)["code"] == "saisie_invalide"


def test_l_unite_de_commande_est_celle_de_la_fiche(achats: TestClient, mad: Achat) -> None:
    """Hérité : test_audit2_achats::test_l_unite_de_commande_est_celle_de_la_fiche."""
    m = mad.matiere("PALETTE", poids_bobine="2.5", bobines_palette="100")

    def creer(unite: str, contenance: float):
        return achats.post(
            "/api/commandes",
            json={
                "fournisseur_id": mad.fournisseur_id,
                "lignes": [
                    {
                        "matiere_id": m,
                        "quantite": 1000,
                        "unite_achat": unite,
                        "contenance": contenance,
                    }
                ],
            },
        )

    r = creer("Palette", 7)
    assert r.status_code == 422 and "250" in r.json()["detail"]
    assert creer("Fût", 200).status_code == 422
    assert creer("kg", 2).json()["detail"].endswith("commandée en kg, la contenance vaut 1.")
    b = ok(creer("Palette", 250), 201)[0]
    assert b["lignes"][0]["unites"] == 4


def test_la_date_promise_se_compte_a_l_envoi(achats: TestClient, mad: Achat) -> None:
    """Hérité : test_audit2_achats::test_la_date_promise_se_compte_a_l_envoi (une promesse
    d'avant la date du bon ne se saisit plus sur le brouillon : contrainte de la base)."""
    m = mad.matiere("G5")
    b = bon(achats, mad, {m: 100})
    assert b["date_livraison_prevue"] is None
    b = geste(achats, b, "envoyer", date=j(-3))
    assert b["date_commande"] == j(-3) and b["date_livraison_prevue"] == j(7)  # + 10 j
    r = achats.post(
        "/api/commandes",
        json={
            "fournisseur_id": mad.fournisseur_id,
            "date_livraison_prevue": j(-1),
            "lignes": [{"matiere_id": m, "quantite": 1}],
        },
    )
    assert r.status_code == 422 and "précède" in r.json()["detail"]
    b = bon(achats, mad, {m: 100}, date_livraison_prevue=j(1))
    with pytest.MonkeyPatch.context() as mp:  # l'envoi a lieu trois jours plus tard
        from gestion_mp_pro.services import horloge

        mp.setattr(horloge, "aujourd_hui", lambda: JOUR + timedelta(days=3))
        r = achats.post(f"/api/commandes/{b['id']}/envoyer", json={"version": b["version"]})
        assert r.status_code == 422 and "précède l'envoi" in r.json()["detail"]
    b = geste(achats, b, "envoyer", date=j(-5))
    assert b["date_livraison_prevue"] == j(1)
    assert "précède" in modifier(achats, b, {m: 100}, 422, date_livraison_prevue=j(-6))["detail"]


def test_la_promesse_se_confirme_avec_les_prix_puis_se_fige(achats: TestClient, mad: Achat) -> None:
    """Hérité : test_audit2_achats::test_la_promesse_se_confirme_avec_les_prix_puis_se_fige."""
    m = mad.matiere("G12")
    b = geste(achats, bon(achats, mad, {m: 100}, date_livraison_prevue=j(1)), "envoyer")
    b = modifier(achats, b, {m: 100}, date_livraison_prevue=j(20))
    assert b["date_livraison_prevue"] == j(20)
    b = prix(achats, b, {b["lignes"][0]["id"]: 10}, date_livraison_prevue=j(25))
    assert b["date_livraison_prevue"] == j(25)
    assert "ETA" in modifier(achats, b, {m: 100}, 422, date_livraison_prevue=j(40))["detail"]


def test_l_eta_saisie_apres_coup_n_efface_pas_la_promesse_passee(
    achats: TestClient, mad: Achat
) -> None:
    """Hérité : test_commandes_receptions::test_l_eta_saisie_apres_coup_n_efface_pas_le_retard
    (partie bon : la promesse passée ne se repousse plus, l'attente va dans l'ETA)."""
    m = mad.matiere("ETA")
    b = bon(achats, mad, {m: 100})
    b = geste(achats, b, "envoyer", date=j(-20))
    b = modifier(achats, b, {m: 100}, date_livraison_prevue=j(-10))
    r = modifier(achats, b, {m: 100}, 422, date_livraison_prevue=j(5))
    assert "ne se repousse plus" in r["detail"] and "ETA" in r["detail"]


def test_vider_la_livraison_prevue_d_un_brouillon(achats: TestClient, eur: Achat) -> None:
    """Hérité : test_defauts_a::test_vider_la_livraison_prevue_d_un_brouillon (A-08)."""
    m = eur.matiere("VIDER", prix="3")
    b = bon(achats, eur, {m: 50}, date_livraison_prevue=j(2))
    b = modifier(achats, b, {m: 50}, date_livraison_prevue=None)
    assert b["date_livraison_prevue"] is None
    b = geste(achats, b, "envoyer")
    assert b["date_livraison_prevue"] == j(45)
    assert "ETA" in modifier(achats, b, {m: 50}, 422, date_livraison_prevue=None)["detail"]
    assert modifier(achats, b, {m: 50})["date_livraison_prevue"] == j(45)  # absente : inchangée


def test_une_fiche_qui_change_de_devise_ne_fausse_pas_le_prix_du_bon(
    achats: TestClient, mad: Achat
) -> None:
    """Hérité : test_audit2_achats::test_une_fiche_qui_change_de_devise_ne_fausse_pas_le_prix_du_bon."""  # noqa: E501
    m = mad.matiere("S18", prix="1.9", devise="USD")
    b = geste(achats, bon(achats, mad, {m: 100}), "envoyer")
    with fabrique_de_sessions()() as s, s.begin():
        x = s.get(Matiere, m)
        assert x is not None
        x.devise, x.prix = "EUR", 1.6  # type: ignore[assignment]
    taux = {d["code"]: d["cours"] for d in ok(achats.get("/api/devises"))}
    attendu = 1.6 * taux["EUR"] / taux["USD"]
    assert fiche(achats, b["id"])["montant_estime"] == pytest.approx(100 * attendu)


def test_le_prix_confirme_respecte_la_devise_de_la_fiche(achats: TestClient, eur: Achat) -> None:
    """Hérité : test_defauts_a::test_le_prix_confirme_respecte_la_devise_de_la_fiche (A-15)."""
    m = eur.matiere("DEVISE FICHE", prix="3")
    b = geste(achats, bon(achats, eur, {m: 100}), "envoyer")
    with fabrique_de_sessions()() as s, s.begin():
        x = s.get(Matiere, m)
        assert x is not None
        x.devise, x.prix = "MAD", 3  # type: ignore[assignment]
    b = geste(achats, b, "prix", lignes=[{"ligne_id": b["lignes"][0]["id"], "prix": 2}])
    with fabrique_de_sessions()() as s:
        x = s.get(Matiere, m)
        assert x is not None and float(x.prix) == pytest.approx(2 * b["cours"], abs=1e-6)
        assert s.scalar(
            select(func.count())
            .select_from(Journal)
            .where(
                Journal.objet == "matiere",
                Journal.objet_id == m,
                Journal.detail.like("%prix confirmé%"),
            )
        )


def test_un_bon_confirme_modifie_attend_le_prix_de_sa_nouvelle_ligne(
    achats: TestClient, mad: Achat
) -> None:
    """Hérité : test_commandes_receptions::test_un_bon_confirme_modifie_attend_le_prix_de_sa_nouvelle_ligne."""  # noqa: E501
    m1, m2 = mad.matiere("MOD1"), mad.matiere("MOD2")
    b = geste(achats, bon(achats, mad, {m1: 100}), "envoyer")
    b = prix(achats, b, {b["lignes"][0]["id"]: 10})
    assert b["statut"] == "confirmee"
    b = modifier(achats, b, {m1: 100, m2: 50})
    assert b["statut"] == "envoyee" and b["prix_a_confirmer"] == 1


def test_la_liste_des_bons_compte_tout_en_kilos(achats: TestClient, mad: Achat) -> None:
    """Hérité : test_audit2_achats::test_la_liste_des_bons_compte_tout_en_kilos."""
    kg = mad.matiere("KGML-FIL")
    cuir = mad.matiere("KGML-CUIR", role="Cuir", densite="0.25", unite_prix="ml", prix="2.5")
    b = geste(achats, bon(achats, mad, {kg: 1000, cuir: 300}), "envoyer")
    assert b["quantite"] == 1300 and "quantite_ml" not in b
    assert b["lignes"][1]["metres"] == pytest.approx(1200)
    recevoir(b["lignes"][0]["id"], 1000)
    b = fiche(achats, b["id"])
    assert b["recu"] == 1000 and b["part_livree"] == pytest.approx(1000 / 1300)


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
