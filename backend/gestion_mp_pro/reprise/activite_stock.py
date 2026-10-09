"""Activité du stock : lots, mouvements (ids gardés), soldes recalculés, inventaires.

- Lot : `interne` déduit du numéro (`LOT-AAAA-NNNN`) ; un numéro avec des blancs (refusé par
  PRO) a ses blancs remplacés par « _ » (signalé) ; `poids_bobine_le` = date de la dernière
  réception validée qui l'a pesé.
- Mouvement : `document_id` → clé typée (`reception_id`, `operation_id`, `inventaire_id`),
  `sortie` → `ordre` ; une entrée de réception reprise de l'ERP Fil sans `document_id` retrouve
  sa réception par (lot, date) ; `cours` 0 ou MAD → NULL ; motif connu → `motif_id`. Le prix
  n'est gardé que sur les entrées (CHECK `ck_mouvement_prix_entree` : sorties, transferts,
  retours machine sont valorisés au coût moyen ; leur prix de Gestion MP, informatif, est
  compté au rapport).
- Solde : **recalculé** = Σ des mouvements arrondis, par (lot, magasin) (C12 par construction).
"""

from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal
from typing import Any

from gestion_mp_pro.reprise import journal_en_tables as jt
from gestion_mp_pro.reprise.activite_production import motifs
from gestion_mp_pro.reprise.contexte import Contexte
from gestion_mp_pro.reprise.outils import Lignes, debut_du_jour, fin_du_jour

LOT_INTERNE = re.compile(r"LOT-[0-9]{4}-[0-9]+")
BLANCS = re.compile(r"\s+")
ENTREES = frozenset({"OUVERTURE", "RECEPTION", "RETOUR_FOURNISSEUR", "AJUSTEMENT"})
TYPE_MOTIF = {
    "RETOUR_MACHINE": "retour_machine",
    "RETOUR_FOURNISSEUR": "retour_fournisseur",
    "AJUSTEMENT": "ajustement",
    "TRANSFERT": "transfert",
    "OUVERTURE": "ouverture",
}
DOCUMENTS = {
    "sortie": "ordre",
    "reception": "reception",
    "operation": "operation",
    "inventaire": "inventaire",
    "reprise": "reprise",
}


def lots(ctx: Contexte, sortie: Lignes) -> None:
    """Lots : numéro sans blanc, lot interne reconnu, date du poids de bobine."""
    pese_le = _pesees(ctx)
    pris: set[tuple[int, str]] = set()
    remplaces = 0
    for x in ctx.photo.lignes("lot"):
        numero = (x["numero"] or "").strip()
        propre = BLANCS.sub("_", numero) or f"SANS-NUMERO-{x['id']}"
        if propre != x["numero"]:
            remplaces += 1
        if (x["article_id"], propre) in pris:
            propre = f"{propre}_{x['id']}"
        pris.add((x["article_id"], propre))
        v = {
            "id": x["id"],
            "matiere_id": x["article_id"],
            "numero": propre,
            "interne": bool(LOT_INTERNE.fullmatch(propre)),
            "fournisseur_id": x["fournisseur_id"],
            "entre_le": x["entre_le"],
            "poids_bobine": x["poids_bobine"],
            "poids_bobine_le": pese_le.get(x["id"]) if x["poids_bobine"] else None,
            "commentaire": x["commentaire"] or "",
        }
        sortie["lot"].append(ctx.ligne("lot", v, x["id"]))
    if remplaces:
        ctx.norm.signaler(
            "lot", "*", f"{remplaces} numéros de lot avec des blancs : blancs → « _ »"
        )
        ctx.compter("lot", "signalees", remplaces)


def _pesees(ctx: Contexte) -> dict[int, Any]:
    """Lot → date de la dernière réception validée qui en a compté les bobines."""
    dates = {r["id"]: r["date"] for r in ctx.photo.lignes("reception") if r["statut"] == "validee"}
    dernier: dict[int, Any] = {}
    for x in ctx.photo.lignes("reception_ligne"):
        jour = dates.get(x["reception_id"])
        if x["lot_id"] and jour and (x["nb_bobines"] or 0) > 0:
            dernier[x["lot_id"]] = max(jour, dernier.get(x["lot_id"], jour))
    return dernier


def _receptions_par_lot(ctx: Contexte) -> dict[tuple[int, Any], int]:
    """(lot, date) → réception validée qui a fait entrer ce lot ce jour-là."""
    receptions = {r["id"]: r for r in ctx.photo.lignes("reception") if r["statut"] != "brouillon"}
    index: dict[tuple[int, Any], int] = {}
    for x in ctx.photo.lignes("reception_ligne"):
        r = receptions.get(x["reception_id"])
        if r and x["lot_id"]:
            index.setdefault((x["lot_id"], r["date"]), r["id"])
    return index


