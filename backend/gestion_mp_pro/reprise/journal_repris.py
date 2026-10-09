"""Le journal de Gestion MP repris tel quel, et les événements de montage des métiers.

- Chaque ligne du journal source est ajoutée **une fois** (correspondance) avec un identifiant
  pris dans la séquence de PRO (le journal de PRO a ses propres lignes : installation,
  connexions) ; l'ordre des identifiants sources est gardé. `utilisateur` → `utilisateur_id`
  (nom gardé dans `utilisateur_nom`), `avant`/`apres` vides.
- L'objet : les noms de Gestion MP sont traduits (`article` → `matiere`, `bon` → `ordre`,
  `role` → `role_nomenclature`…). Les lignes reprises de l'ERP Fil nomment le document en
  texte (« BC-2025-0001 », une référence) : ce texte va dans `numero`, l'objet est déduit de
  l'action, et l'identifiant est retrouvé par le numéro quand il existe.
- « montage » → `montage_evenement` (le texte n'est pas interprété : il va en `alerte`) ; le
  dernier montage d'un métier date ses étages (`metier_etage.monte_le`, `monte_par_id`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import update

from gestion_mp_pro.modeles import metadata
from gestion_mp_pro.modeles.enums import ObjetJournal
from gestion_mp_pro.reprise import ecriture
from gestion_mp_pro.reprise.contexte import Contexte, Ligne

OBJETS = {
    "article": "matiere",
    "bon": "ordre",
    "role": "role_nomenclature",
    "indicateurs": "systeme",
    "types-fil": "type_fil",
    "titrages": "titrage",
}
OBJET_PAR_ACTION = {
    "statut BC": "commande",
    "prix confirmés": "commande",
    "création BC": "commande",
    "préparation commande": "fournisseur",
    "charge dossier import": "dossier",
    "marchandises dossier import": "dossier",
    "ouverture dossier import": "dossier",
    "clôture dossier import": "dossier",
    "ordre de fabrication": "ordre",
    "création réception": "reception",
    "validation réception": "reception",
    "mouvement": "matiere",
    "contre-passation": "matiere",
    "modification référence": "matiere",
    "classification du catalogue": "matiere",
    "création inventaire": "inventaire",
    "validation inventaire": "inventaire",
    "modification titrages": "titrage",
    "modification types-fil": "type_fil",
    "création types-fil": "type_fil",
    "modification fournisseur": "fournisseur",
    "reprise classeur": "reprise",
}
"""Actions de la reprise de l'ERP Fil : l'objet qu'elles visent (leur `objet` est un texte)."""

VALEURS_OBJET = frozenset(o.value for o in ObjetJournal)


def _index_des_numeros(ctx: Contexte) -> dict[str, dict[str, int]]:
    """Objet → (numéro, référence ou libellé → identifiant), pour les lignes de l'ERP Fil."""
    p = ctx.photo

    def par(table: str, *colonnes: str) -> dict[str, int]:
        """Valeur de ces colonnes → identifiant, pour une table source."""
        return {x[c]: x["id"] for x in p.lignes(table) for c in colonnes if x.get(c)}

    return {
        "commande": par("commande", "numero"),
        "reception": par("reception", "numero"),
        "ordre": par("bon_sortie", "numero"),
        "dossier": par("dossier", "numero"),
        "inventaire": par("inventaire", "numero", "libelle"),
        "matiere": par("article", "reference"),
        "fournisseur": par("fournisseur", "nom"),
        "titrage": dict(ctx.ids.get("titrage", {})),
        "type_fil": dict(ctx.ids.get("type_fil", {})),
    }


def _objet(x: dict[str, Any], index: dict[str, dict[str, int]]) -> tuple[str, int | None, str]:
    """(objet PRO, identifiant, numéro) d'une ligne du journal source."""
    objet = OBJETS.get(x["objet"], x["objet"] or "systeme")
    if objet in VALEURS_OBJET:
        return objet, x["objet_id"], ""
    deduit = OBJET_PAR_ACTION.get(x["action"], "systeme")
    texte = x["objet"] or ""
    return deduit, index.get(deduit, {}).get(texte), texte


