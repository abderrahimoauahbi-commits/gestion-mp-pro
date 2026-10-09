"""Fabriques des achats (lot D3) : bons par l'API, réglages et cours le temps d'un essai,
réceptions validées écrites directement (le domaine des réceptions est au lot D4).

    from fabriques.achats import bon, geste, reglage, recevoir, Achat

    a = Achat.nouveau(devise="EUR", delai=45)           # un fournisseur et ses matières
    m = a.matiere("BLEU", prix="3", poids_bobine="2.5", bobines_palette="96")
    b = bon(achats, a, {m: 1000})                        # un brouillon (fiche rendue)
    b = geste(achats, b, "envoyer")                      # la version lue est envoyée d'office
    with reglage("seuil_approbation", "5000"): ...       # remis à sa valeur ensuite
    recevoir(b["lignes"][0]["id"], 478)                  # une réception validée (D4 simulé)
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from fabriques.referentiels import devise as nouvelle_devise
from fabriques.referentiels import fournisseur, magasin_seme, matiere, unique
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.db import fabrique as fabrique_de_sessions
from gestion_mp_pro.modeles import (
    CommandeLigne,
    Devise,
    Matiere,
    Parametre,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import (
    DocumentMouvement,
    QualiteReception,
    SerieNumero,
    StatutDocument,
    TypeMagasin,
    TypeMouvement,
)
from gestion_mp_pro.services import horloge, lots, numerotation, stock
from gestion_mp_pro.services.commandes import recaler_soldes

__all__ = [
    "Achat",
    "bon",
    "cours",
    "fiche",
    "geste",
    "ok",
    "recevoir",
    "reglage",
]


def ok(r: Any, code: int = 200) -> Any:
    """Le code attendu, puis le JSON (ou rien pour un 204)."""
    assert r.status_code == code, r.text
    return None if code == 204 else r.json()


@dataclass
class Achat:
    """Un fournisseur d'essai et ses matières (noms uniques)."""

    fournisseur_id: int
    devise: str
    matieres: dict[str, int] = field(default_factory=dict)

    @classmethod
    def nouveau(cls, *, devise: str = "MAD", delai: int = 30, **champs: Any) -> Achat:
        """Un fournisseur en service dans la devise donnée."""
        return cls(fournisseur(devise=devise, delai_jours=delai, **champs), devise)

    def matiere(
        self, nom: str, *, prix: str = "10", devise: str | None = None, **champs: Any
    ) -> int:
        """Une matière de ce fournisseur (créée une fois par nom)."""
        if nom not in self.matieres:
            self.matieres[nom] = matiere(
                unique(nom),
                fournisseur_id=self.fournisseur_id,
                prix=prix,
                devise=devise or self.devise,
                **champs,
            )
        return self.matieres[nom]


def bon(client: TestClient, a: Achat, lignes: dict[int, float], **entete: Any) -> dict[str, Any]:
    """Un brouillon (le premier bon créé) ; `lignes` : {matière: kg}."""
    corps = {
        "fournisseur_id": a.fournisseur_id,
        **entete,
        "lignes": [{"matiere_id": m, "quantite": kg} for m, kg in lignes.items()],
    }
    return ok(client.post("/api/commandes", json=corps), 201)[0]  # type: ignore[no-any-return]


def fiche(client: TestClient, cid: int) -> dict[str, Any]:
    """La fiche relue."""
    return ok(client.get(f"/api/commandes/{cid}"))  # type: ignore[no-any-return]


def geste(
    client: TestClient, b: dict[str, Any], nom: str, code: int = 200, **corps: Any
) -> dict[str, Any]:
    """Un geste sur le bon, avec sa version lue ; rend la fiche (ou le refus si `code`≠200)."""
    version = fiche(client, b["id"])["version"] if "version" not in corps else corps.pop("version")
    r = client.post(f"/api/commandes/{b['id']}/{nom}", json={"version": version, **corps})
    assert r.status_code == code, r.text
    return r.json()  # type: ignore[no-any-return]


@contextmanager
def reglage(cle: str, valeur: str) -> Iterator[None]:
    """Un réglage changé le temps d'un essai, puis remis."""
    with fabrique_de_sessions()() as s, s.begin():
        p = s.get(Parametre, cle)
        assert p is not None
        avant, p.valeur = p.valeur, valeur  # sa `version` change la signature du cache
    try:
        yield
    finally:
        with fabrique_de_sessions()() as s, s.begin():
            p = s.get(Parametre, cle)
            assert p is not None
            p.valeur = avant


@contextmanager
def cours(code: str, valeur: str) -> Iterator[None]:
    """Le cours du jour d'une devise changé le temps d'un essai."""
    with fabrique_de_sessions()() as s, s.begin():
        d = s.get(Devise, code)
        assert d is not None
        avant, d.cours = d.cours, Decimal(valeur)  # sa `version` change la signature du cache
    try:
        yield
    finally:
        with fabrique_de_sessions()() as s, s.begin():
            d = s.get(Devise, code)
            assert d is not None
            d.cours = avant


def devise_essai(cours_du_jour: str = "10") -> str:
    """Une devise d'essai (code au hasard)."""
    return nouvelle_devise(cours=cours_du_jour)


def recevoir(
    commande_ligne_id: int,
    kg: float,
    *,
    qualite: str = QualiteReception.conforme,
    le: date | None = None,
) -> int:
    """Une réception validée sur une ligne de bon (écrite comme le lot D4 l'écrira : lot,
    entrée de stock — en quarantaine si « sous réserve » —, puis soldes recalés) ; rend son id."""
    jour = le or horloge.aujourd_hui()
    with fabrique_de_sessions()() as s, s.begin():
        ligne = s.get(CommandeLigne, commande_ligne_id)
        assert ligne is not None
        m = s.get(Matiere, ligne.matiere_id)
        assert m is not None
        quarantaine = qualite == QualiteReception.reserve
        magasin = magasin_seme(TypeMagasin.quarantaine if quarantaine else "stock_courant", s=s)
        numero = numerotation.numero(s, SerieNumero.REC, jour)
        r = Reception(
            numero=numero,
            statut=StatutDocument.validee,
            date=jour,
            fournisseur_id=m.fournisseur_id,
            devise=m.devise,
            validee_le=horloge.maintenant(),
        )
        s.add(r)
        s.flush()
        lot = lots.lot_ou_creer(s, m.id, unique("L"), jour, fournisseur_id=m.fournisseur_id)
        s.add(
            ReceptionLigne(
                reception_id=r.id,
                commande_ligne_id=commande_ligne_id,
                matiere_id=m.id,
                lot_numero=lot.numero,
                quantite_pesee=Decimal(str(kg)),
                magasin_id=magasin,
                qualite=QualiteReception(qualite),
                lot_id=lot.id,
            )
        )
        s.flush()
        stock.ecrire(
            s,
            type=TypeMouvement.RECEPTION,
            lot=lot,
            magasin_id=magasin,
            quantite=Decimal(str(kg)),
            jour=jour,
            piece=stock.Piece(DocumentMouvement.reception, r.id, numero),
            auteur_id=None,
            prix=0,
            devise=m.devise,
        )
        recaler_soldes(s, None, {ligne.commande_id}, "réception")
        return r.id


def lot_de_reception(reception_id: int) -> int:
    """Le lot entré par une réception de `recevoir`."""
    with fabrique_de_sessions()() as s:
        lot = s.scalar(
            select(ReceptionLigne.lot_id).where(ReceptionLigne.reception_id == reception_id)
        )
        assert lot is not None
        return lot