def _document(
    m: dict[str, Any], index: dict[tuple[int, Any], int], numeros: dict[str, int]
) -> dict[str, Any]:
    """Le document du mouvement en clés typées (vide de clés si rien n'est retrouvé)."""
    document = DOCUMENTS.get(m["document"], "reprise")
    v: dict[str, Any] = {
        "document": document,
        "reception_id": None,
        "operation_id": None,
        "inventaire_id": None,
        "ordre_id": m["ordre_id"],
    }
    if document == "reception":
        v["reception_id"] = (
            m["document_id"]
            or index.get((m["lot_id"], m["date_effet"]))
            or numeros.get(m["document_numero"])
        )
    elif document == "ordre":
        v["ordre_id"] = m["ordre_id"] or m["document_id"]
    elif document in ("operation", "inventaire"):
        v[f"{document}_id"] = m["document_id"]
    cle = {
        "reception": "reception_id",
        "ordre": "ordre_id",
        "operation": "operation_id",
        "inventaire": "inventaire_id",
    }.get(document)
    if (
        cle
        and v[cle] is None
        or (document == "ordre" and m["type"] != "SORTIE")
        or (document == "inventaire" and m["type"] != "AJUSTEMENT")
    ):
        v.update(document="reprise", reception_id=None, operation_id=None, inventaire_id=None)
    return v


def mouvements(ctx: Contexte, sortie: Lignes) -> None:
    """Mouvements du journal du stock, identifiants gardés ; puis les soldes recalculés."""
    index = _receptions_par_lot(ctx)
    numeros = {r["numero"]: r["id"] for r in ctx.photo.lignes("reception") if r["numero"]}
    connus = motifs(ctx)
    taux = {d["code"]: d["taux"] for d in ctx.photo.lignes("devise")}
    prix_retires = sans_document = cours_figes = 0
    for m in ctx.photo.lignes("mouvement"):
        v = {
            k: m[k]
            for k in (
                "id",
                "date_effet",
                "type",
                "lot_id",
                "magasin_id",
                "quantite",
                "devise",
                "document_numero",
                "contrepasse_id",
                "commentaire",
            )
        }
        v.update(saisi_le=m["date_saisie"], matiere_id=m["article_id"], paire_id=m["paire"])
        v.update(_document(m, index, numeros))
        if v["document"] == "reprise" and m["document"] != "reprise":
            sans_document += 1
        v["prix"] = m["prix"] if m["type"] in ENTREES else 0.0
        prix_retires += int(m["type"] not in ENTREES and bool(m["prix"]))
        v["cours"] = None if m["devise"] == "MAD" or not v["prix"] else m["cours"] or None
        if v["prix"] and m["devise"] != "MAD" and not m["cours"] and taux.get(m["devise"]):
            v["cours"] = taux[m["devise"]]
            cours_figes += 1
        genre = "inventaire" if v["document"] == "inventaire" else TYPE_MOTIF.get(m["type"], "")
        v["motif_id"] = connus.get((genre, m["motif"] or ""))
        v["motif_texte"] = "" if v["motif_id"] else (m["motif"] or "")
        v["auteur_id"] = ctx.personne(m["auteur"])
        sortie["mouvement"].append(ctx.ligne("mouvement", v, m["id"]))
    if prix_retires:
        ctx.norm.signaler(
            "mouvement",
            "*",
            f"{prix_retires} prix de sorties, transferts ou "
            "retours machine non repris (valorisés au coût moyen)",
        )
    if cours_figes:
        ctx.norm.signaler(
            "mouvement",
            "*",
            f"{cours_figes} entrées en devise sans cours : cours du jour de la reprise figé "
            "(V3, V4 : un changement de cours ne revalorise plus un mois clos)",
        )
    if sans_document:
        ctx.norm.signaler(
            "mouvement", "*", f"{sans_document} mouvements sans document retrouvé : « reprise »"
        )
    _soldes(ctx, sortie)


