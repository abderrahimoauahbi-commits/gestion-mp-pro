"""Matières : fiche, prix au kilo ou au mètre, traces, classement (routes 70–77, 81) — lot D1.

Héritage R-REF-21…41 (REGLES § 1.6) ; domaine 3 de ESSAIS (matières au mètre, stock en kilos,
partie fiche) ; défauts A-02, A-11, A-12, H-28.
"""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.referentiels import (
    code_douanier,
    devise,
    fournisseur,
    matiere,
    qualite,
    role_id,
    stock_initial,
    unique,
    valeur_classification,
)
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import select, update

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.api.matieres.schemas import MatiereCreation
from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Fournisseur, Matiere, Mouvement
from gestion_mp_pro.services.matieres import commandable


def ok(r: Any, statut: int = 200) -> Any:
    """La réponse JSON d'un appel qui doit réussir."""
    assert r.status_code == statut, r.text
    return r.json()


def nouvelle(**champs: Any) -> dict[str, Any]:
    """Le corps d'une matière nouvelle : Poil, en service, d'un fournisseur nouveau."""
    return {
        "reference": unique("REF"),
        "role_id": role_id("Poil"),
        "fournisseur_id": fournisseur(),
        **champs,
    }


def corps(client: TestClient, ident: int, **changes: Any) -> dict[str, Any]:
    """La fiche entière relue, modifiée, avec sa version (un PUT est un remplacement)."""
    lue = ok(client.get(f"/api/matieres/{ident}"))
    return {
        **{k: lue[k] for k in MatiereCreation.model_fields},
        "version": lue["version"],
        **changes,
    }


def test_une_matiere_en_service_a_un_fournisseur(achats: TestClient) -> None:
    """Hérité : test_referentiels::test_une_matiere_en_service_a_un_fournisseur (X-REF-25)."""
    r = achats.post("/api/matieres", json=nouvelle(fournisseur_id=None))
    assert r.status_code == 422 and "fournisseur" in r.json()["detail"]
    assert (
        ok(achats.post("/api/matieres", json=nouvelle(fournisseur_id=None, actif=False)), 201)[
            "actif"
        ]
        is False
    )


def test_une_fiche_creee_dit_qui_et_quand(achats: TestClient) -> None:
    """Une matière et un fournisseur créés portent l'auteur et l'heure de leur création
    (`modifie_par` sans `modifie_le` : reste F7)."""
    m = ok(achats.post("/api/matieres", json=nouvelle()), 201)
    fiche = ok(achats.get(f"/api/matieres/{m['id']}"))
    assert fiche["modifie_par"] and fiche["modifie_le"]
    f = ok(achats.post("/api/fournisseurs", json={"nom": unique("Q")}), 201)
    assert ok(achats.get(f"/api/fournisseurs/{f['id']}"))["modifie_le"]


def test_matiere_conditionnement_et_version(achats: TestClient) -> None:
    """Hérité : test_referentiels_complets::test_matiere_conditionnement_et_historique."""
    m = ok(achats.post("/api/matieres", json=nouvelle(poids_bobine=2, bobines_palette=100)), 201)
    assert m["conditionnement"] == {"unite": "Palette", "contenance": 200.0, "declare": False}
    carton = ok(
        achats.put(
            f"/api/matieres/{m['id']}",
            json=corps(achats, m["id"], unite_achat="Carton", contenance_achat=25),
        )
    )
    assert carton["conditionnement"] == {"unite": "Carton", "contenance": 25.0, "declare": True}
    vide = ok(achats.put(f"/api/matieres/{m['id']}", json=corps(achats, m["id"], unite_achat=" ")))
    assert vide["conditionnement"]["unite"] == "Palette" and vide["contenance_achat"] == 1
    perime = achats.put(f"/api/matieres/{m['id']}", json={**corps(achats, m["id"]), "version": 1})
    assert perime.status_code == 409
    assert perime.json()["detail"].startswith(
        "Cette matière a été modifiée entre-temps par Achats ("
    )


def test_code_douanier_verifie(achats: TestClient) -> None:
    """Hérité : test_referentiels_complets::test_code_douanier_verifie (X-REF-30, P7-15)."""
    r = achats.post("/api/matieres", json=nouvelle(code_douanier_id=999999))
    assert r.json()["detail"].startswith(
        "Code douanier inconnu : « 999999 ». Demander à la direction"
    )
    c = code_douanier()
    assert (
        ok(achats.post("/api/matieres", json=nouvelle(code_douanier_id=c)), 201)["code_douanier_id"]
        == c
    )


