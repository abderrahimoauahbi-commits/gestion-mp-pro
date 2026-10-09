"""Les pièces jointes (lot D8 ; routes 224–227, défaut G-10, décision X4 « .exe refusé »).

Dépôt multipart, liste blanche (type, extension, premiers octets), 20 Mo lus par blocs, chemin
relatif sous le dossier des pièces de cette base (temporaire pour la séance : conftest), aucune
traversée de chemin, `attachment`, retrait logique, 404 / 410.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques import importations as imp
from fabriques.referentiels import fournisseur
from fastapi.testclient import TestClient

from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Journal, PieceJointe

PDF = b"%PDF-1.4 essai"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def deposer(  # noqa: PLR0917 — un dépôt se lit dans l'ordre du formulaire
    client: TestClient, objet: str, ident: int, nom: str, contenu: bytes, genre: str
) -> Any:
    """`POST /pieces` (multipart)."""
    return client.post(
        "/api/pieces",
        data={"objet": objet, "id": str(ident)},
        files={"fichier": (nom, contenu, genre)},
    )


def lister(client: TestClient, objet: str, ident: int) -> list[dict[str, Any]]:
    """Les pièces d'un document."""
    r = client.get("/api/pieces", params={"objet": objet, "id": ident})
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def ok(r: Any, code: int = 200) -> Any:
    """Le code attendu, puis le JSON."""
    assert r.status_code == code, r.text
    return r.json() if r.content else None


def test_une_piece_jointe_se_depose_et_se_relit(achats: TestClient) -> None:
    """Hérité : test_suivi::test_une_piece_jointe_se_depose_et_se_relit ;
    test_defauts_g::test_piece_jointe_chemin_relatif — chemin relatif `fournisseur/{id}/…`,
    fichier relu en `attachment`, empreinte SHA-256 gardée ; un .exe est refusé."""
    fid = fournisseur()
    p = ok(deposer(achats, "fournisseur", fid, "contrat.pdf", PDF, "application/pdf"), 201)
    assert (p["nom"], p["type"], p["taille"], p["par"]) == (
        "contrat.pdf",
        "application/pdf",
        14,
        "Achats",
    )
    assert p["empreinte"] == hashlib.sha256(PDF).hexdigest()
    assert [x["nom"] for x in lister(achats, "fournisseur", fid)] == ["contrat.pdf"]
    r = achats.get(f"/api/pieces/{p['id']}/fichier")
    assert r.content == PDF and r.headers["content-disposition"].startswith("attachment")
    with sessions()() as s:
        chemin = s.get(PieceJointe, p["id"]).chemin  # type: ignore[union-attr]
    assert not Path(chemin).is_absolute() and chemin.startswith(f"fournisseur/{fid}/")
    assert (reglages().dossier_pieces / chemin).read_bytes() == PDF
    refus = deposer(achats, "fournisseur", fid, "x.exe", b"MZ", "application/x-msdownload")
    assert refus.status_code == 422 and refus.json()["code"] == "fichier_refuse"


@pytest.mark.parametrize(
    ("nom", "contenu", "genre"),
    [
        ("outil.exe", b"MZ\x90\x00", "application/pdf"),
        ("outil.exe", b"MZ\x90\x00", "application/vnd.microsoft.portable-executable"),
        ("facture.pdf", b"MZ\x90\x00 programme", "application/pdf"),
        ("script.pdf", b"#!/bin/sh\nrm -rf /", "application/pdf"),
        ("dessin.svg", b"<svg/>", "image/svg+xml"),
        ("macro.xlsm", b"PK\x03\x04", "application/vnd.ms-excel.sheet.macroEnabled.12"),
        ("page.html", b"<html>", "text/plain"),
        ("photo.jpg", b"PK\x03\x04 pas une image", "image/jpeg"),
        ("vide.pdf", b"", "application/pdf"),
    ],
)
def test_piece_exe_refusee(achats: TestClient, nom: str, contenu: bytes, genre: str) -> None:
    """Hérité : test_defauts_g::test_piece_exe_refusee (G-10) — type faux, programme déguisé,
    SVG, macros, HTML, contenu d'un autre type, fichier vide : 422, rien de joint."""
    fid = fournisseur()
    r = deposer(achats, "fournisseur", fid, nom, contenu, genre)
    assert r.status_code == 422, r.text
    assert lister(achats, "fournisseur", fid) == []


def test_les_documents_de_bureau_entrent(achats: TestClient) -> None:
    """Hérité : test_defauts_g::test_les_documents_de_bureau_entrent — tableur, document
    (type inconnu du navigateur : l'extension le dit), image, texte."""
    fid = fournisseur()
    for nom, contenu, genre in (
        ("tarif.xlsx", b"PK\x03\x04", XLSX),
        ("lettre.docx", b"PK\x03\x04", "application/octet-stream"),
        ("photo.JPG", b"\xff\xd8\xff\xe0 JFIF", "image/jpeg"),
        ("liste.csv", b"ref;kg\nA;1\n", "application/vnd.ms-excel"),
        ("note.txt", "Écru, 12 kg".encode(), "text/plain"),
    ):
        ok(deposer(achats, "fournisseur", fid, nom, contenu, genre), 201)
    assert len(lister(achats, "fournisseur", fid)) == 5


