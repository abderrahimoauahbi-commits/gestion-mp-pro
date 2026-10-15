"""Le décor de la tournée d'écran : les comptes d'essai et les enregistrements d'exemple.

- `inscrire_comptes` : un compte par rôle (`stress-ecran-direction`, `-achats`, `-alimentation`),
  code tiré au hasard, écrit dans la base d'essai (décor, comme `charge_serveur`) ; jamais dans
  une base qui ne finit pas par `_essai`.
- `contexte` : les identifiants que les fiches ouvrent (le lot le plus récent encore en stock, la
  matière la plus active, le dernier bon, la dernière réception validée…), les lots à étiqueter,
  les mois du bilan, et les mots que la recherche tape. Tout est **lu** en SQL, rien n'est écrit.
"""

from __future__ import annotations

import secrets
from datetime import date
from typing import Any

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

ROLES = ("direction", "achats", "alimentation")
PREFIXE_COMPTE = "stress-ecran"


def garde_fou(adresse: str) -> str:
    """Le nom de la base, qui doit finir par `_essai` (jamais la base en service)."""
    nom = make_url(adresse).database or ""
    if not (nom.startswith("gestion_mp_pro_") and nom.endswith("_essai")):
        raise SystemExit(f"Base refusée : « {nom} » (gestion_mp_pro_…_essai exigé)")
    return nom


def inscrire_comptes(adresse: str) -> dict[str, str]:
    """Un compte par rôle dans la base d'essai (code tiré au hasard) : identifiant → code."""
    from gestion_mp_pro.modeles import Utilisateur
    from gestion_mp_pro.modeles.enums import Role
    from gestion_mp_pro.services.comptes import hacher

    garde_fou(adresse)
    codes = {}
    moteur = create_engine(adresse, poolclass=NullPool)
    with Session(moteur) as s, s.begin():
        for role in ROLES:
            code = (
                f"{secrets.randbelow(10_000):04d}"
                if role == "alimentation"
                else secrets.token_urlsafe(12)
            )
            ident = f"{PREFIXE_COMPTE}-{role}"
            u = s.scalar(select(Utilisateur).where(Utilisateur.identifiant == ident))
            if u is None:
                u = Utilisateur(identifiant=ident, nom=f"Stress écran {role}", role=Role(role))
                s.add(u)
            u.empreinte_code = hacher(code)
            u.actif = True
            codes[ident] = code
    moteur.dispose()
    return codes


def retirer_comptes(adresse: str) -> None:
    """Retire les comptes de la tournée (une base gardée ne doit pas les conserver)."""
    garde_fou(adresse)
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.begin() as c:
        c.execute(
            text(
                "DELETE FROM session WHERE utilisateur_id IN "
                "(SELECT id FROM utilisateur WHERE identifiant LIKE :motif)"
            ),
            {"motif": f"{PREFIXE_COMPTE}-%"},
        )
        c.execute(
            text("DELETE FROM tentative WHERE identifiant LIKE :motif"),
            {"motif": f"{PREFIXE_COMPTE}-%"},
        )
        # Le journal cite ces comptes (connexions) : on les désactive, on ne les efface pas.
        c.execute(
            text(
                "UPDATE utilisateur SET actif = false, empreinte_code = '' "
                "WHERE identifiant LIKE :motif"
            ),
            {"motif": f"{PREFIXE_COMPTE}-%"},
        )
    moteur.dispose()


def _un(c: Connection, sql: str, **p: Any) -> Any:
    """La première valeur d'une requête, ou `None`."""
    return c.execute(text(sql), p).scalar()


_REQUETES: dict[str, str] = {
    "lot": (
        "SELECT l.id FROM lot l JOIN solde s ON s.lot_id = l.id "
        "WHERE s.quantite > 0 ORDER BY l.id DESC LIMIT 1"
    ),
    "matiere": (
        "SELECT matiere_id FROM lot GROUP BY matiere_id ORDER BY count(*) DESC, matiere_id LIMIT 1"
    ),
    "commande": (
        "SELECT id FROM commande WHERE statut IN ('confirmee', 'envoyee', 'soldee') "
        "ORDER BY id DESC LIMIT 1"
    ),
    "reception": "SELECT id FROM reception WHERE statut = 'validee' ORDER BY id DESC LIMIT 1",
    "dossier": "SELECT id FROM dossier ORDER BY id DESC LIMIT 1",
    "qualite": (
        "SELECT q.id FROM qualite q WHERE q.actif AND EXISTS "
        "(SELECT 1 FROM recette r WHERE r.qualite_id = q.id) ORDER BY q.id LIMIT 1"
    ),
    "metier": "SELECT id FROM metier WHERE actif ORDER BY id LIMIT 1",
    "ordre": "SELECT id FROM ordre WHERE statut = 'valide' ORDER BY id DESC LIMIT 1",
    "fournisseur": (
        "SELECT fournisseur_id FROM matiere WHERE fournisseur_id IS NOT NULL AND actif "
        "GROUP BY fournisseur_id ORDER BY count(*) DESC LIMIT 1"
    ),
    "inventaire": "SELECT id FROM inventaire ORDER BY id DESC LIMIT 1",
    "reclamation": "SELECT id FROM reclamation ORDER BY id DESC LIMIT 1",
    "operation": "SELECT id FROM operation ORDER BY id DESC LIMIT 1",
    "signalement": "SELECT id FROM signalement ORDER BY id DESC LIMIT 1",
}
"""Pour chaque fiche, l'enregistrement d'exemple le plus parlant (le plus récent, en stock…)."""