def test_une_classification_laissee_vide_n_est_pas_une_erreur(achats: TestClient) -> None:
    """Hérité : test_zz_restauration::test_une_classification_laissee_vide_n_est_pas_une_erreur."""
    m = ok(achats.post("/api/matieres", json=nouvelle(composition_id=None)), 201)
    assert m["composition"] is None


def test_une_matiere_avec_historique_ne_se_supprime_pas(achats: TestClient) -> None:
    """Hérité : test_referentiels_complets::test_une_matiere_avec_historique_ne_se_supprime_pas ;
    X-REF-34, X-REF-35 ; R-REF-26 (stock de tous les magasins)."""
    m = matiere()
    stock_initial(m, "42.5")
    lue = ok(achats.get(f"/api/matieres/{m}"))
    assert lue["utilisee"] and lue["usages"] == [
        "des mouvements de stock",
        "des lots en stock ou passés",
    ]
    assert lue["stock"] == 42.5
    r = achats.delete(f"/api/matieres/{m}")
    assert r.json()["detail"] == (
        f"« {lue['reference']} » figure dans des mouvements de stock : elle appartient à "
        "l'historique. La désactiver plutôt que la supprimer."
    )
    libre = matiere()
    assert achats.delete(f"/api/matieres/{libre}").status_code == 204


def test_le_prix_au_metre_se_ramene_au_kilo(achats: TestClient) -> None:
    """Hérité : test_matieres_au_metre::test_le_prix_au_metre_se_ramene_au_kilo (R-REF-22, 23)."""
    usd = devise(cours="9.5")
    cuir = matiere(role="Cuir", unite_prix="ml", prix="0.5", densite="0.014")
    bande = matiere(role="Plastique", unite_prix="ml", prix="2.5", densite="0.005", devise=usd)
    poil, franges = matiere(prix="3"), matiere(role="Franges", densite="0.02")
    lus = {x["id"]: x for x in ok(achats.get("/api/matieres"))}
    assert lus[cuir]["prix_kg"] == pytest.approx(35.714285714)
    assert lus[cuir]["kg_par_ml"] == 0.014
    assert (lus[bande]["prix_kg"], lus[bande]["kg_par_ml"]) == (500.0, 0)
    assert (lus[poil]["prix_kg"], lus[poil]["kg_par_ml"]) == (3.0, 0)
    assert lus[franges]["kg_par_ml"] == 0.02


DENSITE = (
    "Une matière du rôle {} (cuir, franges, ruban : comptés au mètre dans les recettes) a besoin "
    "de sa densité (kg/ml) : le stock est en kilos."
)
REFUS_FICHE = [
    ({"role": "Cuir"}, DENSITE.format("Cuir")),
    ({"role": "Ruban"}, DENSITE.format("Ruban")),
    (
        {"unite_prix": "ml"},
        "Un prix au mètre a besoin de la densité (kg/ml) pour se ramener au kilo.",
    ),
    ({"unite_prix": "m"}, "Unité du prix : au kilo (kg) ou au mètre (ml)."),
    (
        {"unite_achat": "ml"},
        "La commande se compte en kilos (ou en palettes, fûts… de tant de kilos). Un fournisseur "
        "qui facture au mètre : choisir le prix « au mètre ».",
    ),
    (
        {"unite_achat": "Fût", "contenance_achat": 0},
        "Une unité d'achat autre que le kilo a besoin de sa contenance (kg par unité).",
    ),
    ({"devise": "XYZ"}, "Devise inconnue : « XYZ ». L'ajouter d'abord (Réglages › Devises)."),
    ({"fournisseur_id": 999999}, "Fournisseur inconnu."),
    (
        {"composition_id": 999999},
        "Composition inconnue : « 999999 ». L'ajouter d'abord dans la classification.",
    ),
    (
        {"titrage_id": 999999},
        "Titrage inconnu : « 999999 ». L'ajouter d'abord dans la classification.",
    ),
    ({"role_id": 999999}, "Rôle inconnu : « 999999 »."),
]


@pytest.mark.parametrize(("champs", "message"), REFUS_FICHE)
def test_creer_une_matiere_au_prix_au_metre_ou_au_kilo(
    achats: TestClient, champs: dict[str, Any], message: str
) -> None:
    """Hérité : test_matieres_au_metre::test_creer_une_matiere_au_prix_au_metre_ou_au_kilo ;
    X-REF-20…29 mot pour mot (accords P7-13)."""
    if "role" in champs:
        champs = {"role_id": role_id(champs.pop("role")), **champs}
    r = achats.post("/api/matieres", json=nouvelle(**champs))
    assert (r.status_code, r.json()["detail"]) == (422, message)


