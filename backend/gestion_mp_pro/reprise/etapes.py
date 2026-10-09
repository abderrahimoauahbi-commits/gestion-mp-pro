"""Les étapes de la reprise, dans l'ordre, à l'intérieur de la transaction de la cible."""

from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, insert, select, update
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import metadata
from gestion_mp_pro.modeles.enums import ModeReprise, ObjetJournal
from gestion_mp_pro.modeles.recherche import TEXTES, texte_de
from gestion_mp_pro.reprise import (
    activite,
    catalogue,
    compteurs,
    controle,
    ecriture,
    journal_repris,
    personnes,
    pieces,
    referentiels,
)
from gestion_mp_pro.reprise import journal_en_tables as jt
from gestion_mp_pro.reprise.contexte import Contexte, Ligne

REFERENTIELS = (ModeReprise.referentiels, ModeReprise.tout)
ACTIVITE = (ModeReprise.activite, ModeReprise.tout)


class ReferentielsAbsents(Exception):
    """`--mode activite` sur une cible dont les référentiels n'ont jamais été repris."""


def _referentiels(ctx: Contexte) -> None:
    """Classification, devises, postes, fournisseurs, magasins, métiers, réglages, catalogue."""
    referentiels.classification(ctx)
    referentiels.devises(ctx)
    referentiels.codes_et_postes(ctx)
    referentiels.fournisseurs(ctx)
    referentiels.magasins_et_metiers(ctx)
    referentiels.reglages(ctx)
    catalogue.matieres(ctx)
    catalogue.qualites(ctx)
    catalogue.versions_de_recette(ctx)
    journal_repris.fils_montes(ctx)
    lignes = [
        Ligne((v["id"],), v, "piece_jointe", v["id"])
        for v in pieces.pieces(ctx, pieces.REFERENTIELS)
    ]
    ecriture.appliquer(ctx, "piece_jointe", lignes, ("id",))


def charger_les_codes(ctx: Contexte) -> None:
    """Les correspondances « code → id » déjà en cible (mode activité seul)."""
    if not ecriture.correspondances(ctx, "article"):
        raise ReferentielsAbsents(
            "--mode activite exige des référentiels repris : lancer d'abord --mode referentiels"
        )
    for table in (
        "composition",
        "type_fil",
        "titrage",
        "couleur",
        "role_nomenclature",
        "code_douanier",
        "poste_frais",
    ):
        t = metadata.tables[table]
        ctx.ids[table] = {code: i for code, i in ctx.c.execute(select(t.c.code, t.c.id))}
    ctx.ids["role"] = ctx.ids["role_nomenclature"]
    ctx.ids["poste"] = ctx.ids["poste_frais"]
    ctx.ids["reference"] = {a["reference"]: a["id"] for a in ctx.photo.lignes("article")}


def derouler(ctx: Contexte, derniere: dict[str, Any] | None, ident: int) -> list[controle.Verdict]:
    """Toutes les étapes ; rend les verdicts du contrôle."""
    ctx.ids["personnes"] = personnes.reprendre(ctx)
    comptes_sources = personnes.ids_des_comptes_sources(ctx, ctx.ids["personnes"])
    if ctx.options.mode in REFERENTIELS:
        _referentiels(ctx)
    else:
        charger_les_codes(ctx)
    journal_ids = journal_repris.journal_repris(ctx)
    attendus_plan = 0
    if ctx.options.mode in REFERENTIELS:
        jt.plans(ctx, journal_ids)
        journal_repris.montages(ctx)
    attendus_plan = _versions_de_plan_attendues(ctx)
    if ctx.options.mode in ACTIVITE:
        _activite(ctx, derniere, comptes_sources)
    compteurs.recaler_les_sequences(ctx)
    recalculer_les_textes(ctx)
    verdicts = [
        controle.comptes(ctx, ctx.options.mode in REFERENTIELS, ctx.options.mode in ACTIVITE),
        controle.recettes(ctx, attendus_plan),
    ]
    if ctx.options.mode in ACTIVITE:
        verdicts += [controle.sommes(ctx), controle.soldes(ctx), controle.numeros(ctx)]
    return verdicts


def _versions_de_plan_attendues(ctx: Contexte) -> int:
    """Versions du plan que le journal source donne : une par changement, plus l'initiale."""
    lignes = [
        x
        for x in ctx.photo.lignes("journal")
        if x["action"] == "plan de production"
        and x["objet"] == "qualite"
        and jt.MARQUE_PLAN in (x["detail"] or "")
    ]
    return len(lignes) + len({x["objet_id"] for x in lignes})


def _activite(
    ctx: Contexte, derniere: dict[str, Any] | None, comptes_sources: dict[int, int]
) -> None:
    """Construit l'activité, décide (sauter, écrire, remplacer, refuser) et l'écrit."""
    j = jt.lire(ctx)
    lignes = activite.construire(ctx, j, comptes_sources)
    construites = activite.empreintes_des_tables(lignes)
    decision = activite.decider(ctx, construites, derniere)
    if decision != "sauter":
        activite.ecrire(ctx, lignes, remplacer=decision == "remplacer")
        ctx.activite_reprise = True
    else:
        for nom, x in lignes.items():
            ctx.compter(nom, "lues", len(x))
            ctx.compter(nom, "sautees", len(x))
    ctx.empreintes_activite = {"tables": construites, "cible": activite.empreinte_cible(ctx)}


def recalculer_les_textes(ctx: Contexte) -> None:
    """`texte_recherche` des fiches écrites en SQL direct (ni `version` ni `modifie_le` touchés)."""
    with Session(bind=ctx.c) as s, s.no_autoflush:
        for modele in TEXTES:
            t = metadata.tables[modele.__tablename__]
            changes = []
            for fiche in s.scalars(select(modele)):
                texte = texte_de(s, fiche)
                if texte != fiche.texte_recherche:  # type: ignore[attr-defined]
                    changes.append({"cle": fiche.id, "texte": texte})  # type: ignore[attr-defined]
            if changes:
                gardees = {c.name: c for c in t.c if c.onupdate is not None}
                ctx.c.execute(
                    update(t)
                    .where(t.c.id == bindparam("cle"))
                    .values(texte_recherche=bindparam("texte"), **gardees),
                    changes,
                )
        s.expunge_all()


def journaliser(ctx: Contexte, ident: int, reussie: bool) -> None:
    """Une ligne au journal de PRO : la reprise elle-même."""
    resume = ", ".join(f"{t} {c['creees']}" for t, c in sorted(ctx.comptes.items()) if c["creees"])
    ctx.c.execute(
        insert(metadata.tables["journal"]),
        {
            "utilisateur_nom": "reprise",
            "action": "reprise de Gestion MP",
            "objet": ObjetJournal.reprise.value,
            "objet_id": ident,
            "detail": (
                f"{ctx.photo.base} · {ctx.options.mode.value} · "
                f"{'réussie' if reussie else 'échouée'} · créées : {resume}"
            )[:2000],
        },
    )
