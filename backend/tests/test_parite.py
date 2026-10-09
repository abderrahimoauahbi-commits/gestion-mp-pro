"""Parité PRO = Gestion MP (lot R2, PLAN-DE-RECETTE-PRO § 7) : les outils de la parité font
leurs preuves, et les corrections faites dans PRO pendant la parité restent faites.

Rapides (jeux réduits, écrits ici) : chaque règle d'explication reconnaît **sa** forme et son
ampleur et rien d'autre ; une faute injectée se voit. Complet (`GESTIONMPPRO_ESSAIS_COMPLETS=1`)
: la parité entière sur l'année d'essai, « à corriger : 0 ».
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.pilotage import Usine, fixture_usine, jour, ok  # noqa: F401
from sqlalchemy.engine import make_url

from gestion_mp_pro.config import reglages

ESSAIS = Path(__file__).resolve().parents[1] / "essais"
sys.path.insert(0, str(ESSAIS))

import parite_api as pa  # noqa: E402
import parite_api_formes as f  # noqa: E402
import parite_comparer as pc  # noqa: E402
import parite_donnees as pd  # noqa: E402
from parite_api_regles import k3_inventaire_abandonne  # noqa: E402
from parite_dynamique_outils import attendu_pro  # noqa: E402

# ── Données : chaque traduction reconnue par sa règle, et seulement elle ───────────────


def _donnees() -> dict[str, Any]:
    return {
        "mouvements": [
            {"type": "SORTIE_PROD", "quantite": 1497.6000000000001, "prix_unite": 2.72,
             "total_devise": 4073.47},
            {"type": "STOCK_INITIAL", "quantite": 3744.0000000000005, "prix_unite": 2.0,
             "total_devise": 7488.000000000001},
        ],
        "recettes": [{"qualite": "A", "reference": "x", "pourcentage": 60.0},
                     {"qualite": "A", "reference": "y", "pourcentage": 40.0}],
        "ordres": [{"date": "2026-01-30", "valide_le": None}],
        "parametres": {"methode": "corrigee", "seuil_bc_urgent": 300000},
    }  # fmt: skip


def _pro() -> dict[str, Any]:
    d = _donnees()
    d["mouvements"][0] |= {"quantite": 1497.6, "prix_unite": 0.0, "total_devise": 0.0}
    d["mouvements"][1] |= {"quantite": 3744.0, "total_devise": 7488.0}
    d["recettes"].reverse()
    d["ordres"][0]["valide_le"] = "2026-01-30T23:59:59.999999"
    del d["parametres"]["methode"]
    d["parametres"]["seuil_bc_urgent"] = 300000.0
    return d


def test_chaque_difference_de_donnees_a_sa_traduction() -> None:
    ecarts = pd.ecarts(_donnees(), _pro(), pd.Contexte())
    classes = {(pd.motif(e.chemin), e.classe) for e in ecarts}
    assert classes == {
        ("mouvements/*/quantite", "K1"),
        ("mouvements/*/prix_unite", "K8a"),
        ("mouvements/*/total_devise", "K8a"),
        ("mouvements/*/total_devise", "K1"),
        ("recettes", "ORDRE"),
        ("ordres/*/valide_le", "K8e"),
        ("parametres/methode", "P17"),
        ("parametres/seuil_bc_urgent", "K1"),
    }
    assert all(e.classe for e in ecarts)
    assert pd.chaine(_donnees(), ecarts)[-1][1] == _pro()


def test_une_difference_hors_regle_reste_a_corriger() -> None:
    pro = _pro()
    pro["mouvements"][1]["quantite"] = 3744.002  # 2 g de plus : pas un arrondi au gramme
    pro["recettes"][0]["pourcentage"] = 61.0  # autre contenu : pas un simple ordre
    pro["ordres"][0]["valide_le"] = "2026-01-30T12:00:00"  # midi : pas la fin du jour
    ecarts = [e for e in pd.ecarts(_donnees(), pro, pd.Contexte()) if e.classe is None]
    assert {pd.motif(e.chemin) for e in ecarts} >= {
        "mouvements/*/quantite", "recettes", "ordres/*/valide_le"
    }  # fmt: skip
    assert pd.arrondi(2.0005, 3) == 2.001 and pd.arrondi(4070.2295999999997, 2) == 4070.23


def test_k8b_la_scission_vient_du_depot_de_gestion_mp_et_k8i_du_cours_du_jour() -> None:
    """K8b : ce qui sépare D0 de D0s (dépôt de Gestion MP sur sa copie scindée) est la scission,
    le reste se compare de D0s à PRO ; K8i : cours 0 d'une entrée en devise → cours du jour."""
    d0 = {
        "receptions": [{"numero": "REC-1", "lignes": [{"devise": "USD"}, {"devise": "EUR"}]}],
        "mouvements": [{"type": "RECEPTION", "devise": "USD", "prix_unite": 2.0, "cours": 0.0}],
        "parametres": {"cours": {"USD": 9.5}},
    }
    d0s = {**d0, "receptions": [{"numero": "REC-1", "lignes": [{"devise": "USD"}]},
                                {"numero": "REC-1-2", "lignes": [{"devise": "EUR"}]}]}  # fmt: skip
    pro = {**d0s, "mouvements": [{**d0["mouvements"][0], "cours": 9.5}]}
    ecarts = pd.ecarts(d0, pro, pd.lire_contexte(d0s, 1))
    assert {(pd.motif(e.chemin), e.classe) for e in ecarts} == {
        ("receptions", "K8b"),
        ("mouvements/*/cours", "K8i"),
    }
    assert pd.chaine(d0, ecarts)[-1][1] == pro
    faux = {**pro, "mouvements": [{**d0["mouvements"][0], "cours": 9.6}]}
    assert [e.classe for e in pd.ecarts(d0, faux, pd.lire_contexte(d0s, 1))] == ["K8b", None]
    sans_scission = pd.ecarts(d0, pro, pd.Contexte())
    assert ("receptions", None) in {(pd.motif(e.chemin), e.classe) for e in sans_scission}


