"""Activité des importations : dossiers, marchandises, frais et parts figées.

- Numéro `NN/AA` → `annee` + `rang` (le compteur DOS repart du plus grand) ; un autre format
  devient `ANC-…` (signalé). Un dossier sans facture est « saisi à la main ».
- Marchandise : `quantite` → `quantite_kg` (`poids_kg`, colonne morte, n'est pas reprise) ;
  cours 0 ou MAD → NULL ; tout cours dit son origine (`clos_au_jour` si figé à la clôture,
  sinon `reprise`) ; une ligne reçue déjà portée par un autre dossier est détachée (signalé).
- Frais : poste par son code ; un frais nul est écarté (signalé) ; un rattachement à la
  marchandise d'un autre dossier est retiré (signalé).
- Parts figées : arrondies au centime **aux plus forts restes** (Σ parts = montant du frais).
"""

from __future__ import annotations

import re
from collections import defaultdict
from decimal import ROUND_FLOOR, Decimal
from typing import Any

from gestion_mp_pro.modeles.enums import OrigineCours, OriginePart
from gestion_mp_pro.reprise import journal_en_tables as jt
from gestion_mp_pro.reprise.contexte import Contexte
from gestion_mp_pro.reprise.outils import Lignes, zero_en_nul

NUMERO = re.compile(r"([0-9]{1,3})/([0-9]{2})")
CENTIME = Decimal("0.01")


def dossiers(ctx: Contexte, j: jt.Journal, sortie: Lignes) -> None:
    """Dossiers d'importation."""
    for d in ctx.photo.lignes("dossier"):
        v = {
            k: d[k]
            for k in (
                "id",
                "libelle",
                "date_arrivee",
                "banque",
                "statut",
                "clos_le",
                "commentaire",
                "facture_id",
            )
        }
        numero = (d["numero"] or "").strip()
        forme = NUMERO.fullmatch(numero)
        if forme:
            v["annee"], v["rang"] = 2000 + int(forme.group(2)), int(forme.group(1))
        else:
            ctx.signaler(
                "dossier", d["id"], f"numéro « {numero} » hors format NN/AA : ANC-{numero}"
            )
            numero = f"ANC-{numero}"
            v["annee"] = v["rang"] = None
        v["numero"] = numero
        v["saisi_a_la_main"] = d["facture_id"] is None
        ouverture = j.dernier("dossier", "ouverture dossier", d["id"])
        if ouverture:
            v["cree_le"], v["cree_par_id"] = ouverture.quand, ouverture.par_id
        cloture = j.dernier("dossier", "clôture dossier", d["id"])
        v["clos_par_id"] = cloture.par_id if (cloture and d["statut"] == "clos") else None
        if d["statut"] == "clos" and d["clos_le"] is None:
            ctx.signaler("dossier", d["id"], "clos sans date : date de clôture du journal")
            v["clos_le"] = cloture.quand if cloture else d["date_arrivee"]
        sortie["dossier"].append(ctx.ligne("dossier", v, d["id"]))
    _marchandises(ctx, sortie)
    _frais(ctx, sortie)


def _marchandises(ctx: Contexte, sortie: Lignes) -> None:
    """Lignes des dossiers (une ligne reçue dans un seul dossier)."""
    portees: set[int] = set()
    for x in ctx.photo.lignes("dossier_ligne"):
        v = {
            k: x[k]
            for k in (
                "id",
                "dossier_id",
                "reception_ligne_id",
                "lot_id",
                "fournisseur_id",
                "valeur_devise",
                "devise",
            )
        }
        v.update(
            matiere_id=x["article_id"],
            quantite_kg=x["quantite"],
            commentaire=x["commentaire"] or "",
        )
        if x["reception_ligne_id"] in portees:
            ctx.signaler(
                "dossier_ligne", x["id"], "ligne reçue déjà dans un autre dossier : détachée"
            )
            v["reception_ligne_id"] = None
        if x["reception_ligne_id"]:
            portees.add(x["reception_ligne_id"])
        cours = None if x["devise"] == "MAD" else zero_en_nul(x["cours"])
        v["cours"] = cours
        origine = OrigineCours.clos_au_jour if x["cours_fige_cloture"] else OrigineCours.reprise
        v["cours_origine"] = origine.value if cours else None
        sortie["dossier_ligne"].append(ctx.ligne("dossier_ligne", v, x["id"]))


