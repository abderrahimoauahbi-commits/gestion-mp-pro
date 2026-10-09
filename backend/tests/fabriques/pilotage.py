"""Fabriques du pilotage et du suivi (lot D8) : une usine **isolée** pour éprouver les chiffres.

Le Cockpit, la valorisation, les contrôles et le bilan additionnent **toute** la base : sur la
base d'essai partagée par la séance, un total exact n'aurait pas de sens. La fixture `usine`
ouvre une transaction, vide l'activité et les référentiels non semés (comptes et sessions
gardés), et branche l'application sur cette transaction (`db.session` remplacée) : les routes
travaillent pour de vrai — droits, schémas, services — sur une usine connue ; tout est annulé à
la fin. Pas d'écriture par une autre session pendant l'essai (elle attendrait les verrous du
vidage) : passer `s=u.s` aux fabriques de référentiels.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import base_connue
import pytest
from fabrique import client_de
from fabriques import referentiels as ref
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro import db
from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Dossier,
    DossierFrais,
    DossierLigne,
    Lot,
    Magasin,
    Metier,
    MetierEtage,
    Montage,
    Mouvement,
    Ordre,
    PosteFrais,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import (
    DocumentMouvement,
    OrigineCours,
    Role,
    StatutCommande,
    StatutDossier,
    StatutOrdre,
    TypeMagasin,
    TypeMouvement,
)
from gestion_mp_pro.services import donnees_moteur, horloge, lots, stock

JOUR = date(2026, 10, 8)
REPRISE = stock.Piece(DocumentMouvement.reprise, None, "")


def jour(decalage: int = 0) -> date:
    """Le jour des essais décalé (−1 : hier)."""
    return JOUR + timedelta(days=decalage)


def ok(r: Any, code: int = 200) -> Any:
    """Le code attendu, puis le JSON (rien pour un 204)."""
    assert r.status_code == code, r.text
    return None if code == 204 or not r.content else r.json()


def vider_activite(s: Session) -> None:
    """La base d'une installation neuve dans la transaction (`base_connue.remettre`) : activité
    et référentiels vidés, réglages à leur défaut, un magasin par type, comptes gardés."""
    base_connue.remettre(s.connection())


@dataclass
class Usine:
    """L'usine de l'essai : sa session (même transaction que l'API) et des postes connectés."""

    s: Session
    direction: TestClient
    achats: TestClient
    alimentation: TestClient
    administrateur: TestClient

    def get(self, client: TestClient, url: str, code: int = 200, **params: Any) -> Any:
        """Une lecture (cache du moteur oublié d'abord : les fabriques écrivent sans journal)."""
        self.s.flush()
        donnees_moteur.invalider()
        return ok(client.get(url, params=params), code)

    @property
    def courant(self) -> int:
        """Le magasin courant semé."""
        return self._magasin(TypeMagasin.stock_courant)

    @property
    def quarantaine(self) -> int:
        """Le magasin de quarantaine semé."""
        return self._magasin(TypeMagasin.quarantaine)

    def _magasin(self, genre: TypeMagasin) -> int:
        trouve = self.s.scalar(select(Magasin.id).where(Magasin.type == genre))
        assert trouve is not None
        return int(trouve)

    def matiere(self, reference: str | None = None, **champs: Any) -> int:
        """Une matière en service (fournisseur créé d'office), dans la transaction."""
        return ref.matiere(reference, s=self.s, **champs)

    def fournisseur(self, nom: str | None = None, **champs: Any) -> int:
        """Un fournisseur, dans la transaction."""
        return ref.fournisseur(nom, s=self.s, **champs)

    def lot(self, matiere_id: int, numero: str | None = None, le: date = JOUR) -> Lot:
        """Un lot de la matière."""
        return lots.lot_ou_creer(self.s, matiere_id, numero or ref.unique("L"), le)

    @property
    def auteur(self) -> int:
        """Le compte de la direction (auteur des écritures des fabriques)."""
        trouve = self.s.scalar(select(Utilisateur.id).where(Utilisateur.identifiant == "direction"))
        assert trouve is not None
        return int(trouve)

    def ecrire(
        self, x: Lot, kg: float | str, *, le: date = JOUR, prix: float | str = 0,
        type_: TypeMouvement = TypeMouvement.OUVERTURE, magasin_id: int | None = None,
        devise: str = "MAD", auteur: bool = True, liens: stock.Liens | None = None,
    ) -> Mouvement:  # fmt: skip
        """Une écriture de stock par le seul chemin (sans document : stock repris)."""
        return stock.ecrire(
            self.s, type=type_, lot=x, magasin_id=magasin_id or self.courant,
            quantite=Decimal(str(kg)), jour=le, piece=REPRISE,
            auteur_id=self.auteur if auteur else None, prix=Decimal(str(prix)), devise=devise,
            liens=liens or stock.Liens(),
        )  # fmt: skip

    def ouvrir(self, matiere_id: int, kg: float, prix: float, le: date = JOUR) -> Lot:
        """Un lot ouvert : `kg` à `prix` MAD le kilo."""
        x = self.lot(matiere_id, le=le)
        self.ecrire(x, kg, le=le, prix=prix)
        return x

    def sortir(self, x: Lot, kg: float, le: date = JOUR, ordre_id: int | None = None) -> Mouvement:
        """Une sortie vers les machines (rattachée à un ordre s'il est donné)."""
        liens = stock.Liens(ordre_id=ordre_id)
        return self.ecrire(x, -kg, le=le, type_=TypeMouvement.SORTIE, liens=liens)

    def ordre(self, numero: str, le: date = JOUR) -> int:
        """Un ordre validé posé en base (numéro donné)."""
        o = Ordre(
            numero=numero,
            statut=StatutOrdre.valide,
            date=le,
            magasin_id=self.courant,
            valide_le=datetime.combine(le, time(12), tzinfo=horloge.FUSEAU),
            valide_par_id=self.auteur,
        )
        self.s.add(o)
        self.s.flush()
        return o.id

    def commande(
        self,
        fournisseur_id: int,
        matiere_id: int,
        kg: float,
        *,
        le: date,
        promise: date | None = None,
        numero: str | None = None,
    ) -> int:
        """Un bon parti (envoyé), une ligne, posé en base."""
        c = Commande(
            numero=numero or ref.unique("BC"),
            fournisseur_id=fournisseur_id,
            statut=StatutCommande.envoyee,
            date_commande=le,
            date_livraison_prevue=promise,
            devise="MAD",
        )
        self.s.add(c)
        self.s.flush()
        self.s.add(
            CommandeLigne(
                commande_id=c.id, matiere_id=matiere_id, quantite=Decimal(kg), prix=Decimal(10)
            )
        )
        self.s.flush()
        return c.id

    def dossier(
        self,
        *,
        arrivee: date | None = None,
        marchandises: tuple[tuple[int, float, float], ...] = (),
        frais: dict[str, float] | None = None,
        facture_id: int | None = None,
        devise: str = "MAD",
        cours: float | None = None,
    ) -> Dossier:
        """Un dossier d'importation ouvert posé en base : marchandises (matière, kg, valeur en
        devise), frais par code de poste (MAD)."""
        d = Dossier(
            numero=ref.unique("ANC-D8"),
            saisi_a_la_main=True,
            date_arrivee=arrivee,
            statut=StatutDossier.ouvert,
            facture_id=facture_id,
        )
        self.s.add(d)
        self.s.flush()
        for mid, kg, valeur in marchandises:
            self.s.add(
                DossierLigne(
                    dossier_id=d.id,
                    matiere_id=mid,
                    quantite_kg=Decimal(str(kg)),
                    valeur_devise=Decimal(str(valeur)),
                    devise=devise,
                    cours=Decimal(str(cours)) if cours else None,
                    cours_origine=OrigineCours.banque if cours else None,
                )
            )
        for code, montant in (frais or {}).items():
            poste = self.s.scalar(select(PosteFrais.id).where(PosteFrais.code == code))
            self.s.add(DossierFrais(dossier_id=d.id, poste_id=poste, montant=Decimal(str(montant))))
        self.s.flush()
        return d

    def metier(
        self,
        *,
        laize: float = 4,
        bobines_par_metre: float = 10,
        etages: int = 3,
        fils: tuple[tuple[int, int, float], ...] = (),
    ) -> Metier:
        """Un métier et son montage posés en base : fils (étage, matière, mètres)."""
        m = Metier(
            code=ref.unique("M"),
            laize=Decimal(str(laize)),
            bobines_par_metre=Decimal(str(bobines_par_metre)),
            etages=etages,
        )
        self.s.add(m)
        self.s.flush()
        for etage in sorted({e for e, _, _ in fils}):
            self.s.add(MetierEtage(metier_id=m.id, etage=etage))
        self.s.flush()
        for etage, mid, metres in fils:
            self.s.add(
                Montage(metier_id=m.id, etage=etage, matiere_id=mid, metres=Decimal(str(metres)))
            )
        self.s.flush()
        return m


@pytest.fixture(name="usine")
def fixture_usine(application: FastAPI) -> Iterator[Usine]:
    """Une usine vide dans une transaction annulée à la fin, servie par l'application."""
    postes = {r: client_de(application, r) for r in Role}
    with db.moteur().connect() as c:
        transaction = c.begin()
        s = Session(bind=c, join_transaction_mode="create_savepoint", expire_on_commit=False)

        def session_d_essai() -> Iterator[Session]:
            try:
                yield s
                s.commit()
            except BaseException:
                s.rollback()
                raise

        vider_activite(s)
        donnees_moteur.invalider()
        application.dependency_overrides[db.session] = session_d_essai
        try:
            yield Usine(
                s, postes[Role.direction], postes[Role.achats], postes[Role.alimentation],
                postes[Role.administrateur],
            )  # fmt: skip
        finally:
            application.dependency_overrides.pop(db.session, None)
            s.close()
            transaction.rollback()
            donnees_moteur.invalider()
