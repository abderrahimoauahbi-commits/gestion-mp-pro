"""Configuration du serveur : les variables GESTIONMPPRO_*, lues une fois (ARCHITECTURE § 16).

C'est le seul module du paquet qui lit l'environnement (essai `test_config`). Le fuseau de
l'usine est passé à PostgreSQL et à `zoneinfo`, jamais au processus (C16 : pas de `TZ`).
Les constantes de coexistence avec Gestion MP (cookie, en-tête, port) sont ici aussi : un seul
endroit à comparer (ARCHITECTURE § 14.1).
"""

from __future__ import annotations

from functools import cached_property, lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

RACINE = Path(__file__).resolve().parents[2]
"""Racine du dépôt (le dossier qui contient `backend/` et `frontend/`)."""

COOKIE_SESSION = "gestion_mp_pro_session"
"""Cookie de session, distinct de celui de Gestion MP : les cookies ne s'isolent pas par port."""

COOKIE_APPAREIL = "gestion_mp_pro_appareil"
"""Cookie d'un appareil enrôlé (téléphone de l'atelier, ARCHITECTURE § 5.1)."""

ENTETE_ANTI_FALSIFICATION = "X-Gestion-MP-PRO"
"""En-tête que l'écran pose sur toute écriture (API-PRO § 0.5)."""

NOM_BASE_DEFAUT = "gestion_mp_pro"

NiveauJournal = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _dossier(valeur: Path | str) -> Path:
    """Un dossier donné avec `~` est rendu absolu."""
    return Path(valeur).expanduser()


class Reglages(BaseSettings):
    """Les réglages techniques du serveur (et non les réglages métier, en base)."""

    model_config = SettingsConfigDict(
        env_prefix="GESTIONMPPRO_", case_sensitive=False, extra="ignore", frozen=True
    )

    base: str = f"postgresql+psycopg://gestion_mp_pro@localhost/{NOM_BASE_DEFAUT}"
    fuseau: str = "Africa/Casablanca"
    port: int = Field(default=8050, ge=1, le=65535)
    ecoute: str = "127.0.0.1"
    https: bool = False
    adresse: str = ""
    processus: int = Field(default=2, ge=1, le=64)
    taches: bool = True
    session_jours: int = Field(default=30, ge=1, le=3650)
    sauvegardes: Path = Path("~/gestion-mp-pro-sauvegardes")
    sauvegardes_copie: Path | None = None
    pieces: Path = Path("~/gestion-mp-pro-pieces")
    pg_bin: Path | None = None
    ecran: Path = RACINE / "frontend" / "dist"
    smtp_hote: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_utilisateur: str = ""
    smtp_mot_de_passe: SecretStr = SecretStr("")
    smtp_expediteur: str = ""
    journal_niveau: NiveauJournal = "INFO"
    journal_fichier: Path | None = None
    source_gestion_mp: str = "postgresql+psycopg:///gestion_mp"
    pieces_gestion_mp: Path = Path("~/gestion-mp-pieces")
    essais_complets: bool = False

    @field_validator("sauvegardes", "pieces", "pieces_gestion_mp", "ecran")
    @classmethod
    def _absolu(cls, valeur: Path) -> Path:
        """Les dossiers donnés avec `~` sont rendus absolus."""
        return _dossier(valeur)

    @field_validator("sauvegardes_copie", "pg_bin", "journal_fichier", mode="before")
    @classmethod
    def _facultatif(cls, valeur: object) -> object:
        """Une variable vide veut dire « non réglé »."""
        if valeur is None or (isinstance(valeur, str) and not valeur.strip()):
            return None
        return _dossier(valeur) if isinstance(valeur, str | Path) else valeur

    @field_validator("fuseau")
    @classmethod
    def _fuseau_connu(cls, valeur: str) -> str:
        """Le fuseau doit être connu de `zoneinfo` (sinon le serveur ne démarre pas)."""
        try:
            ZoneInfo(valeur)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"fuseau inconnu : {valeur}") from exc
        return valeur

    @field_validator("journal_niveau", mode="before")
    @classmethod
    def _niveau_majuscules(cls, valeur: object) -> object:
        """`info` vaut `INFO`."""
        return valeur.upper() if isinstance(valeur, str) else valeur

    @field_validator("adresse")
    @classmethod
    def _sans_barre_finale(cls, valeur: str) -> str:
        """L'adresse publique s'écrit sans `/` final (les liens l'ajoutent)."""
        return valeur.strip().rstrip("/")

    @cached_property
    def zone(self) -> ZoneInfo:
        """Le fuseau de l'usine pour `zoneinfo`."""
        return ZoneInfo(self.fuseau)

    @cached_property
    def nom_base(self) -> str:
        """Le nom de la base (dernier segment de l'URL)."""
        return make_url(self.base).database or NOM_BASE_DEFAUT

    @property
    def dossier_sauvegardes(self) -> Path:
        """Le dossier propre à cette base (ARCHITECTURE § 13.3) : jamais celui d'une autre."""
        return self.sauvegardes / self.nom_base

    @property
    def dossier_pieces(self) -> Path:
        """Les pièces jointes de cette base."""
        return self.pieces / self.nom_base

    @property
    def expediteur(self) -> str:
        """L'expéditeur des courriels : celui réglé, sinon l'utilisateur SMTP."""
        return self.smtp_expediteur or self.smtp_utilisateur


@lru_cache(maxsize=1)
def reglages() -> Reglages:
    """Les réglages du processus, lus une seule fois (`reglages.cache_clear()` pour relire)."""
    return Reglages()
