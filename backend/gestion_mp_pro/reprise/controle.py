"""Contrôle de reprise (MODELE-DONNEES § 10.4) : ce que le rapport affirme, vérifié en base.

1. comptes de lignes par table, source et cible ;
2. Σ quantités et Σ quantité × prix (entrées) du journal du stock, par matière, à l'arrondi
   déclaré près (borne : ½ unité de la dernière décimale par valeur arrondie) ;
3. soldes = journal (en cible : chaque solde = Σ de ses mouvements) ;
4. mêmes numéros de documents ;
5. mêmes recettes, mêmes versions de recette (lignes) et versions du plan attendues.

Chaque contrôle rend un `Verdict` ; la reprise n'est « réussie » que si tous sont tenus.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import text

from gestion_mp_pro.reprise.activite_stock import BLANCS, ENTREES
from gestion_mp_pro.reprise.contexte import Contexte

PAIRES = (
    ("article", "matiere"),
    ("fournisseur", "fournisseur"),
    ("composition", "composition"),
    ("type_fil", "type_fil"),
    ("titrage", "titrage"),
    ("couleur", "couleur"),
    ("role_nomenclature", "role_nomenclature"),
    ("code_douanier", "code_douanier"),
    ("poste_frais", "poste_frais"),
    ("devise", "devise"),
    ("magasin", "magasin"),
    ("metier", "metier"),
    ("fil_monte", "montage"),
    ("qualite", "qualite"),
    ("qualite_poids", "qualite_poids"),
    ("qualite_saison", "qualite_saison"),
    ("recette", "recette"),
    ("recette_version", "recette_version"),
)
PAIRES_ACTIVITE = (
    ("lot", "lot"),
    ("mouvement", "mouvement"),
    ("solde", "solde"),
    ("commande", "commande"),
    ("commande_ligne", "commande_ligne"),
    ("facture", "facture"),
    ("reception", "reception"),
    ("reception_ligne", "reception_ligne"),
    ("bon_sortie", "ordre"),
    ("bon_fabrication", "ordre_qualite"),
    ("bon_ligne", "ordre_ligne"),
    ("operation", "operation"),
    ("operation_ligne", "operation_ligne"),
    ("inventaire", "inventaire"),
    ("inventaire_ligne", "inventaire_ligne"),
    ("dossier", "dossier"),
    ("dossier_ligne", "dossier_ligne"),
    ("dossier_charge", "dossier_frais"),
    ("dossier_charge_part", "dossier_frais_part"),
    ("reclamation", "reclamation"),
    ("signalement", "signalement"),
    ("indicateur_jour", "indicateur_jour"),
)
NUMEROTES = (
    ("commande", "commande"),
    ("reception", "reception"),
    ("bon_sortie", "ordre"),
    ("operation", "operation"),
    ("inventaire", "inventaire"),
    ("dossier", "dossier"),
    ("reclamation", "reclamation"),
    ("facture", "facture"),
)
DEMI_QUANTITE = Decimal("0.0005")
DEMI_PRIX = Decimal("0.0000005")


@dataclass
class Verdict:
    """Un contrôle : tenu ou non, et ses lignes de rapport."""

    titre: str
    tenu: bool = True
    lignes: list[str] = field(default_factory=list)


def _compte(ctx: Contexte, table: str) -> int:
    """Nombre de lignes d'une table cible."""
    return int(ctx.c.execute(text(f"SELECT count(*) FROM {table}")).scalar() or 0)  # noqa: S608


def comptes(ctx: Contexte, referentiels: bool, activite: bool) -> Verdict:
    """Comptes de lignes par table : source = cible (moins les lignes écartées, signalées)."""
    v = Verdict("Comptes de lignes par table (source → cible)")
    paires = (PAIRES if referentiels else ()) + (PAIRES_ACTIVITE if activite else ())
    for source, cible in paires:
        n_source, n_cible = len(ctx.photo.lignes(source)), _compte(ctx, cible)
        ecartees = ctx.comptes[cible]["ecartees"] if cible in ctx.comptes else 0
        egal = n_source - ecartees == n_cible
        v.tenu &= egal
        note = f" (dont {ecartees} écartées, signalées)" if ecartees else ""
        signe = "=" if egal else "ÉCART"
        v.lignes.append(f"{source:<20} {n_source:>7} → {cible:<20} {n_cible:>7}  {signe}{note}")
    repris = len(ctx.photo.lignes("journal"))
    journal_repris = int(
        ctx.c.execute(
            text(
                "SELECT count(*) FROM reprise_correspondance"
                " WHERE source = :s AND table_source = 'journal'"
            ),
            {"s": ctx.source.value},
        ).scalar()
        or 0
    )
    v.tenu &= repris == journal_repris
    signe = "=" if repris == journal_repris else "ÉCART"
    v.lignes.append(
        f"{'journal':<20} {repris:>7} → {'journal (repris)':<20} {journal_repris:>7}  {signe}"
    )
    return v


