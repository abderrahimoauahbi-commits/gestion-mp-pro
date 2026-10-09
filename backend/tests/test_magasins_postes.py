"""Magasins, postes de frais, codes douaniers, motifs (routes 31–42) — lot D1.

Héritage R-REF-71…73, 85…95, X-REF-54…58, 74…86 (REGLES § 1.10, 1.12, 1.13) ; commits f216509
(période close) et 58f507c (changer la clé fige la répartition des dossiers clos).
"""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal
from typing import Any

from fabrique import *  # noqa: F403
from fabriques.referentiels import (
    code_douanier,
    magasin,
    matiere,
    poste_frais,
    poste_seme,
    stock_initial,
    unique,
)
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import (
    CodeDouanier,
    Dossier,
    DossierFrais,
    DossierFraisPart,
    DossierLigne,
    Magasin,
    Parametre,
    PosteFrais,
)
from gestion_mp_pro.modeles.enums import StatutDossier
from gestion_mp_pro.services import lots
from gestion_mp_pro.services.postes_frais import repartir


def ok(r: Any, statut: int = 200) -> Any:
    """La réponse JSON d'un appel qui doit réussir."""
    assert r.status_code == statut, r.text
    return r.json()


def _version(modele: Any, ident: int) -> int:
    """La version d'une fiche."""
    with sessions()() as s:
        return int(s.get_one(modele, ident).version)


def test_magasins_creation_et_refus(direction: TestClient, achats: TestClient) -> None:
    """Hérité : test_referentiels_complets::test_magasin_contenu ; X-REF-54, X-REF-55 (A-12)."""
    code = unique("MAG")
    g = ok(direction.post("/api/magasins", json={"code": f" {code} ", "contenu": "Fils PP"}), 201)
    assert (g["code"], g["contenu"], g["type"], g["kg_detenus"]) == (
        code,
        "Fils PP",
        "stock_courant",
        0,
    )
    assert achats.post("/api/magasins", json={"code": unique("M")}).status_code == 403
    r = direction.post("/api/magasins", json={"code": code.lower()})
    assert (r.status_code, r.json()["detail"]) == (
        409,
        f"Le magasin « {code.lower()} » existe déjà.",
    )
    r = direction.post("/api/magasins", json={"code": unique("M"), "type": "Atelier"})
    assert r.json()["detail"] == "Type de magasin : « Stock courant » ou « Quarantaine »."
    corps = {"code": "Quarantaine", "type": "stock_courant", "version": g["version"]}
    assert direction.put(f"/api/magasins/{g['id']}", json=corps).status_code == 409
    assert {x["code"] for x in ok(achats.get("/api/magasins"))} >= {code, "Quarantaine"}


def test_un_magasin_qui_detient_de_la_matiere(direction: TestClient) -> None:
    """Hérité : X-REF-57, X-REF-58 — ni désactivé (milliers à la française, I-15) ni retypé."""
    g = magasin()
    stock_initial(matiere(), "1234.5", magasin_id=g)
    lu = next(x for x in ok(direction.get("/api/magasins")) if x["id"] == g)
    assert lu["kg_detenus"] == 1234.5
    base = {"code": lu["code"], "version": lu["version"]}
    r = direction.put(f"/api/magasins/{g}", json={**base, "actif": False})
    assert r.json()["detail"] == (
        f"« {lu['code']} » détient encore 1 234 kg : transférer le stock avant de désactiver "
        "le magasin."
    )
    r = direction.put(f"/api/magasins/{g}", json={**base, "type": "quarantaine"})
    assert r.json()["detail"] == "Un magasin qui détient de la matière ne change pas de type."
    perime = direction.put(f"/api/magasins/{g}", json={**base, "nom": "x", "version": 99})
    assert perime.status_code == 409


def test_toujours_une_quarantaine_en_service(base_neuve: None, direction: TestClient) -> None:
    """R-REF-04 : il reste toujours un magasin en service de chaque type (base neuve : la
    quarantaine semée ne détient rien de ce que les autres essais y ont mis)."""
    with sessions()() as s:
        quarantaines = s.scalars(
            select(Magasin).where(Magasin.type == "quarantaine", Magasin.actif)
        ).all()
    seule, autres = quarantaines[0], [q.id for q in quarantaines[1:]]
    with sessions()() as s, s.begin():
        s.execute(update(Magasin).where(Magasin.id.in_(autres)).values(actif=False))
    try:
        corps = {
            "code": seule.code,
            "type": "quarantaine",
            "actif": False,
            "version": seule.version,
        }
        r = direction.put(f"/api/magasins/{seule.id}", json=corps)
        assert r.json()["detail"] == (
            "Il doit toujours rester un magasin « Quarantaine » en service : en créer ou en "
            "réactiver un autre d'abord."
        )
    finally:
        with sessions()() as s, s.begin():
            s.execute(update(Magasin).where(Magasin.id.in_(autres)).values(actif=True))