def _frais(ctx: Contexte, sortie: Lignes) -> None:
    """Frais (poste par son code) et parts figées aux plus forts restes."""
    ligne_de = {x["id"]: x["dossier_id"] for x in ctx.photo.lignes("dossier_ligne")}
    clos = {d["id"]: d["clos_le"] for d in ctx.photo.lignes("dossier")}
    gardes: dict[int, Decimal] = {}
    for f in ctx.photo.lignes("dossier_charge"):
        poste = ctx.code("poste", f["poste"])
        if poste is None or not f["montant"]:
            raison = f"poste « {f['poste']} » inconnu" if poste is None else "montant nul"
            ctx.signaler("dossier_frais", f["id"], f"{raison} : frais non repris")
            ctx.compter("dossier_frais", "ecartees")
            continue
        v = {
            k: f[k]
            for k in (
                "id",
                "dossier_id",
                "montant",
                "piece",
                "prestataire",
                "date_piece",
                "echeance",
                "payee_le",
                "commentaire",
            )
        }
        v.update(
            poste_id=poste,
            ligne_id=f["ligne_id"],
            piece=f["piece"] or "",
            prestataire=f["prestataire"] or "",
            commentaire=f["commentaire"] or "",
        )
        if f["ligne_id"] and ligne_de.get(f["ligne_id"]) != f["dossier_id"]:
            ctx.signaler("dossier_frais", f["id"], "rattaché à la marchandise d'un autre dossier")
            v["ligne_id"] = None
        ligne = ctx.ligne("dossier_frais", v, f["id"])
        gardes[f["id"]] = ligne["montant"]
        sortie["dossier_frais"].append(ligne)
    parts: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for p in ctx.photo.lignes("dossier_charge_part"):
        if p["charge_id"] in gardes:
            parts[p["charge_id"]].append(p)
    dossier_du_frais = {f["id"]: f["dossier_id"] for f in ctx.photo.lignes("dossier_charge")}
    for fid, lot in sorted(parts.items()):
        figee = clos.get(dossier_du_frais[fid])
        for p, montant in zip(
            lot, plus_forts_restes(gardes[fid], [p["montant"] for p in lot]), strict=True
        ):
            v = {
                "frais_id": fid,
                "ligne_id": p["ligne_id"],
                "montant": montant,
                "origine": OriginePart.reprise.value,
            }
            if figee:
                v["figee_le"] = figee
            sortie["dossier_frais_part"].append(ctx.ligne("dossier_frais_part", v, fid))


def plus_forts_restes(total: Decimal, parts: list[float]) -> list[Decimal]:
    """Répartit `total` (au centime) au prorata de `parts` ; Σ du résultat = total exactement."""
    if not parts:
        return []
    somme = sum(Decimal(repr(p)) for p in parts)
    if somme == 0:
        brutes = [total / len(parts)] * len(parts)
    else:
        brutes = [total * Decimal(repr(p)) / somme for p in parts]
    signe = Decimal(-1) if total < 0 else Decimal(1)
    absolues = [abs(b) for b in brutes]
    planchers = [a.quantize(CENTIME, rounding=ROUND_FLOOR) for a in absolues]
    reste = int((abs(total) - sum(planchers)) / CENTIME)
    ordre = sorted(range(len(parts)), key=lambda i: (-(absolues[i] - planchers[i]), i))
    for i in ordre[:reste]:
        planchers[i] += CENTIME
    return [signe * x for x in planchers]
