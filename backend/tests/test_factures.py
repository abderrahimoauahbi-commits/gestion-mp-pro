"""Factures et camions en deux devises (lot D4) : une réception par devise en une seule
transaction (A-09), une facture n'a qu'une devise, elle se complète après la validation, une
réception ne réécrit pas une facture engagée (A-04), le règlement et son annulation par la
direction avec motif (A-21, B-01), la liste des factures (175). Preuves héritées de
`test_achats`, `test_commandes_receptions`, `test_audit2_achats` (domaines 5 et 7).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat, reglage
from fabriques.importations import ouvrir_facture
from fabriques.receptions import (
    JOUR,
    Quai,
    acteur,
    camion,
    camions,
    facture,
    fiche,
    geste,
    j,
    ligne_du_bon,
    menage,  # noqa: F401 — fixture du module
    ok,
    parti,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Facture, Journal, Reception
from gestion_mp_pro.services import factures

pytestmark = pytest.mark.usefixtures("menage")


@pytest.fixture
def eur() -> Achat:
    """Une filature turque en euros, paiement à 60 jours."""
    return Achat.nouveau(devise="EUR", delai=45, pays="TURKEY", delai_paiement_jours=60)


@pytest.fixture
def quai() -> Quai:
    """Un magasin de rangement à soi."""
    return Quai.nouveau()


def _hc(m: int, quai: Quai, lot: str, kg: float = 5, **x: object) -> dict[str, object]:
    """Une ligne hors commande."""
    return {
        "matiere_id": m,
        "lot_numero": lot,
        "quantite_pesee": kg,
        "magasin_id": quai.courant,
        **x,
    }


def _brouillons() -> int:
    with sessions()() as s:
        return int(s.scalar(select(func.count()).select_from(Reception)) or 0)


def test_une_reception_en_deux_devises_s_enregistre_d_un_coup(
    achats: TestClient, eur: Achat, quai: Quai
) -> None:
    """A-09 (Gestion MP corrigé) : un camion qui apporte un bon en EUR et un bon en USD donne
    deux réceptions (même BL, même date), chacune avec sa facture, en une requête ; si la
    seconde est refusée, aucune n'est enregistrée."""
    m_eur, m_usd = eur.matiere("CAMION-EUR"), eur.matiere("CAMION-USD", prix="2", devise="USD")
    b_eur, b_usd = parti(achats, eur, {m_eur: 100}), parti(achats, eur, {m_usd: 200})
    assert b_usd["devise"] == "USD"
    lignes = [
        ligne_du_bon(b_eur, m_eur, 100, "E-1", magasin_id=quai.courant),
        ligne_du_bon(b_usd, m_usd, 200, "U-1", magasin_id=quai.courant),
    ]
    avant = _brouillons()
    refus = camion(achats, eur.fournisseur_id, lignes, 422, numero_bl="BL-2D",
                   factures={"usd": {"numero": "F-U", "date": "2026-10-09"}})  # fmt: skip
    assert "futur" in refus["detail"] and _brouillons() == avant
    faites = camions(
        achats,
        eur.fournisseur_id,
        lignes,
        numero_bl="BL-2D",
        factures={
            "EUR": {"numero": "F-E", "montant": 300},
            "USD": {"numero": "F-U", "montant": 400},
        },
    )
    assert [r["devise"] for r in faites] == ["EUR", "USD"]
    assert {r["numero_bl"] for r in faites} == {"BL-2D"} and {r["date"] for r in faites} == {j()}
    assert [r["facture"]["numero"] for r in faites] == ["F-E", "F-U"]
    assert [r["facture"]["devise"] for r in faites] == ["EUR", "USD"]


def test_une_reception_ne_mele_pas_deux_devises(achats: TestClient, eur: Achat, quai: Quai) -> None:
    """Hérité : test_achats::test_une_reception_ne_mele_pas_deux_devises — une réception = une
    devise (la correction d'un brouillon le refuse) ; une facture = une devise."""
    gris, usd = eur.matiere("GRIS"), eur.matiere("USD", prix="2", devise="USD")
    corps = {"date": j(), "fournisseur_id": eur.fournisseur_id}
    r = camion(achats, eur.fournisseur_id, [_hc(gris, quai, "D1")])
    mixte = [_hc(gris, quai, "D1"), _hc(usd, quai, "D2", devise="USD")]
    refus = achats.put(
        f"/api/receptions/{r['id']}", json=corps | {"version": r["version"], "lignes": mixte}
    )
    assert refus.status_code == 422 and "deux devises" in refus.json()["detail"]
    refus = camion(achats, eur.fournisseur_id, [_hc(gris, quai, "D3")], 422,
                   factures={"USD": {"numero": "F-EUR-1", "montant": 14}})  # fmt: skip
    assert "en EUR" in refus["detail"]
    r = camion(achats, eur.fournisseur_id, [_hc(gris, quai, "D3")],
               factures={"EUR": {"numero": "F-EUR-1", "montant": 14}})  # fmt: skip
    assert r["devise"] == "EUR" and r["facture"]["devise"] == "EUR"
    refus = camion(achats, eur.fournisseur_id, [_hc(usd, quai, "D4", devise="USD")], 422,
                   factures={"USD": {"numero": "F-EUR-1"}})  # fmt: skip
    assert "une devise" in refus["detail"]


