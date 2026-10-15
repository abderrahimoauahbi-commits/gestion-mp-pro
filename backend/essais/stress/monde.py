"""Le monde du simulateur : les trois postes, le catalogue lu par l'API, le hasard à graine.

Rien n'est gardé en mémoire qui ne puisse se relire par l'API : une reprise depuis le dump d'une
année repart de ce que l'application montre (bons ouverts, brouillons, lots en quarantaine,
réclamations ouvertes…), comme le ferait l'usine le lundi matin.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from essais.stress.socle import EchecGeste, Horloge, Journal, Poste

CODES = {"direction": "direction-1", "achats": "achats-12", "alimentation": "1234"}
"""Les codes des comptes d'essai (`tests/fabrique.py`)."""
IDENTIFIANTS = {
    "direction": "stress-direction",
    "achats": "stress-achats",
    "alimentation": "stress-alimentation",
}
NOMS = {
    "direction": "Direction (stress)",
    "achats": "Achats (stress)",
    "alimentation": "Alimentation (stress)",
}
SUFFIXE = " (stress)"
"""Tout élément de référentiel créé par la simulation porte ce suffixe (règle de Mohamed)."""


def code_alimentation(jour: date) -> str:
    """Le code de l'alimentation : remis à zéro chaque janvier (« 12AA »), « 1234 » au départ."""
    return CODES["alimentation"] if jour.year <= 2026 else f"12{jour.year % 100:02d}"


@dataclass
class Catalogue:
    """Ce que l'usine a sous la main (relu au départ de chaque année)."""

    matieres: dict[int, dict[str, Any]] = field(default_factory=dict)
    qualites: dict[int, dict[str, Any]] = field(default_factory=dict)
    fournisseurs: dict[int, dict[str, Any]] = field(default_factory=dict)
    metiers: dict[int, dict[str, Any]] = field(default_factory=dict)
    magasins: dict[str, list[int]] = field(default_factory=dict)
    motifs: dict[str, int] = field(default_factory=dict)
    postes_frais: dict[str, dict[str, Any]] = field(default_factory=dict)
    roles: dict[str, int] = field(default_factory=dict)
    reclamation_motifs: list[str] = field(default_factory=list)
    reclamation_issues: list[str] = field(default_factory=list)

    @property
    def courants(self) -> list[int]:
        """Les magasins de stock courant."""
        return self.magasins.get("stock_courant", [])

    @property
    def quarantaine(self) -> int:
        """Le magasin de quarantaine."""
        return self.magasins["quarantaine"][0]

    def de_stress(self, fiche: dict[str, Any]) -> bool:
        """Un élément créé par la simulation (modifiable), ou un référentiel de Mohamed (intact)."""
        return SUFFIXE in str(fiche.get("reference") or fiche.get("nom") or fiche.get("code") or "")


