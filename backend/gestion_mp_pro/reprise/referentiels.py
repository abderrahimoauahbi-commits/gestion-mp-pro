"""Référentiels simples : classification, rôles, devises et cours, codes douaniers, postes de
frais, fournisseurs, magasins, métiers et leurs étages, réglages et leur historique.

Les tables à clé texte dans Gestion MP (classification, rôles, devises, postes, codes
douaniers) sont rapprochées par leur **code** et reçoivent une clé technique `id` ; les autres
gardent leur identifiant. Les semences de PRO (8 rôles, 11 postes, 3 devises, 2 magasins)
prennent les valeurs de la source (rôles et postes : la nature, `de_base` et `systeme` de PRO
restent).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy import delete, select

from gestion_mp_pro.modeles import CLES_REGLAGES, metadata
from gestion_mp_pro.modeles.enums import TypeMagasin
from gestion_mp_pro.reprise import ecriture
from gestion_mp_pro.reprise.contexte import Contexte, Ligne, ident_de_code

TYPES_MAGASIN = {"Stock courant": TypeMagasin.stock_courant, "Quarantaine": TypeMagasin.quarantaine}
CLASSIFICATION: dict[str, tuple[str, ...]] = {
    "composition": ("libelle", "famille", "composition_detaillee", "commentaire", "actif"),
    "type_fil": ("libelle", "commentaire", "actif"),
    "titrage": ("valeur", "unite", "commentaire", "actif"),
    "couleur": ("libelle", "famille", "commentaire", "actif"),
}
ENTIER_DECIMAL = re.compile(r"-?[0-9]+\.0")
PREFIXE_COURS = "cours_"


def _par_code(ctx: Contexte, table: str, source: str, valeurs: list[dict[str, Any]]) -> None:
    """Applique des fiches rapprochées par code, puis note « code → id » dans le contexte."""
    lignes = [
        Ligne((v["code"],), ctx.ligne(table, v, v["code"]), source, ident_de_code(v["code"]))
        for v in valeurs
    ]
    ecriture.appliquer(ctx, table, lignes, ("code",))
    t = metadata.tables[table]
    ident = t.c.id if "id" in t.c else t.c.code
    ctx.ids[table] = {code: i for code, i in ctx.c.execute(select(t.c.code, ident))}


def classification(ctx: Contexte) -> None:
    """Compositions, types de fil, titrages, couleurs ; rôles de nomenclature."""
    for table, colonnes in CLASSIFICATION.items():
        valeurs = [
            {"code": x["code"], **{c: x[c] for c in colonnes}} for x in ctx.photo.lignes(table)
        ]
        _par_code(ctx, table, table, valeurs)
    roles = [
        {"code": x["code"], "lineaire": x["lineaire"], "ordre": x["ordre"]}
        for x in ctx.photo.lignes("role_nomenclature")
    ]
    _par_code(ctx, "role_nomenclature", "role_nomenclature", roles)
    ctx.ids["role"] = ctx.ids["role_nomenclature"]


def devises(ctx: Contexte) -> None:
    """Devises (le taux devient le cours ; date du dernier cours) et historique des cours."""
    historique = [
        h for h in ctx.photo.lignes("parametre_historique") if h["cle"].startswith(PREFIXE_COURS)
    ]
    dernier = {h["cle"][len(PREFIXE_COURS) :]: h["quand"] for h in historique}
    valeurs = []
    for d in ctx.photo.lignes("devise"):
        v: dict[str, Any] = {
            "code": d["code"],
            "nom": d["nom"],
            "cours": d["taux"],
            "actif": d["actif"],
        }
        if d["code"] == "MAD" and d["taux"] != 1:
            ctx.signaler("devise", "MAD", f"cours {d['taux']} : le dirham vaut 1")
            v["cours"] = 1
        if d["code"] in dernier:
            v["cours_le"] = dernier[d["code"]]
        valeurs.append(v)
    _par_code(ctx, "devise", "devise", valeurs)
    connues = {d["code"] for d in ctx.photo.lignes("devise")}
    lignes = []
    for h in historique:
        code = h["cle"][len(PREFIXE_COURS) :]
        if code not in connues:
            ctx.signaler("devise_cours", h["id"], f"devise {code} inconnue : cours non repris")
            continue
        v = {"devise": code, "cours": float(h["valeur"]), "saisi_le": h["quand"]}
        v["par_id"] = ctx.personne(h["par"])
        lignes.append(
            Ligne((0,), ctx.ligne("devise_cours", v, h["id"]), "parametre_historique", h["id"])
        )
    _ajouter_avec_ids(ctx, "devise_cours", lignes)


def _ajouter_avec_ids(ctx: Contexte, table: str, lignes: list[Ligne]) -> list[Ligne]:
    """Ajoute des lignes d'historique pas encore reprises, avec un identifiant de la séquence."""
    deja = ecriture.correspondances(ctx, lignes[0].table_source) if lignes else {}
    nouvelles = [x for x in lignes if x.id_source not in deja]
    ids = ecriture.prochains_ids(ctx, table, len(nouvelles))
    for x, i in zip(nouvelles, ids, strict=True):
        x.valeurs["id"] = i
        x.cle = (i,)
    ctx.compter(table, "sautees", len(lignes) - len(nouvelles))
    return ecriture.ajouter(ctx, table, nouvelles)