def test_piece_trop_lourde_refusee_sans_tout_lire(achats: TestClient) -> None:
    """Hérité : test_defauts_g::test_piece_trop_lourde_refusee_sans_tout_lire — au-delà de
    20 Mo : 422 « trop lourd », ni fichier ni reste partiel sur le disque."""
    fid = fournisseur()
    lourd = b"%PDF" + b"0" * (20 * 1024 * 1024)
    r = deposer(achats, "fournisseur", fid, "gros.pdf", lourd, "application/pdf")
    assert r.status_code == 422 and "trop lourd" in r.json()["detail"]
    assert r.json()["code"] == "fichier_trop_gros"
    dossier = reglages().dossier_pieces / "fournisseur" / str(fid)
    assert not dossier.exists() or not any(dossier.iterdir())


def test_aucune_traversee_de_chemin(achats: TestClient) -> None:
    """Un nom « ../../… » ne sert qu'à l'affichage (sans chemin) ; le fichier est rangé sous
    le dossier du document, sous un nom tiré au hasard."""
    fid = fournisseur()
    p = ok(
        deposer(achats, "fournisseur", fid, "../../../etc/passwd.pdf", PDF, "application/pdf"), 201
    )
    assert p["nom"] == "passwd.pdf"
    with sessions()() as s:
        chemin = s.get(PieceJointe, p["id"]).chemin  # type: ignore[union-attr]
    assert ".." not in chemin and chemin.startswith(f"fournisseur/{fid}/")


def test_piece_disparue_410_retiree_404_objet_inconnu_404(
    achats: TestClient, alimentation: TestClient
) -> None:
    """Hérité : test_defauts_g::test_piece_disparue_410_et_objet_inconnu_404 — fichier effacé du
    disque : 410 ; document inconnu : 404 ; retrait logique (journal, fichier gardé) puis 404 ;
    l'alimentation ne voit aucune pièce."""
    fid = fournisseur()
    p = ok(deposer(achats, "fournisseur", fid, "d.pdf", PDF, "application/pdf"), 201)
    q = ok(deposer(achats, "fournisseur", fid, "e.pdf", PDF, "application/pdf"), 201)
    with sessions()() as s:
        chemin = reglages().dossier_pieces / s.get(PieceJointe, p["id"]).chemin  # type: ignore[union-attr]
    chemin.unlink()
    r = achats.get(f"/api/pieces/{p['id']}/fichier")
    assert r.status_code == 410 and r.json()["detail"].endswith("la redéposer.")
    assert achats.get("/api/pieces", params={"objet": "inconnu", "id": 1}).status_code == 404
    assert (
        achats.get("/api/pieces", params={"objet": "fournisseur", "id": 999999}).status_code == 404
    )
    assert deposer(achats, "commande", 999999, "a.pdf", PDF, "application/pdf").status_code == 404
    assert achats.delete(f"/api/pieces/{q['id']}").status_code == 204
    assert achats.delete(f"/api/pieces/{q['id']}").status_code == 409
    assert achats.get(f"/api/pieces/{q['id']}/fichier").status_code == 404
    assert [x["id"] for x in lister(achats, "fournisseur", fid)] == [p["id"]]
    with sessions()() as s:
        retiree = s.get(PieceJointe, q["id"])
        assert retiree is not None and retiree.retiree_le is not None
        assert (reglages().dossier_pieces / retiree.chemin).is_file()
        assert s.query(Journal).filter_by(action="pièce retirée", objet_id=fid).count() == 1
    for appel in (
        alimentation.get("/api/pieces", params={"objet": "fournisseur", "id": fid}),
        alimentation.get(f"/api/pieces/{p['id']}/fichier"),
        alimentation.delete(f"/api/pieces/{p['id']}"),
        deposer(alimentation, "fournisseur", fid, "a.pdf", PDF, "application/pdf"),
    ):
        assert appel.status_code == 403


def test_documents_du_dossier(achats: TestClient, alimentation: TestClient) -> None:
    """Hérité : test_importations::test_documents_du_dossier (laissé par D7) — la DUM d'un vrai
    dossier se joint, se relit, se retire ; la fiche du dossier compte ses pièces."""
    i = imp.Import.nouveau(cours="10")
    i.recevoir(achats, "DOC-D8", [("FIL", "DOC-1", 10, 2.0)])
    d = imp.ouvrir(achats, i.f("DOC-D8"), local_confirme=True)
    p = ok(deposer(achats, "dossier", d["id"], "DUM-2026-118.pdf", PDF, "application/pdf"), 201)
    assert [x["nom"] for x in lister(achats, "dossier", d["id"])] == ["DUM-2026-118.pdf"]
    assert imp.fiche(achats, d["id"])["nb_pieces"] == 1
    assert achats.get(f"/api/pieces/{p['id']}/fichier").content == PDF
    assert (
        alimentation.get("/api/pieces", params={"objet": "dossier", "id": d["id"]}).status_code
        == 403
    )
    assert achats.delete(f"/api/pieces/{p['id']}").status_code == 204
    assert lister(achats, "dossier", d["id"]) == []
