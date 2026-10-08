"""Compare le schéma réel d'une base de Gestion MP PRO à `docs/MODELE-DONNEES.md` (lot S1).

    backend/.venv/bin/python outils/schema_contre_modele.py [--base URL] [--document CHEMIN]

Liste les tables (§ 11 du document contre la base) puis, table par table, les colonnes :
- en base mais jamais nommées dans la section de la table (§ 3) ;
- décrites dans le document (ligne de tableau ou colonne typée d'une seule table) mais
  absentes de la base.
Les écarts voulus sont déclarés dans `ECARTS_DECLARES`, avec leur raison (`docs/lots/S1.md`) :
ils sont rappelés, pas comptés. Code de sortie 1 s'il reste un écart non déclaré.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import create_engine, inspect

RACINE = Path(__file__).resolve().parents[1]
DOCUMENT = RACINE / "docs" / "MODELE-DONNEES.md"

ECARTS_DECLARES: dict[tuple[str, str], str] = {
    ("inventaire", "annule_le"): "inventaire validé puis annulé (étape 17 de Gestion MP)",
    ("inventaire", "annule_par_id"): "inventaire validé puis annulé (étape 17 de Gestion MP)",
    ("inventaire", "annulation_motif"): "inventaire validé puis annulé (étape 17 de Gestion MP)",
    ("inventaire_ligne", "matiere_id"): "lot trouvé créé à la validation (étape 17)",
    ("inventaire_ligne", "lot_numero"): "lot trouvé créé à la validation (étape 17)",
    ("inventaire_ligne", "lot_interne"): "lot trouvé créé à la validation (étape 17)",
    ("reclamation", "reception_ligne_id"): "ligne reçue en cause (étape 15 de Gestion MP)",
}
"""Colonnes ajoutées par S1 pour suivre Gestion MP corrigé (étapes 15 à 18)."""

_JETON = re.compile(r"`([^`]+)`")
_MOT = re.compile(r"[a-z_][a-z0-9_]*")
_TYPE = re.compile(
    r"^(INTEGER|BIGINT|SMALLINT|VARCHAR|CHAR|TEXT|NUMERIC|BOOLEAN|DATE|TIMESTAMPTZ|JSONB|[A-Z][a-z])"
)


@dataclass
class Documentation:
    """Ce que le document dit : tables listées, colonnes nommées et colonnes sûres."""

    tables: set[str]
    nommees: dict[str, set[str]] = field(default_factory=dict)
    sures: dict[str, set[str]] = field(default_factory=dict)

    def nommer(self, table: str, colonnes: set[str], sures: bool) -> None:
        """Ajoute des colonnes à une table (sûres : décrites sans ambiguïté)."""
        self.nommees.setdefault(table, set()).update(colonnes)
        if sures:
            self.sures.setdefault(table, set()).update(colonnes)


def _tables_listees(texte: str) -> set[str]:
    """La liste des tables du § 11 (« Liste des 71 tables : … »)."""
    liste = texte.split("Liste des 71 tables :", 1)[1]
    return {t.strip(" .\n") for t in liste.split(",") if t.strip(" .\n")}


def _premiere_cellule(ligne: str) -> tuple[set[str], set[str]]:
    """(colonnes de la première cellule, mots des deux premières) d'une ligne de tableau."""
    cellules = [c.strip() for c in ligne.strip().strip("|").split("|")]
    noms = {_MOT.match(n.strip(" `")).group(0) for n in re.split(r"[,;]", cellules[0])
            if _MOT.match(n.strip(" `"))}  # fmt: skip
    mots = set(_MOT.findall(" ".join(cellules[:2])))
    return noms, noms | mots


def _jetons(ligne: str) -> tuple[set[str], set[str]]:
    """(colonnes typées, colonnes nommées) des jetons `entre accents graves` d'une ligne."""
    typees, nommees = set(), set()
    for jeton in _JETON.findall(ligne):
        if jeton.startswith("("):  # clé composée : `(version_id, matiere_id)`
            nommees.update(_MOT.findall(jeton))
            continue
        mots = jeton.split()
        if not mots or not _MOT.fullmatch(mots[0]):
            continue
        nommees.add(mots[0])
        if len(mots) > 1 and _TYPE.match(mots[1]):
            typees.add(mots[0])
    return typees, nommees


