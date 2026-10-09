"""Écriture dans la cible : insertions groupées, mise à jour par correspondance (§ 3.10.1).

Règle d'une fiche de référentiel rejouée (`appliquer`) :

- absente de la cible → **créée** ;
- même empreinte qu'à la dernière reprise → **sautée** (rien n'est écrit) ;
- changée dans la source, la fiche cible étant restée telle que la reprise l'avait écrite →
  **mise à jour** (le miroir suit Gestion MP) ;
- changée dans la source **et** modifiée dans PRO depuis → **signalée** et gardée, sauf
  `--mettre-a-jour` (jamais écrasée en silence) ;
- présente dans la cible sans correspondance (semence de PRO : devises, rôles, postes,
  magasins) → mise aux valeurs de la source, comptée « mise à jour ».

Les tables enfants (recette, poids, saisons, fils montés) se traitent **par parent**
(`appliquer_groupes`) : l'ensemble des lignes d'une qualité est remplacé quand il a changé
dans la source et pas dans PRO. Les tables d'historique (versions, cours, journal) ne font que
s'allonger (`ajouter`) : une ligne déjà reprise n'est jamais réécrite.

L'empreinte gardée dans `reprise_correspondance` est celle de la ligne source **normalisée**
(les valeurs écrites), ce qui permet les deux comparaisons.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from sqlalchemy import Table, and_, delete, insert, select, text, update

from gestion_mp_pro.modeles import metadata
from gestion_mp_pro.reprise.contexte import Contexte, Ligne
from gestion_mp_pro.reprise.normalisation import empreinte, empreinte_lignes

CORRESPONDANCE: Table = metadata.tables["reprise_correspondance"]
PAQUET = 1000
Note = tuple[str, int, str, int, str]
"""(table source, id source, table cible, id cible, empreinte)."""


def table(nom: str) -> Table:
    """La table PRO de ce nom."""
    return metadata.tables[nom]


def inserer(ctx: Contexte, nom: str, lignes: list[dict[str, Any]]) -> None:
    """Insère des lignes (groupées par jeu de colonnes, par paquets)."""
    groupes: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for x in lignes:
        groupes[tuple(sorted(x))].append(x)
    for groupe in groupes.values():
        for debut in range(0, len(groupe), PAQUET):
            ctx.c.execute(insert(table(nom)), groupe[debut : debut + PAQUET])
    ctx.compter(nom, "creees", len(lignes))


def correspondances(ctx: Contexte, table_source: str) -> dict[int, tuple[int, str]]:
    """id source → (id cible, empreinte) déjà repris de cette table source."""
    c = CORRESPONDANCE.c
    lignes = ctx.c.execute(
        select(c.id_source, c.id_cible, c.empreinte).where(
            c.source == ctx.source.value, c.table_source == table_source
        )
    )
    return {r.id_source: (r.id_cible, r.empreinte) for r in lignes}


def noter(ctx: Contexte, notes: Iterable[Note]) -> None:
    """Écrit (ou remplace) des correspondances."""
    par_table: dict[str, list[Note]] = defaultdict(list)
    for n in notes:
        par_table[n[0]].append(n)
    c = CORRESPONDANCE.c
    for table_source, lot in par_table.items():
        ids = [n[1] for n in lot]
        for debut in range(0, len(ids), PAQUET * 10):
            ctx.c.execute(
                delete(CORRESPONDANCE).where(
                    c.source == ctx.source.value,
                    c.table_source == table_source,
                    c.id_source.in_(ids[debut : debut + PAQUET * 10]),
                )
            )
        paquet = [
            {
                "source": ctx.source.value,
                "table_source": ts,
                "id_source": ids_,
                "table_cible": tc,
                "id_cible": idc,
                "empreinte": e,
            }
            for ts, ids_, tc, idc, e in lot
        ]
        for debut in range(0, len(paquet), PAQUET):
            ctx.c.execute(insert(CORRESPONDANCE), paquet[debut : debut + PAQUET])


def oublier(ctx: Contexte, tables_source: Iterable[str]) -> None:
    """Retire les correspondances de ces tables sources (activité remplacée)."""
    c = CORRESPONDANCE.c
    ctx.c.execute(
        delete(CORRESPONDANCE).where(
            c.source == ctx.source.value, c.table_source.in_(list(tables_source))
        )
    )


def _condition(t: Table, colonnes: tuple[str, ...], cle: tuple[Any, ...]) -> Any:
    """`col1 = v1 AND col2 = v2` pour une clé."""
    return and_(*(t.c[n] == v for n, v in zip(colonnes, cle, strict=True)))


def cibles(ctx: Contexte, nom: str, colonnes: tuple[str, ...]) -> dict[tuple[Any, ...], Any]:
    """Les lignes de la cible indexées par leur clé."""
    t = table(nom)
    return {tuple(r._mapping[n] for n in colonnes): r._mapping for r in ctx.c.execute(select(t))}


def _decider(ctx: Contexte, nom: str, x: Ligne, actuelle: str, avant: str | None) -> str:
    """« sauter », « ecrire » ou « garder » une fiche existante (règle du module)."""
    e = empreinte(x.valeurs)
    if actuelle == e:
        return "sauter"
    if avant is None or avant == actuelle or ctx.options.mettre_a_jour:
        return "ecrire"
    if avant == e:
        return "sauter"
    ctx.signaler(nom, x.cle, "modifiée dans PRO et dans la source : gardée telle quelle")
    return "garder"


def appliquer(ctx: Contexte, nom: str, lignes: list[Ligne], colonnes: tuple[str, ...]) -> None:
    """Crée, met à jour ou saute chaque fiche d'un référentiel (règle du module)."""
    t = table(nom)
    existantes = cibles(ctx, nom, colonnes)
    deja: dict[str, dict[int, tuple[int, str]]] = {}
    nouvelles: list[Ligne] = []
    notes: list[Note] = []
    for x in lignes:
        ctx.compter(nom, "lues")
        connues = deja.setdefault(x.table_source, correspondances(ctx, x.table_source))
        cible = existantes.get(x.cle)
        if cible is None:
            nouvelles.append(x)
            continue
        avant = connues.get(x.id_source)
        decision = _decider(
            ctx, nom, x, empreinte({k: cible[k] for k in x.valeurs}), avant and avant[1]
        )
        if decision == "ecrire":
            ctx.c.execute(update(t).where(_condition(t, colonnes, x.cle)).values(x.valeurs))
            ctx.compter(nom, "mises_a_jour")
        elif decision == "sauter":
            ctx.compter(nom, "sautees")
        e = empreinte(x.valeurs)
        if decision != "garder" and (avant is None or avant[1] != e):
            notes.append((x.table_source, x.id_source, nom, _ident(t, cible, x), e))
    if nouvelles:
        inserer(ctx, nom, [x.valeurs for x in nouvelles])
        relues = cibles(ctx, nom, colonnes)
        notes += [
            (
                x.table_source,
                x.id_source,
                nom,
                _ident(t, relues.get(x.cle), x),
                empreinte(x.valeurs),
            )
            for x in nouvelles
        ]
    noter(ctx, notes)