def _soldes(ctx: Contexte, sortie: Lignes) -> None:
    """Soldes = Σ des mouvements arrondis, par (lot, magasin)."""
    somme: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    maj: dict[tuple[int, int], Any] = {}
    for v in sortie["mouvement"]:
        cle = (v["lot_id"], v["magasin_id"])
        somme[cle] += v["quantite"]
        maj[cle] = max(v["saisi_le"], maj.get(cle, v["saisi_le"]))
    for (lot, magasin), total in sorted(somme.items()):
        q = total
        if q < 0:
            ctx.signaler("solde", f"{lot}/{magasin}", f"Σ des mouvements {q} < 0 : solde à 0")
            q = Decimal("0.000")
        sortie["solde"].append(
            {"lot_id": lot, "magasin_id": magasin, "quantite": q, "maj_le": maj[(lot, magasin)]}
        )


def inventaires(ctx: Contexte, j: jt.Journal, sortie: Lignes) -> None:
    """Inventaires (ouverts repris ouverts, signalés), lignes et matières suspendues."""
    for i in ctx.photo.lignes("inventaire"):
        v = {
            k: i[k]
            for k in ("id", "numero", "libelle", "statut", "date", "magasin_id", "tolerance")
        }
        ouverture = j.dernier("inventaire", "ouverture inventaire", i["id"])
        v["cree_le"] = ouverture.quand if ouverture else debut_du_jour(i["date"])
        v["cree_par_id"] = ctx.personne(i["cree_par"])
        v["valide_par_id"] = ctx.personne(i["valide_par"])
        v["valide_le"] = i["valide_le"]
        if i["statut"] in ("valide", "annule") and i["valide_le"] is None:
            v["valide_le"] = fin_du_jour(i["date"])
            ctx.signaler("inventaire", i["numero"], "validé sans date : fin de son jour")
        if i["statut"] == "ouvert":
            ctx.signaler(
                "inventaire", i["numero"], "inventaire ouvert dans la source : repris ouvert"
            )
        _fin(i, j, v)
        sortie["inventaire"].append(ctx.ligne("inventaire", v, i["id"]))
    _lignes_d_inventaire(ctx, sortie)


def _fin(i: dict[str, Any], j: jt.Journal, v: dict[str, Any]) -> None:
    """Abandon ou annulation : date, auteur, motif lus au journal (à défaut, la validation)."""
    if i["statut"] == "abandonne":
        fait = j.dernier("inventaire", "abandon inventaire", i["id"])
        v["abandonne_le"] = fait.quand if fait else fin_du_jour(i["date"])
        v["abandonne_par_id"] = fait.par_id if fait else None
        v["abandon_motif"] = fait.motif if fait else ""
    if i["statut"] == "annule":
        fait = j.dernier("inventaire", "annulation inventaire", i["id"])
        v["annule_le"] = fait.quand if fait else v["valide_le"]
        v["annule_par_id"] = fait.par_id if fait else None
        v["annulation_motif"] = fait.motif if fait else ""


def _lignes_d_inventaire(ctx: Contexte, sortie: Lignes) -> None:
    """Lignes comptées ; matière de la ligne (ou de son lot) ; lot trouvé = théorique nul."""
    matiere_du_lot = {x["id"]: x["article_id"] for x in ctx.photo.lignes("lot")}
    suspendues: set[tuple[int, int]] = set()
    for x in ctx.photo.lignes("inventaire_ligne"):
        v = {
            k: x[k]
            for k in (
                "id",
                "inventaire_id",
                "lot_id",
                "magasin_id",
                "theorique",
                "compte",
                "nb_palettes",
                "nb_bobines",
                "second_compte",
                "justification",
            )
        }
        v["matiere_id"] = x["article_id"] or matiere_du_lot.get(x["lot_id"])
        interne = (x["lot_numero"] or "").strip().upper() == "LOT INTERNE"
        v["lot_interne"] = interne and x["lot_id"] is None
        v["lot_numero"] = "" if interne else (x["lot_numero"] or "")
        v["second_par_id"] = ctx.personne(x["second_par"])
        if x["second_compte"] is not None and x["compte"] is None:
            ctx.signaler("inventaire_ligne", x["id"], "recomptage sans premier comptage : 1ᵉʳ = 2ᵉ")
            v["compte"] = x["second_compte"]
        if x["lot_id"] is None and x["theorique"]:
            ctx.signaler("inventaire_ligne", x["id"], "lot trouvé avec un théorique : mis à 0")
            v["theorique"] = 0.0
        v["lot_trouve"] = not v["theorique"]
        sortie["inventaire_ligne"].append(ctx.ligne("inventaire_ligne", v, x["id"]))
        suspendues.add((x["inventaire_id"], v["matiere_id"]))
    sortie["inventaire_matiere"] += [
        {"inventaire_id": i, "matiere_id": m} for i, m in sorted(suspendues) if m is not None
    ]