# ── Comparaison et explication ────────────────────────────────────────────────────────


def test_les_tolerances_du_plan_de_recette() -> None:
    assert pc.egal("stock", 100.0, 100.0009) and not pc.egal("stock", 100.0, 100.0011)
    assert pc.egal("valeur_mad", 1e7, 1e7 + 9) and not pc.egal("valeur_mad", 10.0, 10.02)
    assert pc.egal("cmup_mad", 21.599, 21.599 * (1 + 5e-7))
    assert not pc.egal("prix_kg", 21.599, 21.599 * (1 + 2e-6))
    assert not pc.egal("rang", 3, 4) and not pc.egal("statut", "OK", "ok")
    assert not pc.egal("otif", 0.5, 0.500002)


def test_une_faute_injectee_se_voit_et_n_est_pas_excusee() -> None:
    """CMUP × 1,1 côté PRO : aucune traduction de la chaîne ne le redonne."""
    gmp = pc.ranger({"valorisation": [{"reference": "A", "cmup_mad": 20.0}]})
    pro = pc.ranger({"valorisation": [{"reference": "A", "cmup_mad": 22.0}]})
    k1 = pc.ranger({"valorisation": [{"reference": "A", "cmup_mad": 20.00001}]})
    ecarts = pc.comparer(gmp, pro).ecarts
    assert len(ecarts) == 1
    assert pc.expliquer(ecarts, [("K1", k1)])[0].classe is None
    juste = pc.ranger({"valorisation": [{"reference": "A", "cmup_mad": 22.0}]})
    assert pc.expliquer(ecarts, [("K1", k1), ("K9", juste)])[0].classe == "K9"


def test_un_element_en_plus_ou_en_moins_se_voit_par_sa_cle() -> None:
    gmp = pc.ranger({"stock": [{"reference": "A", "stock": 1.0}]})
    pro = pc.ranger({"stock": [{"reference": "A", "stock": 1.0}, {"reference": "B"}]})
    assert [e[0] for e in pc.comparer(gmp, pro).ecarts] == [("stock", "B")]


