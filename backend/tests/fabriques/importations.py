"""Fabriques des dossiers d'importation (lot D7) : de vrais dossiers, ouverts par l'API depuis
la facture d'une vraie réception validée (lot D4), ou à la main pour un dossier d'avant la mise
en service ; des gestes avec la version lue.

    from fabriques.importations import Import, ouvrir, geste, frais, a_la_main

    imp = Import.nouveau(cours="10")                 # un fournisseur turc dans une devise à soi
    r = imp.recevoir(achats, "F-1", [("ROUGE", "IR-1", 1000, 2)], montant=6000)
    d = ouvrir(achats, "F-1")                        # le dossier de la facture (fiche)
    d = frais(achats, d, "FRET", 3500)               # un frais (poste semé, par son code)
    d = geste(achats, d, "cloturer", alertes_lues=True)

Les réceptions sont datées `JOUR` (31/12/2025, comme celles de D4) : les dossiers ouverts par
leur facture sont de la série `NN/25` ; un dossier saisi à la main est d'avant la mise en
service (avant 2020) et prend un numéro libre de la série `NN/1x`.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from typing import Any

from fabriques.receptions import JOUR, Quai, camion, j, ok
from fabriques.receptions import geste as geste_reception
from fabriques.referentiels import devise, fournisseur, matiere, poste_seme, unique
from fastapi.testclient import TestClient

from gestion_mp_pro.db import fabrique as fabrique_de_sessions
from gestion_mp_pro.services import donnees_moteur

__all__ = [
    "JOUR",
    "Import",
    "a_la_main",
    "facture_id",
    "fiche",
    "frais",
    "invalider",
    "geste",
    "ligne",
    "numero_ancien",
    "ouvrir",
    "poste",
    "sessions",
]

sessions = fabrique_de_sessions
_RANGS = itertools.count(random.randint(1, 60))  # noqa: S311 — un numéro d'essai, pas un secret


def numero_ancien() -> str:
    """Un numéro libre d'un dossier d'avant la mise en service : « 07/14 »."""
    n = next(_RANGS)
    return f"{n % 900 + 1:02d}/1{n // 900 % 10}"


@dataclass
class Import:
    """Un fournisseur étranger dans une devise à soi (cours connu), ses matières, un quai."""

    fournisseur_id: int
    devise: str
    quai: Quai
    matieres: dict[str, int] = field(default_factory=dict)
    factures: dict[str, str] = field(default_factory=dict)

    @classmethod
    def nouveau(cls, *, cours: str = "10", pays: str = "TURKEY", code: str | None = None) -> Import:
        """Un fournisseur (pays donné) facturant dans une devise neuve au cours donné."""
        d = code or devise(cours=cours)
        return cls(fournisseur(devise=d, pays=pays), d, Quai.nouveau())

    def matiere(self, nom: str, **champs: Any) -> int:
        """Une matière de ce fournisseur (créée une fois par nom)."""
        if nom not in self.matieres:
            self.matieres[nom] = matiere(
                unique(f"IMP {nom}"),
                fournisseur_id=self.fournisseur_id,
                devise=self.devise,
                **champs,
            )
        return self.matieres[nom]

    def f(self, nom: str) -> str:
        """Le vrai numéro (unique dans la séance) de la facture nommée `nom` dans l'essai."""
        return self.factures.setdefault(nom, unique(nom))

    def ligne(self, nom: str, lot: str, kg: float, prix: float) -> dict[str, Any]:
        """Une ligne hors commande du camion (pesée = BL)."""
        return {
            "matiere_id": self.matiere(nom),
            "lot_numero": unique(lot),
            "quantite_bl": kg,
            "quantite_pesee": kg,
            "magasin_id": self.quai.courant,
            "prix": prix,
            "devise": self.devise,
        }

    def recevoir(
        self,
        client: TestClient,
        facture: str | None,
        lignes: list[tuple[str, str, float, float]],
        *,
        montant: float | None = None,
        le: str | None = None,
    ) -> dict[str, Any]:
        """Un camion validé, sa facture saisie (son vrai numéro : `self.f(facture)`)."""
        corps: dict[str, Any] = {"date": le or j()}
        if facture:
            saisie = {"numero": self.f(facture), "date": le or j(), "montant": montant}
            corps["factures"] = {self.devise: saisie}
        r = camion(client, self.fournisseur_id, [self.ligne(*x) for x in lignes], **corps)
        return geste_reception(client, r, "valider")  # type: ignore[no-any-return]


def facture_id(client: TestClient, numero: str) -> int:
    """L'identifiant d'une facture qui attend son dossier (fournisseurs marocains compris)."""
    attente = ok(client.get("/api/dossiers/a-rattacher", params={"locaux": True}))
    return next(f["facture_id"] for f in attente["factures"] if f["numero"] == numero)  # type: ignore[no-any-return]


def ouvrir(client: TestClient, numero: str, code: int = 201, **corps: Any) -> Any:
    """Le dossier de la facture `numero`, ouvert par l'API (fiche, ou le refus)."""
    r = client.post("/api/dossiers", json={"facture_id": facture_id(client, numero), **corps})
    assert r.status_code == code, r.text
    return r.json()


def a_la_main(client: TestClient, code: int = 201, **corps: Any) -> Any:
    """Un dossier d'avant la mise en service (2018 par défaut, numéro libre « NN/1x »)."""
    corps = {"numero": numero_ancien(), "date_arrivee": "2018-03-01", **corps}
    r = client.post("/api/dossiers", json=corps)
    assert r.status_code == code, r.text
    return r.json()


def fiche(client: TestClient, did: int) -> dict[str, Any]:
    """La fiche relue."""
    return ok(client.get(f"/api/dossiers/{did}"))  # type: ignore[no-any-return]


def geste(client: TestClient, d: dict[str, Any], nom: str, code: int = 200, **corps: Any) -> Any:
    """`POST /dossiers/{id}/{nom}` avec la version lue (ou donnée) ; la fiche ou le refus."""
    version = corps.pop("version") if "version" in corps else fiche(client, d["id"])["version"]
    r = client.post(f"/api/dossiers/{d['id']}/{nom}", json={"version": version, **corps})
    assert r.status_code == code, r.text
    return r.json()


def poste(code: str) -> int:
    """L'identifiant d'un poste de frais (semé, ou créé par l'essai)."""
    return poste_seme(code)


def frais(
    client: TestClient,
    d: dict[str, Any],
    code_poste: str,
    montant: float,
    code: int = 200,
    **champs: Any,
) -> Any:
    """Un frais ajouté au dossier (version lue) ; la fiche ou le refus."""
    corps = {"poste_id": poste(code_poste), "montant": montant, **champs}
    return geste(client, d, "frais", code, **corps)


def ligne(d: dict[str, Any], reference_debut: str) -> dict[str, Any]:
    """La marchandise du dossier dont la référence commence ainsi (« IMP ROUGE »)."""
    return next(x for x in d["lignes"] if x["reference"].startswith(reference_debut))


def invalider() -> None:
    """Le cache du moteur oublié (après une écriture directe en base, sans journal)."""
    donnees_moteur.invalider()