def test_la_facture_se_complete_apres_la_validation(
    achats: TestClient, eur: Achat, quai: Quai
) -> None:
    """Hérité : test_achats::test_la_facture_se_complete_apres_la_validation — échéance avant la
    facture : 422 ; défaut : date + 60 j ; 224 → 230 et échéance choisie ; numéro vide :
    détachée ; réception annulée : 409. Un brouillon porte sa facture dans sa saisie."""
    r = camion(achats, eur.fournisseur_id, [_hc(eur.matiere("GRIS"), quai, "G-F", 80)])
    assert facture(achats, r, 409, numero="F-1")["detail"].startswith("Un brouillon porte")
    r = geste(achats, r, "valider")
    assert r["facture"] is None
    assert (
        facture(achats, r, 422, numero="F-1", date=j(), echeance=j(-1))["code"] == "date_invalide"
    )
    r = facture(achats, r, numero="F-1", date=j(), montant=224)
    assert r["facture"]["numero"] == "F-1" and r["facture"]["montant"] == 224
    assert r["facture"]["echeance"] == (JOUR + timedelta(days=60)).isoformat()
    r = facture(achats, r, montant=230, echeance=j(1))
    assert r["facture"]["montant"] == 230 and r["facture"]["echeance"] == j(1)
    assert r["facture"]["date"] == j()  # absent : inchangé
    r = facture(achats, r, numero="")
    assert r["facture"] is None
    geste(achats, r, "annuler", motif="erreur de saisie")
    assert facture(achats, r, 409, numero="F-2")["detail"] == (
        "Cette réception est annulée : sa facture ne se modifie plus."
    )


def _regler(fid: int, payee_le: date | None, role: str = "achats", motif: str = "") -> None:
    """Le règlement par le service (la route 229 est au lot D8)."""
    with sessions()() as s, s.begin():
        version = s.get_one(Facture, fid).version
        factures.regler(s, acteur(role), fid, payee_le=payee_le, version=version, motif=motif)


def test_une_reception_ne_reecrit_pas_une_facture_reglee(
    achats: TestClient, eur: Achat, quai: Quai
) -> None:
    """A-04 (Gestion MP corrigé, test_defauts_a) : un second camion de la facture l'attache sans
    la réécrire ; réglée, elle ne se corrige plus (« annuler d'abord le règlement ») ; portée par
    un dossier clos, non plus ; d'un dossier ouvert, pas dans un mois clos."""
    m = eur.matiere("REGLEE")
    r = geste(achats, camion(achats, eur.fournisseur_id, [_hc(m, quai, "R-1", 100)],
                             factures={"EUR": {"numero": "F-R", "date": j(), "montant": 500}}),
              "valider")  # fmt: skip
    fid = r["facture"]["id"]
    _regler(fid, JOUR)
    r2 = camion(achats, eur.fournisseur_id, [_hc(m, quai, "R-2", 10)],
                factures={"EUR": {"numero": "F-R", "montant": 999}})  # fmt: skip
    assert r2["facture"]["id"] == fid and r2["facture"]["montant"] == 500
    refus = facture(achats, r, 409, montant=300)
    assert refus["detail"] == (
        "La facture F-R est réglée le 31/12/2025 : annuler d'abord le règlement (Analyse › "
        "Échéancier), puis la corriger."
    )
    r3 = geste(achats, camion(achats, eur.fournisseur_id, [_hc(m, quai, "R-3", 10)],
                              factures={"EUR": {"numero": "F-D", "date": j(), "montant": 50}}),
               "valider")  # fmt: skip
    d = ouvrir_facture(achats, r3["facture"]["id"], clos=True)
    refus = facture(achats, r3, 409, montant=60)
    assert "clos : la corriger depuis le dossier" in refus["detail"]
    assert refus["code"] == "dossier_clos" and d
    r4 = geste(achats, camion(achats, eur.fournisseur_id, [_hc(m, quai, "R-4", 10)],
                              factures={"EUR": {"numero": "F-O", "date": j(), "montant": 50}}),
               "valider")  # fmt: skip
    ouvrir_facture(achats, r4["facture"]["id"])
    with reglage("date_cloture", j()):
        refus = facture(achats, r4, 409, montant=70)
    assert (
        refus["code"] == "cout_periode_close"
        and "(correction de la facture F-O refusé)" in refus["detail"]
    )
    refus = facture(achats, r4, 409, numero="F-AUTRE")
    assert "son numéro, non" in refus["detail"] and "Détacher la réception" in refus["detail"]
    refus = geste(achats, r4, "annuler", 409, motif="erreur")
    assert refus["detail"].startswith("Cette réception est dans le dossier d'importation")
    assert fiche(achats, r4["id"])["actions"]["annuler"] == refus["detail"]