def test_postes_creation_lecture_suppression(direction: TestClient, achats: TestClient) -> None:
    """Hérité : R-REF-85, 88, 92 ; X-REF-74, 76, 81, 82 ; une seule lecture (D, A)."""
    code = unique("M")[-12:].replace("-", "_")
    p = ok(
        direction.post(
            "/api/postes-frais",
            json={"code": code.lower(), "libelle": " Manutention ", "cle": "poids"},
        ),
        201,
    )
    assert (p["code"], p["libelle"], p["cle"], p["systeme"]) == (
        code,
        "Manutention",
        "poids",
        False,
    )
    lus = {x["code"]: x for x in ok(achats.get("/api/postes-frais"))}
    assert lus["TVA"]["recuperable"] and lus["TVA"]["systeme"] and lus[code]["ordre"] >= 11
    r = direction.post("/api/postes-frais", json={"code": "MAN UT", "libelle": "x"})
    assert r.json()["detail"] == (
        "Le code d'un poste : lettres, chiffres ou « _ », sans espace (ex. MANUT)."
    )
    r = direction.post("/api/postes-frais", json={"code": code, "libelle": "x"})
    assert (r.status_code, r.json()["detail"]) == (409, f"Le poste « {code} » existe déjà.")
    dd = lus["DD"]
    r = direction.delete(f"/api/postes-frais/{dd['id']}?version={dd['version']}")
    assert (
        r.json()["detail"]
        == "« Droits de douane » sert aux calculs du dossier : il ne se supprime pas."
    )
    assert (
        direction.delete(f"/api/postes-frais/{p['id']}?version={p['version']}").status_code == 204
    )


def test_un_poste_systeme_garde_sa_nature(direction: TestClient) -> None:
    """Hérité : X-REF-78 — la TVA reste récupérable."""
    tva = poste_seme("TVA")
    corps = {
        "libelle": "TVA",
        "recuperable": False,
        "nature": "autre",
        "version": _version(PosteFrais, tva),
    }
    r = direction.put(f"/api/postes-frais/{tva}", json=corps)
    assert r.json()["detail"] == (
        "« TVA à l'importation » est récupérable par nature : les calculs du dossier (TVA "
        "attendue) le lisent ainsi."
    )


def _dossier(statut: str, poste: int, montant: str = "100") -> tuple[int, list[int]]:
    """Un dossier saisi à la main, deux marchandises (1 000 et 3 000 MAD), un frais global."""
    with sessions()() as s, s.begin():
        d = Dossier(
            numero=f"ANC-{unique('P')}", saisi_a_la_main=True, date_arrivee=date(2026, 9, 10)
        )
        d.statut = StatutDossier(statut)
        if statut == "clos":
            from gestion_mp_pro.services import horloge

            d.clos_le = horloge.maintenant()
        s.add(d)
        s.flush()
        lignes = []
        for valeur, kg in (("1000", "300"), ("3000", "100")):
            m = matiere(s=s)
            lot = lots.lot_ou_creer(s, m, unique("L"), date(2026, 9, 10))
            x = DossierLigne(dossier_id=d.id, matiere_id=m, lot_id=lot.id, devise="MAD")
            x.valeur_devise, x.quantite_kg = Decimal(valeur), Decimal(kg)
            s.add(x)
            s.flush()
            lignes.append(x.id)
        s.add(DossierFrais(dossier_id=d.id, poste_id=poste, montant=Decimal(montant)))
        return d.id, lignes


def test_changer_la_cle_fige_les_dossiers_clos(direction: TestClient) -> None:
    """Hérité : test_importations::test_changer_la_cle_garde_une_piece_et_son_reglement (R-REF-90) ;
    X-REF-79 — un dossier clos garde sa répartition à l'ancienne clé, Σ parts = montant."""
    p = poste_frais(cle="valeur")
    clos, (l1, l2) = _dossier("clos", p, "100.01")
    corps = {"libelle": "Poste d'essai", "cle": "poids", "version": _version(PosteFrais, p)}
    fiche = ok(direction.put(f"/api/postes-frais/{p}", json=corps))
    assert (fiche["cle"], fiche["parts_figees"], fiche["frais_clos"]) == ("poids", 1, 1)
    with sessions()() as s:
        parts = dict(s.execute(select(DossierFraisPart.ligne_id, DossierFraisPart.montant)).all())
    assert (parts[l1], parts[l2]) == (Decimal("25.00"), Decimal("75.01"))
    corps = {"libelle": "x", "cle": "poids", "recuperable": True, "version": fiche["version"]}
    r = direction.put(f"/api/postes-frais/{p}", json=corps)
    assert r.json()["detail"] == (
        "Ce poste porte des frais dans 1 dossier(s) clos : changer sa nature changerait leur "
        "coût. Créer un autre poste."
    )
    r = direction.delete(f"/api/postes-frais/{p}?version={fiche['version']}")
    assert (
        r.json()["detail"] == "Ce poste porte des frais dans des dossiers : il ne se supprime pas."
    )
    assert clos