def journal_repris(ctx: Contexte) -> dict[int, int]:
    """Ajoute les lignes du journal source pas encore reprises ; rend id source → id PRO."""
    index = _index_des_numeros(ctx)
    deja = ecriture.correspondances(ctx, "journal")
    lignes: list[Ligne] = []
    for x in ctx.photo.lignes("journal"):
        if x["id"] in deja:
            continue
        objet, objet_id, numero = _objet(x, index)
        v = {
            "quand": x["quand"],
            "utilisateur_id": ctx.personne(x["utilisateur"]),
            "utilisateur_nom": x["utilisateur"] or "",
            "role": x["role"] or "",
            "action": x["action"],
            "objet": objet,
            "objet_id": objet_id,
            "numero": numero,
            "detail": x["detail"] or "",
        }
        lignes.append(Ligne((0,), ctx.ligne("journal", v, x["id"]), "journal", x["id"]))
    ctx.compter("journal", "sautees", len(ctx.photo.lignes("journal")) - len(lignes))
    for ligne, i in zip(lignes, ecriture.prochains_ids(ctx, "journal", len(lignes)), strict=True):
        ligne.valeurs["id"], ligne.cle = i, (i,)
    ecriture.ajouter(ctx, "journal", lignes)
    return {k: v[0] for k, v in ecriture.correspondances(ctx, "journal").items()}


def montages(ctx: Contexte) -> None:
    """Événements de montage (journal « montage ») ; étages datés du dernier montage."""
    metiers = {m["id"] for m in ctx.photo.lignes("metier")}
    deja = ecriture.correspondances(ctx, "journal:montage")
    lignes: list[Ligne] = []
    for x in ctx.photo.lignes("journal"):
        if x["action"] != "montage" or x["objet_id"] not in metiers or x["id"] in deja:
            continue
        v = {
            "metier_id": x["objet_id"],
            "etage": None,
            "quand": x["quand"],
            "par_id": ctx.personne(x["utilisateur"]),
            "alerte": x["detail"] or "",
        }
        lignes.append(
            Ligne((0,), ctx.ligne("montage_evenement", v, x["id"]), "journal:montage", x["id"])
        )
    ids = ecriture.prochains_ids(ctx, "montage_evenement", len(lignes))
    for ligne, i in zip(lignes, ids, strict=True):
        ligne.valeurs["id"], ligne.cle = i, (i,)
    ecriture.ajouter(ctx, "montage_evenement", lignes)
    t = metadata.tables["metier_etage"]
    for ligne in lignes:
        v = ligne.valeurs
        ctx.c.execute(
            update(t)
            .where(t.c.metier_id == v["metier_id"])
            .values(monte_le=v["quand"], monte_par_id=v["par_id"])
        )


def fils_montes(ctx: Contexte) -> None:
    """Fils montés (← `fil_monte`), métier par métier ; un étage absent est signalé."""
    etages = {m["id"]: int(m["etages"]) for m in ctx.photo.lignes("metier")}
    groupes: dict[int, list[dict[str, Any]]] = {mid: [] for mid in etages}
    for f in ctx.photo.lignes("fil_monte"):
        if not 1 <= f["etage"] <= etages.get(f["metier_id"], 0):
            ctx.signaler("montage", f["id"], f"étage {f['etage']} absent du métier : non repris")
            ctx.compter("montage", "ecartees")
            continue
        v = {k: f[k] for k in ("id", "metier_id", "etage", "metres", "pourcentage")}
        v["matiere_id"] = f["article_id"]
        v["commentaire"] = f["commentaire"] or ""
        groupes[f["metier_id"]].append(ctx.ligne("montage", v, f["id"]))
    ecriture.appliquer_groupes(ctx, "montage", "metier_id", groupes)
