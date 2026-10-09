"""Les règles d'une réception sur ses bons (lot D4) : excédent toléré tous lots ensemble, bon
annulé ou soldé, solde automatique et solde à la main, reçu net des retours, devise hors
commande, date d'envoi, recalage sans écriture, livraison partielle sans BL, approbation en
attente, matière désactivée (A-11), bobines entières (D-08). Preuves héritées de
`test_audit2_achats`, `test_commandes_receptions` (domaines 5 et 6 de ESSAIS.md).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat, reglage
from fabriques.achats import geste as geste_bon
from fabriques.receptions import (
    Quai,
    bon_relu,
    camion,
    fiche,
    geste,
    j,
    ligne_du_bon,
    ok,
    parti,
    performance,
    recevoir,
    retour,
)
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Matiere, ReceptionLigne
from gestion_mp_pro.services import horloge


@pytest.fixture
def mad() -> Achat:
    """Une filature marocaine en dirhams, paiement à 30 jours."""
    return Achat.nouveau(devise="MAD", delai=30, pays="MAROC", delai_paiement_jours=30)


@pytest.fixture
def quai() -> Quai:
    """Un magasin de rangement à soi."""
    return Quai.nouveau()


def _recevoir(client: TestClient, a: Achat, b: dict, m: int, kg: float, *, quai: Quai, **x: object):
    """Un camion d'une ligne du bon, validé."""
    lot = str(x.pop("lot", f"L{kg}"))
    return recevoir(
        client, a.fournisseur_id, [ligne_du_bon(b, m, kg, lot, magasin_id=quai.courant, **x)]
    )


