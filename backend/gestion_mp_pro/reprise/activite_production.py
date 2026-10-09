"""Activité de la production et des opérations : ordres (← `bon_sortie`), qualités tissées,
lignes, prévu figé ; opérations et leurs lignes ; besoins signalés ; photos des indicateurs.

- Un ordre validé sans date de validation prend la fin de son jour : c'est l'instant que le
  moteur de Gestion MP prenait pour lui (recette en vigueur ce jour-là) ; signalé.
- `theorique` (JSON `{perte, fils: {référence: kg}}`) → `ordre_prevu` (la matière par son id)
  et `taux_perte_fige` ; une référence introuvable est signalée.
- Une qualité deux fois sur un ordre : m² additionnés (ce que `theorique` faisait déjà).
- Motif d'une opération : libellé connu → `motif_id`, sinon `motif_texte`.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from sqlalchemy import select

from gestion_mp_pro.modeles import Motif
from gestion_mp_pro.reprise import journal_en_tables as jt
from gestion_mp_pro.reprise.contexte import Contexte
from gestion_mp_pro.reprise.outils import Lignes, fin_du_jour, numero_de_document

URGENCES = {"normale": "normale", "urgente": "urgente", "urgent": "urgente", "": "normale"}
INDICATEURS = (
    "valeur_stock_mad",
    "couverture_jours",
    "ruptures",
    "critiques",
    "urgents",
    "a_commander_mad",
    "commandes_en_cours_mad",
    "otif_moyen",
)


def motifs(ctx: Contexte) -> dict[tuple[str, str], int]:
    """(type d'opération, libellé) → id du motif (table semée par PRO)."""
    lignes = ctx.c.execute(select(Motif.type_operation, Motif.libelle, Motif.id)).all()
    return {(str(t), lib): i for t, lib, i in lignes}


def ordres(ctx: Contexte, j: jt.Journal, sortie: Lignes) -> None:
    """Ordres de fabrication (← bons de sortie) et ce qui leur appartient."""
    for b in ctx.photo.lignes("bon_sortie"):
        v = {
            k: b[k]
            for k in (
                "id",
                "statut",
                "date",
                "magasin_id",
                "metier_id",
                "commentaire",
                "cree_le",
                "valide_le",
            )
        }
        v["numero"] = numero_de_document(ctx, "ordre", b, b["statut"] == "brouillon")
        v["cree_par_id"] = ctx.personne(b["cree_par"])
        v["valide_par_id"] = ctx.personne(b["valide_par"])
        if b["statut"] != "brouillon" and b["valide_le"] is None:
            v["valide_le"] = fin_du_jour(b["date"])
            ctx.compter("ordre", "signalees")
        if b["statut"] == "annule":
            fait = j.dernier("bon", "annulation bon de sortie", b["id"])
            v["annule_le"] = fait.quand if fait else v["valide_le"]
            v["annule_par_id"] = fait.par_id if fait else None
        fige = _theorique(ctx, b)
        v["prevu_fige"] = fige is not None
        v["taux_perte_fige"] = fige.get("perte", 0.0) if fige else None
        sortie["ordre"].append(ctx.ligne("ordre", v, b["id"]))
        if fige:
            _prevu(ctx, b["id"], fige.get("fils") or {}, sortie)
    sans_date = sum(
        1
        for b in ctx.photo.lignes("bon_sortie")
        if b["statut"] != "brouillon" and b["valide_le"] is None
    )
    if sans_date:
        ctx.norm.signaler("ordre", "*", f"{sans_date} ordres validés sans date : fin de leur jour")
    _fabrications(ctx, sortie)
    for x in ctx.photo.lignes("bon_ligne"):
        v = {
            "id": x["id"],
            "ordre_id": x["bon_id"],
            "matiere_id": x["article_id"],
            "lot_id": x["lot_id"],
            "quantite": x["quantite"],
        }
        sortie["ordre_ligne"].append(ctx.ligne("ordre_ligne", v, x["id"]))


def _theorique(ctx: Contexte, b: dict[str, Any]) -> dict[str, Any] | None:
    """Le prévu figé d'un ordre (None s'il n'en a pas, ou s'il est illisible : signalé)."""
    if not b["theorique"]:
        return None
    try:
        fige = json.loads(b["theorique"])
    except ValueError:
        ctx.signaler("ordre", b["id"], "prévu figé illisible : recalculé comme avant l'étape 9")
        return None
    return fige if isinstance(fige, dict) else None


def _prevu(ctx: Contexte, oid: int, fils: dict[str, float], sortie: Lignes) -> None:
    """`theorique.fils` (par référence) → `ordre_prevu` (par matière)."""
    cumul: dict[int, float] = defaultdict(float)
    for reference, kg in fils.items():
        mid = ctx.ids["reference"].get(reference)
        if mid is None:
            ctx.signaler("ordre_prevu", oid, f"référence « {reference} » introuvable")
            continue
        cumul[mid] += kg
    for mid, kg in sorted(cumul.items()):
        v = {"ordre_id": oid, "matiere_id": mid, "kg_hors_perte": kg}
        sortie["ordre_prevu"].append(ctx.ligne("ordre_prevu", v, oid))


def _fabrications(ctx: Contexte, sortie: Lignes) -> None:
    """Qualités tissées par ordre ; une qualité deux fois : m² additionnés (signalé)."""
    fusion: dict[tuple[int, int], dict[str, Any]] = {}
    for f in sorted(ctx.photo.lignes("bon_fabrication"), key=lambda x: x["id"]):
        cle = (f["bon_id"], f["qualite_id"])
        if cle in fusion:
            fusion[cle]["m2"] += f["m2"]
            ctx.signaler("ordre_qualite", f["id"], "qualité deux fois sur l'ordre : m² additionnés")
            ctx.compter("ordre_qualite", "ecartees")
            continue
        fusion[cle] = {
            "id": f["id"],
            "ordre_id": f["bon_id"],
            "qualite_id": f["qualite_id"],
            "m2": f["m2"],
        }
    sortie["ordre_qualite"] += [ctx.ligne("ordre_qualite", v, v["id"]) for v in fusion.values()]


def operations(ctx: Contexte, j: jt.Journal, sortie: Lignes) -> None:
    """Opérations (retours, transferts, ajustements, ouvertures, retours fournisseur)."""
    connus = motifs(ctx)
    for o in ctx.photo.lignes("operation"):
        v = {
            k: o[k]
            for k in (
                "id",
                "type",
                "statut",
                "date",
                "fournisseur_id",
                "commentaire",
                "cree_le",
                "validee_le",
            )
        }
        v["numero"] = numero_de_document(ctx, "operation", o, o["statut"] == "brouillon")
        v["ordre_id"] = o["bon_id"] if o["type"] == "retour_machine" else None
        v["motif_id"] = connus.get((o["type"], o["motif"] or ""))
        v["motif_texte"] = "" if v["motif_id"] or not o["motif"] else o["motif"]
        v["cree_par_id"] = ctx.personne(o["cree_par"])
        v["validee_par_id"] = ctx.personne(o["validee_par"])
        if o["statut"] != "brouillon" and o["validee_le"] is None:
            ctx.signaler("operation", o["id"], "validée sans date : fin de son jour")
            v["validee_le"] = fin_du_jour(o["date"])
        if o["statut"] == "annulee":
            fait = j.dernier("operation", "annulation opération", o["id"])
            v["annulee_le"] = fait.quand if fait else v["validee_le"]
            v["annulee_par_id"] = fait.par_id if fait else None
        sortie["operation"].append(ctx.ligne("operation", v, o["id"]))
    for x in ctx.photo.lignes("operation_ligne"):
        v = {
            k: x[k]
            for k in (
                "id",
                "operation_id",
                "lot_id",
                "magasin_id",
                "magasin_destination_id",
                "quantite",
                "prix",
            )
        }
        v["matiere_id"] = x["article_id"]
        interne = (x["lot_numero"] or "").strip().upper() == "LOT INTERNE"
        v["lot_interne"] = interne
        v["lot_numero"] = "" if interne else (x["lot_numero"] or "")
        v["devise"] = x["devise"] or None
        if x["prix"] and v["devise"] is None:
            ctx.signaler("operation_ligne", x["id"], "prix sans devise : MAD")
            v["devise"] = "MAD"
        sortie["operation_ligne"].append(ctx.ligne("operation_ligne", v, x["id"]))


def signalements(ctx: Contexte, comptes_sources: dict[int, int], sortie: Lignes) -> None:
    """Besoins signalés par l'atelier (le compte qui signale, étape 19 de Gestion MP)."""
    for x in ctx.photo.lignes("signalement"):
        v = {
            "id": x["id"],
            "quand": x["quand"],
            "matiere_id": x["article_id"],
            "texte": x["texte"],
            "urgence": URGENCES.get((x["urgence"] or "").lower(), "normale"),
            "reponse": x["reponse"] or "",
        }
        v["par_id"] = comptes_sources.get(x["par_id"]) if x["par_id"] else ctx.personne(x["par"])
        traite_par = ctx.personne(x["traite_par"])
        v["traite_le"] = x["traite_le"] if traite_par else None
        v["traite_par_id"] = traite_par if x["traite_le"] else None
        if x["traite_le"] and not traite_par:
            ctx.signaler("signalement", x["id"], "traité par un inconnu : remis « à traiter »")
        sortie["signalement"].append(ctx.ligne("signalement", v, x["id"]))


def indicateurs(ctx: Contexte, sortie: Lignes) -> None:
    """Photos des indicateurs du jour : le JSON en colonnes."""
    for x in ctx.photo.lignes("indicateur_jour"):
        try:
            contenu = json.loads(x["contenu"] or "{}")
        except ValueError:
            ctx.signaler("indicateur_jour", x["jour"], "photo illisible : non reprise")
            continue
        v = {k: contenu.get(k) for k in INDICATEURS}
        for k in ("valeur_stock_mad", "a_commander_mad", "commandes_en_cours_mad"):
            v[k] = v[k] or 0
        for k in ("ruptures", "critiques", "urgents"):
            v[k] = int(v[k] or 0)
        v["jour"] = x["jour"]
        v["pris_le"] = fin_du_jour(x["jour"])
        sortie["indicateur_jour"].append(ctx.ligne("indicateur_jour", v, x["jour"]))