def codes_et_postes(ctx: Contexte) -> None:
    """Codes douaniers ; postes de frais (nature et caractère « système » de PRO gardés)."""
    codes = [
        {k: x[k] for k in ("code", "libelle", "taux_droits", "actif")}
        for x in ctx.photo.lignes("code_douanier")
    ]
    _par_code(ctx, "code_douanier", "code_douanier", codes)
    postes = [
        {k: x[k] for k in ("code", "libelle", "recuperable", "ordre", "cle")}
        for x in ctx.photo.lignes("poste_frais")
    ]
    _par_code(ctx, "poste_frais", "poste_frais", postes)
    ctx.ids["poste"] = ctx.ids["poste_frais"]


def fournisseurs(ctx: Contexte) -> None:
    """Fournisseurs (identifiants gardés ; jours en entiers ; pays en majuscules)."""
    colonnes = (
        "id",
        "nom",
        "code",
        "contact",
        "telephone",
        "email",
        "devise",
        "delai_jours",
        "couverture_commande_jours",
        "mode_paiement",
        "delai_paiement_jours",
        "conditions_paiement",
        "incoterm",
        "notes",
        "port_chargement",
        "banque",
        "actif",
    )
    lignes = []
    for f in ctx.photo.lignes("fournisseur"):
        v = {k: f[k] for k in colonnes}
        v["pays"] = (f["pays"] or "").upper()
        if not v["delai_jours"] or v["delai_jours"] <= 0:
            ctx.signaler("fournisseur", f["id"], f"délai {f['delai_jours']} j : 60 j (défaut)")
            v["delai_jours"] = 60
        lignes.append(
            Ligne((f["id"],), ctx.ligne("fournisseur", v, f["id"]), "fournisseur", f["id"])
        )
    ecriture.appliquer(ctx, "fournisseur", lignes, ("id",))


def magasins_et_metiers(ctx: Contexte) -> None:
    """Magasins (type traduit), métiers (densité → bobines par mètre) et leurs étages."""
    lignes = []
    for m in ctx.photo.lignes("magasin"):
        v = {k: m[k] for k in ("id", "code", "nom", "actif")}
        v["contenu"] = m["contenu"] or ""
        v["type"] = TYPES_MAGASIN.get(m["type"], TypeMagasin.stock_courant).value
        if m["type"] not in TYPES_MAGASIN:
            ctx.signaler("magasin", m["id"], f"type « {m['type']} » inconnu : stock courant")
        lignes.append(Ligne((m["id"],), ctx.ligne("magasin", v, m["id"]), "magasin", m["id"]))
    ecriture.appliquer(ctx, "magasin", lignes, ("id",))
    metiers = []
    for m in ctx.photo.lignes("metier"):
        v = {k: m[k] for k in ("id", "code", "nom", "laize", "etages", "actif")}
        v["bobines_par_metre"] = m["densite"]
        v["commentaire"] = m["commentaire"] or ""
        metiers.append(Ligne((m["id"],), ctx.ligne("metier", v, m["id"]), "metier", m["id"]))
    ecriture.appliquer(ctx, "metier", metiers, ("id",))
    _etages(ctx)