@dataclass
class Monde:
    """Ce que les gestes partagent."""

    app: Any
    horloge: Horloge
    journal: Journal
    hasard: random.Random
    postes: dict[str, Poste] = field(default_factory=dict)
    catalogue: Catalogue = field(default_factory=Catalogue)
    base: str = ""
    annee: int = 0
    seuil_approbation: float = 300000.0

    @property
    def D(self) -> Poste:  # noqa: N802 — comme API-PRO (D, A, L)
        """La direction."""
        return self.postes["direction"]

    @property
    def A(self) -> Poste:  # noqa: N802
        """Les achats."""
        return self.postes["achats"]

    @property
    def L(self) -> Poste:  # noqa: N802
        """L'alimentation des machines (téléphone)."""
        return self.postes["alimentation"]

    @property
    def jour(self) -> date:
        """Le jour de l'usine."""
        return self.horloge.jour

    @property
    def iso(self) -> str:
        """Le jour de l'usine en ISO."""
        return self.horloge.jour.isoformat()

    # --- hasard ------------------------------------------------------------------------------
    def chance(self, p: float) -> bool:
        """Vrai avec la probabilité `p`."""
        return self.hasard.random() < p

    def entre(self, a: float, b: float) -> float:
        """Un réel entre `a` et `b`."""
        return self.hasard.uniform(a, b)

    def entier(self, a: int, b: int) -> int:
        """Un entier entre `a` et `b` compris."""
        return self.hasard.randint(a, b)

    def choix(self, liste: list[Any]) -> Any:
        """Un élément au hasard."""
        return self.hasard.choice(liste)

    def echantillon(self, liste: list[Any], k: int) -> list[Any]:
        """`k` éléments distincts au plus."""
        return self.hasard.sample(liste, min(k, len(liste)))

    def bruit(self, valeur: float, ecart: float) -> float:
        """`valeur` × (1 ± ecart)."""
        return valeur * (1 + self.hasard.uniform(-ecart, ecart))

    # --- postes ------------------------------------------------------------------------------
    def poste(self, role: str) -> Poste:
        """Un poste connecté pour le rôle (code du jour)."""
        code = code_alimentation(self.jour) if role == "alimentation" else CODES[role]
        p = Poste(
            self.app,
            self.journal,
            self.horloge,
            role=role,
            identifiant=IDENTIFIANTS[role],
            code=code,
        )
        r = p.connecter()
        if not r.ok and role == "alimentation":
            for autre in (f"12{self.jour.year % 100 - 1:02d}", CODES["alimentation"]):
                r = p.connecter(autre)
                if r.ok:
                    break
        if not r.ok:
            raise EchecGeste(r, f"connexion impossible pour {role}")
        self.postes[role] = p
        return p

    def connecter_tous(self) -> None:
        """Les trois comptes se connectent (le lundi matin)."""
        for role in ("direction", "achats", "alimentation"):
            self.poste(role)

    # --- catalogue ---------------------------------------------------------------------------
    def lire_catalogue(self) -> None:
        """Relit matières, qualités, fournisseurs, métiers, magasins, motifs, postes de frais."""
        c = self.catalogue
        a = self.A
        c.matieres = {}
        for x in a.get("/matieres?actif=true"):
            fiche = a.get(f"/matieres/{x['id']}")
            c.matieres[fiche["id"]] = fiche
        c.qualites = {q["id"]: q for q in a.get("/qualites") if q.get("actif", True)}
        for q in a.get("/production/plan")["qualites"]:
            if q["id"] in c.qualites:
                c.qualites[q["id"]]["recette_conforme"] = q["recette_conforme"]
        c.fournisseurs = {f["id"]: f for f in a.get("/fournisseurs") if f.get("actif", True)}
        c.metiers = {x["id"]: x for x in a.get("/metiers") if x.get("actif", True)}
        c.magasins = {}
        for mag in a.get("/magasins"):
            if mag.get("actif", True):
                c.magasins.setdefault(mag["type"], []).append(mag["id"])
        lus = a.get("/motifs")
        c.motifs = {x["libelle"]: x["id"] for x in lus["motifs"]}
        c.reclamation_motifs = [x["code"] for x in lus["reclamation_motifs"]]
        c.reclamation_issues = [x["code"] for x in lus["reclamation_issues"]]
        c.postes_frais = {x["code"]: x for x in a.get("/postes-frais") if x.get("actif", True)}
        c.roles = {r["code"]: r["id"] for r in self.D.get("/classification")["roles"]}

    def matiere(self, ident: int) -> dict[str, Any]:
        """La fiche d'une matière (relue si elle manque au catalogue : créée en cours d'année)."""
        if ident not in self.catalogue.matieres:
            self.catalogue.matieres[ident] = self.A.get(f"/matieres/{ident}")
        return self.catalogue.matieres[ident]

    def unite_et_quantite(
        self, matiere: dict[str, Any], kilos: float, *, entamer: bool = True
    ) -> tuple[str, float]:
        """Comment l'atelier compte cette quantité : bobines entières, palette ou kilos."""
        poids = float(matiere.get("poids_bobine") or 0)
        par_palette = float(matiere.get("bobines_palette") or 0)
        if poids > 0 and par_palette > 0 and kilos >= 2 * poids * par_palette and self.chance(0.3):
            palettes = kilos / (poids * par_palette)
            return "palette", round(palettes, 1) if entamer else math.floor(palettes)
        if poids > 0:
            return "bobine", max(1, round(kilos / poids))
        return "kg", round(kilos, 1)

    def kilos_de(self, matiere: dict[str, Any], unite: str, quantite: float) -> float:
        """La quantité ramenée en kilos (pour les comptes du générateur)."""
        poids = float(matiere.get("poids_bobine") or 0)
        if unite == "bobine":
            return quantite * poids
        if unite == "palette":
            return quantite * poids * float(matiere.get("bobines_palette") or 0)
        return quantite