def test_bornes_et_longueurs_sans_500(achats: TestClient) -> None:
    """R5 de ECRANS-PRO partie 7 ; H-28 (bornes) : une saisie hors bornes est un 422 français."""
    for champs in (
        {"prix": -1},
        {"couv_min_mois": 61},
        {"reference": "x" * 161},
    ):
        r = achats.post("/api/matieres", json=nouvelle(**champs))
        assert r.status_code == 422, champs
    brut = json.dumps(nouvelle(densite=0)).replace('"densite": 0', '"densite": Infinity')
    r = achats.post("/api/matieres", content=brut, headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_l_unite_du_prix_se_change_et_le_journal_ne_bouge_pas(achats: TestClient) -> None:
    """Hérité : test_valeur_et_dates::test_l_unite_du_prix_se_change_et_le_journal_ne_bouge_pas."""
    m = matiere(prix="10")
    stock_initial(m, "100", prix="10")
    lu = ok(
        achats.put(
            f"/api/matieres/{m}", json=corps(achats, m, prix=2.5, unite_prix="ml", densite=0.25)
        )
    )
    assert lu["prix_kg"] == 10.0
    with sessions()() as s:
        mv = s.scalars(select(Mouvement).where(Mouvement.matiere_id == m)).one()
        assert (float(mv.quantite), float(mv.prix)) == (100.0, 10.0)
    r = achats.put(f"/api/matieres/{m}", json=corps(achats, m, densite=0))
    assert r.status_code == 422


def test_le_role_d_une_matiere_en_recette_ne_change_pas(direction: TestClient) -> None:
    """Hérité : test_defauts_a::test_le_role_d_une_matiere_en_recette_ne_change_pas (A-02, F13)."""
    m = matiere()
    qualite(recette={m: 100}, poids={"Poil": "1"})
    r = direction.put(f"/api/matieres/{m}", json=corps(direction, m, role_id=role_id("Trame")))
    assert r.status_code == 409
    assert (
        "figure dans 1 recette(s) comme Poil : son rôle ne change pas tant qu'elle y est"
        in r.json()["detail"]
    )


def test_une_valeur_desactivee_ne_se_pose_pas_sur_une_matiere(achats: TestClient) -> None:
    """Hérité : test_defauts_a::test_une_valeur_desactivee_ne_se_pose_pas_sur_une_matiere (A-11)
    — la matière qui la porte déjà la garde."""
    v = valeur_classification("couleur", unique("Gris"), actif=False)
    r = achats.post("/api/matieres", json=nouvelle(couleur_id=v))
    assert "est désactivée dans la classification" in r.json()["detail"]
    m = matiere(couleur_id=v)
    assert (
        ok(achats.put(f"/api/matieres/{m}", json=corps(achats, m, designation="garde")))[
            "couleur_id"
        ]
        == v
    )


def test_une_matiere_desactivee_ne_se_commande_pas() -> None:
    """Hérité : test_defauts_a::test_une_matiere_desactivee_ne_se_commande_pas (A-11, pour D3)."""
    with sessions()() as s:
        m = s.get_one(Matiere, matiere(actif=False))
        with pytest.raises(Refus) as refus:
            commandable(s, m.id)
        assert (
            refus.value.detail
            == f"« {m.reference} » est désactivée : la réactiver avant de la commander."
        )
        f = fournisseur(actif=False, s=s)
        autre = s.get_one(Matiere, matiere(fournisseur_id=f, s=s))
        with pytest.raises(Refus) as refus:
            commandable(s, autre.id)
        assert refus.value.code == "fiche_inactive"
        s.rollback()


def test_une_ancienne_matiere_incomplete_se_desactive(achats: TestClient) -> None:
    """Défaut H-28 : désactiver ne revalide que ce qui change (sans fournisseur, elle sort)."""
    m = matiere()
    with sessions()() as s, s.begin():
        s.execute(update(Matiere).where(Matiere.id == m).values(fournisseur_id=None))
    lu = ok(achats.put(f"/api/matieres/{m}", json=corps(achats, m, actif=False)))
    assert lu["actif"] is False
    assert achats.put(f"/api/matieres/{m}", json=corps(achats, m, actif=True)).status_code == 422


def test_reference_unique_et_l_alimentation_sans_prix(
    achats: TestClient, alimentation: TestClient
) -> None:
    """Hérité : test_referentiels_complets::test_l_alimentation_ne_voit_aucun_prix (R-REF-27) ;
    X-REF-31 et A-12 (casse)."""
    ref = unique("Poil Rouge")
    m = ok(
        achats.post("/api/matieres", json=nouvelle(reference=ref, prix=2.5, minimum_commande=500)),
        201,
    )
    r = achats.post("/api/matieres", json=nouvelle(reference=ref.upper()))
    assert (r.status_code, r.json()["detail"]) == (
        409,
        f"La matière « {ref} » existe déjà (« {ref.upper()} »).",
    )
    vue = ok(alimentation.get(f"/api/matieres/{m['id']}"))
    assert (vue["prix"], vue["prix_kg"], vue["devise"], vue["minimum_commande"]) == (
        None,
        None,
        None,
        None,
    )
    assert vue["reference"] == ref
    assert alimentation.post("/api/matieres", json=nouvelle()).status_code == 403
    trouvees = ok(achats.get("/api/matieres", params={"q": ref.lower()}))
    assert [x["id"] for x in trouvees] == [m["id"]]


def test_reference_composee(alimentation: TestClient) -> None:
    """Hérité : R-REF-48 (`POST /articles/composer` devenu `GET /matieres/reference`)."""
    pp = valeur_classification("composition", unique("PP")[:12])
    frz = valeur_classification("type_fil", "FRZ" + unique("")[-4:])
    t = valeur_classification("titrage", unique("2900 Dtex"), valeur="2900", unite="Dtex")
    c = valeur_classification("couleur", unique("C"), libelle="Gold")
    lu = ok(alimentation.get("/api/matieres/reference", params={
        "composition_id": pp, "type_fil_id": frz, "titrage_id": t, "couleur_id": c,
        "couleur_code": "3423", "suffixe": "Hs"}))  # fmt: skip
    assert lu["reference"].endswith("-2900 Dtex-Gold 3423-Hs") and lu["existe"] is False
    assert lu["designation"] == "Gold (3423)"


def test_classer_le_catalogue_lit_les_references(
    achats: TestClient, alimentation: TestClient
) -> None:
    """Hérité : test_referentiels::test_classer_le_catalogue_lit_les_references (R-REF-35…41)."""
    m = matiere(f"PP FRZ-2900 Dtex-Red 7612-Hs {unique('x')}")
    propositions = ok(achats.get("/api/matieres/classement"))["propositions"]
    p = next(x for x in propositions if x["matiere_id"] == m)
    assert p["changements"]["composition"] == "PP" and p["changements"]["type_fil"] == "FRZ"
    assert p["changements"]["titrage"] == "2900 Dtex"
    perime = achats.post(
        "/api/matieres/classement", json={"ids": [m], "versions": [p["version"] + 1]}
    )
    assert perime.status_code == 409
    ok(achats.post("/api/matieres/classement", json={"ids": [m], "versions": [p["version"]]}))
    lue = ok(achats.get(f"/api/matieres/{m}"))
    assert (lue["composition"], lue["type_fil"], lue["titrage"]) == ("PP", "FRZ", "2900 Dtex")
    assert all(
        x["matiere_id"] != m for x in ok(achats.get("/api/matieres/classement"))["propositions"]
    )
    assert alimentation.get("/api/matieres/classement").status_code == 403


def test_export_des_matieres(achats: TestClient, alimentation: TestClient) -> None:
    """Hérité : test_referentiels_complets::test_les_exports_des_referentiels (matières) — avec
    les filtres de la liste."""
    m = matiere(prix="4.1")
    with sessions()() as s:
        ref = s.get_one(Matiere, m).reference
        nom = s.get_one(Fournisseur, s.get_one(Matiere, m).fournisseur_id).nom
    r = achats.get("/api/export/matieres", params={"q": ref})
    feuille = load_workbook(BytesIO(r.content)).active
    lignes = list(feuille.iter_rows(min_row=4, values_only=True))
    assert len(lignes) == 1 and lignes[0][0] == ref and lignes[0][8] == nom and lignes[0][9] == 4.1
    assert alimentation.get("/api/export/matieres").status_code == 403


def test_l_unite_d_achat_kg_s_ecrit_en_minuscules(achats: TestClient) -> None:
    """Audit n° 2 : « Kg » ou « KG » (un tableur) est le kilo — pas une unité déclarée de
    contenance 1 qui ferait un conditionnement « Kg » à côté de « kg »."""
    m = ok(achats.post("/api/matieres", json=nouvelle(unite_achat="Kg", poids_bobine=2)), 201)
    assert m["unite_achat"] == "kg" and m["contenance_achat"] == 1
    assert m["conditionnement"] == {"unite": "Bobine", "contenance": 2.0, "declare": False}
    m = ok(achats.put(f"/api/matieres/{m['id']}", json=corps(achats, m["id"], unite_achat="KG")))
    assert m["unite_achat"] == "kg" and not m["conditionnement"]["declare"]
