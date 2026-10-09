"""Activité des achats : factures, bons de commande (lignes, version partie, décisions),
réceptions et leurs lignes, réclamations. Identifiants et numéros gardés.

Traductions (MODELE-DONNEES § 10.3) : cours, montant approuvé, montant de facture à 0 → NULL ;
`version_approuvee` (JSON) → une `commande_version` (motif `reprise`) ; une réception porte
**une** devise (celle de sa facture, sinon celle de la plupart de ses lignes : deux devises sur
une réception : scindée ensuite par `scission`) ; `LOT INTERNE` → `lot_interne` ; prix
confirmé sans date → date de création du bon (signalé).
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from gestion_mp_pro.modeles.enums import IssueReclamation, MotifReclamation, MotifVersionCommande
from gestion_mp_pro.reprise import journal_en_tables as jt
from gestion_mp_pro.reprise.contexte import Contexte
from gestion_mp_pro.reprise.outils import (
    Lignes,
    date_apres,
    numero_de_document,
    plus_frequent,
    zero_en_nul,
)

LOT_INTERNE = "LOT INTERNE"
JALONS = (
    "proforma_le",
    "acompte_le",
    "embarquee_le",
    "au_port_le",
    "dedouanee_le",
    "arrivee_usine_le",
)
MOTIFS = {
    "Qualité (défaut du fil)": MotifReclamation.qualite,
    "Quantité manquante": MotifReclamation.quantite_manquante,
    "Poids des bobines": MotifReclamation.poids_bobines,
    "Bobines endommagées": MotifReclamation.bobines_endommagees,
    "Retard": MotifReclamation.retard,
    "Documents": MotifReclamation.documents,
    "Autre": MotifReclamation.autre,
}
ISSUES = {
    "Avoir": IssueReclamation.avoir,
    "Remplacement": IssueReclamation.remplacement,
    "Remise sur la prochaine commande": IssueReclamation.remise,
    "Refusée": IssueReclamation.refusee,
    "Abandonnée": IssueReclamation.abandonnee,
}


def factures(ctx: Contexte, sortie: Lignes) -> None:
    """Factures (montant 0 → inconnu ; échéance avant la date → vidée, signalée)."""
    for f in ctx.photo.lignes("facture"):
        v = {k: f[k] for k in ("id", "fournisseur_id", "numero", "date", "devise", "payee_le")}
        v["montant"] = zero_en_nul(f["montant"])
        v["echeance"] = (
            date_apres(ctx, "facture", f["id"], "échéance", f["echeance"], debut=f["date"])
            if f["date"]
            else f["echeance"]
        )
        sortie["facture"].append(ctx.ligne("facture", v, f["id"]))


def commandes(ctx: Contexte, j: jt.Journal, sortie: Lignes) -> None:
    """Bons de commande et leurs lignes, versions parties et décisions."""
    for c in ctx.photo.lignes("commande"):
        v = {
            k: c[k]
            for k in (
                "id",
                "fournisseur_id",
                "statut",
                "date_commande",
                "devise",
                "observations",
                "eta",
                "conteneur",
                "navire",
                "approuvee_le",
                "cree_le",
            )
        }
        v["numero"] = numero_de_document(ctx, "commande", c, c["statut"] == "brouillon")
        v["date_livraison_prevue"] = date_apres(
            ctx,
            "commande",
            c["id"],
            "date promise",
            c["date_livraison_prevue"],
            debut=c["date_commande"],
        )
        for jalon in JALONS:
            v[jalon] = date_apres(
                ctx, "commande", c["id"], jalon, c[jalon], debut=c["date_commande"]
            )
        cours = None if c["devise"] == "MAD" else zero_en_nul(c["cours"])
        v["cours"] = cours
        v["cours_fige_le"] = (c["approuvee_le"] or c["cree_le"]) if cours else None
        v["montant_approuve"] = zero_en_nul(c["montant_approuve"])
        v["approuvee_par_id"] = ctx.personne(c["approuvee_par"])
        v["cree_par_id"] = ctx.personne(c["cree_par"])
        v.update(jt.solde_de_commande(j, c["id"], c["statut"]))
        sortie["commande"].append(ctx.ligne("commande", v, c["id"]))
        if c["version_approuvee"]:
            _version_partie(ctx, c, sortie)
    _lignes_de_commande(ctx, sortie)
    ids = {c["id"] for c in ctx.photo.lignes("commande")}
    sortie["commande_decision"] += jt.decisions(ctx, j, ids)


def _lignes_de_commande(ctx: Contexte, sortie: Lignes) -> None:
    """Lignes des bons (prix confirmé sans date : date de création du bon)."""
    crees = {c["id"]: c["cree_le"] for c in ctx.photo.lignes("commande")}
    sans_date = 0
    for x in ctx.photo.lignes("commande_ligne"):
        v = {
            k: x[k]
            for k in ("id", "commande_id", "quantite", "contenance", "prix", "prix_confirme")
        }
        v["matiere_id"] = x["article_id"]
        v["unite_achat"] = "kg" if (x["unite_achat"] or "").lower() == "ml" else x["unite_achat"]
        v["confirme_par_id"] = ctx.personne(x["confirme_par"])
        v["confirme_le"] = x["confirme_le"]
        if x["prix_confirme"] and x["confirme_le"] is None:
            v["confirme_le"] = crees.get(x["commande_id"])
            sans_date += 1
        elif not x["prix_confirme"]:
            v["confirme_le"] = None
        sortie["commande_ligne"].append(ctx.ligne("commande_ligne", v, x["id"]))
    if sans_date:
        ctx.signaler("commande_ligne", "*", f"{sans_date} prix confirmés sans date : date du bon")


def _version_partie(ctx: Contexte, c: dict[str, Any], sortie: Lignes) -> None:
    """`version_approuvee` (JSON) → une version figée (motif `reprise`) et ses lignes."""
    try:
        version = json.loads(c["version_approuvee"])
    except ValueError:
        ctx.signaler("commande", c["id"], "version partie illisible : non reprise")
        return
    lignes = []
    for x in version.get("lignes", []):
        if not x.get("quantite") or x["quantite"] <= 0:
            ctx.signaler("commande_version", c["id"], "ligne sans quantité : non reprise")
            continue
        v = {
            "matiere_id": x["article_id"],
            "quantite": x["quantite"],
            "unite_achat": x.get("unite_achat") or "kg",
            "contenance": x.get("contenance") or 1,
            "prix": x.get("prix", 0.0),
            "prix_confirme": bool(x.get("prix_confirme")),
            "confirme_par_id": ctx.personne(x.get("confirme_par")),
            "confirme_le": x.get("confirme_le"),
        }
        lignes.append(ctx.ligne("commande_version_ligne", v, c["id"]))
    v = {
        "commande_id": c["id"],
        "figee_le": c["approuvee_le"] or c["cree_le"],
        "montant_reference": max(version.get("montant", 0.0), 0.0),
        "motif": MotifVersionCommande.reprise.value,
        "par_id": ctx.personne(c["approuvee_par"]),
    }
    sortie["commande_version"].append(
        {**ctx.ligne("commande_version", v, c["id"]), "_lignes": lignes}
    )


def receptions(ctx: Contexte, j: jt.Journal, sortie: Lignes) -> None:
    """Réceptions (une devise par en-tête, annulation lue au journal) et leurs lignes."""
    devises: dict[int, list[str]] = defaultdict(list)
    for x in ctx.photo.lignes("reception_ligne"):
        devises[x["reception_id"]].append(x["devise"])
    factures_ = {f["id"]: f["devise"] for f in ctx.photo.lignes("facture")}
    fournisseurs = {f["id"]: f["devise"] for f in ctx.photo.lignes("fournisseur")}
    for r in ctx.photo.lignes("reception"):
        v = {
            k: r[k]
            for k in (
                "id",
                "statut",
                "date",
                "fournisseur_id",
                "numero_bl",
                "facture_id",
                "observations",
                "controle_par",
                "cree_le",
                "validee_le",
            )
        }
        v["numero"] = numero_de_document(ctx, "reception", r, r["statut"] == "brouillon")
        defaut = factures_.get(r["facture_id"]) or fournisseurs.get(r["fournisseur_id"]) or "MAD"
        v["devise"] = factures_.get(r["facture_id"]) or plus_frequent(devises[r["id"]], defaut)
        v["cree_par_id"] = ctx.personne(r["cree_par"])
        v["validee_par_id"] = ctx.personne(r["validee_par"])
        if r["statut"] != "brouillon" and r["validee_le"] is None:
            ctx.signaler("reception", r["id"], "validée sans date : date de création")
            v["validee_le"] = r["cree_le"]
        if r["statut"] == "annulee":
            fait = j.dernier("reception", "annulation réception", r["id"])
            v["annulee_le"] = fait.quand if fait else v["validee_le"]
            v["annulee_par_id"] = fait.par_id if fait else None
            v["annulation_motif"] = fait.motif if fait else ""
        sortie["reception"].append(ctx.ligne("reception", v, r["id"]))
    _lignes_de_reception(ctx, sortie)


def _lignes_de_reception(ctx: Contexte, sortie: Lignes) -> None:
    """Lignes reçues : « LOT INTERNE » devient la case `lot_interne`."""
    colonnes = (
        "id",
        "reception_id",
        "commande_ligne_id",
        "quantite_attendue",
        "quantite_bl",
        "quantite_pesee",
        "nb_palettes",
        "bobines_en_plus",
        "nb_bobines",
        "magasin_id",
        "qualite",
        "observations",
        "prix",
        "lot_id",
    )
    for x in ctx.photo.lignes("reception_ligne"):
        v = {k: x[k] for k in colonnes}
        v["matiere_id"] = x["article_id"]
        interne = (x["lot_numero"] or "").strip().upper() == LOT_INTERNE
        v["lot_interne"] = interne and x["qualite"] != "refuse"
        v["lot_numero"] = "" if interne else (x["lot_numero"] or "")
        if x["qualite"] == "refuse" and x["lot_id"] is not None:
            ctx.signaler("reception_ligne", x["id"], "ligne refusée avec un lot : lot retiré")
            v["lot_id"] = None
        sortie["reception_ligne"].append(ctx.ligne("reception_ligne", v, x["id"]))


def reclamations(ctx: Contexte, sortie: Lignes) -> None:
    """Réclamations (motif et issue en énumérations ; ligne de réception de sa réception)."""
    lignes_de = {x["id"]: x["reception_id"] for x in ctx.photo.lignes("reception_ligne")}
    for r in ctx.photo.lignes("reclamation"):
        v = {
            k: r[k]
            for k in (
                "id",
                "numero",
                "fournisseur_id",
                "reception_id",
                "lot_id",
                "description",
                "quantite",
                "montant_demande",
                "devise",
                "reponse",
                "montant_obtenu",
                "statut",
                "ouverte_le",
                "close_le",
            )
        }
        v["motif"] = _enum(ctx, r, "motif", MOTIFS, MotifReclamation.autre.value)
        v["issue"] = _enum(ctx, r, "issue", ISSUES, None) if r["issue"] else None
        v["reception_ligne_id"] = r["reception_ligne_id"]
        if r["reception_ligne_id"] and lignes_de.get(r["reception_ligne_id"]) != r["reception_id"]:
            ctx.signaler("reclamation", r["id"], "ligne d'une autre réception : retirée")
            v["reception_ligne_id"] = None
        if r["statut"] == "close" and v["issue"] is None:
            ctx.signaler("reclamation", r["id"], "close sans issue : « abandonnée »")
            v["issue"] = IssueReclamation.abandonnee.value
        v["cree_par_id"] = ctx.personne(r["cree_par"])
        sortie["reclamation"].append(ctx.ligne("reclamation", v, r["id"]))


def _enum(
    ctx: Contexte, r: dict[str, Any], champ: str, table: dict[str, Any], defaut: str | None
) -> str | None:
    """Un libellé de Gestion MP traduit en valeur d'énumération (inconnu : signalé)."""
    texte = r[champ] or ""
    valeurs = {e.value for e in table.values()}
    if texte in valeurs:
        return texte
    if texte in table:
        return str(table[texte].value)
    ctx.signaler("reclamation", r["id"], f"{champ} « {texte} » inconnu : {defaut}")
    return defaut