def test_une_paire_de_routes_traduit_renomme_ajoute_et_voit_la_reciproque() -> None:
    route = pa.Route("essai", "", "", liste=pa.Liste(
        ("id",), renommes={"article_id": "matiere_id"}, formes={"livraison": f.code},
        deplaces={"contact": "fiche du fournisseur"}))  # fmt: skip
    gmp = [{"id": 1, "article_id": 7, "livraison": "🟠 Partiel retard", "contact": "x",
            "perdu": 3}]  # fmt: skip
    pro = [{"id": 1, "matiere_id": 7, "livraison": "partiel_retard", "version": 2}]
    r = pa.comparer_route(route, gmp, pro)
    assert r.ajoutes == {"essai.version"} and r.deplaces == {
        "essai.contact": "fiche du fournisseur"
    }
    assert [(e.champ, e.classe) for e in r.ecarts] == [("perdu (absent de PRO)", None)]
    assert r.traduites["livraison"] == 1


def test_les_formes_declarees() -> None:
    assert f.instant("2026-01-30T10:07", "2026-01-30T09:07:31Z") == (
        "2026-01-30T10:07", "2026-01-30T10:07"
    )  # fmt: skip
    assert f.code("⚫ Soldé", "solde") == ("solde", "solde")
    assert f.code("⚫ Soldé", "livre")[0] != "livre"
    assert f.nul(0.0, None) == (None, None) and f.nul(1.0, None) == (1.0, None)
    assert f.surcout_en_pourcent(None, [{"surcout": 139.69}])[1] == [{"surcout_pct": 13969.0}]
    vue = f.pesee_comme_gestion_mp({"compare_au": "bl", "quantite_bl": 2571.3,
                                    "quantite_attendue": 3780.0, "ecart": -3.0})  # fmt: skip
    assert vue["quantite_attendue"] == 2571.3
    note = "lot à voir · cours du jour 9.5 figé à la clôture du 09/10/2026"
    assert f.note_de_cloture(note, "lot à voir") == ("lot à voir", "lot à voir")


def test_k3_ne_reconnait_que_les_lignes_d_un_inventaire_abandonne() -> None:
    route = pa.Route("", "", "")
    abandonne = {"statut": "abandonne", "nb_lignes": 0}
    ligne = pa.Ecart("i", "1 › 9", "(élément)", pc.ABSENT, {"id": 9}, element=abandonne)
    assert k3_inventaire_abandonne(route, ligne) == "K3"
    ligne.element = {"statut": "valide", "nb_lignes": 0}
    assert k3_inventaire_abandonne(route, ligne) is None


def test_un_geste_se_compare_par_ce_qu_il_change() -> None:
    """L'écart d'arrondi de la valeur de départ (K1) ne compte pas deux fois."""
    avant_g, apres_g = {"v": 100.0, "s": "OK"}, {"v": 130.0, "s": "OK"}
    avant_p = {"v": 100.004}
    assert attendu_pro(avant_p, avant_g, apres_g) == {"v": pytest.approx(130.004), "s": "OK"}


# ── Corrections faites dans PRO pendant la parité ─────────────────────────────────────


def test_la_famille_d_un_fil_dit_le_code_de_son_titrage() -> None:
    """Parité (dossiers, familles) : « PLASTIQUE 45 », comme Gestion MP, pas « PLASTIQUE 45 Cm »
    (le titrage est dit par son code, pas par sa valeur et son unité)."""
    from gestion_mp_pro.services.importations.socle import famille

    m = SimpleNamespace(composition_id=1, type_fil_id=None, titrage_id=1, reference="P45")
    titrage = SimpleNamespace(code="45", valeur="45", unite="Cm")
    assert famille(m, {1: "PLASTIQUE"}, {}, {1: titrage}) == "PLASTIQUE 45"  # type: ignore[arg-type]