def _ligne_de_tableau(ligne: str) -> bool:
    """Une ligne de données d'un tableau (ni en-tête ni séparateur)."""
    return ligne.startswith("|") and not ligne.startswith(("| Colonne", "|---"))


def _lire_section(doc: Documentation, lignes: list[str]) -> None:
    """Une section `####` du § 3 : tableaux et paragraphes, attribués à leur table."""
    titre = lignes[0]
    du_titre = [t for t in _JETON.findall(titre) if t in doc.tables]
    courantes = du_titre[:1] if len(du_titre) == 1 else du_titre
    for ligne in lignes[1:]:
        tete = _JETON.match(ligne)
        if tete and tete.group(1) in doc.tables:
            courantes = [tete.group(1)]
        if _ligne_de_tableau(ligne):
            noms, mots = _premiere_cellule(ligne)
            for table in courantes:
                doc.nommer(table, noms, sures=len(courantes) == 1)
                doc.nommer(table, mots, sures=False)
        elif ligne.strip():
            typees, nommees = _jetons(ligne)
            for table in courantes:
                doc.nommer(table, typees, sures=len(courantes) == 1)
                doc.nommer(table, nommees, sures=False)


def lire_document(chemin: Path = DOCUMENT) -> Documentation:
    """Les tables et colonnes que décrit MODELE-DONNEES."""
    texte = chemin.read_text(encoding="utf-8")
    doc = Documentation(tables=_tables_listees(texte))
    partie = texte.split("## 3. Les tables", 1)[1].split("## 4.", 1)[0]
    for section in partie.split("\n####")[1:]:
        _lire_section(doc, section.splitlines())
    return doc


def lire_base(adresse: str) -> dict[str, list[str]]:
    """Les tables et colonnes de la base (schéma `public`)."""
    moteur = create_engine(adresse)
    try:
        inspecteur = inspect(moteur)
        tables = inspecteur.get_table_names()
        return {t: [c["name"] for c in inspecteur.get_columns(t)] for t in tables}
    finally:
        moteur.dispose()


@dataclass
class Rapport:
    """Les écarts trouvés, et les écarts déclarés rencontrés."""

    ecarts: list[str] = field(default_factory=list)
    declares: list[str] = field(default_factory=list)

    def noter(self, table: str, colonne: str, sens: str) -> None:
        """Range un écart parmi les déclarés ou les écarts à corriger."""
        raison = ECARTS_DECLARES.get((table, colonne))
        if raison:
            self.declares.append(f"{table}.{colonne} ({sens}) : {raison}")
        else:
            self.ecarts.append(f"{table}.{colonne} : {sens}")


def comparer(doc: Documentation, base: dict[str, list[str]]) -> Rapport:
    """Les écarts entre le document et la base."""
    rapport = Rapport()
    for table in sorted(doc.tables - set(base)):
        rapport.ecarts.append(f"table {table} : dans le document, absente de la base")
    for table in sorted(set(base) - doc.tables):
        rapport.ecarts.append(f"table {table} : en base, absente du document")
    for table, colonnes in sorted(base.items()):
        if table == "alembic_version":
            continue
        for colonne in colonnes:
            if colonne not in doc.nommees.get(table, set()):
                rapport.noter(table, colonne, "en base, non décrite dans le document")
        for colonne in sorted(doc.sures.get(table, set()) - set(colonnes)):
            rapport.noter(table, colonne, "décrite dans le document, absente de la base")
    return rapport


def main(arguments: list[str] | None = None) -> int:
    """Compare, écrit le rapport sur la sortie, rend 1 s'il reste un écart non déclaré."""
    lecteur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    lecteur.add_argument("--base", default="postgresql+psycopg:///gestion_mp_pro_essai")
    lecteur.add_argument("--document", type=Path, default=DOCUMENT)
    options = lecteur.parse_args(arguments)
    doc = lire_document(options.document)
    base = lire_base(options.base)
    rapport = comparer(doc, base)
    colonnes = sum(len(c) for t, c in base.items() if t != "alembic_version")
    sortie = [f"{len(base)} tables en base, {len(doc.tables)} au document ; {colonnes} colonnes."]
    sortie += [f"Écart déclaré : {e}" for e in rapport.declares]
    sortie += [f"ÉCART : {e}" for e in rapport.ecarts] or ["Aucun écart non déclaré."]
    sys.stdout.write("\n".join(sortie) + "\n")
    return 1 if rapport.ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