def _etages(ctx: Contexte) -> None:
    """Une ligne `metier_etage` par étage existant (1..etages) ; les étages en trop retirés."""
    t = metadata.tables["metier_etage"]
    existants: dict[int, set[int]] = defaultdict(set)
    for mid, etage in ctx.c.execute(select(t.c.metier_id, t.c.etage)):
        existants[mid].add(etage)
    nouveaux = []
    for m in ctx.photo.lignes("metier"):
        voulus = set(range(1, int(m["etages"]) + 1))
        nouveaux += [
            {"metier_id": m["id"], "etage": e} for e in sorted(voulus - existants[m["id"]])
        ]
        en_trop = existants[m["id"]] - voulus
        if en_trop:
            ctx.c.execute(delete(t).where(t.c.metier_id == m["id"], t.c.etage.in_(en_trop)))
            ctx.compter("metier_etage", "supprimees", len(en_trop))
    ecriture.inserer(ctx, "metier_etage", nouveaux)


def _valeur_reglage(valeur: str | None) -> str:
    """Texte normalisé d'un réglage : « 60.0 » → « 60 » (entier sans « .0 »)."""
    texte = valeur or ""
    return texte[:-2] if ENTIER_DECIMAL.fullmatch(texte) else texte


def reglages(ctx: Contexte) -> None:
    """Réglages connus de PRO ; les autres clés sont signalées (courriel_dernier_envoi…)."""
    lignes = []
    for p in ctx.photo.lignes("parametre"):
        if p["cle"] not in CLES_REGLAGES:
            ctx.signaler("parametre", p["cle"], "clé inconnue de PRO : non reprise")
            continue
        v = {
            "cle": p["cle"],
            "valeur": _valeur_reglage(p["valeur"]),
            "modifie_le": p["modifie_le"],
            "modifie_par_id": ctx.personne(p["modifie_par"]),
        }
        lignes.append(
            Ligne(
                (p["cle"],),
                ctx.ligne("parametre", v, p["cle"]),
                "parametre",
                ident_de_code(p["cle"]),
            )
        )
    ecriture.appliquer(ctx, "parametre", lignes, ("cle",))
    _historique_des_reglages(ctx)


def _historique_des_reglages(ctx: Contexte) -> None:
    """L'historique des réglages, avec la valeur d'avant (recalculée dans l'ordre)."""
    precedent: dict[str, str | None] = {}
    lignes = []
    historique = sorted(
        ctx.photo.lignes("parametre_historique"), key=lambda h: (h["quand"], h["id"])
    )
    for h in historique:
        if h["cle"].startswith(PREFIXE_COURS):
            continue
        if h["cle"] not in CLES_REGLAGES:
            ctx.signaler("parametre_historique", h["id"], f"clé « {h['cle']} » inconnue de PRO")
            continue
        apres = _valeur_reglage(h["valeur"])
        v = {
            "cle": h["cle"],
            "avant": precedent.get(h["cle"]),
            "apres": apres,
            "quand": h["quand"],
            "par_id": ctx.personne(h["par"]),
        }
        precedent[h["cle"]] = apres
        lignes.append(
            Ligne(
                (0,), ctx.ligne("parametre_historique", v, h["id"]), "parametre_historique", h["id"]
            )
        )
    _ajouter_avec_ids(ctx, "parametre_historique", lignes)
