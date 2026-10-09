"""Ce qui bloquerait la validation d'un brouillon, et ce qui mérite d'être su avant (REGLES
§ 3.6, X-RCP-B1 à B8, A-RCP-01 et 02).

La **même liste** sert à l'écran (annoncée sur le brouillon, `blocages` de la fiche) et à la
validation (refusée avec le premier, à son code). L'excédent se compte **tous les lots d'une
ligne de bon ensemble** ; à la validation, il se lit après le verrou des bons (deux postes ne
franchissent pas la borne à deux). Les lignes refusées ne sont soumises qu'à la date et aux
problèmes du bon. Une suspension d'inventaire ne vaut que pour les matières de son périmètre
(K2). Un bon parti qui attend l'approbation de la direction se reçoit : la réception l'annonce
sans bloquer (A-RCP-02).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Inventaire,
    InventaireMatiere,
    Magasin,
    Matiere,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import QualiteReception, StatutCommande, StatutInventaire
from gestion_mp_pro.services import periode
from gestion_mp_pro.services.commandes_socle import nom_commande
from gestion_mp_pro.services.conversions import kg
from gestion_mp_pro.services.receptions_socle import Bons, probleme_du_bon

PRECISION = 1e-6


@dataclass(frozen=True)
class Blocage:
    """Un blocage : le code du refus qu'il deviendra à la validation, et sa phrase."""

    code: str
    message: str


@dataclass(frozen=True)
class _Inventaire:
    """Un inventaire ouvert : son numéro, son magasin (`None` : tous), son périmètre."""

    numero: str
    magasin_id: int | None
    matieres: frozenset[int]


def inventaires_ouverts(s: Session) -> list[_Inventaire]:
    """Les inventaires ouverts et les matières de leur périmètre (deux requêtes)."""
    ouverts = list(
        s.scalars(
            select(Inventaire)
            .where(Inventaire.statut == StatutInventaire.ouvert)
            .order_by(Inventaire.id)
        )
    )
    if not ouverts:
        return []
    perimetres: dict[int, set[int]] = {i.id: set() for i in ouverts}
    for iid, mid in s.execute(
        select(InventaireMatiere.inventaire_id, InventaireMatiere.matiere_id).where(
            InventaireMatiere.inventaire_id.in_(list(perimetres))
        )
    ):
        perimetres[iid].add(mid)
    return [_Inventaire(i.numero, i.magasin_id, frozenset(perimetres[i.id])) for i in ouverts]


@dataclass
class Contexte:
    """Ce que les blocages lisent, chargé une fois pour une liste de réceptions."""

    bons: Bons
    quarantaine: Magasin | None
    inventaires: list[_Inventaire]
    matieres: dict[int, Matiere]
    magasins: dict[int, Magasin]


def contexte(s: Session, receptions: list[Reception], b: Bons, q: Magasin | None) -> Contexte:
    """Le contexte des blocages de ces réceptions."""
    mids = {x.matiere_id for r in receptions for x in r.lignes}
    matieres = (
        {m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(mids)))} if mids else {}
    )
    magasins = {g.id: g for g in s.scalars(select(Magasin))}
    return Contexte(b, q, inventaires_ouverts(s), matieres, magasins)


def _date(s: Session, r: Reception) -> list[Blocage]:
    """La date de la réception, permise ou non (X-RCP-B1)."""
    try:
        periode.date_permise(s, r.date)
    except Refus as refus:
        return [Blocage(refus.code, refus.detail)]
    return []


def _apporte(r: Reception) -> dict[int, float]:
    """Ce que la réception apporte à chaque ligne de bon, tous ses lots ensemble (hors refus)."""
    apporte: dict[int, float] = {}
    for x in r.lignes:
        if x.commande_ligne_id and x.qualite != QualiteReception.refuse:
            cle = x.commande_ligne_id
            apporte[cle] = apporte.get(cle, 0.0) + float(x.quantite_pesee)
    return apporte


def _excedent(x: ReceptionLigne, ctx: Contexte, apporte: dict[int, float]) -> Blocage | None:
    """Au-delà du reste net plus l'excédent toléré, une ligne de bon ne reçoit plus (X-RCP-B3) :
    deux lots de 700 kg sur une ligne de 1 000 kg en font 1 400 ; un bon soldé, même à la main,
    n'en reçoit pas davantage."""
    b = ctx.bons
    cl = b.lignes[x.commande_ligne_id or 0]
    quantite = float(cl.quantite)
    reste = max(0.0, quantite - b.recu.get(cl.id, 0.0))
    total = apporte.get(cl.id, 0.0)
    if total <= reste + quantite * b.excedent + PRECISION:
        return None
    plusieurs = total - float(x.quantite_pesee) > PRECISION
    reference = ctx.matieres[x.matiere_id].reference
    return Blocage(
        "excedent",
        f"« {reference} » : {kg(total)} kg reçus {'(tous lots ensemble) ' if plusieurs else ''}"
        f"pour {kg(reste)} kg restant à livrer sur {nom_commande(b.bon(cl.id))} (excédent "
        f"toléré : {b.excedent:.0%} de la ligne). Recevoir le surplus sur une ligne hors "
        "commande, ou faire corriger le bon.",
    )


