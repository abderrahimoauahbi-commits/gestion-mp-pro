"""Une commande livrée en plusieurs camions (décision de Mohamed du 12/10/2026,
docs/lots/LIVRAISON-PARTIELLE.md) : choisir le bon reprend toutes ses lignes restantes ; celles
que le camion n'a pas apportées, laissées vides, ne bloquent rien, sont retirées à la validation
et restent dues sur le bon. Une ligne de bon à moitié remplie, ou une ligne hors bon vide, garde
les blocages d'avant (X-RCP-B5, B6, B8 mot pour mot).
"""

from __future__ import annotations

from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat
from fabriques.importations import Import, frais, ouvrir
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
)
from fabriques.receptions import facture as facture_reception
from fabriques.referentiels import unique
from fastapi.testclient import TestClient

from gestion_mp_pro.services.receptions_non_livrees import RIEN_N_EST_PESE

RIEN = (
    "Rien n'est pesé : saisir ce que le camion a apporté (les lignes laissées vides restent "
    "dues sur le bon)."
)
"""La phrase, écrite en clair : l'écran dit la même (calculSaisie.ts)."""


@pytest.fixture
def imp() -> Achat:
    """Un fournisseur belge dans une devise à soi (cours 10) : ses factures ouvrent un dossier."""
    return Achat.nouveau(devise=Import.nouveau(cours="10").devise, pays="BELGIUM")


@pytest.fixture
def quai() -> Quai:
    """Un magasin de rangement à soi."""
    return Quai.nouveau()


def _vide(b: dict[str, Any], m: int, **autres: Any) -> dict[str, Any]:
    """La ligne d'un bon reprise par la saisie et laissée vide (ce camion ne l'a pas apportée)."""
    x = next(x for x in b["lignes"] if x["matiere_id"] == m)
    return {"commande_ligne_id": x["id"], "matiere_id": m, **autres}


def _reste(b: dict[str, Any], m: int) -> float:
    return next(x["reste"] for x in b["lignes"] if x["matiere_id"] == m)  # type: ignore[no-any-return]


def _trois(imp: Achat) -> tuple[int, int, int]:
    return imp.matiere("ROUGE", prix="2"), imp.matiere("VERT", prix="2"), imp.matiere("BLEU")


def test_un_bon_livre_en_deux_camions_puis_deux_dossiers(
    achats: TestClient, direction: TestClient, imp: Achat, quai: Quai
) -> None:
    """Le cas de Mohamed : un bon de 3 lignes ; le 1er camion n'apporte que la ligne 1 (2 et 3
    vides, facture F1 dans le brouillon) → validé, 2 et 3 retirées, toujours dues, bon partiel ;
    le 2e camion apporte 2 et 3 (facture complétée après validation) → bon soldé ; un dossier
    par facture, des droits de douane sur le premier."""
    rouge, vert, bleu = _trois(imp)
    b = parti(achats, imp, {rouge: 1000, vert: 600, bleu: 400}, prix=2)
    f1, f2 = unique("PART-1"), unique("PART-2")
    lignes = [
        ligne_du_bon(b, rouge, 1000, unique("R"), quantite_bl=1000, magasin_id=quai.courant),
        _vide(b, vert, observations="pas dans ce camion"),
        _vide(b, bleu),
    ]
    r1 = camion(achats, imp.fournisseur_id, lignes, factures={imp.devise: {"numero": f1}})
    assert r1["blocages"] == [] and r1["actions"]["valider"] is None
    r1 = geste(achats, r1, "valider")
    assert r1["statut"] == "validee" and len(r1["lignes"]) == 1
    assert r1["lignes"][0]["matiere_id"] == rouge and r1["facture"]["numero"] == f1
    c = bon_relu(achats, b["id"])
    assert c["statut"] in ("envoyee", "confirmee") and c["livraison"] in (
        "en_cours",
        "partiel_retard",
    )
    assert _reste(c, rouge) == 0 and _reste(c, vert) == 600 and _reste(c, bleu) == 400
    assert c["reste_kg"] == pytest.approx(1000)
    histoire = ok(direction.get(f"/api/historique/reception/{r1['id']}"))
    retrait = next(x for x in histoire if x["action"] == "lignes non livrées retirées")
    assert "2 ligne(s) non livrée(s)" in retrait["detail"] and b["numero"] in retrait["detail"]
    assert len(retrait["avant"]["lignes"]) == 2
    validation = next(x for x in histoire if x["action"] == "validation réception")
    assert validation["detail"].endswith(
        "1 entrée(s) · 2 ligne(s) non livrée(s) retirée(s), dues sur le bon"
    )
    # Le second camion : seules les lignes 2 et 3 restent à livrer (la saisie ne reprend qu'elles).
    assert {x["matiere_id"] for x in c["lignes"] if x["reste"] > 0} == {vert, bleu}
    lignes = [
        ligne_du_bon(c, m, kg, unique("S"), magasin_id=quai.courant)
        for m, kg in ((vert, 600), (bleu, 400))
    ]
    r2 = geste(achats, camion(achats, imp.fournisseur_id, lignes), "valider")
    assert len(r2["lignes"]) == 2 and r2["facture"] is None
    c = bon_relu(achats, b["id"])
    assert c["statut"] == "soldee" and c["livraison"] == "livre" and c["reste_kg"] == 0
    r2 = facture_reception(achats, r2, numero=f2, date=j(), montant=2000)
    assert r2["facture"]["numero"] == f2
    # Un dossier par facture : F1 ouvre le sien (droits de douane), F2 un second.
    d1 = ouvrir(achats, f1)
    assert [x["matiere_id"] for x in d1["lignes"]] == [rouge]
    d1 = frais(achats, d1, "DD", 450)
    assert [x["montant"] for x in d1["frais"]] == [450]
    d2 = ouvrir(achats, f2)
    assert d2["id"] != d1["id"] and d2["numero"] != d1["numero"]
    assert sorted(x["matiere_id"] for x in d2["lignes"]) == sorted([vert, bleu])
    assert (d1["factures"][0]["numero"], d2["factures"][0]["numero"]) == (f1, f2)