def test_le_bilan_rend_la_perte_et_la_densite_de_ses_ordres() -> None:
    """Parité (réciproque, route 233) : `ecarts_ordres` rend ce que Gestion MP rendait —
    `taux_perte` de l'ordre, `kg_par_ml` de chaque fil (l'écran Sorties le lit ainsi)."""
    from gestion_mp_pro.api.suivi.schemas import BilanMois, EcartOrdreBilan

    ordre = {
        "numero_of": "OF-1", "consomme": 10.0, "retours": 0.0, "lots": [], "net": 10.0,
        "debut": date(2026, 3, 2), "fin": date(2026, 3, 2), "fabrications": [], "qualite": "",
        "m2": 0.0, "commentaire": "", "theorique": 9.0, "taux_perte_fige": None, "ecart": 1.0,
        "ecart_relatif": 0.1, "taux_perte": 0.02,
        "references": [{"reference": "R", "quantite": 10.0, "theorique": 9.0, "ecart": 1.0,
                        "hors_recette": False, "kg_par_ml": 0.014}],
    }  # fmt: skip
    lu = EcartOrdreBilan.model_validate(ordre).model_dump()
    assert lu["taux_perte"] == 0.02 and lu["references"][0]["kg_par_ml"] == 0.014
    assert "EcartOrdreBilan" in str(BilanMois.model_fields["ecarts_ordres"].annotation)


def test_K9_les_prix_d_une_date_passee_sont_ceux_connus_ce_jour_la(usine: Usine) -> None:
    """K9 (D8 n° 6) : opportunités et économies du Cockpit à une date passée ne lisent que les
    réceptions jusqu'à cette date — Gestion MP lisait aussi les prix payés après (défaut
    signalé par la parité)."""
    from gestion_mp_pro.services.pilotage import lignes_recues

    u = usine
    f_ = u.fournisseur("K9 FILATURE")
    m = u.matiere("K9 FIL", fournisseur_id=f_)
    for le, lot in ((-10, "K9-1"), (0, "K9-2")):
        r = ok(u.achats.post("/api/receptions", json={
            "date": jour(le).isoformat(), "fournisseur_id": f_, "lignes": [
                {"matiere_id": m, "lot_numero": lot, "quantite_pesee": 100,
                 "magasin_id": u.courant, "prix": 2 + le / 100,
                 "devise": "MAD"}]}), 201)[0]  # fmt: skip
        ok(u.achats.post(f"/api/receptions/{r['id']}/valider", json={"version": r["version"]}))
    avant = [x for x in lignes_recues(u.s, jour(-5)) if x.reference == "K9 FIL"]
    tout = [x for x in lignes_recues(u.s, jour(0)) if x.reference == "K9 FIL"]
    assert [x.jour for x in avant] == [jour(-10)] and len(tout) == 2


# ── Complet : l'année d'essai ─────────────────────────────────────────────────────────


@pytest.mark.complet
@pytest.mark.skipif(not reglages().essais_complets, reason="GESTIONMPPRO_ESSAIS_COMPLETS=1")
def test_parite_sur_l_annee_d_essai(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A6 : à corriger 0 aux 19 dates, par l'API, en dynamique et pour K7 (bases d'essai au nom
    de la base d'essai, supprimées ensuite)."""
    import parite_gestion_mp

    nom = make_url(os.environ["GESTIONMPPRO_BASE"]).database or "gestion_mp_pro_essai"
    monkeypatch.setenv("GESTIONMPPRO_PARITE_PREFIXE", f"{nom.removesuffix('_essai')}_parite")
    sortie = tmp_path / "parite.txt"
    debut = datetime.now()  # noqa: DTZ005
    assert parite_gestion_mp.main(["--sortie", str(sortie)]) == 0, sortie.read_text()[-4000:]
    assert "À CORRIGER : 0" in sortie.read_text() and (datetime.now() - debut).seconds < 1800  # noqa: DTZ005