def _cible(x: ReceptionLigne, ctx: Contexte) -> int | None:
    """Le magasin où la ligne entrera : la quarantaine pour une ligne sous réserve."""
    if x.qualite == QualiteReception.reserve:
        return ctx.quarantaine.id if ctx.quarantaine is not None else None
    return x.magasin_id


def _rangement(x: ReceptionLigne, ctx: Contexte) -> list[Blocage]:
    """Inventaire en cours, magasin désactivé, pesée, lot, quarantaine, magasin (B4 à B8)."""
    reference = ctx.matieres[x.matiere_id].reference
    cible = _cible(x, ctx)
    manques: list[Blocage] = []
    for inv in ctx.inventaires:
        sur_le_magasin = inv.magasin_id is None or inv.magasin_id == cible
        if cible is not None and sur_le_magasin and x.matiere_id in inv.matieres:
            manques.append(
                Blocage(
                    "inventaire_en_cours",
                    f"L'inventaire {inv.numero} est en cours : les entrées y sont suspendues "
                    "jusqu'à sa validation.",
                )
            )
    magasin = ctx.magasins.get(cible) if cible is not None else None
    if magasin is not None and not magasin.actif:
        manques.append(
            Blocage(
                "saisie_invalide",
                f"Le magasin « {magasin.code} » est désactivé : il ne reçoit plus rien.",
            )
        )
    if x.quantite_pesee <= 0:
        manques.append(
            Blocage(
                "quantite_invalide",
                f"« {reference} » : la pesée est à zéro. La saisir, ou marquer la ligne "
                "« refusé ».",
            )
        )
    if not x.lot_interne and not x.lot_numero:
        manques.append(
            Blocage(
                "saisie_invalide",
                f"« {reference} » : le numéro de lot manque (celui de l'étiquette, ou "
                "« Lot interne »).",
            )
        )
    if x.qualite == QualiteReception.reserve and ctx.quarantaine is None:
        manques.append(
            Blocage(
                "etat_incompatible",
                "Une ligne sous réserve va en quarantaine : créer d'abord un magasin de type "
                "« Quarantaine » (Réglages › Magasins).",
            )
        )
    elif x.qualite == QualiteReception.conforme and x.magasin_id is None:
        manques.append(
            Blocage("saisie_invalide", f"« {reference} » : choisir le magasin de rangement.")
        )
    return manques


def blocages(s: Session, r: Reception, ctx: Contexte) -> list[Blocage]:
    """Ce qui empêcherait de valider ce brouillon, dans l'ordre, sans doublon."""
    manques = _date(s, r)
    apporte = _apporte(r)
    for x in sorted(r.lignes, key=lambda y: y.id or 0):
        probleme = None
        if x.commande_ligne_id is not None:
            probleme = probleme_du_bon(ctx.bons.bon(x.commande_ligne_id), r.date)
            if probleme is not None:
                manques.append(Blocage(*probleme))
        if x.qualite == QualiteReception.refuse:
            continue
        if x.commande_ligne_id is not None and probleme is None:
            excedent = _excedent(x, ctx, apporte)
            if excedent is not None:
                manques.append(excedent)
        manques.extend(_rangement(x, ctx))
    vus: dict[str, Blocage] = {}
    for m in manques:
        vus.setdefault(m.message, m)
    return list(vus.values())


def avertissements(r: Reception, ctx: Contexte) -> list[str]:
    """Ce qui ne bloque pas mais mérite d'être su : matière désactivée sur un bon (A-11), bon
    soldé (A-RCP-01), bon parti qui attend l'approbation d'une modification (A-RCP-02)."""
    alertes: list[str] = []
    for x in sorted(r.lignes, key=lambda y: y.id or 0):
        if x.commande_ligne_id is None:
            continue
        m = ctx.matieres[x.matiere_id]
        if not m.actif:
            alertes.append(
                f"« {m.reference} » est désactivée au catalogue : le camion est là, la "
                "réception passe, mais elle ne se recommandera pas."
            )
        c = ctx.bons.bon(x.commande_ligne_id)
        if c.statut == StatutCommande.soldee:
            alertes.append(
                f"Le bon {nom_commande(c)} est soldé : il n'attend plus rien. Le rouvrir si le "
                "fournisseur le complète vraiment, sinon recevoir hors commande."
            )
        elif c.numero and c.statut == StatutCommande.a_approuver:
            alertes.append(
                f"Le bon {nom_commande(c)} est parti, mais une modification attend "
                "l'approbation de la direction : la réception s'impute à ses lignes "
                "d'aujourd'hui. Si elle la refuse, le bon revient à sa version partie."
            )
    return list(dict.fromkeys(alertes))