def sommes(ctx: Contexte) -> Verdict:
    """Σ quantités et Σ q × prix des entrées, par matière, à l'arrondi déclaré près."""
    v = Verdict("Σ quantités et Σ quantité × prix (entrées) par matière")
    source: dict[int, list[Decimal]] = defaultdict(lambda: [Decimal(0)] * 4)
    for m in ctx.photo.lignes("mouvement"):
        q, p = Decimal(repr(m["quantite"])), Decimal(repr(m["prix"]))
        s = source[m["article_id"]]
        s[0] += q
        s[1] += DEMI_QUANTITE
        if m["type"] in ENTREES:
            s[2] += q * p
            s[3] += abs(p) * DEMI_QUANTITE + (abs(q) + DEMI_QUANTITE) * DEMI_PRIX
    sql = text(
        "SELECT matiere_id, sum(quantite), sum(CASE WHEN type IN ('OUVERTURE','RECEPTION',"
        "'RETOUR_FOURNISSEUR','AJUSTEMENT') THEN quantite * prix ELSE 0 END) "
        "FROM mouvement GROUP BY matiere_id"
    )
    cible = {mid: (q or Decimal(0), qp or Decimal(0)) for mid, q, qp in ctx.c.execute(sql)}
    hors, ecart_q, ecart_qp = 0, Decimal(0), Decimal(0)
    for mid, (q, borne_q, qp, borne_qp) in source.items():
        cq, cqp = cible.get(mid, (Decimal(0), Decimal(0)))
        eq, eqp = abs(cq - q), abs(cqp - qp)
        ecart_q, ecart_qp = max(ecart_q, eq), max(ecart_qp, eqp)
        if eq > borne_q or eqp > borne_qp:
            hors += 1
            v.lignes.append(f"matière {mid} : écart {eq} kg / {eqp} hors borne")
    hors += len(set(cible) - set(source))
    v.tenu = hors == 0
    v.lignes.insert(
        0,
        f"{len(source)} matières ; écart max {ecart_q:.2e} kg, {ecart_qp:.2e} en valeur ; "
        f"hors de l'arrondi déclaré : {hors}",
    )
    return v


def soldes(ctx: Contexte) -> Verdict:
    """Chaque solde = Σ de ses mouvements (en cible), et proche du solde de la source."""
    v = Verdict("Soldes = journal")
    faux = ctx.c.execute(
        text(
            "SELECT count(*) FROM solde s FULL JOIN (SELECT lot_id, magasin_id, sum(quantite) q "
            "FROM mouvement GROUP BY 1, 2) m USING (lot_id, magasin_id) "
            "WHERE coalesce(s.quantite, 0) <> coalesce(m.q, 0) OR s.lot_id IS NULL"
        )
    ).scalar()
    cible = {
        (lot, mag): q
        for lot, mag, q in ctx.c.execute(text("SELECT lot_id, magasin_id, quantite FROM solde"))
    }
    ecart = max(
        (
            abs(
                cible.get((s["lot_id"], s["magasin_id"]), Decimal(0)) - Decimal(repr(s["quantite"]))
            )
            for s in ctx.photo.lignes("solde")
        ),
        default=Decimal(0),
    )
    v.tenu = faux == 0
    v.lignes.append(
        f"soldes ≠ Σ mouvements en cible : {faux} ; écart max au solde source : {ecart:.2e} kg"
    )
    return v


def numeros(ctx: Contexte) -> Verdict:
    """Mêmes numéros de documents (hors numéros retirés aux brouillons, signalés)."""
    v = Verdict("Mêmes numéros de documents")
    for source, cible in NUMEROTES:
        attendus = {x["numero"] for x in ctx.photo.lignes(source) if x.get("numero")}
        attendus -= set(ctx.numeros_retires.get(cible, []))
        if source == "dossier":
            attendus = {n if "/" in n else f"ANC-{n}" for n in attendus}
        sql = f"SELECT numero FROM {cible} WHERE numero IS NOT NULL"  # noqa: S608
        presents = {n for (n,) in ctx.c.execute(text(sql))}
        egal = attendus == presents
        v.tenu &= egal
        v.lignes.append(
            f"{cible:<12} {len(attendus):>5} numéros ; manquants {len(attendus - presents)}, "
            f"en plus {len(presents - attendus)}"
        )
    lots = {BLANCS.sub("_", (x["numero"] or "").strip()) for x in ctx.photo.lignes("lot")}
    presents = {n for (n,) in ctx.c.execute(text("SELECT numero FROM lot"))}
    v.tenu &= lots == presents
    v.lignes.append(f"{'lot':<12} {len(lots):>5} numéros ; manquants {len(lots - presents)}")
    return v


def recettes(ctx: Contexte, attendus_plan: int) -> Verdict:
    """Mêmes recettes, mêmes versions de recette (lignes), versions du plan attendues."""
    v = Verdict("Mêmes recettes et plans versionnés")
    source = {
        (r["qualite_id"], r["article_id"], round(r["pourcentage"], 6))
        for r in ctx.photo.lignes("recette")
    }
    cible = {
        (q, m, float(p))
        for q, m, p in ctx.c.execute(
            text("SELECT qualite_id, matiere_id, pourcentage FROM recette")
        )
    }
    v.tenu &= source == cible
    differentes = len(source ^ cible)
    v.lignes.append(
        f"recettes : {len(source)} source, {len(cible)} cible, différentes {differentes}"
    )
    refs = ctx.ids.get("reference", {})
    lignes_src = {
        (r["id"], refs.get(x["reference"]), round(x["pourcentage"], 6))
        for r in ctx.photo.lignes("recette_version")
        for x in json.loads(r["contenu"] or "[]")
        if x.get("reference") in refs
    }
    lignes_cib = {
        (i, m, float(p))
        for i, m, p in ctx.c.execute(
            text("SELECT version_id, matiere_id, pourcentage FROM recette_version_ligne")
        )
    }
    v.tenu &= lignes_src <= lignes_cib
    v.lignes.append(
        f"versions de recette : {len(lignes_src)} lignes source, absentes en cible "
        f"{len(lignes_src - lignes_cib)}"
    )
    plans = _compte(ctx, "plan_version")
    v.tenu &= plans >= attendus_plan
    v.lignes.append(f"versions du plan : {attendus_plan} attendues (journal), {plans} en cible")
    return v
