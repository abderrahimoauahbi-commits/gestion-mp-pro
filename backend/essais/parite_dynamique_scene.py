"""Parité dynamique : la scène (choix des pièces dans les données, photos, ids créés)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from parite_api_documents import documents
from parite_api_formes import aujourdhui
from parite_dynamique_outils import Journal, comparer_photos, photo
from parite_serveurs import Serveurs

LOT = "PARITE-R1"
FACTURE = "F-PARITE-1"


def _liste(nom: str) -> Any:
    return next(r.liste for r in documents() if r.nom == nom)


def choisir(s: Serveurs) -> dict[str, Any]:
    """Le bon (confirmé, en dollars, une ligne d'au moins 1 000 kg à recevoir), son fournisseur,
    sa matière, le magasin principal, et les identifiants de PRO (motif, poste de frais)."""
    g, p = s.gestion_mp["direction"], s.pro["direction"]
    bon, ligne = next(
        (c, x) for c in g.get("/api/commandes")
        if c["statut"] == "confirmee" and c["devise"] == "USD"
        for x in c["lignes"] if x["reste"] >= 1000  # noqa: PLR2004
    )  # fmt: skip
    magasin = next(m for m in g.get("/api/magasins") if m["type"] == "Stock courant")
    motifs = p.get("/api/motifs")["motifs"]
    motif = next(m["id"] for m in motifs if m["libelle"] == "Reliquat de fin d'ordre")
    poste = next(x["id"] for x in p.get("/api/postes-frais") if x["code"] == "FRET")
    autre = next(
        x for x in g.get("/api/soldes")
        if x["article_id"] != ligne["article_id"] and x["disponible"] > 100  # noqa: PLR2004
        and x["magasins"][0]["magasin_id"] == magasin["id"]
    )  # fmt: skip
    return {"bon": bon, "ligne": ligne, "fournisseur": bon["fournisseur_id"],
            "matiere": ligne["article_id"], "reference": ligne["reference"],
            "magasin": magasin["id"], "motif": motif, "poste": poste, "autre": autre,
            "jour": aujourdhui().isoformat()}  # fmt: skip


def _photos(s: Serveurs, refs: set[str], lots: set[int]) -> tuple[dict[str, Any], dict[str, Any]]:
    return (photo(s.gestion_mp["direction"], False, refs, lots),
            photo(s.pro["direction"], True, refs, lots))  # fmt: skip


class Scene:
    """Le scénario en cours : les deux serveurs, le journal, ce qui a été créé."""

    def __init__(self, s: Serveurs) -> None:
        self.s, self.j, self.ctx = s, Journal(), choisir(s)
        self.refs = {self.ctx["reference"], self.ctx["autre"]["reference"]}
        self.lots: set[int] = {self.ctx["autre"]["lot_id"]}
        self.ids: dict[str, tuple[int, int]] = {}
        self.k2: Any = None

    def geste(self, nom: str, faire: Callable[[], None]) -> None:
        """Un geste : photos avant et après, ce qu'il a changé comparé des deux côtés."""
        avant = _photos(self.s, self.refs, self.lots)
        faire()
        comparer_photos(self.j, nom, avant, _photos(self.s, self.refs, self.lots))

    def version_pro(self, chemin: str) -> int:
        """La version d'un document de PRO (verrou optimiste)."""
        return int(self.s.pro["direction"].get(chemin)["version"])
