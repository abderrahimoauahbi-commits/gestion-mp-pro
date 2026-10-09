"""Le rapport de reprise : en tête les contrôles, puis les comptes, les arrondis, les signalements.

Le même texte va dans `reprise_execution.rapport` et, sur demande, dans un fichier
(`essais/resultat-reprise.txt`).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from gestion_mp_pro.reprise.contexte import COMPTES, Contexte
from gestion_mp_pro.reprise.controle import Verdict

MAX_PAR_GENRE = 12
"""Signalements détaillés par (table, message) au-delà desquels on ne donne que le nombre."""


def _entete(ctx: Contexte, empreinte_apres: str, duree: float) -> list[str]:
    """Source, cible, mode, empreintes, durée."""
    o = ctx.options
    meme = "identique" if empreinte_apres == ctx.photo.empreinte else "DIFFÉRENTE"
    return [
        "REPRISE DE GESTION MP DANS GESTION MP PRO",
        f"source : {ctx.photo.base} ({ctx.source.value}) — lecture seule vérifiée : "
        f"{'oui' if ctx.photo.lecture_seule_verifiee else 'NON'}",
        f"cible  : {o.cible.rsplit('/', 1)[-1]} — mode {o.mode.value}"
        f"{' --remplacer-activite' if o.remplacer_activite else ''}"
        f"{' --mettre-a-jour' if o.mettre_a_jour else ''}{' (essai à blanc)' if o.essai else ''}",
        f"empreinte de la source avant : {ctx.photo.empreinte}",
        f"empreinte de la source après : {empreinte_apres} ({meme})",
        f"activité : {'reprise' if ctx.activite_reprise else 'inchangée ou non demandée'}",
        f"durée : {duree:.1f} s",
        "",
    ]


def _verdicts(verdicts: Iterable[Verdict]) -> list[str]:
    """Les contrôles, chacun « tenu » ou « NON TENU », avec leurs lignes."""
    lignes = ["CONTRÔLES"]
    for v in verdicts:
        lignes.append(f"[{'tenu' if v.tenu else 'NON TENU'}] {v.titre}")
        lignes += [f"    {x}" for x in v.lignes]
    return [*lignes, ""]


def _comptes(ctx: Contexte) -> list[str]:
    """Lignes par table : lues, créées, mises à jour, sautées, signalées, supprimées."""
    lignes = ["LIGNES PAR TABLE CIBLE (" + ", ".join(COMPTES) + ")"]
    for table, c in sorted(ctx.comptes.items()):
        if any(c.values()):
            lignes.append(f"    {table:<24} " + " ".join(f"{c[k]:>7}" for k in COMPTES))
    return [*lignes, ""]


def _arrondis(ctx: Contexte) -> list[str]:
    """Valeurs arrondies à l'échelle de leur colonne (règle K1)."""
    lignes = ["ARRONDIS À L'ÉCHELLE DES COLONNES (K1)"]
    for (table, colonne), a in sorted(ctx.norm.arrondis.items()):
        lignes.append(
            f"    {table}.{colonne} : {a.nombre} valeurs arrondies, écart max {a.ecart_max:.2e}"
        )
    if len(lignes) == 1:
        lignes.append("    aucune")
    return [*lignes, ""]


def _signalements(ctx: Contexte) -> list[str]:
    """Valeurs signalées (jamais corrigées en silence), groupées par table et message."""
    groupes: dict[tuple[str, str], list[str]] = defaultdict(list)
    for s in ctx.norm.signalements:
        groupes[(s.table, s.message)].append(s.ident)
    lignes = [f"SIGNALEMENTS ({len(ctx.norm.signalements)})"]
    for (table, message), idents in sorted(groupes.items()):
        if len(idents) == 1:
            lignes.append(f"    {table} {idents[0]} : {message}")
        else:
            liste = ", ".join(idents[:MAX_PAR_GENRE]) + (
                " …" if len(idents) > MAX_PAR_GENRE else ""
            )
            lignes.append(f"    {table} ({len(idents)}) : {message} — {liste}")
    return lignes


def rediger(ctx: Contexte, verdicts: list[Verdict], empreinte_apres: str, duree: float) -> str:
    """Le texte complet du rapport."""
    morceaux = (
        _entete(ctx, empreinte_apres, duree)
        + _verdicts(verdicts)
        + _comptes(ctx)
        + _arrondis(ctx)
        + _signalements(ctx)
    )
    return "\n".join(morceaux) + "\n"