def _ident(t: Table, cible: Any, x: Ligne) -> int:
    """L'identifiant cible d'une fiche : son `id`, sinon celui de la source."""
    if "id" in t.c and cible is not None:
        return int(cible["id"])
    return x.id_source


def appliquer_groupes(
    ctx: Contexte, nom: str, parent: str, groupes: dict[int, list[dict[str, Any]]]
) -> None:
    """Remplace, parent par parent, l'ensemble des lignes d'une table enfant s'il a changé.

    Correspondance : `(nom, id du parent)` → empreinte de l'ensemble. Un ensemble modifié dans
    PRO depuis la dernière reprise est gardé et signalé (sauf `--mettre-a-jour`).
    """
    t = table(nom)
    actuels: dict[int, list[dict[str, Any]]] = defaultdict(list)
    colonnes = [c.name for c in t.columns]
    for r in ctx.c.execute(select(t)):
        actuels[int(r._mapping[parent])].append(dict(r._mapping))
    connues = correspondances(ctx, nom)
    notes: list[Note] = []
    a_inserer: list[dict[str, Any]] = []
    for pid, lignes in sorted(groupes.items()):
        ctx.compter(nom, "lues", len(lignes))
        cles = list(lignes[0]) if lignes else colonnes
        e = empreinte_lignes(lignes)
        actuelle = empreinte_lignes([{k: x[k] for k in cles} for x in actuels.get(pid, [])])
        avant = connues.get(pid)
        modifie_dans_pro = avant is not None and avant[1] != actuelle
        if actuelle == e or (modifie_dans_pro and avant and avant[1] == e):
            ctx.compter(nom, "sautees", len(lignes))
        elif modifie_dans_pro and not ctx.options.mettre_a_jour:
            ctx.signaler(nom, pid, "lignes modifiées dans PRO et dans la source : gardées")
            continue
        else:
            ctx.c.execute(delete(t).where(t.c[parent] == pid))
            ctx.compter(nom, "supprimees", len(actuels.get(pid, [])))
            a_inserer += lignes
        if avant is None or avant[1] != e:
            notes.append((nom, pid, nom, pid, e))
    inserer(ctx, nom, a_inserer)
    noter(ctx, notes)


def ajouter(ctx: Contexte, nom: str, lignes: list[Ligne]) -> list[Ligne]:
    """Insère les lignes d'historique pas encore reprises ; rend celles qui ont été écrites."""
    deja: dict[str, dict[int, tuple[int, str]]] = {}
    nouvelles = []
    for x in lignes:
        ctx.compter(nom, "lues")
        connues = deja.setdefault(x.table_source, correspondances(ctx, x.table_source))
        if x.id_source in connues:
            ctx.compter(nom, "sautees")
        else:
            nouvelles.append(x)
    inserer(ctx, nom, [x.valeurs for x in nouvelles])
    noter(
        ctx,
        [
            (x.table_source, x.id_source, nom, int(x.cle[0]), empreinte(x.valeurs))
            for x in nouvelles
        ],
    )
    return nouvelles


def prochains_ids(ctx: Contexte, nom: str, n: int) -> list[int]:
    """`n` identifiants pris dans la séquence de la table (lignes sans identifiant source)."""
    if n <= 0:
        return []
    recaler_sequence(ctx, nom)
    sql = text("SELECT nextval(pg_get_serial_sequence(:t, 'id')) FROM generate_series(1, :n)")
    return [int(v) for v in ctx.c.execute(sql, {"t": nom, "n": n}).scalars()]


def recaler_sequence(ctx: Contexte, nom: str, colonne: str = "id") -> None:
    """Met la séquence d'identité au-delà du plus grand identifiant présent (jamais en arrière)."""
    sequence = ctx.c.execute(
        text("SELECT pg_get_serial_sequence(:t, :c)"), {"t": nom, "c": colonne}
    ).scalar()
    if sequence is None:
        return
    plus_grand = ctx.c.execute(text(f"SELECT max({colonne}) FROM {nom}")).scalar()  # noqa: S608
    dernier, appele = ctx.c.execute(text(f"SELECT last_value, is_called FROM {sequence}")).one()  # noqa: S608
    courant = dernier if appele else dernier - 1
    if plus_grand is not None and plus_grand > courant:
        ctx.c.execute(text("SELECT setval(:s, :v)"), {"s": sequence, "v": plus_grand})
