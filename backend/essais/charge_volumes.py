"""Épreuve de charge (PLAN-DE-RECETTE-PRO § 10) : la base de l'année d'essai multipliée.

La base « réel » est l'année d'essai de l'ERP Fil reprise par R1 (copie de
`gestion_mp_comparaison`, lue seulement). Les volumes ×10 et ×30 la recopient **en SQL**, dans une
base d'essai à part, comme une usine plus grande et plus ancienne :

- `annees` : l'année d'activité est rejouée autant de fois, chaque copie reculée d'un an de plus
  (dates et horodatages décalés ensemble : l'ordre des événements et les contrôles de dates
  restent vrais) ;
- `gammes` : chaque copie de gamme recrée les matières et les qualités avec leurs recettes (même
  nomenclature, références suffixées « #c ») ; l'activité de cette gamme porte sur ses matières.

×10 = 5 ans × 2 gammes, ×30 = 10 ans × 3 gammes. Chaque ligne d'activité (lots, soldes,
mouvements, commandes, réceptions, factures, dossiers et frais, ordres, opérations, inventaires,
journal) est recopiée avec ses liens : identifiants décalés table par table, numéros de pièces
rendus uniques (`SERIE-AAAA-NNNN` : rang + 1 000 × copie ; dossiers `NN/AA` : rang + 100 × …,
toujours ≤ 999), compteurs relevés au plus haut rang de chaque année. Le journal des
mouvements reste égal aux soldes (on recopie les deux), si bien que la base reste juste ; elle
est **plus dure** que le réel : les lots des années recopiées gardent leur solde (une vraie
usine les aurait épuisés), et les commandes ou dossiers ouverts restent ouverts.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Column, Date, DateTime, String, Table, create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool

from gestion_mp_pro.modeles import Base
from gestion_mp_pro.modeles.enums import SerieNumero


@dataclass(frozen=True)
class Volume:
    """Un volume de l'épreuve : nom, années d'activité, gammes."""

    nom: str
    annees: int
    gammes: int

    @property
    def facteur(self) -> int:
        """Le multiplicateur de l'activité."""
        return self.annees * self.gammes


VOLUMES = (Volume("reel", 1, 1), Volume("x10", 5, 2), Volume("x30", 10, 3))

GAMME = (
    "matiere qualite qualite_poids qualite_saison recette recette_version "
    "recette_version_ligne recette_version_poids"
).split()
"""Tables recopiées une fois par gamme (référentiels de la nomenclature)."""

ACTIVITE = (
    "lot solde mouvement facture commande commande_ligne commande_version "
    "commande_version_ligne commande_decision reception reception_ligne dossier dossier_ligne "
    "dossier_frais dossier_frais_part ordre ordre_qualite ordre_ligne ordre_prevu operation "
    "operation_ligne inventaire inventaire_matiere inventaire_ligne inventaire_critere "
    "reclamation journal"
).split()
"""Tables recopiées une fois par (année, gamme)."""

FILTRES = {
    "inventaire": "statut <> 'ouvert'",
    "inventaire_ligne": "inventaire_id IN (SELECT id FROM inventaire WHERE statut <> 'ouvert')",
    "inventaire_matiere": "inventaire_id IN (SELECT id FROM inventaire WHERE statut <> 'ouvert')",
    "inventaire_critere": "inventaire_id IN (SELECT id FROM inventaire WHERE statut <> 'ouvert')",
    "journal": "action <> 'reprise'",
}
"""Ce qui n'est pas recopié : un inventaire ouvert (un seul à la fois), la ligne de reprise."""

NUMEROS = ("numero", "document_numero", "lot_numero")
SERIES = "|".join(s.value for s in SerieNumero if s is not SerieNumero.DOS)