_REPLIS: dict[str, str] = {
    "lot": "SELECT id FROM lot ORDER BY id DESC LIMIT 1",
    "matiere": "SELECT id FROM matiere WHERE actif ORDER BY id LIMIT 1",
    "commande": "SELECT id FROM commande ORDER BY id DESC LIMIT 1",
    "reception": "SELECT id FROM reception ORDER BY id DESC LIMIT 1",
    "qualite": "SELECT id FROM qualite ORDER BY id LIMIT 1",
    "ordre": "SELECT id FROM ordre ORDER BY id DESC LIMIT 1",
    "fournisseur": "SELECT id FROM fournisseur ORDER BY id LIMIT 1",
}
"""Quand la base n'a pas l'enregistrement idéal (référentiels seuls) : n'importe lequel."""


def _identifiants(c: Connection) -> dict[str, int | None]:
    ids: dict[str, int | None] = {}
    for nom, sql in _REQUETES.items():
        valeur = _un(c, sql)
        if valeur is None and nom in _REPLIS:
            valeur = _un(c, _REPLIS[nom])
        ids[nom] = None if valeur is None else int(valeur)
    return ids


def _mots(c: Connection, ids: dict[str, int | None]) -> dict[str, str]:
    """Les mots que la recherche tape : tirés de la base, donc toujours trouvables."""
    designation = _un(c, "SELECT designation FROM matiere WHERE id = :id", id=ids["matiere"]) or ""
    reference = _un(c, "SELECT reference FROM matiere WHERE id = :id", id=ids["matiere"]) or ""
    fournisseur = _un(c, "SELECT nom FROM fournisseur WHERE id = :id", id=ids["fournisseur"]) or ""
    lot = _un(c, "SELECT numero FROM lot WHERE id = :id", id=ids["lot"]) or ""
    bon = _un(c, "SELECT numero FROM commande WHERE id = :id", id=ids["commande"]) or ""
    premier = lambda t: (str(t).split() or [""])[0]  # noqa: E731
    return {
        "defaut": premier(reference) or premier(designation) or "a",
        "reference": premier(reference),
        "fournisseur": premier(fournisseur),
        "lot": str(lot)[:12],
        "bon": str(bon)[:12] or "BC-",
        "global": premier(fournisseur) or premier(reference) or "a",
    }


def _mois(jour: date) -> list[str]:
    """Le mois en cours et le précédent (bilan du mois), en `AAAA-MM`."""
    premier = jour.replace(day=1)
    if premier.month == 1:
        precedent = premier.replace(year=premier.year - 1, month=12)
    else:
        precedent = premier.replace(month=premier.month - 1)
    return [jour.strftime("%Y-%m"), precedent.strftime("%Y-%m")]


def contexte(adresse: str, jour: date) -> dict[str, Any]:
    """Les enregistrements d'exemple, les lots à étiqueter, les mois, les mots de recherche."""
    garde_fou(adresse)
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.connect() as c:
        ids = _identifiants(c)
        lots_reception = [
            int(r[0])
            for r in c.execute(
                text(
                    "SELECT lot_id FROM reception_ligne WHERE reception_id = :r "
                    "AND lot_id IS NOT NULL ORDER BY id LIMIT 6"
                ),
                {"r": ids["reception"] or 0},
            )
        ]
        if not lots_reception:
            lots_reception = [
                int(r[0]) for r in c.execute(text("SELECT id FROM lot ORDER BY id DESC LIMIT 6"))
            ]
        comptes = {
            t: int(_un(c, f"SELECT count(*) FROM {t}") or 0)  # noqa: S608
            for t in (
                "matiere",
                "lot",
                "mouvement",
                "commande",
                "reception",
                "ordre",
                "dossier",
                "inventaire",
                "operation",
                "journal",
            )  # fmt: skip
        }
        mots = _mots(c, ids)
    moteur.dispose()
    return {
        "ids": ids,
        "lots_etiquettes": lots_reception,
        "mois": _mois(jour),
        "mots": mots,
        "comptes": comptes,
        "jour": jour.isoformat(),
    }