def test_journal_facture_nombre_francais(achats: TestClient, eur: Achat, quai: Quai) -> None:
    """A-28 (Gestion MP corrigé) : le journal dit « 1 234,50 EUR », pas « 1,234.50 »."""
    r = geste(achats, camion(achats, eur.fournisseur_id, [_hc(eur.matiere("J"), quai, "J-1")]),
              "valider")  # fmt: skip
    facture(achats, r, numero="F-J", montant=1234.5)
    with sessions()() as s:
        detail = s.scalar(
            select(Journal.detail)
            .where(
                Journal.objet == "reception",
                Journal.objet_id == r["id"],
                Journal.action == "facture complétée",
            )  # fmt: skip
            .order_by(Journal.id.desc())
        )
    assert detail is not None and detail.endswith("facture F-J · 1 234,50 EUR")


def test_un_reglement_s_annule_par_la_direction_avec_un_motif(
    achats: TestClient, eur: Achat, quai: Quai
) -> None:
    """A-21, B-01 (Gestion MP corrigé) ; hérité : test_commandes_receptions::test_l_echeancier_suit_les_paiements
    (partie règlement) et test_audit2_achats::test_une_facture_reglee_dont_la_reception_est_annulee_reste_visible
    (paiement pas avant la facture). Ni dans le futur, ni avant la pièce, ni en période close."""  # noqa: E501
    r = geste(achats, camion(achats, eur.fournisseur_id, [_hc(eur.matiere("PAIE"), quai, "P-1")],
                             factures={"EUR": {"numero": "F-P", "date": j(-10), "montant": 20}}),
              "valider")  # fmt: skip
    fid = r["facture"]["id"]
    for jour, code in (
        (JOUR + timedelta(days=400), "date_future"),
        (date(2001, 1, 1), "date_invalide"),
    ):
        with pytest.raises(Refus) as refus:
            _regler(fid, jour)
        assert refus.value.code == code
    with reglage("date_cloture", j(-1)), pytest.raises(Refus) as refus:
        _regler(fid, JOUR - timedelta(days=5))
    assert refus.value.code == "periode_close"
    _regler(fid, JOUR)
    with pytest.raises(Refus) as refus:
        _regler(fid, None)
    assert refus.value.http == 403 and "ne s'annule que par la direction" in refus.value.detail
    with pytest.raises(Refus) as refus:
        _regler(fid, None, "direction")
    assert refus.value.code == "motif_requis"
    _regler(fid, None, "direction", "virement rejeté par la banque")
    with sessions()() as s:
        assert s.get_one(Facture, fid).payee_le is None
        ligne = s.scalars(
            select(Journal)
            .where(Journal.objet == "facture", Journal.objet_id == fid)
            .order_by(Journal.id.desc())  # fmt: skip
        ).first()
        assert ligne is not None and ligne.action == "règlement annulé"
        assert ligne.detail == "motif : virement rejeté par la banque"
    with sessions()() as s, s.begin(), pytest.raises(Refus) as refus:
        factures.regler(s, acteur(), fid, payee_le=JOUR, version=1)
    assert refus.value.code == "conflit_version"


def test_les_factures_se_listent_avec_leurs_receptions(
    achats: TestClient, eur: Achat, quai: Quai
) -> None:
    """Route 175 : réceptions, ce qu'elles ont apporté (pesée × prix), dossier ; filtres
    fournisseur, recherche et « sans dossier »."""
    m = eur.matiere("LISTE", prix="2.5")
    r = geste(achats, camion(achats, eur.fournisseur_id, [_hc(m, quai, "LI-1", 100)],
                             factures={"EUR": {"numero": "FA-2026/117"}}), "valider")  # fmt: skip
    vues = ok(achats.get("/api/factures", params={"fournisseur": eur.fournisseur_id}))
    x = next(f for f in vues if f["numero"] == "FA-2026/117")
    assert x["montant"] is None and x["montant_estime"] == 250 and x["poids"] == 100
    assert [y["numero"] for y in x["receptions"]] == [r["numero"]] and x["dossier"] is None
    assert ok(achats.get("/api/factures", params={"q": "fa 2026 117"}))[0]["id"] == x["id"]
    d = ouvrir_facture(achats, x["id"])
    sans = ok(achats.get("/api/factures", params={"fournisseur": eur.fournisseur_id,
                                                  "sans_dossier": True}))  # fmt: skip
    assert x["id"] not in {f["id"] for f in sans}
    avec = ok(achats.get("/api/factures", params={"fournisseur": eur.fournisseur_id}))
    assert next(f for f in avec if f["id"] == x["id"])["dossier"]["numero"] == d["numero"]
    assert Decimal(str(x["montant_estime"])) == Decimal("250")