def test_toutes_les_lignes_vides_rien_n_est_pese(
    achats: TestClient, imp: Achat, quai: Quai
) -> None:
    """Aucune ligne apportée : la validation est refusée par une phrase claire, annoncée sur le
    brouillon ; rien n'est retiré, le bon reste entier."""
    assert RIEN_N_EST_PESE == RIEN
    rouge, vert, _ = _trois(imp)
    b = parti(achats, imp, {rouge: 1000, vert: 600})
    r = camion(achats, imp.fournisseur_id, [_vide(b, rouge), _vide(b, vert)])
    assert r["blocages"] == [RIEN] and r["actions"]["valider"] == RIEN
    refus = geste(achats, r, "valider", 422)
    assert refus["code"] == "quantite_invalide" and refus["detail"] == RIEN
    assert len(fiche(achats, r["id"])["lignes"]) == 2
    assert bon_relu(achats, b["id"])["reste_kg"] == pytest.approx(1600)


def test_une_ligne_de_bon_a_moitie_remplie_garde_ses_blocages(
    achats: TestClient, imp: Achat, quai: Quai
) -> None:
    """Un BL saisi sans pesée, ou une pesée sans lot : ce n'est pas « non livré », les blocages
    d'avant restent mot pour mot (X-RCP-B5, B6, B8)."""
    rouge, vert, _ = _trois(imp)
    b = parti(achats, imp, {rouge: 1000, vert: 600})
    lignes = [
        _vide(b, rouge, quantite_bl=1000),
        _vide(b, vert, quantite_pesee=600, magasin_id=quai.courant),
    ]
    r = camion(achats, imp.fournisseur_id, lignes)
    ref_rouge, ref_vert = (x["reference"] for x in r["lignes"])
    assert r["blocages"] == [
        f"« {ref_rouge} » : la pesée est à zéro. La saisir, ou marquer la ligne « refusé ».",
        f"« {ref_rouge} » : le numéro de lot manque (celui de l'étiquette, ou « Lot interne »).",
        f"« {ref_rouge} » : choisir le magasin de rangement.",
        f"« {ref_vert} » : le numéro de lot manque (celui de l'étiquette, ou « Lot interne »).",
    ]
    assert geste(achats, r, "valider", 422)["detail"] == r["blocages"][0]


def test_une_ligne_hors_bon_vide_garde_ses_blocages(
    achats: TestClient, imp: Achat, quai: Quai
) -> None:
    """Hors bon, une ligne vide n'est due par personne : elle bloque comme avant ; à côté, la
    ligne de bon vide, elle, ne bloque pas."""
    rouge, vert, _ = _trois(imp)
    b = parti(achats, imp, {rouge: 1000})
    hors = {"matiere_id": vert, "magasin_id": quai.courant}
    plein = ligne_du_bon(b, rouge, 1000, unique("R"), magasin_id=quai.courant)
    r = camion(achats, imp.fournisseur_id, [plein, hors])
    ref = r["lignes"][1]["reference"]
    assert r["blocages"] == [
        f"« {ref} » : la pesée est à zéro. La saisir, ou marquer la ligne « refusé ».",
        f"« {ref} » : le numéro de lot manque (celui de l'étiquette, ou « Lot interne »).",
    ]
    r = camion(achats, imp.fournisseur_id, [hors])
    assert RIEN not in r["blocages"] and len(r["blocages"]) == 2


def test_une_ligne_refusee_et_des_lignes_vides(achats: TestClient, imp: Achat) -> None:
    """Une ligne refusée reste la trace du camion renvoyé : les lignes vides à côté sont
    retirées, la réception se valide « tout refusé », le bon garde tout son reste."""
    rouge, vert, _ = _trois(imp)
    b = parti(achats, imp, {rouge: 1000, vert: 600})
    lignes = [_vide(b, rouge, qualite="refuse", quantite_bl=1000), _vide(b, vert)]
    r = geste(achats, camion(achats, imp.fournisseur_id, lignes), "valider")
    assert [x["qualite"] for x in r["lignes"]] == ["refuse"]
    assert bon_relu(achats, b["id"])["reste_kg"] == pytest.approx(1600)