FONCTION_NUMERO = f"""
CREATE OR REPLACE FUNCTION pg_temp.charge_rang(n int, largeur int) RETURNS text
LANGUAGE sql IMMUTABLE AS $$ SELECT lpad(n::text, greatest(largeur, length(n::text)), '0') $$;
CREATE OR REPLACE FUNCTION pg_temp.charge_numero(t text, y int, c int, k int) RETURNS text
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE m text[]; d int;
BEGIN
  IF t IS NULL OR k = 0 THEN RETURN t; END IF;
  m := regexp_match(t, '^({SERIES})-([0-9]{{4}})-([0-9]+)$');
  IF m IS NOT NULL THEN
    RETURN m[1] || '-' || (m[2]::int - y) || '-' || pg_temp.charge_rang(m[3]::int + 1000 * k, 4);
  END IF;
  m := regexp_match(t, '^([0-9]{{1,3}})/([0-9]{{2}})$');
  IF m IS NOT NULL THEN
    d := {{amax}} % 100 - m[2]::int;
    RETURN pg_temp.charge_rang(m[1]::int + 100 * (2 * c + 1 - d), 2) || '/'
      || pg_temp.charge_rang(((m[2]::int - y) % 100 + 100) % 100, 2);
  END IF;
  RETURN t || '-' || k;
END $$;
"""
"""Un numéro de pièce rendu unique dans la copie k (année y en arrière, gamme c).

Séries `SERIE-AAAA-NNNN` : année − y, rang + 1 000 k (les rangs réels sont < 1 000 par an).
Dossiers `NN/AA` : année − y, rang + 100 (2c + 1 − d), d = 1 pour l'année la plus ancienne de
l'année d'essai (elle en couvre deux) : dans une même année d'arrivée, les copies de gamme c
viennent de (y, dernière année) et (y − 1, première année), et l'original occupe le rang nu ;
les rangs restent ≤ 583 (≤ 999 exigé). Autres numéros (lots de fournisseur, factures,
inventaires) : suffixe `-k`.
"""


def _cible(colonne: Column[object]) -> str | None:
    """La table que vise la colonne (la clé vers un `id`, de préférence)."""
    cles = sorted(colonne.foreign_keys, key=lambda f: f.column.name != "id")
    return cles[0].column.table.name if cles else None


def _numero_decale(t: Table, colonne: Column[object]) -> str | None:
    """Les colonnes dont la valeur est un numéro de pièce à rendre unique dans la copie."""
    nom = colonne.name
    if t.name == "dossier" and nom == "rang":
        nouveau = "split_part(pg_temp.charge_numero(numero, :y, :c, :k), '/', 1)::int"
        return f"CASE WHEN rang IS NULL THEN NULL ELSE {nouveau} END"
    if nom in NUMEROS and isinstance(colonne.type, String):
        longueur = colonne.type.length or 1000
        return f"left(pg_temp.charge_numero({nom}, :y, :c, :k), {longueur})"
    return None


def _texte_decale(t: Table, colonne: Column[object], decalages: dict[str, int]) -> str | None:
    """Les colonnes dont la valeur est un texte ou un id propre à la gamme ou à la copie."""
    nom = colonne.name
    if t.name == "matiere" and nom == "reference":
        return "reference || ' #' || :c"
    if t.name == "qualite" and nom == "code":
        return "code || '-' || :c"
    if t.name == "journal" and nom == "objet_id":
        cas = " ".join(
            f"WHEN '{x}' THEN objet_id + :k * {decalages[x]}" for x in ACTIVITE if x in decalages
        )
        return f"CASE objet {cas} ELSE objet_id END"
    return None


def _expression(t: Table, colonne: Column[object], decalages: dict[str, int], y: int) -> str:
    """L'expression SQL qui recopie une colonne dans la copie (`:k` copie, `:c` gamme)."""
    nom = colonne.name
    cible = t.name if nom == "id" and "id" in t.primary_key.columns else _cible(colonne)
    if cible in decalages and (cible in ACTIVITE or cible in GAMME):
        rang = ":k" if cible in ACTIVITE else ":c"
        return f"{nom} + {rang} * {decalages[cible]}"
    if t.name == "dossier" and nom == "annee":
        return f"annee - {y}"
    special = _numero_decale(t, colonne) or _texte_decale(t, colonne, decalages)
    if special is not None:
        return special
    if y and isinstance(colonne.type, Date):
        return f"({nom} - make_interval(years => {y}))::date"
    if y and isinstance(colonne.type, DateTime):
        return f"{nom} - make_interval(years => {y})"
    return nom


def _recopier(
    c: Connection, t: Table, decalages: dict[str, int], copie: tuple[int, int, int]
) -> None:
    """Une table recopiée une fois (copie `(y, g, k)` : y ans plus tôt, gamme g)."""
    y, g, k = copie
    colonnes = [x for x in t.columns if x.computed is None]
    noms = ", ".join(x.name for x in colonnes)
    valeurs = ", ".join(_expression(t, x, decalages, y) for x in colonnes)
    filtre = FILTRES.get(t.name, "TRUE")
    c.execute(
        text(
            f"INSERT INTO {t.name} ({noms}) OVERRIDING SYSTEM VALUE "  # noqa: S608
            f"SELECT {valeurs} FROM {t.name} WHERE {filtre} AND {_originaux(t, decalages)}"
        ),
        {"y": y, "c": g, "k": k},
    )