def test_deux_lots_sur_une_ligne_de_bon_ne_depassent_pas_l_excedent(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_audit2_achats::test_deux_lots_sur_une_ligne_de_bon_ne_depassent_pas_l_excedent
    — 700 + 700 sur 1 000 : « tous lots ensemble », refusé (409 `excedent`) ; 1 000 + 50 passe."""
    m = mad.matiere("G2")
    b = parti(achats, mad, {m: 1000})
    lignes = [ligne_du_bon(b, m, 700, f"A-{i}", magasin_id=quai.courant) for i in (1, 2)]
    r = camion(achats, mad.fournisseur_id, lignes)
    assert any("(tous lots ensemble)" in x for x in r["blocages"])
    assert geste(achats, r, "valider", 409)["code"] == "excedent"
    ok(achats.delete(f"/api/receptions/{r['id']}", params={"version": r["version"]}), 204)
    lignes = [
        ligne_du_bon(b, m, 1000, "A-3", magasin_id=quai.courant),
        ligne_du_bon(b, m, 50, "A-4", magasin_id=quai.courant),
    ]
    recevoir(achats, mad.fournisseur_id, lignes)
    assert bon_relu(achats, b["id"])["recu"] == pytest.approx(1050)


def test_un_brouillon_ne_se_valide_pas_sur_un_bon_annule_entre_temps(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_audit2_achats::test_un_brouillon_ne_se_valide_pas_sur_un_bon_annule_entre_temps."""  # noqa: E501
    m = mad.matiere("G3")
    b = parti(achats, mad, {m: 500})
    r = camion(
        achats, mad.fournisseur_id, [ligne_du_bon(b, m, 500, "G3-1", magasin_id=quai.courant)]
    )
    assert geste_bon(achats, b, "solder")["statut"] == "annulee"
    vue = next(x for x in ok(achats.get("/api/receptions?statut=brouillon")) if x["id"] == r["id"])
    assert any("annulé" in x for x in vue["blocages"])
    assert geste(achats, r, "valider", 409)["code"] == "bon_clos"


def test_annuler_une_reception_ne_rouvre_pas_un_bon_solde_a_la_main(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_audit2_achats::test_annuler_une_reception_ne_rouvre_pas_un_bon_solde_a_la_main."""  # noqa: E501
    m = mad.matiere("G4")
    b = parti(achats, mad, {m: 1000})
    _recevoir(achats, mad, b, m, 600, quai=quai)
    r2 = _recevoir(achats, mad, b, m, 100, quai=quai)
    geste_bon(achats, b, "solder")
    geste(achats, r2, "annuler", motif="doublon")
    c = bon_relu(achats, b["id"])
    assert c["statut"] == "soldee" and c["recu"] == pytest.approx(600)
    assert c["lignes"][0]["reste"] == 0


def test_annuler_une_reception_recale_le_bon_sans_le_contredire(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_audit2_achats::test_annuler_une_reception_recale_le_bon_sans_le_contredire."""
    m = mad.matiere("G4A")
    b = parti(achats, mad, {m: 1000})
    r1 = _recevoir(achats, mad, b, m, 1000, quai=quai)
    r2 = _recevoir(achats, mad, b, m, 30, quai=quai)
    assert bon_relu(achats, b["id"])["statut"] == "soldee"
    geste(achats, r2, "annuler", motif="doublon")
    c = bon_relu(achats, b["id"])
    assert c["statut"] == "soldee" and c["livraison"] == "livre"
    geste(achats, r1, "annuler", motif="erreur")
    assert bon_relu(achats, b["id"])["statut"] == "envoyee"


def test_hors_commande_la_devise_se_choisit_sur_la_reception(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_audit2_achats::test_hors_commande_la_devise_se_choisit_sur_la_reception —
    défaut : la devise du fournisseur ; USD choisi ; sans prix : le catalogue converti."""
    from fabriques.achats import cours

    m = mad.matiere("G8", prix="2", devise="USD")
    base = {"matiere_id": m, "quantite_pesee": 10, "magasin_id": quai.courant}
    r = camion(achats, mad.fournisseur_id, [base | {"lot_numero": "G8-1", "prix": 20}])
    assert r["devise"] == "MAD" and r["lignes"][0]["prix"] == 20
    r = camion(
        achats, mad.fournisseur_id, [base | {"lot_numero": "G8-2", "prix": 2, "devise": "USD"}]
    )
    assert r["devise"] == "USD" and r["lignes"][0]["prix"] == 2
    with cours("USD", "9.5"):
        r = camion(achats, mad.fournisseur_id, [base | {"lot_numero": "G8-3"}])
    assert r["lignes"][0]["prix"] == pytest.approx(2 * 9.5)
    refus = camion(achats, mad.fournisseur_id, [base | {"devise": "XYZ"}], 422)
    assert refus["detail"] == "Devise inconnue : XYZ."


def test_une_reception_ne_precede_pas_l_envoi_de_son_bon(achats: TestClient, mad: Achat) -> None:
    """Hérité : test_audit2_achats::test_une_reception_ne_precede_pas_l_envoi_de_son_bon."""
    m = mad.matiere("DATE")
    b = parti(achats, mad, {m: 100}, envoye=j(-5))
    refus = camion(achats, mad.fournisseur_id, [ligne_du_bon(b, m, 100, "D-1")], 422, date=j(-30))
    assert "précède" in refus["detail"] and refus["code"] == "date_invalide"


def test_lire_les_receptions_n_ecrit_rien(achats: TestClient, mad: Achat, quai: Quai) -> None:
    """Hérité : test_audit2_achats::test_lire_les_receptions_n_ecrit_rien — le brouillon est
    recalé à l'affichage (400), la base garde l'ancien attendu (A.12-27)."""
    m = mad.matiere("LECTURE")
    b = parti(achats, mad, {m: 1000})
    r = camion(
        achats, mad.fournisseur_id, [ligne_du_bon(b, m, 400, "L-1", magasin_id=quai.courant)]
    )
    _recevoir(achats, mad, b, m, 600, quai=quai, lot="L-2")
    with sessions()() as s:
        avant = s.get(ReceptionLigne, r["lignes"][0]["id"]).quantite_attendue  # type: ignore[union-attr]
    vue = fiche(achats, r["id"])
    assert vue["lignes"][0]["quantite_attendue"] == pytest.approx(400) and avant == 1000
    ok(achats.get("/api/receptions"))
    with sessions()() as s:
        assert s.get(ReceptionLigne, r["lignes"][0]["id"]).quantite_attendue == avant  # type: ignore[union-attr]


def test_un_retour_au_fournisseur_rouvre_le_bon_solde_de_lui_meme(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_commandes_receptions::test_un_retour_au_fournisseur_rouvre_le_bon_solde_de_lui_meme."""  # noqa: E501
    # Reçu net 700, reste 300, la réception dit « retourné 300 », le stock attend 300 ; retour
    # annulé : le bon se solde de nouveau (retours par le lot D5).
    m = mad.matiere("RET")
    b = parti(achats, mad, {m: 1000})
    r = _recevoir(achats, mad, b, m, 1000, quai=quai)
    assert bon_relu(achats, b["id"])["statut"] == "soldee"
    o = retour(achats, r["lignes"][0], 300, le=j())
    c = bon_relu(achats, b["id"])
    assert c["statut"] == "envoyee" and c["recu"] == pytest.approx(700)
    assert c["lignes"][0]["reste"] == pytest.approx(300)
    assert fiche(achats, r["id"])["lignes"][0]["retourne"] == pytest.approx(300)
    ligne = next(x for x in ok(achats.get("/api/stock"))["lignes"] if x["matiere_id"] == m)
    assert ligne["bc_en_cours"] + ligne["bc_hors_horizon"] == pytest.approx(300)
    ok(achats.post(f"/api/operations/{o['id']}/annuler", json={"version": o["version"]}))
    assert bon_relu(achats, b["id"])["statut"] == "soldee"


def test_un_bon_solde_a_la_main_le_reste_apres_un_retour(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_commandes_receptions::test_un_bon_solde_a_la_main_le_reste_apres_un_retour."""
    m = mad.matiere("MAIN")
    b = parti(achats, mad, {m: 1000})
    r = _recevoir(achats, mad, b, m, 600, quai=quai)
    geste_bon(achats, b, "solder")
    retour(achats, r["lignes"][0], 100, le=j())
    c = bon_relu(achats, b["id"])
    assert c["statut"] == "soldee" and c["recu"] == pytest.approx(500)


def test_une_ligne_sur_dix_livree_dix_fois_n_est_ni_complete_ni_livree(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_commandes_receptions::test_une_ligne_sur_dix_livree_dix_fois_n_est_ni_complete_ni_livree."""  # noqa: E501
    ms = [mad.matiere(f"DIX{i}") for i in range(10)]
    b = parti(achats, mad, dict.fromkeys(ms, 100))
    r = camion(
        achats, mad.fournisseur_id, [ligne_du_bon(b, ms[0], 1000, "DIX-1", magasin_id=quai.courant)]
    )
    assert any("excédent" in x for x in r["blocages"])
    geste(achats, r, "valider", 409)
    with reglage("toler_excedent", "10"):
        r = geste(achats, r, "valider")
    p = performance(r["numero"])
    assert p.in_full == 0 and p.otif == 0
    c = bon_relu(achats, b["id"])
    assert c["livraison"] != "livre" and c["statut"] == "envoyee" and c["livree_le"] is None


def test_un_excedent_dans_la_tolerance_passe(achats: TestClient, mad: Achat, quai: Quai) -> None:
    """Hérité : test_commandes_receptions::test_un_excedent_dans_la_tolerance_passe — 1 080 /
    1 000 : complet, bon soldé."""
    m = mad.matiere("PLUS")
    b = parti(achats, mad, {m: 1000})
    r = _recevoir(achats, mad, b, m, 1080, quai=quai)
    assert performance(r["numero"]).in_full == 1
    assert bon_relu(achats, b["id"])["statut"] == "soldee"


def test_recevoir_sur_un_bon_solde_avertit(achats: TestClient, mad: Achat, quai: Quai) -> None:
    """Hérité : test_commandes_receptions::test_recevoir_sur_un_bon_solde_avertit."""
    m = mad.matiere("SOLDE")
    b = parti(achats, mad, {m: 100})
    _recevoir(achats, mad, b, m, 100, quai=quai)
    assert bon_relu(achats, b["id"])["statut"] == "soldee"
    r = camion(achats, mad.fournisseur_id, [ligne_du_bon(b, m, 20, "S-2", magasin_id=quai.courant)])
    assert any("soldé" in x for x in r["avertissements"])


def test_une_livraison_partielle_sans_bl_n_est_pas_un_ecart(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_commandes_receptions::test_une_livraison_partielle_sans_bl_n_est_pas_un_ecart
    — 500 sans BL : aucun écart ; 450 pour un BL de 500 : −10 %, hors tolérance (archive)."""
    m = mad.matiere("PART")
    b = parti(achats, mad, {m: 1000})
    r = _recevoir(achats, mad, b, m, 500, quai=quai)
    assert r["lignes"][0]["ecart"] is None
    page = ok(achats.get("/api/receptions/pesees", params={"q": r["numero"]}))
    assert page["elements"][0]["ecart_relatif"] is None
    assert not page["elements"][0]["hors_tolerance"]
    r = _recevoir(achats, mad, b, m, 450, quai=quai, quantite_bl=500, lot="P-2")
    page = ok(achats.get("/api/receptions/pesees", params={"q": r["numero"]}))
    x = page["elements"][0]
    assert x["ecart_relatif"] == pytest.approx(-0.1) and x["hors_tolerance"]
    assert x["compare_au"] == "bl" and x["quantite_bl"] == 500


def test_apres_un_solde_a_la_main_la_livraison_suivante_n_est_pas_notee(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_audit2_achats::test_apres_un_solde_a_la_main_la_livraison_suivante_n_est_pas_notee."""  # noqa: E501
    m = mad.matiere("G11")
    b = parti(achats, mad, {m: 1000})
    _recevoir(achats, mad, b, m, 100, quai=quai)
    geste_bon(achats, b, "solder")
    r = camion(
        achats, mad.fournisseur_id, [ligne_du_bon(b, m, 300, "G11-2", magasin_id=quai.courant)]
    )
    assert "soldé" in r["avertissements"][0]
    horloge.fixer(horloge.maintenant() + timedelta(minutes=5))  # validée après le solde
    r = geste(achats, r, "valider")
    p = performance(r["numero"])
    assert p.in_full is None and p.otif is None
    r = camion(
        achats, mad.fournisseur_id, [ligne_du_bon(b, m, 5000, "G11-3", magasin_id=quai.courant)]
    )
    assert any("excédent" in x for x in r["blocages"])


def test_la_reception_d_un_bon_qui_attend_l_approbation_avertit(
    achats: TestClient, direction: TestClient, mad: Achat, quai: Quai
) -> None:
    """A-RCP-02 (D3 § 5) : un bon parti dont une modification attend la direction se reçoit ;
    la réception l'annonce sans bloquer."""
    m = mad.matiere("APPRO", prix="100")
    b = parti(achats, mad, {m: 100})
    with reglage("seuil_approbation", "5000"):
        corps = {"version": b["version"], "lignes": [{"matiere_id": m, "quantite": 500}]}
        c = ok(achats.put(f"/api/commandes/{b['id']}", json=corps))
    assert c["statut"] == "a_approuver" and c["numero"]
    r = camion(
        achats, mad.fournisseur_id, [ligne_du_bon(c, m, 100, "AP-1", magasin_id=quai.courant)]
    )
    assert any("attend l'approbation de la direction" in x for x in r["avertissements"])
    assert r["blocages"] == []
    assert geste(achats, r, "valider")["statut"] == "validee"


def test_une_matiere_desactivee_ne_se_recoit_plus_hors_commande(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """A-11 (Gestion MP corrigé) : hors commande, refus ; sur un bon, le camion est là :
    avertissement seulement."""
    m = mad.matiere("ARRET")
    b = parti(achats, mad, {m: 100})
    with sessions()() as s, s.begin():
        s.execute(update(Matiere).where(Matiere.id == m).values(actif=False))
    refus = camion(achats, mad.fournisseur_id,
                   [{"matiere_id": m, "lot_numero": "X", "quantite_pesee": 1}], 409)  # fmt: skip
    assert (
        refus["code"] == "fiche_inactive" and "ne se reçoit plus hors commande" in refus["detail"]
    )
    r = camion(
        achats, mad.fournisseur_id, [ligne_du_bon(b, m, 100, "AR-1", magasin_id=quai.courant)]
    )
    assert any("désactivée au catalogue" in x for x in r["avertissements"])
    assert geste(achats, r, "valider")["statut"] == "validee"


def test_une_bobine_se_compte_entiere(achats: TestClient, mad: Achat, quai: Quai) -> None:
    """D-08 (Gestion MP corrigé) : des bobines en plus fractionnaires sont refusées ; une palette
    entamée passe si elle fait des bobines entières."""
    m = mad.matiere("BOB", bobines_palette="50")
    base = {"matiere_id": m, "lot_numero": "B-1", "quantite_pesee": 100, "magasin_id": quai.courant}
    refus = camion(achats, mad.fournisseur_id, [base | {"bobines_en_plus": 2.5}], 422)
    assert refus["detail"].endswith("saisir un nombre entier de bobines en plus des palettes.")
    refus = camion(achats, mad.fournisseur_id, [base | {"nb_palettes": 0.33}], 422)
    assert "une bobine se compte entière" in refus["detail"]
    r = camion(achats, mad.fournisseur_id, [base | {"nb_palettes": 1.5, "bobines_en_plus": 3}])
    assert r["lignes"][0]["nb_bobines"] == 78


def test_lot_fournisseur_forme_lot_ne_decale_pas_la_serie(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """C-16 (Gestion MP corrigé) : un lot du fournisseur qui a la forme d'un lot interne ne fait
    pas sauter la série ; s'il porte le numéro suivant, ce numéro est passé (jamais deux lots)."""
    m = mad.matiere("SERIE")
    interne = {
        "matiere_id": m,
        "lot_interne": True,
        "quantite_pesee": 5,
        "magasin_id": quai.courant,
    }
    premier = geste(achats, camion(achats, mad.fournisseur_id, [interne]), "valider")
    n = int(premier["lignes"][0]["lot_numero"].rsplit("-", 1)[1])
    fournisseur = {**interne, "lot_interne": False, "lot_numero": "LOT-2026-9999"}
    geste(achats, camion(achats, mad.fournisseur_id, [fournisseur]), "valider")
    suivant = f"LOT-2026-{n + 1:04d}"
    pris = {**interne, "lot_interne": False, "lot_numero": suivant}
    geste(achats, camion(achats, mad.fournisseur_id, [pris]), "valider")
    r = geste(achats, camion(achats, mad.fournisseur_id, [interne]), "valider")
    assert r["lignes"][0]["lot_numero"] == f"LOT-2026-{n + 2:04d}"
    with sessions()() as s:
        assert s.scalar(select(Matiere.reference).where(Matiere.id == m))
