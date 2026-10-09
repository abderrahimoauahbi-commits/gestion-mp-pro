"""Fabriques des réceptions (lot D4) : un camion par l'API, des gestes avec la version lue, une
réception validée écrite par le vrai service (pour les essais des autres lots).

    from fabriques.receptions import Quai, camion, geste, ligne_du_bon, recevoir_ligne

    quai = Quai.nouveau()                                    # un magasin courant à soi
    r = camion(achats, a.fournisseur_id, [ligne_du_bon(b, m, 478, "B-1", magasin=quai.courant)])
    r = geste(achats, r, "valider")                          # la version lue est envoyée d'office
    rid = recevoir_ligne(cl_id, 400, qualite="reserve")      # validée par le service, sans client

Les données des réceptions **validées** par ces essais sont datées en 2025 (`JOUR`) : le monde
de S1 (`tests/modele_monde.py`) pose `REC-2026-0001` et `RCL-2026-0001` à la main (note D5).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fabrique import assurer_comptes
from fabriques.referentiels import magasin, unique
from fastapi.testclient import TestClient

from gestion_mp_pro.db import fabrique as fabrique_de_sessions
from gestion_mp_pro.modeles import Commande, CommandeLigne, Utilisateur
from gestion_mp_pro.modeles.enums import QualiteReception
from gestion_mp_pro.services import horloge, receptions
from gestion_mp_pro.services.comptes import Acteur, acteur_de
from gestion_mp_pro.services.receptions_saisie import LigneSaisie, Saisie

JOUR = date(2025, 12, 31)
"""Le jour des réceptions validées par les essais du lot (une autre année que le monde de S1)."""


def j(n: int = 0) -> str:
    """`JOUR` décalé de `n` jours, en ISO."""
    return (JOUR + timedelta(days=n)).isoformat()


def ok(r: Any, code: int = 200) -> Any:
    """Le code attendu, puis le JSON (ou rien pour un 204)."""
    assert r.status_code == code, r.text
    return None if code == 204 else r.json()


@dataclass
class Quai:
    """Un magasin de rangement à soi (le stock posé dans les magasins semés gêne D1)."""

    courant: int

    @classmethod
    def nouveau(cls) -> Quai:
        """Un magasin courant neuf."""
        return cls(magasin())


def ligne_du_bon(
    b: dict[str, Any], matiere_id: int, kg: float, lot: str, **autres: Any
) -> dict[str, Any]:
    """La ligne d'un camion qui livre la matière d'un bon (fiche du bon de D3)."""
    x = next(x for x in b["lignes"] if x["matiere_id"] == matiere_id)
    return {
        "commande_ligne_id": x["id"],
        "matiere_id": matiere_id,
        "lot_numero": lot,
        "quantite_pesee": kg,
        **autres,
    }


def camion(
    client: TestClient,
    fournisseur_id: int,
    lignes: list[dict[str, Any]],
    code: int = 201,
    **entete: Any,
) -> Any:
    """`POST /receptions` (date `JOUR` par défaut) ; rend la première fiche (ou le refus)."""
    corps = {"date": entete.pop("date", j()), "fournisseur_id": fournisseur_id, **entete}
    r = client.post("/api/receptions", json={**corps, "lignes": lignes})
    assert r.status_code == code, r.text
    return r.json()[0] if code == 201 else r.json()


def camions(
    client: TestClient, fournisseur_id: int, lignes: list[dict[str, Any]], **entete: Any
) -> list[Any]:
    """`POST /receptions` : toutes les fiches créées (une par devise)."""
    corps = {"date": entete.pop("date", j()), "fournisseur_id": fournisseur_id, **entete}
    return ok(client.post("/api/receptions", json={**corps, "lignes": lignes}), 201)  # type: ignore[no-any-return]


def fiche(client: TestClient, rid: int) -> dict[str, Any]:
    """La fiche relue."""
    return ok(client.get(f"/api/receptions/{rid}"))  # type: ignore[no-any-return]


def geste(client: TestClient, r: dict[str, Any], nom: str, code: int = 200, **corps: Any) -> Any:
    """Un geste sur la réception avec sa version lue ; rend la fiche (ou le refus)."""
    version = corps.pop("version") if "version" in corps else fiche(client, r["id"])["version"]
    reponse = client.post(f"/api/receptions/{r['id']}/{nom}", json={"version": version, **corps})
    assert reponse.status_code == code, reponse.text
    return reponse.json()


def facture(client: TestClient, r: dict[str, Any], code: int = 200, **champs: Any) -> Any:
    """`PUT /receptions/{id}/facture` avec la version lue."""
    version = fiche(client, r["id"])["version"]
    reponse = client.put(f"/api/receptions/{r['id']}/facture", json={"version": version, **champs})
    assert reponse.status_code == code, reponse.text
    return reponse.json()


def recevoir(
    client: TestClient, fournisseur_id: int, lignes: list[dict[str, Any]], **entete: Any
) -> Any:
    """Un camion enregistré puis validé ; rend la fiche validée."""
    return geste(client, camion(client, fournisseur_id, lignes, **entete), "valider")


def acteur(role: str = "achats") -> Acteur:
    """L'acteur d'un compte de base (pour appeler un service sans client)."""
    ids = assurer_comptes()
    with fabrique_de_sessions()() as s:
        u = s.get(Utilisateur, ids[role])
        assert u is not None
        return acteur_de(u)


def recevoir_ligne(
    commande_ligne_id: int,
    kg: float,
    *,
    qualite: str = QualiteReception.conforme,
    le: date | None = None,
    lot: str | None = None,
) -> int:
    """Une réception validée sur une ligne de bon, par le vrai service (création puis
    validation, soldes recalés) ; rend son id. Le magasin de rangement est neuf."""
    jour = le or horloge.aujourd_hui()
    courant = magasin()
    qui = acteur()
    with fabrique_de_sessions()() as s, s.begin():
        cl = s.get(CommandeLigne, commande_ligne_id)
        assert cl is not None
        c = s.get(Commande, cl.commande_id)
        assert c is not None
        x = LigneSaisie(
            matiere_id=cl.matiere_id,
            commande_ligne_id=cl.id,
            lot_numero=lot or unique("L"),
            quantite_pesee=Decimal(str(kg)),
            magasin_id=courant,
            qualite=QualiteReception(qualite),
        )
        r = receptions.creer(s, qui, Saisie(jour, c.fournisseur_id, [x]))[0]
        s.flush()
        receptions.valider(s, qui, r.id, r.version)
        return r.id
