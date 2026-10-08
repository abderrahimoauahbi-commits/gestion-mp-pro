"""Cloche, recherche globale et contexte de démarrage (lot S2 ; routes 3, 53–56 ; A6, A10).

Notifications par rôle ou par personne, dédoublonnées, jamais monétaires hors D et A ; recherche
« tous les mots, sans accents », filtrée par rôle ; `/contexte` en un appel.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fabrique import *  # noqa: F403
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.db import fabrique as sessions_db
from gestion_mp_pro.modeles import Commande, Fournisseur, Lot, Matiere, Qualite, RoleNomenclature
from gestion_mp_pro.modeles.enums import Role, TonNotification
from gestion_mp_pro.services import contexte, notifications, recherche


def _notifier(destinataire: Role | int, texte: str, **options: object) -> int | None:
    with sessions_db()() as s, s.begin():
        return notifications.notifier(s, destinataire, texte, **options)  # type: ignore[arg-type]


def test_cloche_par_role_et_par_personne(
    direction: TestClient, achats: TestClient, alimentation: TestClient, comptes: dict[str, int]
) -> None:
    cle = "essai:cloche:rupture:12"
    premier = _notifier(Role.alimentation, "Rupture : POIL ROUGE", lien="/lots/12", cle=cle)
    assert premier is not None
    assert _notifier(Role.alimentation, "Rupture : POIL ROUGE (bis)", cle=cle) is None
    _notifier(Role.alimentation, "Commande en retard : 12 000 MAD", monetaire=True)
    _notifier(comptes["achats"], "Réception REC-2026-0318 à valider", ton=TonNotification.alerte)
    cloche = alimentation.get("/api/notifications").json()
    textes = [n["texte"] for n in cloche["elements"]]
    assert "Rupture : POIL ROUGE" in textes and not any("MAD" in t for t in textes)
    assert not any("REC-2026-0318" in t for t in textes)
    assert "Réception REC-2026-0318 à valider" in [
        n["texte"] for n in achats.get("/api/notifications").json()["elements"]
    ]
    pour_la_direction = direction.get("/api/notifications").json()["elements"]
    assert all("POIL ROUGE" not in n["texte"] for n in pour_la_direction)
    avant = cloche["non_lues"]
    assert alimentation.post(f"/api/notifications/{premier}/lue").status_code == 204
    assert alimentation.get("/api/notifications").json()["non_lues"] == avant - 1
    assert achats.post(f"/api/notifications/{premier}/lue").status_code == 404
    assert alimentation.post("/api/notifications/lues").status_code == 204
    apres = alimentation.get("/api/notifications", params={"non_lues": True}).json()
    assert (apres["non_lues"], apres["total"], apres["elements"]) == (0, 0, [])


def test_cloche_paginee(administrateur: TestClient, comptes: dict[str, int]) -> None:
    for i in range(5):
        _notifier(
            comptes["administrateur"], f"Sauvegarde {i} en défaut", ton=TonNotification.danger
        )
    page = administrateur.get("/api/notifications", params={"limite": 2}).json()
    assert len(page["elements"]) == 2 and page["suivant"]
    suite = administrateur.get(
        "/api/notifications", params={"limite": 2, "apres": page["suivant"]}
    ).json()
    ids = [n["id"] for n in page["elements"] + suite["elements"]]
    assert ids == sorted(ids, reverse=True) and len(set(ids)) == 4


def test_normaliser_comme_l_ecran() -> None:
    """E0 : NFD, accents retirés, minuscules, blancs réduits (« frise rouge » → « FRISÉ ROUGE »)."""
    assert recherche.normaliser("  IMP  FRISÉ\tRouge ") == "imp frise rouge"
    assert recherche.mots("Écru  POLYESTER a b c d e f g") == [
        "ecru",
        "polyester",
        "a",
        "b",
        "c",
        "d",
    ]
    assert recherche.echapper("50%_x\\") == "50\\%\\_x\\\\"


@pytest.fixture(scope="module")
def catalogue_essai() -> dict[str, int]:
    """Un fournisseur, une matière, un lot, une qualité, une commande à chercher."""
    with sessions_db()() as s, s.begin():
        poil = s.scalars(select(RoleNomenclature).where(RoleNomenclature.code == "Poil")).one()
        f = Fournisseur(nom="Filature Écrue Recherche", pays="TURQUIE")
        s.add(f)
        s.flush()
        m = Matiere(reference="IMP FRISÉ ROUGE RECH", designation="Poil frisé", role_id=poil.id,
                    fournisseur_id=f.id, priorite_equiv=Decimal(50))  # fmt: skip
        q = Qualite(code="RECHQ", nom="Qualité frisée", base_mensuelle=Decimal(100))
        s.add_all([m, q])
        s.flush()
        lot = Lot(matiere_id=m.id, numero="RECH-LOT-1", entre_le=date(2026, 10, 1))
        c = Commande(fournisseur_id=f.id, date_commande=date(2026, 10, 1), devise="USD")
        s.add_all([lot, c])
        s.flush()
        return {"matiere": m.id, "lot": lot.id, "qualite": q.id, "commande": c.id}


def test_recherche_globale_filtree_par_role(
    catalogue_essai: dict[str, int],
    achats: TestClient,
    alimentation: TestClient,
    administrateur: TestClient,
) -> None:
    vu = achats.get("/api/recherche", params={"q": "frise rouge"}).json()
    assert {(r["genre"], r["lien"]) for r in vu} >= {
        ("matiere", f"/matieres/{catalogue_essai['matiere']}"),
        ("lot", f"/lots/{catalogue_essai['lot']}"),
    }
    genres = {
        r["genre"] for r in achats.get("/api/recherche", params={"q": "ecrue recherche"}).json()
    }
    assert {"fournisseur", "commande"} <= genres
    lu = {
        r["genre"]
        for r in alimentation.get("/api/recherche", params={"q": "ecrue recherche"}).json()
    }
    assert lu <= {"matiere", "lot", "ordre", "qualite"} and "matiere" in lu
    assert alimentation.get("/api/recherche", params={"q": "x"}).status_code == 422
    assert alimentation.get("/api/recherche", params={"q": "%%"}).json() == []
    assert administrateur.get("/api/recherche", params={"q": "poil"}).status_code == 403


def test_contexte_en_un_appel(
    direction: TestClient, alimentation: TestClient, administrateur: TestClient
) -> None:
    ctx = alimentation.get("/api/contexte").json()
    assert ctx["moi"]["role"] == "alimentation" and ctx["moi"]["droits"]
    assert ctx["heure_serveur"].startswith("2026-10-08T10:00")
    assert ctx["base_essai"] is True and ctx["alerte_serveur"] is None
    with sessions_db()() as s:
        au_metre = s.scalars(select(RoleNomenclature.code).where(RoleNomenclature.lineaire)).all()
    assert sorted(ctx["roles_au_metre"]) == sorted(au_metre) and au_metre
    domaines = {d["domaine"]: d for d in ctx["menu"]}
    assert domaines["Comptes et appareils"] == {
        "domaine": "Comptes et appareils",
        "lecture": True,
        "ecriture": True,
    }
    admin = {d["domaine"] for d in administrateur.get("/api/contexte").json()["menu"]}
    assert "Journal et historique" in admin
    contexte.COMPTEURS["essai"] = lambda _s, role: 3 if role == Role.direction else None
    contexte.ALERTES_SERVEUR.append(lambda _s: "Sauvegarde du jour en défaut.")
    try:
        d = direction.get("/api/contexte").json()
        assert (
            d["compteurs"] == {"essai": 3}
            and d["alerte_serveur"] == "Sauvegarde du jour en défaut."
        )
        a = alimentation.get("/api/contexte").json()
        assert a["compteurs"] == {} and a["alerte_serveur"] is None
    finally:
        contexte.COMPTEURS.pop("essai")
        contexte.ALERTES_SERVEUR.pop()
