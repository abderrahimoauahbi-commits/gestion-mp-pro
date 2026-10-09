"""Ce qui attend son dossier (route 188) : les factures dont la marchandise reçue n'est encore
dans aucun dossier — ou, pour un second camion, le dossier qu'elle rejoint —, et les réceptions
dont la facture n'est pas saisie (REGLES R-IMP-15 à R-IMP-18 ; défaut B-06).

Un fournisseur marocain (`fournisseurs.est_local`, la seule définition, A-23) n'a pas de dossier
d'importation : ses factures sont écartées (comptées), sauf à les demander — et sauf le second
camion d'une facture dont le dossier est déjà ouvert, qui se montre pour le rejoindre (B-06).
Les valeurs se disent devise par devise, jamais additionnées.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import Dossier, Facture, Fournisseur, Reception, ReceptionLigne
from gestion_mp_pro.modeles.enums import StatutDossier
from gestion_mp_pro.modeles.types import MONTANT, arrondir
from gestion_mp_pro.services.fournisseurs import est_local
from gestion_mp_pro.services.importations.libres import (
    factures_acceptees,
    lignes_libres,
    porteurs,
)
from gestion_mp_pro.services.importations.modele import (
    EnAttente,
    FactureARattacher,
    FamillePoids,
    Locaux,
    ReceptionCitee,
    ReceptionSansFacture,
    ValeurDevise,
)
from gestion_mp_pro.services.importations.socle import MatiereLue, matieres

Libres = list[tuple[ReceptionLigne, Reception]]


@dataclass
class _Tas:
    """Des lignes libres qui s'additionnent (une facture, ou une réception sans facture)."""

    receptions: dict[int, str] = field(default_factory=dict)
    lignes: int = 0
    lots: set[int | str] = field(default_factory=set)
    quantite: float = 0.0
    valeurs: dict[str, Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    familles: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    date: dt.date = dt.date.max

    def ajouter(self, x: ReceptionLigne, r: Reception, famille: str) -> None:
        """Une ligne libre de plus : son poids, sa valeur dans sa devise, sa famille."""
        self.receptions[r.id] = r.numero or ""
        self.lignes += 1
        self.lots.add(x.lot_id or x.lot_numero or f"ligne {x.id}")
        kg = float(x.quantite_pesee)
        self.quantite += kg
        self.valeurs[r.devise] += x.quantite_pesee * x.prix
        self.familles[famille] += kg
        self.date = min(self.date, r.date)

    def valeurs_lues(self) -> list[ValeurDevise]:
        """Les valeurs, une par devise."""
        return [
            ValeurDevise(d, float(arrondir(v, MONTANT))) for d, v in sorted(self.valeurs.items())
        ]


@dataclass
class _Lecture:
    """Le contexte d'une lecture de la marchandise libre."""

    fournisseurs: dict[int, Fournisseur]
    factures: dict[int, Facture]
    matieres: dict[int, MatiereLue]
    dossiers: dict[int, tuple[int, str]]

    def local(self, r: Reception) -> bool:
        """Le fournisseur de la réception est-il marocain ?"""
        f = self.fournisseurs[r.fournisseur_id]
        return est_local(f.pays, f.devise)


def _lecture(s: Session, libres: Libres) -> _Lecture:
    """Fournisseurs, factures, matières et porteurs des lignes libres (requêtes fixes)."""
    fournisseurs = {r.fournisseur_id for _, r in libres}
    factures = {r.facture_id for _, r in libres if r.facture_id}
    return _Lecture(
        fournisseurs={
            f.id: f for f in s.scalars(select(Fournisseur).where(Fournisseur.id.in_(fournisseurs)))
        },
        factures={f.id: f for f in s.scalars(select(Facture).where(Facture.id.in_(factures)))},
        matieres=matieres(s, (x.matiere_id for x, _ in libres)),
        dossiers={f: p[0] for f, p in porteurs(s, factures).items()},
    )


def _facture(fid: int, tas: _Tas, lu: _Lecture, local: bool) -> FactureARattacher:
    """Une facture en attente, ou le second camion qui rejoint son dossier."""
    f = lu.factures[fid]
    dossier = lu.dossiers.get(fid)
    return FactureARattacher(
        facture_id=fid,
        numero=f.numero,
        fournisseur_id=f.fournisseur_id,
        fournisseur=lu.fournisseurs[f.fournisseur_id].nom,
        date=tas.date,
        receptions=[
            ReceptionCitee(i, n) for i, n in sorted(tas.receptions.items(), key=lambda z: z[1])
        ],
        lignes=tas.lignes,
        lots=len(tas.lots),
        quantite=tas.quantite,
        valeurs=tas.valeurs_lues(),
        familles=[FamillePoids(k, v) for k, v in sorted(tas.familles.items(), key=lambda z: -z[1])],
        local=local,
        dossier_id=dossier[0] if dossier else None,
        dossier=dossier[1] if dossier else None,
    )


def _factures(libres: Libres, lu: _Lecture) -> list[FactureARattacher]:
    """Les lignes libres regroupées par facture, la plus récente d'abord."""
    tas: dict[int, _Tas] = {}
    locales: dict[int, bool] = {}
    for x, r in libres:
        if r.facture_id is None:
            continue
        tas.setdefault(r.facture_id, _Tas()).ajouter(x, r, lu.matieres[x.matiere_id].famille)
        locales[r.facture_id] = lu.local(r)
    lues = [_facture(fid, t, lu, locales[fid]) for fid, t in tas.items()]
    return sorted(lues, key=lambda f: (f.date, f.facture_id), reverse=True)


def _sans_facture(libres: Libres, lu: _Lecture) -> list[ReceptionSansFacture]:
    """Les réceptions dont la facture n'est pas saisie, la plus récente d'abord."""
    tas: dict[int, tuple[Reception, _Tas]] = {}
    for x, r in libres:
        if r.facture_id is None:
            tas.setdefault(r.id, (r, _Tas()))[1].ajouter(x, r, lu.matieres[x.matiere_id].famille)
    lues = [
        ReceptionSansFacture(
            reception_id=r.id,
            reception=r.numero or "",
            date=r.date,
            fournisseur_id=r.fournisseur_id,
            fournisseur=lu.fournisseurs[r.fournisseur_id].nom,
            numero_bl=r.numero_bl,
            local=lu.local(r),
            lignes=t.lignes,
            lots=len(t.lots),
            quantite=t.quantite,
            valeurs=t.valeurs_lues(),
        )
        for r, t in tas.values()
    ]
    return sorted(lues, key=lambda g: (g.date, g.reception_id), reverse=True)


def en_attente(s: Session, *, locaux: bool = False) -> EnAttente:
    """Ce qui attend son dossier (route 188) ; `locaux` montre aussi les fournisseurs marocains."""
    libres = lignes_libres(s)
    lu = _lecture(s, libres)
    gardees: Libres = []
    ecartees: set[int] = set()
    lignes_ecartees = 0
    for x, r in libres:
        rejoint = r.facture_id is not None and r.facture_id in lu.dossiers
        if lu.local(r) and not locaux and not rejoint:
            lignes_ecartees += 1
            if r.facture_id is not None:
                ecartees.add(r.facture_id)
            continue
        gardees.append((x, r))
    return EnAttente(
        factures=_factures(gardees, lu),
        sans_facture=_sans_facture(gardees, lu),
        locaux=Locaux(factures=len(ecartees), lignes=lignes_ecartees),
    )


def du_dossier(s: Session, d: Dossier) -> list[FactureARattacher]:
    """Le second camion des factures de ce dossier, à rattacher (locaux compris, anomalie
    5.10) ; rien pour un dossier clos, annulé ou saisi à la main."""
    if d.statut != StatutDossier.ouvert:
        return []
    acceptees = factures_acceptees(s, d)
    if not acceptees:
        return []
    libres = lignes_libres(s, factures=acceptees)
    return _factures(libres, _lecture(s, libres))
