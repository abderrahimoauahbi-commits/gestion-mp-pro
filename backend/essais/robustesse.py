"""Robustesse des entrées (lot V5, critère A13 de PLAN-DE-RECETTE-PRO § 11.6).

On génère des corps de requête **depuis l'OpenAPI** (types faux, bornes, chaînes vides, unicode,
nombres énormes, objets trop profonds) et on tape chaque route d'écriture avec chacun des rôles
qui y a droit. La seule exigence : **jamais d'erreur 500**. Un refus propre (422 saisie, 409
contrainte de la base ou version périmée, 400/404/403/401) est permis et attendu — c'est le filet
de `api/erreurs.py` (héritage : défaut F-08 de Gestion MP, « une contrainte de base donne une
500 »).

Les identifiants de chemin ne désignent rien (999999), donc une requête bien formée n'écrit
jamais une vraie ligne métier : elle bute sur un 404/409. Les corps sont presque tous invalides,
donc rejetés à la validation (422) avant la base.

Lancement :
- en mémoire (défaut) : `python -m essais.robustesse` depuis `backend/` ;
- sur un serveur réel : `python -m essais.robustesse --serveur http://127.0.0.1:8050`.

Code de sortie : 0 si aucune 500, 1 si au moins une, 2 si l'épreuve n'a pas pu se mettre en place.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

Schema = dict[str, Any]

# Caractères hostiles construits par code (nuls, émoji, forçage bidirectionnel) : écrits par
# `chr()` pour ne pas poser de caractère de contrôle dans le source.
_NULS = chr(0) + chr(1) + chr(2)
_UNICODE = "✓ " + chr(0x1F600) + chr(0x202E) + " rtl \t\n"

# Valeurs hostiles, indépendantes du schéma : chacune est envoyée telle quelle comme corps entier.
CORPS_GLOBAUX: tuple[Any, ...] = (
    {},
    [],
    "texte",
    1234567890,
    True,
    None,
    {chr(0) + "clef": chr(0)},
    {"profond": {"profond": {"profond": {"profond": {"profond": [1, 2, 3]}}}}},
    {"x" * 300: "y" * 5000},
    {"inconnu": _UNICODE},
)

# Valeurs hostiles par type JSON déclaré d'un champ.
FAUX_PAR_TYPE: dict[str, tuple[Any, ...]] = {
    "string": (12345, [], {}, None, "", "a" * 5000, _NULS, _UNICODE),
    "integer": ("pas un entier", 10**50, -(10**50), 1.5, None, [], {}),
    "number": ("pas un nombre", 1e308, -1e308, float("inf"), None, [], "NaN"),
    "boolean": ("peut-être", 2, None, [], {}),
    "array": ("pas une liste", 1, {}, None, [None] * 500),
    "object": ("pas un objet", 1, [], None),
}


@dataclass
class Route:
    """Une route d'écriture de l'OpenAPI : méthode, chemin et schéma de corps résolu."""

    methode: str
    chemin: str
    corps: Schema | None


@dataclass
class Rapport:
    """Le relevé d'une campagne : requêtes envoyées, routes couvertes, 500 trouvées."""

    envois: int = 0
    routes: int = 0
    cas: int = 0
    cinq_cents: list[str] = field(default_factory=list)

    def lignes(self) -> list[str]:
        """Les lignes du rapport, pour la sortie standard."""
        tete = [
            f"{self.routes} routes d'écriture, {self.cas} corps générés, {self.envois} envois.",
            f"Erreurs 500 : {len(self.cinq_cents)}.",
        ]
        return tete + [f"  500 — {x}" for x in self.cinq_cents]


def _resoudre(schema: Schema | None, composants: dict[str, Schema], vus: frozenset[str]) -> Schema:
    """Déréférence un `$ref` (une fois par nom, pour éviter les schémas récursifs)."""
    if not schema:
        return {}
    ref = schema.get("$ref")
    if isinstance(ref, str):
        nom = ref.rsplit("/", 1)[-1]
        if nom in vus:
            return {}
        return _resoudre(composants.get(nom, {}), composants, vus | {nom})
    for cle in ("allOf", "anyOf", "oneOf"):
        if cle in schema and isinstance(schema[cle], list) and schema[cle]:
            return _resoudre(schema[cle][0], composants, vus)
    return schema


def _type_de(schema: Schema) -> str:
    """Le type JSON d'un champ (sans `null`), `string` par défaut."""
    t = schema.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    return t if isinstance(t, str) else "string"


def corps_hostiles(schema: Schema | None, composants: dict[str, Schema]) -> Iterator[Any]:
    """Les corps hostiles pour un schéma de requête : globaux, puis un champ faussé à la fois."""
    yield from CORPS_GLOBAUX
    resolu = _resoudre(schema, composants, frozenset())
    proprietes = resolu.get("properties")
    if not isinstance(proprietes, dict):
        return
    requis = [c for c in resolu.get("required", []) if isinstance(c, str)]
    for champ, sous in list(proprietes.items())[:25]:
        sous_resolu = _resoudre(sous, composants, frozenset())
        for faux in FAUX_PAR_TYPE.get(_type_de(sous_resolu), ("texte", 1, None))[:4]:
            corps = {r: None for r in requis}
            corps[champ] = faux
            yield corps
    yield {r: None for r in requis}


def routes_ecriture(openapi: Schema) -> Iterator[Route]:
    """Les routes POST/PUT/PATCH/DELETE de l'API, avec le schéma JSON de leur corps."""
    composants = openapi.get("components", {}).get("schemas", {})
    for chemin, operations in sorted(openapi.get("paths", {}).items()):
        if not chemin.startswith("/api/"):
            continue
        for methode, op in operations.items():
            if methode.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
                continue
            contenu = (op.get("requestBody") or {}).get("content", {})
            schema = (contenu.get("application/json") or {}).get("schema")
            yield Route(methode.upper(), chemin, _resoudre(schema, composants, frozenset()) or None)


