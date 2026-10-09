"""Réception payée en deux devises : **scindée** en une réception par devise (R1 n° 2, K8b).

Dans PRO, un camion payé en deux devises donne une réception par devise, chacune avec sa
facture (D4, I35). Une réception de Gestion MP dont les lignes portent deux devises est donc
reprise en autant de réceptions que de devises :

- la **première** garde l'identifiant, le numéro, la facture, les pièces et le journal
  d'origine ; sa devise est celle de sa facture (sinon celle de la plupart des lignes) ;
- chaque **autre** devise donne une réception nouvelle (identifiant pris après le plus grand
  de la source, numéro d'origine suivi de `-2`, `-3`…, ce que `reception.numero` permet :
  aucun format n'est imposé, 32 caractères au plus), mêmes date, fournisseur, BL, contrôle,
  auteurs et statut, **sans facture** (Gestion MP n'en a qu'une par réception : signalé) ;
- ses lignes, ses mouvements d'entrée (retrouvés par leur lot) et ses réclamations de ligne
  la suivent ; les lots, quantités, prix, cours et valeurs ne changent pas ; les dossiers
  d'importation restent sur leur facture et sur les lignes reçues (identifiants gardés).

Seule la devise dans laquelle un prix est lu change : elle devient la vraie.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from gestion_mp_pro.modeles.longueurs import NUMERO
from gestion_mp_pro.reprise.contexte import Contexte
from gestion_mp_pro.reprise.outils import Lignes

TABLE_SOURCE = "reception:scindee"
"""Table source des correspondances des réceptions nées d'une scission (aucune ligne source)."""


def numero_scinde(numero: str | None, rang: int) -> str | None:
    """Le numéro de la `rang`-ième réception d'une scission (`REC-2026-0042-2`)."""
    if numero is None:
        return None
    nouveau = f"{numero}-{rang}"
    if len(nouveau) > NUMERO:
        msg = f"numéro {nouveau} trop long pour reception.numero ({NUMERO})"
        raise ValueError(msg)
    return nouveau


def _devises_des_lignes(ctx: Contexte) -> dict[int, dict[int, str]]:
    """Réception → (ligne → devise de la ligne dans la source)."""
    par_reception: dict[int, dict[int, str]] = defaultdict(dict)
    for x in ctx.photo.lignes("reception_ligne"):
        par_reception[x["reception_id"]][x["id"]] = x["devise"]
    return par_reception


def scinder(ctx: Contexte, sortie: Lignes) -> None:
    """Scinde chaque réception en deux devises ; suit lignes, mouvements, réclamations."""
    devises = _devises_des_lignes(ctx)
    prochain = max((r["id"] for r in ctx.photo.lignes("reception")), default=0) + 1
    deplacees: dict[int, int] = {}
    nouvelles = []
    for r in sortie["reception"]:
        autres = sorted(set(devises[r["id"]].values()) - {r["devise"]})
        for rang, devise in enumerate(autres, start=2):
            n = _nouvelle(ctx, r, devise, rang, prochain)
            nouvelles.append(n)
            for ligne, d in devises[r["id"]].items():
                if d == devise:
                    deplacees[ligne] = prochain
            _signaler(ctx, r, n)
            prochain += 1
    if not nouvelles:
        return
    sortie["reception"] += nouvelles
    _suivre(sortie, deplacees)


def _nouvelle(
    ctx: Contexte, r: dict[str, Any], devise: str, rang: int, ident: int
) -> dict[str, Any]:
    """La réception d'une autre devise : l'en-tête d'origine, sans facture."""
    v = dict(r) | {
        "id": ident,
        "numero": numero_scinde(r["numero"], rang),
        "devise": devise,
        "facture_id": None,
    }
    ctx.scindees[ident] = r["id"]
    ctx.compter("reception", "scindees")
    if v["numero"]:
        ctx.numeros_ajoutes["reception"].append(v["numero"])
    return v


def _signaler(ctx: Contexte, r: dict[str, Any], n: dict[str, Any]) -> None:
    """Le rapport dit la correspondance des deux réceptions et la facture manquante."""
    origine = r["numero"] or f"brouillon n° {r['id']}"
    nouvelle = n["numero"] or f"brouillon n° {n['id']}"
    facture = "sa facture" if r["facture_id"] else "sans facture"
    ctx.signaler(
        "reception",
        origine,
        f"payée en deux devises : scindée — {origine} ({r['devise']}, {facture}) et "
        f"{nouvelle} (id {n['id']}, {n['devise']}, sans facture : Gestion MP n'en avait "
        "qu'une)",
    )


def _suivre(sortie: Lignes, deplacees: dict[int, int]) -> None:
    """Les lignes déplacées, puis ce qui les désigne : mouvements d'entrée, réclamations."""
    lots: dict[tuple[int, int], int] = {}
    restent: set[tuple[int, int]] = set()
    for x in sortie["reception_ligne"]:
        nouvelle = deplacees.get(x["id"])
        if nouvelle is None:
            restent.add((x["reception_id"], x["lot_id"]))
            continue
        if x["lot_id"] is not None:
            lots[(x["reception_id"], x["lot_id"])] = nouvelle
        x["reception_id"] = nouvelle
    for cle in restent & set(lots):
        del lots[cle]  # un lot reçu dans les deux devises : ses entrées restent à l'origine
    for m in sortie["mouvement"]:
        cle = (m["reception_id"], m["lot_id"])
        if m["reception_id"] is not None and cle in lots:
            m["reception_id"] = lots[cle]
    for c in sortie["reclamation"]:
        nouvelle = deplacees.get(c["reception_ligne_id"] or 0)
        if nouvelle is not None:
            c["reception_id"] = nouvelle
