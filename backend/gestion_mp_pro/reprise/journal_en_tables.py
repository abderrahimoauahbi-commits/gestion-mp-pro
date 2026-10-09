"""Le journal de Gestion MP relu une fois, rangé en tables (MODELE-DONNEES § 4 et § 10.3).

Gestion MP gardait dans `journal.detail` des informations que ses calculs relisaient. PRO les
range en colonnes ou en tables ; ce module les tire du journal source :

- « plan de production » (`plan={avant, après}`) → `plan_version` + `plan_version_saison`
  (la première ligne donne aussi la version d'avant, valable depuis le 1ᵉʳ janvier 2000) ;
- « commande soldée » / « commande annulée » → `commande.solde_origine`, `solde_le`,
  `solde_par_id` (« tout reçu » → automatique, autre → manuel, aucune ligne → reprise) ;
- renvois, demandes d'approbation, approbations… → `commande_decision` (montants lus) ;
- « annulation réception », « annulation bon de sortie », « annulation opération »,
  « abandon inventaire », « annulation inventaire » → dates, auteurs et motifs ;
- « montage » → `montage_evenement` (texte en `alerte` : il n'est pas interprété).

Le journal lui-même est repris tel quel dans `journal` (`journal_repris`).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from gestion_mp_pro.modeles.enums import DecisionCommande, OrigineSolde, OrigineVersion
from gestion_mp_pro.reprise import ecriture
from gestion_mp_pro.reprise.contexte import Contexte, Ligne

MARQUE_PLAN = "plan="
DEBUT_DES_TEMPS = dt.datetime(2000, 1, 1)  # noqa: DTZ001 (heure de l'usine, posée par la normalisation)
DECISIONS = {
    "commande à approuver": DecisionCommande.demande_approbation,
    "approbation commande": DecisionCommande.approbation,
    "renvoi aux achats": DecisionCommande.renvoi,
    "version partie rétablie": DecisionCommande.version_retablie,
    "approbation plus nécessaire": DecisionCommande.approbation_plus_necessaire,
    "retour en brouillon": DecisionCommande.retour_brouillon,
    "commande rouverte": DecisionCommande.rouverture,
}
MONTANT = re.compile(r"(-?[0-9][0-9   ]*)(?:[.,][0-9]+)? MAD")
SEPARATEUR = " · "
MOTIF_MINIMUM = 3


@dataclass
class Fait:
    """Un geste lu au journal : quand, par qui (id PRO), le texte après le premier « · »."""

    quand: dt.datetime
    par_id: int | None
    detail: str
    journal_id: int

    @property
    def motif(self) -> str:
        """Le texte après « · » (le motif d'une annulation, d'un renvoi)."""
        return self.detail.split(SEPARATEUR, 1)[1].strip() if SEPARATEUR in self.detail else ""


@dataclass
class Journal:
    """Les gestes du journal source, par (objet, action, objet_id), dans l'ordre."""

    faits: dict[tuple[str, str], dict[int, list[Fait]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list))
    )

    def tous(self, objet: str, action: str, oid: int) -> list[Fait]:
        """Tous les gestes de cette action sur cet objet, du plus ancien au plus récent."""
        return self.faits.get((objet, action), {}).get(oid, [])

    def dernier(self, objet: str, action: str, oid: int) -> Fait | None:
        """Le plus récent geste de cette action sur cet objet."""
        faits = self.tous(objet, action, oid)
        return faits[-1] if faits else None


def lire(ctx: Contexte) -> Journal:
    """Indexe le journal source (ordre des identifiants)."""
    j = Journal()
    for x in ctx.photo.lignes("journal"):
        if x["objet_id"] is None:
            continue
        fait = Fait(
            ctx.norm.instant(x["quand"]) or x["quand"],
            ctx.personne(x["utilisateur"]),
            x["detail"] or "",
            x["id"],
        )
        j.faits[(x["objet"], x["action"])][x["objet_id"]].append(fait)
    return j


def montant(texte: str, rang: int = 0) -> float | None:
    """Le `rang`-ième montant « 1 234 567 MAD » d'un texte (None s'il n'y en a pas)."""
    trouves = MONTANT.findall(texte)
    if len(trouves) <= rang:
        return None
    return float(re.sub(r"[   ]", "", trouves[rang]))


def solde_de_commande(j: Journal, cid: int, statut: str) -> dict[str, Any]:
    """`solde_origine`, `solde_le`, `solde_par_id` d'un bon soldé ou annulé."""
    if statut not in ("soldee", "annulee"):
        return {"solde_origine": None, "solde_le": None, "solde_par_id": None}
    action = "commande soldée" if statut == "soldee" else "commande annulée"
    fait = j.dernier("commande", action, cid)
    if fait is None:
        return {"solde_origine": OrigineSolde.reprise.value, "solde_le": None, "solde_par_id": None}
    automatique = statut == "soldee" and fait.detail.endswith("tout reçu")
    origine = OrigineSolde.automatique if automatique else OrigineSolde.manuel
    return {"solde_origine": origine.value, "solde_le": fait.quand, "solde_par_id": fait.par_id}