def _chemin_sans_parametre(chemin: str) -> str:
    """Remplit les paramètres de chemin par des valeurs qui ne désignent rien."""
    import re

    return re.sub(r"\{[^}]*\}", lambda g: "zz" if "code" in g.group(0) else "999999", chemin)


class Taper:
    """Un tapeur de routes : en mémoire (TestClient) ou sur un serveur réel (httpx)."""

    def __init__(self, clients: dict[str, Any]) -> None:
        self._clients = clients

    @property
    def roles(self) -> list[str]:
        """Les rôles connectés disponibles."""
        return list(self._clients)

    def envoyer(self, role: str, methode: str, chemin: str, corps: Any) -> int:
        """Envoie une requête et rend le code HTTP (0 si le transport a échoué sans réponse)."""
        client = self._clients[role]
        try:
            reponse = client.request(methode, chemin, json=corps)
        except Exception:  # noqa: BLE001 — un transport cassé n'est pas une 500 du serveur
            return 0
        return int(reponse.status_code)


def _permis(matrice: Any, app: Any) -> dict[tuple[str, str], list[str]]:
    """Pour chaque (méthode, chemin), les rôles dont la matrice dit « ok »."""
    from gestion_mp_pro.modeles.enums import Role

    permis: dict[tuple[str, str], list[str]] = {}
    for ligne in matrice(app):
        roles = [r.value for r in Role if ligne.attendu(r.value) == "ok"]
        if roles:
            permis[(ligne.methode, ligne.chemin)] = roles
    return permis


def campagne(taper: Taper, openapi: Schema, permis: dict[tuple[str, str], list[str]]) -> Rapport:
    """Tape chaque route d'écriture, par chaque rôle permis, avec tous ses corps hostiles."""
    rapport = Rapport()
    composants = openapi.get("components", {}).get("schemas", {})
    for route in routes_ecriture(openapi):
        roles = permis.get((route.methode, route.chemin))
        if not roles:
            continue
        rapport.routes += 1
        cibles = [r for r in roles if r in taper.roles] or taper.roles[:1]
        corps = list(corps_hostiles(route.corps, composants))
        rapport.cas += len(corps)
        url = _chemin_sans_parametre(route.chemin)
        for role in cibles:
            for un_corps in corps:
                rapport.envois += 1
                code = taper.envoyer(role, route.methode, url, un_corps)
                if code >= 500:
                    rapport.cinq_cents.append(
                        f"{route.methode} {route.chemin} [{role}] → {code} (corps {un_corps!r:.80})"
                    )
    return rapport


def _clients_memoire(app: Any) -> dict[str, Any]:
    """Un TestClient connecté par rôle, sur des comptes à soi (comme la matrice des droits)."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))
    from fabrique import CODES, compte, connecter  # type: ignore[import-not-found]

    from gestion_mp_pro.modeles.enums import Role

    clients: dict[str, Any] = {}
    for role in Role:
        ident = f"robustesse-{role.value}-{uuid4().hex[:8]}"
        compte(role, identifiant=ident)
        clients[role.value] = connecter(app, ident, CODES[role])
    return clients


def verifier_en_memoire() -> Rapport:
    """Monte l'application d'essai, connecte un client par rôle et lance la campagne."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))
    import conftest  # noqa: F401 — règle les variables d'environnement et le garde-fou _essai

    from gestion_mp_pro.main import creer_application
    from gestion_mp_pro.securite.matrice import matrice

    conftest.preparer_schema()
    app = creer_application()
    taper = Taper(_clients_memoire(app))
    return campagne(taper, app.openapi(), _permis(matrice, app))


def verifier_sur_serveur(base_url: str, codes: dict[str, str]) -> Rapport:
    """Tape un serveur déjà en marche ; `codes` donne le code de connexion de chaque rôle."""
    import httpx

    from gestion_mp_pro.config import ENTETE_ANTI_FALSIFICATION

    clients: dict[str, Any] = {}
    for role, code in codes.items():
        client = httpx.Client(base_url=base_url, headers={ENTETE_ANTI_FALSIFICATION: "1"})
        reponse = client.post("/api/connexion", json={"identifiant": role, "code": code})
        if reponse.status_code == 200:
            clients[role] = client
    if not clients:
        raise SystemExit(2)
    openapi = httpx.get(f"{base_url}/openapi.json").json()
    permis = {
        (m.upper(), c): list(clients)
        for c, ops in openapi.get("paths", {}).items()
        for m in ops
        if m.upper() in {"POST", "PUT", "PATCH", "DELETE"}
    }
    return campagne(Taper(clients), openapi, permis)


def main(arguments: list[str] | None = None) -> int:
    """Lance l'épreuve ; 0 sans 500, 1 avec, 2 si l'épreuve n'a pas pu démarrer."""
    args = sys.argv[1:] if arguments is None else arguments
    try:
        if "--serveur" in args:
            url = args[args.index("--serveur") + 1]
            rapport = verifier_sur_serveur(
                url,
                {"direction": "direction-1", "achats": "achats-12", "alimentation": "1234"},
            )
        else:
            rapport = verifier_en_memoire()
    except SystemExit as sortie:
        sys.stderr.write("L'épreuve de robustesse n'a pas pu démarrer.\n")
        return int(sortie.code or 2)
    sys.stdout.write("\n".join(rapport.lignes()) + "\n")
    return 1 if rapport.cinq_cents else 0


if __name__ == "__main__":
    sys.exit(main())
