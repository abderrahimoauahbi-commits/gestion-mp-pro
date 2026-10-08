"""Le socle des contrôles : l'objet rendu, le contexte lu, et le registre (ARCHITECTURE § 7).

Chaque contrôle est une fonction `(ctx) -> (libellé, lignes)` déclarée par
`@controle("C08", gravite=…, lien=…, colonnes=…, garanti=…)`. Le registre les rejoue dans
l'ordre numérique ; le détail est complet (aucune troncature) et ses colonnes sont déclarées
avec leur unité.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from functools import cached_property
from typing import Literal

from gestion_mp_pro.calcul.controles.textes import COLONNES, QUOI_FAIRE
from gestion_mp_pro.calcul.modele import Donnees, Parametres
from gestion_mp_pro.calcul.stock import FilEnMachine, LigneStock, fils_en_machine

Gravite = Literal["bloquant", "avertissement", "information"]
"""Bloquant : le pilotage est faussé ; avertissement : une saisie à revoir ; information : un
fait à connaître."""

Unite = Literal["kg", "m", "MAD", "%", "j", "date", "texte", "nombre"]
"""L'unité d'une colonne du détail : l'écran et l'export la formatent une seule fois (« % » :
une fraction, 0,034 → 3,4 %)."""

Ligne = dict[str, object]
"""Une ligne du détail : clé technique → valeur simple (texte, nombre, booléen, None)."""


@dataclass(frozen=True)
class Colonne:
    """Une colonne du détail : sa clé, son libellé français, son unité."""

    cle: str
    libelle: str
    unite: Unite


def colonne(cle: str, unite: Unite) -> Colonne:
    """La colonne `cle`, libellée par `COLONNES`."""
    return Colonne(cle, COLONNES[cle], unite)


@dataclass
class Controle:
    """Le résultat d'un contrôle : le compte et la liste complète des lignes fautives."""

    code: str
    libelle: str
    anomalies: int
    detail: list[Ligne] = field(default_factory=list)
    gravite: Gravite = "avertissement"
    garanti: str = ""
    """Pourquoi ce contrôle ne peut pas sonner — seulement s'il ne le peut pas ET est conforme."""
    quoi_faire: str = ""
    lien: str = ""
    """La route PRO de l'écran où se fait la correction (« Ouvrir l'écran »)."""
    colonnes: list[Colonne] = field(default_factory=list)

    @property
    def conforme(self) -> bool:
        """Aucune anomalie."""
        return self.anomalies == 0


@dataclass
class Contexte:
    """Ce que lisent les contrôles.

    `donnees` : les données à la date de référence ; `complet` : toutes les données, rien de
    retiré (C12, C14, C25, C27, C37 tournent sur elles) ; `aujourdhui` : la date du jour, à
    laquelle C14 juge le futur (jamais avant `date_ref`).
    """

    donnees: Donnees
    lignes_stock: list[LigneStock]
    date_ref: date
    complet: Donnees
    aujourdhui: date

    @classmethod
    def preparer(
        cls,
        donnees: Donnees,
        lignes_stock: list[LigneStock],
        date_ref: date,
        complet: Donnees | None = None,
        aujourdhui: date | None = None,
    ) -> Contexte:
        """Le contexte de `controler()`, aux mêmes règles que Gestion MP."""
        return cls(
            donnees=donnees,
            lignes_stock=lignes_stock,
            date_ref=date_ref,
            complet=complet if complet is not None else donnees,
            aujourdhui=max(date_ref, aujourdhui) if aujourdhui else date_ref,
        )

    @property
    def parametres(self) -> Parametres:
        """Les réglages des données à la date."""
        return self.donnees.parametres

    @cached_property
    def fils(self) -> list[FilEnMachine]:
        """Le fil monté sur les métiers actifs (C23, C25)."""
        return fils_en_machine(self.donnees)

    @cached_property
    def jours_par_of(self) -> dict[str, set[date]]:
        """Les jours où chaque ordre a servi du fil (C31, C32)."""
        jours: dict[str, set[date]] = {}
        for m in self.donnees.mouvements:
            if m.type == "SORTIE_PROD" and m.numero_of and m.quantite > 0:
                jours.setdefault(m.numero_of, set()).add(m.date)
        return jours


Regle = Callable[[Contexte], tuple[str, list[Ligne]]]
"""Une règle de contrôle : le libellé (parfois calculé d'un réglage) et les lignes fautives."""


@dataclass(frozen=True)
class Definition:
    """Un contrôle déclaré : son code, sa gravité, son lien, ses colonnes et sa règle."""

    code: str
    gravite: Gravite
    lien: str
    colonnes: tuple[Colonne, ...]
    garanti: str
    regle: Regle

    def executer(self, ctx: Contexte) -> Controle:
        """Rejoue la règle ; `garanti` n'est dit que si le contrôle est conforme."""
        libelle, lignes = self.regle(ctx)
        return Controle(
            code=self.code,
            libelle=libelle,
            anomalies=len(lignes),
            detail=lignes,
            gravite=self.gravite,
            garanti=self.garanti if not lignes else "",
            quoi_faire=QUOI_FAIRE[self.code],
            lien=self.lien,
            colonnes=list(self.colonnes),
        )


REGISTRE: dict[str, Definition] = {}
"""Les contrôles déclarés, par code."""


def controle(
    code: str,
    *,
    gravite: Gravite,
    lien: str,
    colonnes: tuple[Colonne, ...],
    garanti: str = "",
) -> Callable[[Regle], Regle]:
    """Déclare la règle du contrôle `code` (un code ne se déclare qu'une fois)."""

    def _enregistrer(regle: Regle) -> Regle:
        if code in REGISTRE:
            raise ValueError(f"Contrôle {code} déjà déclaré.")
        REGISTRE[code] = Definition(code, gravite, lien, colonnes, garanti, regle)
        return regle

    return _enregistrer