def _originaux(t: Table, decalages: dict[str, int]) -> str:
    """Les lignes de l'année d'essai seulement (pas celles des copies déjà faites)."""
    if t.name in decalages:
        return f"id < {decalages[t.name]}"
    cle = next(iter(t.primary_key.columns))
    cible = _cible(cle)
    return f"{cle.name} < {decalages[cible]}" if cible in decalages else "TRUE"


def _decalages(c: Connection, tables: list[Table]) -> dict[str, int]:
    """Pour chaque table à `id`, une puissance de dix au-dessus de son plus grand `id`."""
    sortie = {}
    for t in tables:
        if "id" in t.columns and "id" in t.primary_key.columns:
            plus_grand = c.execute(text(f"SELECT coalesce(max(id), 0) FROM {t.name}")).scalar_one()  # noqa: S608
            sortie[t.name] = 10 ** len(str(int(plus_grand) + 1))
    return sortie


def multiplier(adresse: str, volume: Volume) -> dict[str, int]:
    """Multiplie l'activité de la base (déjà reprise) ; rend les comptes de lignes."""
    tables = [t for t in Base.metadata.sorted_tables if t.name in GAMME or t.name in ACTIVITE]
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.begin() as c:
        amax = _controler_annees(c)
        c.execute(text(FONCTION_NUMERO.replace("{amax}", str(amax))))
        decalages = _decalages(c, tables)
        for g in range(1, volume.gammes):
            for t in tables:
                if t.name in GAMME:
                    _recopier(c, t, decalages, (0, g, 0))
        for y in range(volume.annees):
            for g in range(volume.gammes):
                k = g * volume.annees + y
                if k:
                    for t in tables:
                        if t.name in ACTIVITE:
                            _recopier(c, t, decalages, (y, g, k))
        _recaler(c, tables)
    with moteur.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        c.execute(text("ANALYZE"))
    comptes = compter(adresse)
    moteur.dispose()
    return comptes


def _controler_annees(c: Connection) -> int:
    """La dernière année des dossiers numérotés ; ils couvrent au plus deux années (voir
    `FONCTION_NUMERO`), sinon la règle des rangs ne garantit plus l'unicité."""
    annees = c.execute(text("SELECT count(DISTINCT annee), max(annee) FROM dossier")).one()
    if annees[0] > 2:  # noqa: PLR2004
        raise SystemExit(f"Dossiers sur {annees[0]} années : règle de numérotation à revoir")
    return int(annees[1] or 2026)


def _recaler(c: Connection, tables: list[Table]) -> None:
    """Séquences au plus haut `id` ; compteurs au plus haut rang de chaque série et année."""
    for t in tables:
        if "id" in t.columns and "id" in t.primary_key.columns:
            c.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{t.name}', 'id'), "  # noqa: S608
                    f"(SELECT coalesce(max(id), 1) FROM {t.name}))"
                )
            )
    sources = " UNION ALL ".join(
        f"SELECT numero FROM {x} WHERE numero IS NOT NULL"  # noqa: S608
        for x in ("commande", "reception", "ordre", "operation", "inventaire", "reclamation", "lot")
    )
    c.execute(
        text(
            "INSERT INTO compteur (serie, annee, dernier) "  # noqa: S608
            "SELECT m[1], m[2]::int, max(m[3]::int) FROM ("
            f"SELECT regexp_match(numero, '^({SERIES})-([0-9]{{4}})-([0-9]+)$') AS m "
            f"FROM ({sources}) n) x WHERE m IS NOT NULL GROUP BY 1, 2 "
            "UNION ALL SELECT 'DOS', annee, max(rang) FROM dossier WHERE rang IS NOT NULL "
            "GROUP BY annee "
            "ON CONFLICT (serie, annee) DO UPDATE SET dernier = "
            "greatest(compteur.dernier, excluded.dernier)"
        )
    )


COMPTES = (
    "matiere qualite lot mouvement solde commande reception facture ordre ordre_ligne dossier "
    "dossier_ligne dossier_frais operation inventaire journal"
).split()


def compter(adresse: str) -> dict[str, int]:
    """Les comptes de lignes des tables qui font le volume, et le nombre d'années d'activité."""
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.connect() as c:
        comptes = {
            t: int(c.execute(text(f"SELECT count(*) FROM {t}")).scalar_one())  # noqa: S608
            for t in COMPTES
        }
        comptes["annees"] = int(
            c.execute(
                text("SELECT count(DISTINCT extract(year FROM date_effet)) FROM mouvement")
            ).scalar_one()
        )
        comptes["lots_presents"] = int(
            c.execute(text("SELECT count(*) FROM solde WHERE quantite > 0")).scalar_one()
        )
    moteur.dispose()
    return comptes
