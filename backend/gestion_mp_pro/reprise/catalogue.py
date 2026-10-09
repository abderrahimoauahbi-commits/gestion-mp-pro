"""Catalogue et qualités : matières, qualités, poids, saisons, recettes, versions de recette.

- `article` → `matiere` (identifiants gardés ; codes de classification, rôle et code douanier
  → identifiants). Ce que le schéma de PRO refuse est corrigé **et signalé** : contenance
  d'achat nulle (→ achat au kg, 1 kg par unité), unité d'achat « ml » (→ kg), prix au mètre
  sans densité (→ kg), priorité hors 0–100 (→ vide).
- Poids, saisons et recette d'une qualité : ensembles remplacés qualité par qualité.
- `recette_version` : versions gardées avec leur identifiant, numérotées 1, 2, 3… par qualité
  dans l'ordre de leur date ; le JSON devient des lignes (`recette_version_ligne`, la matière
  par son **id**) et des poids (`recette_version_poids`) ; poids absents → `poids_connus` faux.
  Une version sans auteur vient de la reprise de l'ERP Fil (origine `reprise`).
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from sqlalchemy import func, select

from gestion_mp_pro.modeles import RecetteVersion
from gestion_mp_pro.modeles.enums import OrigineVersion
from gestion_mp_pro.reprise import ecriture
from gestion_mp_pro.reprise.contexte import Contexte, Ligne

COLONNES_MATIERE = (
    "id",
    "reference",
    "designation",
    "couleur_code",
    "unite_prix",
    "densite",
    "fournisseur_id",
    "prix",
    "devise",
    "unite_achat",
    "contenance_achat",
    "minimum_commande",
    "poids_bobine",
    "bobines_palette",
    "stock_min",
    "couv_min_mois",
    "groupe_equiv",
    "priorite_equiv",
    "actif",
    "modifie_le",
)
RELEVE = "relevé à la mise à jour"
"""Auteur écrit par Gestion MP pour une version relevée à une mise à jour (étape 9)."""
CODES = (
    ("composition", "composition"),
    ("type_fil", "type_fil"),
    ("titrage", "titrage"),
    ("couleur", "couleur"),
)


def _corriger_matiere(ctx: Contexte, a: dict[str, Any], v: dict[str, Any]) -> None:
    """Ce que les CHECK de PRO refuseraient : corrigé et signalé."""
    if not a["contenance_achat"] or a["contenance_achat"] <= 0:
        ctx.signaler(
            "matiere",
            a["reference"],
            f"contenance d'achat nulle ({a['unite_achat']}) : achat au kg",
        )
        v["contenance_achat"] = 1
        v["unite_achat"] = "kg"
    if (a["unite_achat"] or "").lower() == "ml":
        ctx.signaler("matiere", a["reference"], "unité d'achat « ml » : kg")
        v["unite_achat"] = "kg"
    if a["unite_prix"] == "ml" and not (a["densite"] or 0) > 0:
        ctx.signaler("matiere", a["reference"], "prix au mètre sans densité : prix au kg")
        v["unite_prix"] = "kg"
    priorite = a["priorite_equiv"]
    if priorite is not None and not 0 <= priorite <= 100:  # noqa: PLR2004
        ctx.signaler("matiere", a["reference"], f"priorité {priorite} hors 0–100 : vide")
        v["priorite_equiv"] = None


def matieres(ctx: Contexte) -> None:
    """Les matières (← `article`)."""
    lignes = []
    for a in ctx.photo.lignes("article"):
        v = {k: a[k] for k in COLONNES_MATIERE}
        v["role_id"] = ctx.code("role", a["role"])
        if v["role_id"] is None:
            ctx.signaler("matiere", a["reference"], f"rôle « {a['role']} » inconnu : non reprise")
            ctx.compter("matiere", "ecartees")
            continue
        for colonne, genre in CODES:
            v[f"{colonne}_id"] = ctx.code(genre, a[colonne])
            if a[colonne] and v[f"{colonne}_id"] is None:
                ctx.signaler("matiere", a["reference"], f"{colonne} « {a[colonne]} » inconnu")
        v["code_douanier_id"] = ctx.code("code_douanier", a["code_douanier"])
        v["modifie_par_id"] = ctx.personne(a["modifie_par"])
        _corriger_matiere(ctx, a, v)
        lignes.append(Ligne((a["id"],), ctx.ligne("matiere", v, a["id"]), "article", a["id"]))
    ecriture.appliquer(ctx, "matiere", lignes, ("id",))
    ctx.ids["reference"] = {a["reference"]: a["id"] for a in ctx.photo.lignes("article")}
    ctx.ids["role_matiere"] = {
        a["id"]: ctx.code("role", a["role"]) or 0 for a in ctx.photo.lignes("article")
    }


def qualites(ctx: Contexte) -> None:
    """Qualités, puis leurs poids, saisons et recettes (ensembles par qualité)."""
    lignes = [
        Ligne(
            (q["id"],),
            ctx.ligne(
                "qualite",
                {k: q[k] for k in ("id", "code", "nom", "base_mensuelle", "actif")},
                q["id"],
            ),
            "qualite",
            q["id"],
        )
        for q in ctx.photo.lignes("qualite")
    ]
    ecriture.appliquer(ctx, "qualite", lignes, ("id",))
    ids = [q["id"] for q in ctx.photo.lignes("qualite")]
    ecriture.appliquer_groupes(ctx, "qualite_poids", "qualite_id", _poids(ctx, ids))
    saisons: dict[int, list[dict[str, Any]]] = {i: [] for i in ids}
    for s in ctx.photo.lignes("qualite_saison"):
        v = {"qualite_id": s["qualite_id"], "mois": s["mois"], "coefficient": s["coefficient"]}
        saisons[s["qualite_id"]].append(ctx.ligne("qualite_saison", v, s["id"]))
    ecriture.appliquer_groupes(ctx, "qualite_saison", "qualite_id", saisons)
    ecriture.appliquer_groupes(ctx, "recette", "qualite_id", _recettes(ctx, ids))


def _poids(ctx: Contexte, ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """Poids au m² par qualité et rôle (rôle inconnu : signalé)."""
    poids: dict[int, list[dict[str, Any]]] = {i: [] for i in ids}
    for p in ctx.photo.lignes("qualite_poids"):
        role = ctx.code("role", p["role"])
        if role is None:
            ctx.signaler("qualite_poids", p["id"], f"rôle « {p['role']} » inconnu")
            ctx.compter("qualite_poids", "ecartees")
            continue
        v = {"qualite_id": p["qualite_id"], "role_id": role, "poids": p["poids"]}
        poids[p["qualite_id"]].append(ctx.ligne("qualite_poids", v, p["id"]))
    return poids


def _recettes(ctx: Contexte, ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """Recette de chaque qualité ; une matière en double dans une qualité : additionnée."""
    cumul: dict[tuple[int, int], float] = defaultdict(float)
    for r in ctx.photo.lignes("recette"):
        cle = (r["qualite_id"], r["article_id"])
        if cle in cumul:
            ctx.signaler("recette", r["id"], "matière deux fois dans la recette : additionnée")
            ctx.compter("recette", "ecartees")
        cumul[cle] += r["pourcentage"]
    recettes: dict[int, list[dict[str, Any]]] = {i: [] for i in ids}
    for (qid, mid), pct in sorted(cumul.items()):
        v = {"qualite_id": qid, "matiere_id": mid, "pourcentage": pct}
        recettes[qid].append(ctx.ligne("recette", v, f"{qid}/{mid}"))
    return recettes


def versions_de_recette(ctx: Contexte) -> None:
    """Versions de recette (identifiants gardés), leurs lignes et leurs poids."""
    sources = sorted(ctx.photo.lignes("recette_version"), key=lambda r: (r["quand"], r["id"]))
    rang: dict[int, int] = defaultdict(int)
    existants = dict(
        ctx.c.execute(
            select(RecetteVersion.qualite_id, func.max(RecetteVersion.numero)).group_by(
                RecetteVersion.qualite_id
            )
        ).all()
    )
    deja = ecriture.correspondances(ctx, "recette_version")
    lignes = []
    for r in sources:
        rang[r["qualite_id"]] += 1
        if r["id"] in deja:
            ctx.compter("recette_version", "sautees")
            continue
        numero = max(rang[r["qualite_id"]], existants.get(r["qualite_id"], 0) + 1)
        existants[r["qualite_id"]] = numero
        v = {
            "id": r["id"],
            "qualite_id": r["qualite_id"],
            "numero": numero,
            "valide_depuis": r["quand"],
            "par_id": ctx.personne(r["par"]),
            "origine": _origine(r["par"]).value,
            "poids_connus": r["poids"] is not None,
        }
        lignes.append(
            Ligne((r["id"],), ctx.ligne("recette_version", v, r["id"]), "recette_version", r["id"])
        )
    ecriture.recaler_sequence(ctx, "recette_version")
    ajoutees = ecriture.ajouter(ctx, "recette_version", lignes)
    _contenu_des_versions(ctx, {x.id_source for x in ajoutees})


def _origine(par: str | None) -> OrigineVersion:
    """Saisie (une personne), relevé (mise à jour de Gestion MP), reprise (ERP Fil, sans auteur)."""
    nom = (par or "").strip().lower()
    if nom == RELEVE:
        return OrigineVersion.releve
    return OrigineVersion.saisie if nom else OrigineVersion.reprise


def _contenu_des_versions(ctx: Contexte, ids: set[int]) -> None:
    """Le JSON `contenu` et `poids` des versions ajoutées, en lignes."""
    lignes, poids = [], []
    for r in ctx.photo.lignes("recette_version"):
        if r["id"] not in ids:
            continue
        cumul: dict[int, dict[str, Any]] = {}
        for x in json.loads(r["contenu"] or "[]"):
            mid = ctx.ids["reference"].get(x.get("reference"))
            if mid is None:
                ctx.signaler("recette_version", r["id"], f"« {x.get('reference')} » introuvable")
                continue
            role = ctx.code("role", x.get("role")) or ctx.ids["role_matiere"].get(mid)
            if mid in cumul:
                cumul[mid]["pourcentage"] += x.get("pourcentage", 0.0)
                ctx.signaler("recette_version", r["id"], "matière en double : additionnée")
                continue
            cumul[mid] = {
                "version_id": r["id"],
                "matiere_id": mid,
                "role_id": role,
                "pourcentage": x.get("pourcentage", 0.0),
            }
        lignes += [ctx.ligne("recette_version_ligne", v, r["id"]) for v in cumul.values()]
        for role_code, valeur in json.loads(r["poids"] or "{}").items():
            role = ctx.code("role", role_code)
            if role is None:
                ctx.signaler("recette_version", r["id"], f"rôle « {role_code} » inconnu")
                continue
            v = {"version_id": r["id"], "role_id": role, "poids": valeur}
            poids.append(ctx.ligne("recette_version_poids", v, r["id"]))
    ecriture.inserer(ctx, "recette_version_ligne", lignes)
    ecriture.inserer(ctx, "recette_version_poids", poids)