def test_un_dossier_ouvert_de_periode_close_refuse_le_changement(direction: TestClient) -> None:
    """Hérité : test_valorisation::test_un_mois_clos_ne_se_revalorise_pas (clé) ; X-REF-80."""
    p = poste_frais()
    _dossier("ouvert", p)
    with sessions()() as s, s.begin():
        s.execute(
            update(Parametre).where(Parametre.cle == "date_cloture").values(valeur="2026-09-30")
        )
    try:
        corps = {"libelle": "Poste d'essai", "cle": "poids", "version": _version(PosteFrais, p)}
        r = direction.put(f"/api/postes-frais/{p}", json=corps)
        assert r.status_code == 409 and r.json()["code"] == "cout_periode_close"
        assert "entrée le 10/09/2026" in r.json()["detail"]
    finally:
        with sessions()() as s, s.begin():
            s.execute(update(Parametre).where(Parametre.cle == "date_cloture").values(valeur=""))


def test_repartir_aux_plus_forts_restes() -> None:
    """Σ parts = montant au centime, signe gardé (un avoir), lignes de poids nul exclues."""
    assert repartir(Decimal("100"), {1: Decimal(1), 2: Decimal(1), 3: Decimal(1)}) == {
        1: Decimal("33.34"),
        2: Decimal("33.33"),
        3: Decimal("33.33"),
    }
    assert sum(
        repartir(Decimal("-10"), {1: Decimal(2), 2: Decimal(1), 3: Decimal(0)}).values()
    ) == Decimal("-10")


def test_codes_douaniers(
    direction: TestClient, achats: TestClient, alimentation: TestClient
) -> None:
    """Hérité : R-REF-93…95 ; X-REF-83…86."""
    code = f"5402.{random.randint(1000, 9999)}.{random.randint(10, 99)}"
    c = ok(
        direction.post(
            "/api/codes-douaniers",
            json={"code": f" {code} ", "libelle": "Fils", "taux_droits": 0.1},
        ),
        201,
    )
    assert (c["code"], c["taux_droits"], c["nb_matieres"]) == (code, 0.1, 0)
    r = direction.post("/api/codes-douaniers", json={"code": code, "taux_droits": 0})
    assert r.json()["detail"] == f"Le code douanier « {code} » existe déjà."
    r = direction.post("/api/codes-douaniers", json={"code": "PP-12", "taux_droits": 0})
    assert r.json()["detail"] == (
        "Un code douanier s'écrit en chiffres, éventuellement séparés de points "
        "(ex. 5402.47.00.00)."
    )
    assert (
        achats.post("/api/codes-douaniers", json={"code": "1234", "taux_droits": 0}).status_code
        == 403
    )
    assert alimentation.get("/api/codes-douaniers").status_code == 403
    porte = code_douanier()
    matiere(code_douanier_id=porte)
    r = direction.delete(f"/api/codes-douaniers/{porte}")
    assert (
        r.json()["detail"]
        == "1 matière(s) portent ce code : le leur retirer d'abord, ou le désactiver."
    )
    corps = {"code": code, "taux_droits": 0.025, "actif": False, "version": c["version"]}
    assert ok(direction.put(f"/api/codes-douaniers/{c['id']}", json=corps))["taux_droits"] == 0.025
    assert direction.delete(f"/api/codes-douaniers/{c['id']}").status_code == 204
    with sessions()() as s:
        assert s.get(CodeDouanier, c["id"]) is None


def test_motifs_une_seule_source(alimentation: TestClient) -> None:
    """Hérité : S80–S85, U2 — types et rôles, 16 motifs (R1–R6), motifs et issues des
    réclamations ; lisible par l'alimentation."""
    m = ok(alimentation.get("/api/motifs"))
    types = {x["type"]: x for x in m["types"]}
    assert types["retour_machine"]["roles"] == ["direction", "alimentation"]
    assert types["transfert"]["libelle"] == "Transfert entre magasins"
    assert len(m["motifs"]) == 16
    liberation = next(x for x in m["motifs"] if x["libelle"] == "Libération de quarantaine")
    assert liberation["impose_role"] == "achats"
    codes = {x["libelle"]: x["code_r"] for x in m["motifs"]}
    assert codes["Refus après quarantaine"] == codes["Non-conformité qualité"] == "R3"
    assert [x["code"] for x in m["reclamation_issues"]][0] == "avoir"
    assert len(m["reclamation_motifs"]) == 7
