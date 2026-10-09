"""Routes des lots (lot S4) : liste et statut (107), fiche et commentaire (108, 109), scan
(110), lots disponibles à une date (111), traçabilité (112), contrôle des soldes (113).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fabrique import *  # noqa: F403
from fabriques.stock import (
    autre_magasin,
    entree,
    jour,
    lot,
    magasin,
    matiere,
    sortie,
    unique,
)
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles.enums import DocumentMouvement, TypeMagasin, TypeMouvement
from gestion_mp_pro.services import stock


@pytest.fixture
def base() -> Iterator[Session]:
    """Une session dont les écritures sont validées."""
    with fabrique()() as s:
        yield s


def test_lots_historique_statut_et_tracabilite(base: Session, direction: TestClient) -> None:
    """Routes 107, 112. Hérité : test_stock_atelier::test_lots_historique_statut_et_tracabilite —
    entré 500, sorti 100 (net des retours), disponible ; la traçabilité dit les mêmes totaux ;
    une annulation et la ligne annulée ne comptent pas, un transfert non plus."""
    m = matiere(base, unique("Fil suivi"))
    x = lot(base, m, numero="E-L1", entre_le=jour(-3))
    entree(base, x, 500, jour(-3))
    sortie(base, x, 120, jour(-2))
    entree(base, x, 20, jour(-1), type=TypeMouvement.RETOUR_MACHINE)
    annulee = sortie(base, x, 7, jour(-1))
    stock.contrepasser_mouvements(base, [annulee], None)
    q = magasin(base, TypeMagasin.quarantaine)
    stock.transferer(
        base, lot=x, source_id=magasin(base).id, destination_id=q.id, quantite=50, jour=jour(0),
        piece=stock.Piece(DocumentMouvement.reprise), auteur_id=None,
    )  # fmt: skip
    base.commit()
    (ligne,) = direction.get("/api/lots", params={"matiere": m.id}).json()
    assert (ligne["lot"], ligne["quantite"], ligne["disponible"], ligne["quarantaine"]) == (
        "E-L1", 400, 350, 50,
    )  # fmt: skip
    assert ligne["statut"] == "partiel"
    assert (ligne["historique"]["entre"], ligne["historique"]["sorti"]) == (500, 100)
    assert ligne["historique"]["dernier_mouvement"] == jour(0).isoformat()
    assert direction.get("/api/lots", params={"matiere": m.id, "statut": "epuise"}).json() == []
    t = direction.get("/api/tracabilite", params={"lot": x.id}).json()
    assert (t["entrees"], t["sorties"], t["lot"]) == (500, 100, "E-L1")
    libelles = [e["libelle"] for e in t["mouvements"]]
    assert "Annulation — sortie vers les machines" in libelles
    assert direction.get("/api/tracabilite").status_code == 422
    assert direction.get("/api/tracabilite", params={"lot": 999_999}).status_code == 404


def test_fiche_de_lot_et_commentaire(
    base: Session, direction: TestClient, achats: TestClient, alimentation: TestClient
) -> None:
    """Routes 108, 109 : la fiche ; le commentaire (D, A) avec la version lue ; une version
    périmée → 409 qui nomme l'auteur ; l'alimentation n'écrit pas ; lot inconnu → 404."""
    m = matiere(base, unique("Fil commenté"))
    x = lot(base, m, poids_bobine="2.5")
    entree(base, x, 100)
    base.commit()
    f = direction.get(f"/api/lots/{x.id}").json()
    assert (f["lot_id"], f["version"], f["commentaire"], f["bobines"]) == (x.id, 1, "", 40)
    assert [mvt["quantite"] for mvt in f["mouvements"]] == [100]
    r = achats.put(f"/api/lots/{x.id}", json={"commentaire": "Palette abîmée", "version": 1})
    assert r.status_code == 200, r.text
    assert (r.json()["commentaire"], r.json()["version"]) == ("Palette abîmée", 2)
    perime = direction.put(f"/api/lots/{x.id}", json={"commentaire": "Autre", "version": 1})
    assert (perime.status_code, perime.json()["code"]) == (409, "conflit_version")
    assert "modifié entre-temps par Achats" in perime.json()["detail"]
    assert (
        alimentation.put(f"/api/lots/{x.id}", json={"commentaire": "x", "version": 2}).status_code
        == 403
    )
    assert direction.get("/api/lots/999999").status_code == 404
    historique = direction.get(f"/api/historique/lot/{x.id}").json()
    assert historique[0]["apres"] == {"commentaire": "Palette abîmée"}


