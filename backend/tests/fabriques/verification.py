"""Fabriques de la vérification indépendante (lot V1) : une petite usine qui exerce chaque règle
de valeur, et l'accès du vérificateur branché sur elle.

    from fabriques.pilotage import Usine, fixture_usine  # noqa: F401
    from fabriques.verification import AccesUsine, batir

    acces = AccesUsine(usine)       # l'API (direction) et le SQL dans la transaction de l'essai
    faits = batir(usine)            # le scénario ; rend les identifiants utiles aux fautes

Le scénario (jours avant le 8 octobre 2026) : une annulation du jour qui doit se rejouer juste
après son original, une ré-entrée sur stock vide, un retour au fournisseur au coût de son lot,
une entrée à coût nul, un dossier d'importation dont un frais se répartit au poids, deux
réceptions (une notée, une hors commande, donc non notée).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from fabriques.pilotage import Usine, jour
from sqlalchemy import select, text

from gestion_mp_pro.modeles import CommandeLigne, Mouvement, Utilisateur
from gestion_mp_pro.modeles.enums import TypeMouvement
from gestion_mp_pro.services import donnees_moteur, receptions, stock
from gestion_mp_pro.services.comptes import acteur_de
from gestion_mp_pro.services.receptions_saisie import LigneSaisie, Saisie

AUJOURDHUI = date(2026, 10, 8)


class AccesUsine:
    """L'accès du vérificateur dans une usine d'essai : l'API par le poste de la direction (le
    cache du moteur oublié avant chaque lecture), le SQL par la connexion de la transaction."""

    def __init__(self, usine: Usine) -> None:
        self.usine = usine

    def get(self, chemin: str, **params: Any) -> Any:
        """Une lecture de l'API ; un refus lève `RuntimeError` (comme l'accès réel). Le point de
        sauvegarde de l'usine est d'abord libéré : un refus (404 d'une table hors de la liste
        des données brutes) ne défait que la lecture, pas le scénario."""
        self.usine.s.commit()
        donnees_moteur.invalider()
        propres = {k: v for k, v in params.items() if v is not None}
        r = self.usine.direction.get("/api" + chemin, params=propres)
        if r.status_code != 200:
            raise RuntimeError(f"GET {chemin} : {r.status_code} {r.text[:300]}")
        return r.json()

    def sql(self, requete: str, params: Any = None) -> list[tuple[Any, ...]]:
        """Une lecture SQL (style psycopg) dans la transaction de l'essai."""
        self.usine.s.flush()
        brut = self.usine.s.connection().connection.driver_connection
        with brut.cursor() as c:  # type: ignore[union-attr]
            c.execute(requete, params)
            return [
                tuple(float(v) if isinstance(v, Decimal) else v for v in rang)
                for rang in c.fetchall()
            ]


@dataclass
class Faits:
    """Ce que les fautes injectées visent."""

    lot_a1: int
    lot_b1: int
    matiere_a: int
    dossier_id: int


def _valeurs(u: Usine) -> tuple[int, int, int]:
    """Annulation du jour (G1), ré-entrée sur stock vide (G2), retour fournisseur, coût nul."""
    a = u.matiere(prix="30")
    a1 = u.ouvrir(a, 100, 10, le=jour(-10))
    a2 = u.ouvrir(a, 100, 30, le=jour(-9))
    of1 = u.ordre("OF-V1-1", le=jour(-9))
    u.sortir(a1, 50, le=jour(-9), ordre_id=of1)
    entree_a2 = u.s.scalars(select(Mouvement).where(Mouvement.lot_id == a2.id)).one()
    stock.contrepasser_mouvements(u.s, [entree_a2], u.auteur)
    b = u.matiere(prix="50")
    b1 = u.ouvrir(b, 100, 10, le=jour(-8))
    of2 = u.ordre("OF-V1-2", le=jour(-7))
    u.sortir(b1, 100, le=jour(-7), ordre_id=of2)
    retour = stock.Liens(ordre_id=of2)
    u.ecrire(b1, 20, le=jour(-6), type_=TypeMouvement.RETOUR_MACHINE, liens=retour)
    c = u.matiere(prix="20")
    u.ouvrir(c, 100, 10, le=jour(-5))
    c2 = u.ouvrir(c, 100, 50, le=jour(-5))
    u.ecrire(c2, -40, le=jour(-4), type_=TypeMouvement.RETOUR_FOURNISSEUR)
    u.ouvrir(u.matiere(prix="0"), 10, 0, le=jour(-3))
    return a, a1.id, b1.id


def _dossier(u: Usine, a: int) -> int:
    """Deux marchandises de rapport valeur / poids différent ; le fret se répartit au poids."""
    u.s.execute(text("UPDATE poste_frais SET cle = 'poids' WHERE code = 'FRET'"))
    b = u.matiere(prix="12")
    d = u.dossier(
        arrivee=jour(-2),
        marchandises=((a, 1000, 60000), (b, 3000, 40000)),
        frais={"DD": 10000, "FRET": 8000, "TVA": 21000},
    )
    return d.id


def _receptions(u: Usine) -> None:
    """Une réception sur bon, à l'heure et complète (notée) ; une hors commande (non notée)."""
    f = u.fournisseur()
    m = u.matiere(prix="8", fournisseur_id=f)
    bon = u.commande(f, m, 500, le=jour(-20), promise=jour(-5))
    ligne = u.s.scalars(select(CommandeLigne.id).where(CommandeLigne.commande_id == bon)).one()
    utilisateur = u.s.get(Utilisateur, u.auteur)
    assert utilisateur is not None
    qui = acteur_de(utilisateur)
    for cl, kg in ((ligne, 500), (None, 80)):
        x = LigneSaisie(
            matiere_id=m,
            commande_ligne_id=cl,
            lot_numero=f"V1-{kg}",
            quantite_pesee=Decimal(kg),
            magasin_id=u.courant,
            prix=Decimal(8),
        )
        r = receptions.creer(u.s, qui, Saisie(jour(-6), f, [x]))[0]
        u.s.flush()
        receptions.valider(u.s, qui, r.id, r.version)


def batir(u: Usine) -> Faits:
    """Le scénario complet ; rend ce que les fautes visent."""
    a, a1, b1 = _valeurs(u)
    dossier = _dossier(u, a)
    _receptions(u)
    u.s.flush()
    return Faits(lot_a1=a1, lot_b1=b1, matiere_a=a, dossier_id=dossier)
