"""Les bons de commande (lot D3) : un brouillon sans numéro jusqu'à son envoi, le cours figé à la
première confirmation, la date promise, les jalons, l'unité de la fiche, les défauts de Gestion
MP corrigés (A-05, A-08, A-11, A-15, A-16, A-17, A-27). Preuves héritées de `test_achats`,
`test_audit2_achats`, `test_commandes_receptions`, `test_defauts_a`.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat, bon, cours, fiche, geste, ok, recevoir
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from gestion_mp_pro.db import fabrique as fabrique_de_sessions
from gestion_mp_pro.modeles import Journal, Matiere

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


def test_un_numero_n_est_pris_qu_a_l_envoi_et_sans_trou(achats: TestClient, mad: Achat) -> None:
    """M65 : un brouillon n'a pas de numéro ; un envoi refusé n'en consomme pas ; le suivant
    suit le dernier donné, et un brouillon supprimé ne laisse aucun trou."""
    m = mad.matiere("M65")
    premier = geste(achats, bon(achats, mad, {m: 10}), "envoyer")["numero"]
    jete = bon(achats, mad, {m: 10})
    ok(achats.delete(f"/api/commandes/{jete['id']}", params={"version": jete["version"]}), 204)
    b = bon(achats, mad, {m: 10})
    geste(achats, b, "envoyer", 422, date=j(1))
    second = geste(achats, b, "envoyer")["numero"]
    assert int(second.rsplit("-", 1)[1]) == int(premier.rsplit("-", 1)[1]) + 1