def test_scan_d_une_etiquette(base: Session, alimentation: TestClient) -> None:
    """Route 110. Hérité : test_parcours::test_l_etiquette_porte_un_qr (scan) — l'adresse de
    l'étiquette ou le numéro tapé (sans la casse) ; rien → 404 « Lot introuvable. »."""
    m = matiere(base, unique("Fil scanné"))
    x = lot(base, m, numero=unique("SCAN"))
    entree(base, x, "12.5")
    base.commit()
    (trouve,) = alimentation.get(
        "/api/lots/scan", params={"code": f"http://x:8050/lot/{x.id}"}
    ).json()
    assert (trouve["lot_id"], trouve["quantite"]) == (x.id, 12.5)
    assert (
        alimentation.get("/api/lots/scan", params={"code": x.numero.lower()}).json()[0]["lot_id"]
        == x.id
    )
    r = alimentation.get("/api/lots/scan", params={"code": "INCONNU-0"})
    assert (r.status_code, r.json()["detail"]) == (404, "Lot introuvable.")


def test_lots_disponibles_a_une_date(base: Session, alimentation: TestClient) -> None:
    """Route 111. Hérités :
    test_audit2_atelier::test_la_proposition_ne_prend_que_les_lots_presents_a_la_date
    (aujourd'hui [VIEUX, NEUF], hier [VIEUX]) ;
    test_audit2_atelier::test_le_disponible_a_une_date_tient_compte_de_ce_qui_est_sorti_depuis
    (500 hier, −480 aujourd'hui : hier 20 ; J−3 : rien). La quarantaine n'est jamais proposée."""
    m = matiere(base, unique("Fil FIFO"))
    vieux, neuf = lot(base, m, "VIEUX", jour(-5)), lot(base, m, "NEUF", jour(0))
    entree(base, vieux, 500, jour(-1))
    sortie(base, vieux, 480, jour(0))
    entree(base, neuf, 100, jour(0))
    entree(
        base,
        lot(base, m, "BLOQUE", jour(-5)),
        30,
        jour(-5),
        g=magasin(base, TypeMagasin.quarantaine),
    )
    autre = autre_magasin(base)
    base.commit()

    def lots_(**params: object) -> list[tuple[str, float]]:
        r = alimentation.get("/api/lots/disponibles", params={"matiere": m.id, **params})
        assert r.status_code == 200, r.text
        return [(x["lot"], x["quantite"]) for x in r.json()]

    assert lots_() == [("VIEUX", 20), ("NEUF", 100)]
    assert lots_(date=jour(-1).isoformat()) == [("VIEUX", 20)]
    assert lots_(date=jour(-3).isoformat()) == []
    assert lots_(magasin=autre.id) == []


def test_controle_des_soldes(
    direction: TestClient, achats: TestClient, alimentation: TestClient
) -> None:
    """Route 113 (D, A) : les soldes égalent le journal. Hérité :
    test_parcours::test_les_soldes_egalent_le_journal."""
    r = achats.get("/api/controles/soldes")
    assert r.status_code == 200, r.text
    assert (r.json()["conforme"], r.json()["ecarts"], r.json()["negatifs"]) == (True, [], 0)
    assert alimentation.get("/api/controles/soldes").status_code == 403
    assert direction.get("/api/controles/soldes").json()["lots"] > 0
