"""Le monde du scénario (lot V2) : les postes connectés, le calendrier du mois, les fiches créées.

Le mois joué est **novembre 2026**, après la fin de l'année d'essai (dernier mouvement le
2 octobre 2026) : le bilan du mois ne contient que les gestes du scénario, et chaque valeur
attendue se calcule à la main. Le scénario crée ses propres fournisseur, matières, qualités et
métier (préfixe `SCN`) : rien de l'année d'essai n'entre dans ses calculs, sauf les totaux de
l'usine (valeur du stock, nombres d'anomalies), vérifiés comme « avant + variation calculée ».
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from scenario_outils import Horloge, Poste, Verif

JOURS = {
    "referentiels": date(2026, 11, 2),
    "plan_revise": date(2026, 11, 10),
    "confirmation_1": date(2026, 11, 11),
    "cours_change": date(2026, 11, 12),
    "confirmation_2": date(2026, 11, 12),
    "expedition": date(2026, 11, 13),
    "camion": date(2026, 11, 19),
    "liberation": date(2026, 11, 20),
    "dossier": date(2026, 11, 20),
    "montage": date(2026, 11, 23),
    "ordres": date(2026, 11, 23),
    "retour_machine": date(2026, 11, 24),
    "retour_fournisseur": date(2026, 11, 25),
    "reclamation": date(2026, 11, 25),
    "inventaire": date(2026, 11, 26),
    "annulation_ordre": date(2026, 11, 27),
    "reglements": date(2026, 11, 30),
    "cloture": date(2026, 12, 1),
}
"""Le calendrier du mois (jours ouvrés de novembre 2026)."""

COMPTES = {
    "D": ("scn-direction", "Mohamed (scénario)", "direction", "Direction-2026"),
    "A": ("scn-achats", "Amine (scénario)", "achats", "Achats-2026"),
    "L": ("scn-alimentation", "Youssef (scénario)", "alimentation", "2611"),
    "T": ("scn-administrateur", "Sara (scénario)", "administrateur", "Administrateur-2026"),
}
"""Un compte par rôle : (identifiant, nom, rôle, code). Le premier est posé en base."""


@dataclass
class Monde:
    """Ce que les étapes partagent."""

    verif: Verif
    horloge: Horloge
    adresse: str
    entete: str
    court: bool = False
    postes: dict[str, Poste] = field(default_factory=dict)
    ids: dict[str, int] = field(default_factory=dict)
    avant: dict[str, Any] = field(default_factory=lambda: {"faits": {}})
    notes: list[str] = field(default_factory=list)

    @property
    def D(self) -> Poste:  # noqa: N802 — le rôle s'écrit comme dans API-PRO (D, A, L, T)
        """La direction."""
        return self.postes["D"]

    @property
    def A(self) -> Poste:  # noqa: N802
        """Les achats."""
        return self.postes["A"]

    @property
    def L(self) -> Poste:  # noqa: N802
        """L'alimentation des machines (téléphone)."""
        return self.postes["L"]

    @property
    def T(self) -> Poste:  # noqa: N802
        """L'administrateur technique."""
        return self.postes["T"]

    def poste(self, role: str) -> Poste:
        """Un nouveau poste (non connecté) sur le serveur du scénario."""
        return Poste(self.adresse, self.entete, role)

    def connecter(self, role: str) -> Poste:
        """Connecte le compte du rôle par `POST /connexion` (identifiant et code)."""
        identifiant, _nom, _role, code = COMPTES[role]
        p = self.poste(role)
        p.ok("POST", "/connexion", {"identifiant": identifiant, "code": code})
        if role in self.postes:
            p.appels += self.postes[role].appels
        self.postes[role] = p
        return p

    def jour(self, cle: str, heure: int = 8) -> date:
        """Avance l'horloge de l'usine au jour du calendrier."""
        jour = JOURS[cle]
        self.horloge.aller(jour, heure)
        return jour

    def noter(self, texte: str) -> None:
        """Une remarque pour le résultat (décision, écart expliqué)."""
        self.notes.append(texte)
