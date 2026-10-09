"""Fabriques des réceptions (lot D4) : un camion par l'API, des gestes avec la version lue, une
réception validée écrite par le vrai service (pour les essais des autres lots).

    from fabriques.receptions import Quai, camion, geste, ligne_du_bon, recevoir_ligne

    quai = Quai.nouveau()                                    # un magasin courant à soi
    r = camion(achats, a.fournisseur_id, [ligne_du_bon(b, m, 478, "B-1", magasin=quai.courant)])
    r = geste(achats, r, "valider")                          # la version lue est envoyée d'office
    rid = recevoir_ligne(cl_id, 400, qualite="reserve")      # validée par le service, sans client

Les réceptions des essais sont datées de `JOUR` (août 2026) : le monde de S1 travaille sur une
base neuve dans sa propre transaction (`base_connue`), ses numéros posés à la main ne rencontrent
plus ceux des essais (RESTES3 : la date en 2025 et la fixture `menage` sont retirées).
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

JOUR = date(2026, 8, 3)
"""Le jour des réceptions des essais du lot (assez tôt pour que `j(45)` soit passé)."""


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


# ── Bons, retours, libérations, performance ─────────────────────────────────


def parti(
    client: TestClient,
    a: Any,
    lignes: dict[int, float],
    *,
    envoye: str | None = None,
    prix: float | None = None,
    prevue: str | None = None,
) -> dict[str, Any]:
    """Un bon parti (envoyé `envoye`, 30 jours avant `JOUR` par défaut), prix confirmés si
    `prix` est donné ; rend la fiche du bon (lot D3)."""
    from fabriques.achats import bon
    from fabriques.achats import geste as geste_bon

    entete = {"date_livraison_prevue": prevue} if prevue else {}
    b = geste_bon(client, bon(client, a, lignes, **entete), "envoyer", date=envoye or j(-30))
    if prix is not None:
        confirmes = [{"ligne_id": x["id"], "prix": prix} for x in b["lignes"]]
        b = geste_bon(client, b, "prix", lignes=confirmes, mettre_a_jour_catalogue=False)
    return b


def bon_relu(client: TestClient, cid: int) -> dict[str, Any]:
    """La fiche d'un bon relue."""
    return ok(client.get(f"/api/commandes/{cid}"))  # type: ignore[no-any-return]


def motif_operation(type_: str, libelle: str) -> int:
    """L'identifiant d'un motif d'opération semé (lot D5)."""
    from fabriques.operations import motif

    with fabrique_de_sessions()() as s:
        return motif(s, type_, libelle)


def _ligne_op(x: dict[str, Any], kg: float, vers: int | None = None) -> dict[str, Any]:
    ligne = {
        "matiere_id": x["matiere_id"],
        "lot_id": x["lot_id"],
        "magasin_id": x["magasin_id"],
        "quantite": kg,
    }
    return ligne | ({"magasin_destination_id": vers} if vers else {})


def retour(client: TestClient, x: dict[str, Any], kg: float, *, le: str) -> dict[str, Any]:
    """Un retour au fournisseur validé (lot D5, « Non-conformité qualité ») du lot d'une ligne
    de réception validée."""
    corps = {
        "type": "retour_fournisseur",
        "date": le,
        "motif_id": motif_operation("retour_fournisseur", "Non-conformité qualité"),
        "valider": True,
        "lignes": [_ligne_op(x, kg)],
    }
    return ok(client.post("/api/operations", json=corps), 201)  # type: ignore[no-any-return]


def liberer(
    client: TestClient, x: dict[str, Any], vers: int, kg: float, *, le: str
) -> dict[str, Any]:
    """La libération de quarantaine (transfert validé, lot D5) du lot d'une ligne reçue sous
    réserve, vers le magasin `vers`."""
    corps = {
        "type": "transfert",
        "date": le,
        "motif_id": motif_operation("transfert", "Libération de quarantaine"),
        "valider": True,
        "lignes": [_ligne_op(x, kg, vers)],
    }
    return ok(client.post("/api/operations", json=corps), 201)  # type: ignore[no-any-return]


def performance(numero: str) -> Any:
    """La note d'une réception (ponctualité, complétude, OTIF) calculée par le moteur."""
    from gestion_mp_pro.calcul.fournisseurs import performance_receptions
    from gestion_mp_pro.services import donnees_moteur

    donnees_moteur.invalider()
    with fabrique_de_sessions()() as s:
        notes = performance_receptions(donnees_moteur.charger(s))
    return next(p for p in notes if p.numero == numero)