def decisions(ctx: Contexte, j: Journal, commandes: set[int]) -> list[dict[str, Any]]:
    """Les décisions sur les bons (renvois, approbations…), dans l'ordre du journal."""
    lignes = []
    for action, decision in DECISIONS.items():
        for cid, faits in j.faits.get(("commande", action), {}).items():
            if cid not in commandes:
                continue
            for f in faits:
                motif = f.motif
                if decision == DecisionCommande.renvoi and len(motif) < MOTIF_MINIMUM:
                    ctx.signaler("commande_decision", f.journal_id, "renvoi sans motif lisible")
                    motif = "(motif non relu)"
                avant, apres = _montants(decision, f.detail)
                v = {
                    "commande_id": cid,
                    "quand": f.quand,
                    "par_id": f.par_id,
                    "decision": decision.value,
                    "motif": motif,
                    "montant_avant": avant,
                    "montant_apres": apres,
                }
                lignes.append((f.journal_id, ctx.ligne("commande_decision", v, f.journal_id)))
    return [v for _, v in sorted(lignes, key=lambda x: x[0])]


def _montants(decision: DecisionCommande, detail: str) -> tuple[float | None, float | None]:
    """Montants avant → après (MAD) d'une décision, quand le texte les donne."""
    if decision == DecisionCommande.approbation:
        return None, montant(detail)
    if "→" in detail:
        return montant(detail, 0), montant(detail, 1)
    return None, None


def plans(ctx: Contexte, journal_ids: dict[int, int]) -> None:
    """Versions du plan tirées du journal « plan de production » (ajoutées, jamais réécrites)."""
    par_qualite: dict[int, list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]] = (
        defaultdict(list)
    )
    for x in ctx.photo.lignes("journal"):
        if x["action"] != "plan de production" or x["objet"] != "qualite":
            continue
        try:
            v = json.loads((x["detail"] or "").split(MARQUE_PLAN, 1)[1])
            par_qualite[x["objet_id"]].append((x, v["avant"], v["apres"]))
        except (ValueError, IndexError, KeyError, TypeError):
            ctx.signaler("plan_version", x["id"], "plan illisible au journal : non repris")
    lignes: list[Ligne] = []
    saisons: dict[tuple[str, int], list[float]] = {}
    for qid, versions in sorted(par_qualite.items()):
        versions.sort(key=lambda t: (t[0]["quand"], t[0]["id"]))
        premier = versions[0][0]
        lignes.append(
            _version(
                ctx,
                qid,
                DEBUT_DES_TEMPS,
                versions[0][1],
                None,
                OrigineVersion.reprise,
                journal_ids.get(premier["id"]),
                "journal:plan_initial",
                qid,
                saisons,
            )
        )
        for x, _, apres in versions:
            lignes.append(
                _version(
                    ctx,
                    qid,
                    x["quand"],
                    apres,
                    ctx.personne(x["utilisateur"]),
                    OrigineVersion.saisie,
                    journal_ids.get(x["id"]),
                    "journal:plan",
                    x["id"],
                    saisons,
                )
            )
    _ajouter_versions(ctx, lignes, saisons)


def _version(  # noqa: PLR0917 (une version : toutes ses colonnes)
    ctx: Contexte,
    qid: int,
    quand: dt.datetime,
    plan: dict[str, Any],
    par: int | None,
    origine: OrigineVersion,
    journal_id: int | None,
    source: str,
    ident: int,
    saisons: dict[tuple[str, int], list[float]],
) -> Ligne:
    """Une version du plan (`b` base, `c` saisonnalité, `a` en service)."""
    v = {
        "qualite_id": qid,
        "valide_depuis": quand,
        "base_mensuelle": float(plan.get("b", 0.0)),
        "en_service": bool(plan.get("a", True)),
        "par_id": par,
        "origine": origine.value,
        "journal_id": journal_id,
    }
    saisons[(source, ident)] = [float(c) for c in plan.get("c", [1.0] * 12)]
    return Ligne((0,), ctx.ligne("plan_version", v, f"{source}/{ident}"), source, ident)


def _ajouter_versions(
    ctx: Contexte, lignes: list[Ligne], saisons: dict[tuple[str, int], list[float]]
) -> None:
    """Insère les versions pas encore reprises et leurs douze coefficients."""
    deja = {s: ecriture.correspondances(ctx, s) for s in ("journal:plan", "journal:plan_initial")}
    nouvelles = [x for x in lignes if x.id_source not in deja[x.table_source]]
    ctx.compter("plan_version", "sautees", len(lignes) - len(nouvelles))
    for x, i in zip(
        nouvelles, ecriture.prochains_ids(ctx, "plan_version", len(nouvelles)), strict=True
    ):
        x.valeurs["id"], x.cle = i, (i,)
    ecriture.ajouter(ctx, "plan_version", nouvelles)
    coefficients = [
        ctx.ligne("plan_version_saison", {"version_id": x.cle[0], "mois": m, "coefficient": c})
        for x in nouvelles
        for m, c in enumerate(saisons[(x.table_source, x.id_source)][:12], start=1)
    ]
    ecriture.inserer(ctx, "plan_version_saison", coefficients)
