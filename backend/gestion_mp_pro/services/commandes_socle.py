"""Le socle des bons de commande : lecture verrouillée, montants estimés, cours du bon,
numérotation à l'envoi, soldes automatiques (`gestion_mp/api/achats.py`, REGLES § 2.1–2.2,
2.15).

Les autres modules du domaine (`approbation`, `commandes`, `commandes_lecture`) s'appuient sur
celui-ci ; il ne dépend d'aucun d'eux. Les montants estimés se comptent en `float`, comme le
moteur (`services.chargeur.achats.prix_estime`) : la fiche, la liste et le plan d'achat disent
le même chiffre.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import flag_modified

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Devise,
    Fournisseur,
    Journal,
    Matiere,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import (
    OrigineSolde,
    SerieNumero,
    StatutCommande,
    StatutDocument,
    UnitePrix,
)
from gestion_mp_pro.services import audit, horloge, numerotation, periode, reglages
from gestion_mp_pro.services.chargeur.achats import en_quarantaine_par_ligne, recu_par_ligne

PARTIS = frozenset({StatutCommande.envoyee, StatutCommande.confirmee})
CLOS = frozenset({StatutCommande.soldee, StatutCommande.annulee})
TOUT_RECU = "tout reçu"
"""Fin du détail du journal d'un solde automatique (une réception a tout apporté)."""


@dataclass
class Bon:
    """Un bon chargé avec ses lignes, son fournisseur et les fiches de ses matières."""

    commande: Commande
    fournisseur: Fournisseur
    matieres: dict[int, Matiere]

    @property
    def lignes(self) -> list[CommandeLigne]:
        """Les lignes du bon, dans l'ordre de leur saisie."""
        return sorted(self.commande.lignes, key=lambda x: x.id or 0)


# ── Réglages, cours, prix ────────────────────────────────────────────────────


def reglage_nombre(s: Session, cle: str) -> float:
    """Un réglage numérique (`services.reglages.nombre`, lot D1 : défaut si vide)."""
    return reglages.nombre(s, cle)


def taux_des_devises(s: Session) -> dict[str, float]:
    """Le cours du jour de chaque devise (MAD pour une unité)."""
    return {code: float(cours) for code, cours in s.execute(select(Devise.code, Devise.cours))}


def prix_catalogue_kg(m: Matiere) -> float:
    """Le prix du catalogue au kilo : un prix au mètre se ramène par la densité (R-CMD-08)."""
    if m.unite_prix == UnitePrix.ml:
        return float(m.prix) / float(m.densite) if m.densite else 0.0
    return float(m.prix)


def prix_catalogue_en(m: Matiere, devise: str, taux: dict[str, float]) -> float:
    """Le prix du catalogue dans la devise voulue, converti au cours du jour (R-CMD-09)."""
    prix = prix_catalogue_kg(m)
    if not prix or m.devise == devise:
        return prix
    return prix * taux.get(m.devise, 1.0) / (taux.get(devise) or 1.0)


def prix_estime(x: CommandeLigne, m: Matiere, devise: str, taux: dict[str, float]) -> float:
    """Le prix confirmé, sinon celui du catalogue dans la devise du bon (R-CMD-10)."""
    return float(x.prix) if x.prix_confirme else prix_catalogue_en(m, devise, taux)


def montant_estime(bon: Bon, taux: dict[str, float]) -> float:
    """Le montant du bon dans sa devise : ce montant décide de l'approbation."""
    c = bon.commande
    return sum(
        float(x.quantite) * prix_estime(x, bon.matieres[x.matiere_id], c.devise, taux)
        for x in c.lignes
    )


def cours_du_bon(c: Commande, taux: dict[str, float]) -> float:
    """Le cours figé du bon, sinon celui du jour (R-CMD-11)."""
    return float(c.cours) if c.cours else taux.get(c.devise, 1.0)


def mad(x: float) -> str:
    """« 98 923 MAD » (R-CMD-12)."""
    return f"{x:,.0f}".replace(",", " ") + " MAD"


def nom_commande(c: Commande) -> str:
    """Le numéro du bon, sinon « brouillon n° 7 » (R-CMD-07)."""
    return c.numero or numerotation.libelle_brouillon(c.id)


def statut_parti(c: Commande) -> StatutCommande:
    """Confirmée si toutes ses lignes ont un prix confirmé, sinon envoyée (R-CMD-05)."""
    confirme = bool(c.lignes) and all(x.prix_confirme for x in c.lignes)
    return StatutCommande.confirmee if confirme else StatutCommande.envoyee


# ── Lecture et écriture d'un bon ─────────────────────────────────────────────


def charger(s: Session, cid: int, *, verrou: bool = False) -> Bon:
    """Le bon (404 « Commande introuvable. »), verrouillé pour un geste, relu en base (ce qui
    est en attente dans la session est d'abord écrit : la relecture ne l'efface pas)."""
    s.flush()
    requete = (
        select(Commande)
        .where(Commande.id == cid)
        .options(selectinload(Commande.lignes))
        .execution_options(populate_existing=True)
    )
    if verrou:
        requete = requete.with_for_update(of=Commande)
    c = s.scalars(requete).first()
    if c is None:
        raise Refus.introuvable("Commande introuvable.")
    return completer(s, c)


def completer(s: Session, c: Commande) -> Bon:
    """Le fournisseur et les fiches des matières d'un bon chargé."""
    ids = {x.matiere_id for x in c.lignes}
    matieres = {m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(ids)))}
    fournisseur = s.get(Fournisseur, c.fournisseur_id)
    if fournisseur is None:  # pragma: no cover — clé étrangère
        raise Refus.introuvable("Fournisseur inconnu.")
    return Bon(c, fournisseur, matieres)


def verifier(s: Session, c: Commande, version: int) -> None:
    """409 `conflit_version` si le bon a changé depuis sa lecture."""
    audit.verifier_version(s, c, version, "Cette commande")


def toucher(c: Commande, qui: audit.Qui | None) -> None:
    """Marque le bon modifié : sa `version` monte même si seules ses lignes ont changé."""
    c.modifie_par_id = qui.id if qui is not None else None
    flag_modified(c, "modifie_par_id")


def photo(bon: Bon) -> dict[str, object]:
    """L'en-tête du bon et ses lignes (`{référence: kg, prix, confirmé}`), pour le journal."""
    lignes = {
        bon.matieres[x.matiere_id].reference: {
            "quantite": audit.valeur_json(x.quantite),
            "unite_achat": x.unite_achat,
            "contenance": audit.valeur_json(x.contenance),
            "prix": audit.valeur_json(x.prix),
            "prix_confirme": x.prix_confirme,
        }
        for x in bon.commande.lignes
        if x.matiere_id in bon.matieres
    }
    return {**audit.photo(bon.commande), "lignes": lignes}


def journaliser(
    s: Session,
    qui: audit.Qui | None,
    action: str,
    bon: Bon,
    avant: dict[str, object] | None,
    *,
    detail: str,
) -> None:
    """Une ligne de journal du bon : les seuls champs changés depuis `avant` (photo)."""
    a, b = audit.differences(avant or {}, photo(bon)) if avant is not None else ({}, {})
    audit.journal(
        s,
        qui,
        action,
        "commande",
        bon.commande.id,
        numero=bon.commande.numero or "",
        detail=detail,
        avant=a,
        apres=b,
    )


def prix_deja_confirmes(s: Session, c: Commande) -> bool:
    """Les prix ont-ils déjà été confirmés une fois ? Le cours s'est alors figé — sauf pour un
    bon en dirhams, qui n'a pas de cours (contrainte `ck_commande_cours_mad`) : le journal le
    dit. La date promise se fige au même moment (R-CMD-29)."""
    if c.cours is not None:
        return True
    requete = select(Journal.id).where(
        Journal.objet == "commande", Journal.objet_id == c.id, Journal.action == "prix confirmés"
    )
    return s.scalar(requete.limit(1)) is not None


# ── Réceptions d'un bon ──────────────────────────────────────────────────────


def lignes_receptionnees(s: Session, ids: Iterable[int] | None = None) -> set[int]:
    """Les lignes de bon nommées par une réception, même brouillon ou annulée (R-CMD-28)."""
    requete = select(ReceptionLigne.commande_ligne_id).where(
        ReceptionLigne.commande_ligne_id.is_not(None)
    )
    if ids is not None:
        requete = requete.where(ReceptionLigne.commande_ligne_id.in_(list(ids)))
    return {x for x in s.scalars(requete) if x is not None}


def a_des_receptions(s: Session, c: Commande) -> bool:
    """Une réception (de tout statut) nomme-t-elle une ligne du bon ?"""
    return bool(lignes_receptionnees(s, [x.id for x in c.lignes]))


def a_ete_livre(s: Session, c: Commande) -> bool:
    """Un camion est-il venu (réception validée, même toute renvoyée depuis) ? Alors le bon se
    solde ; il ne s'annule pas (sa livraison garde sa note)."""
    if not c.lignes:
        return False
    requete = (
        select(func.count())
        .select_from(ReceptionLigne)
        .join(Reception, Reception.id == ReceptionLigne.reception_id)
        .where(
            Reception.statut == StatutDocument.validee,
            ReceptionLigne.commande_ligne_id.in_([x.id for x in c.lignes]),
        )
    )
    return bool(s.scalar(requete))


# ── Numérotation à l'envoi (M65) ─────────────────────────────────────────────


def numeroter(s: Session, bon: Bon, jour: date | None, *, recompter_promesse: bool = False) -> None:
    """Le bon reçoit son numéro et sa date le jour où il part ; la date promise se fixe alors
    (celle saisie, sinon date d'envoi + délai du fournisseur). Une promesse antérieure au départ
    est refusée, ou — `recompter_promesse`, à l'approbation — recomptée (R-CMD-34, R-CMD-35)."""
    c = bon.commande
    if c.numero:
        return
    jour = jour or horloge.aujourd_hui()
    periode.date_permise(s, jour)
    prevue = c.date_livraison_prevue
    if prevue is not None and prevue < jour:
        if not recompter_promesse:
            raise Refus.saisie(
                f"La livraison prévue ({prevue:%d/%m/%Y}) précède l'envoi du bon "
                f"({jour:%d/%m/%Y}) : la corriger, ou la vider (date d'envoi + délai "
                "du fournisseur).",
                code="date_invalide",
            )
        prevue = None
    if prevue is None:
        prevue = date.fromordinal(jour.toordinal() + int(bon.fournisseur.delai_jours or 0))
    c.date_commande, c.date_livraison_prevue = jour, prevue
    c.numero = numerotation.numero(s, SerieNumero.BC, jour)


# ── Soldes automatiques (R-CMD-47, R-CMD-48) ─────────────────────────────────


def livre(c: Commande, recu: dict[int, float], tolerance: float, bloque: dict[int, float]) -> bool:
    """Chaque ligne reçue (net des retours, hors `bloque`) à la tolérance près."""
    return bool(c.lignes) and all(
        recu.get(x.id, 0.0) - bloque.get(x.id, 0.0) >= float(x.quantite) * (1 - tolerance)
        for x in c.lignes
    )


def recaler_soldes(
    s: Session, qui: audit.Qui | None, commandes: Iterable[int], raison: str
) -> list[int]:
    """Le statut des bons touchés par une réception, un retour ou une libération (et leurs
    annulations) : un bon parti livré se solde de lui-même ; un bon soldé de lui-même qui ne
    l'est plus se rouvre. Un bon soldé à la main reste soldé ; un bon soldé repris ne se rouvre
    que si des retours l'ont dégarni ; un bon à approuver garde son statut. Rend les bons
    changés. Appelé par les réceptions (D4) et les opérations (D5)."""
    ids = sorted(set(commandes))
    if not ids:
        return []
    s.flush()
    tolerance = reglage_nombre(s, "toler_in_full")
    recu, bloque = recu_par_ligne(s), en_quarantaine_par_ligne(s)
    brut: dict[int, float] | None = None
    changes: list[int] = []
    for cid in ids:
        bon = charger(s, cid, verrou=True)
        c = bon.commande
        avant = photo(bon)
        if c.statut in PARTIS and livre(c, recu, tolerance, bloque):
            c.statut, c.solde_origine = StatutCommande.soldee, OrigineSolde.automatique
            c.solde_le, c.solde_par_id = horloge.maintenant(), qui.id if qui else None
            action, detail = "commande soldée", f"{nom_commande(c)} · {TOUT_RECU}"
        elif c.statut == StatutCommande.soldee and not livre(c, recu, tolerance, bloque):
            if c.solde_origine == OrigineSolde.reprise and brut is None:
                brut = recu_par_ligne(s, net=False)
            rouvrir = c.solde_origine == OrigineSolde.automatique or (
                c.solde_origine == OrigineSolde.reprise and livre(c, brut or {}, tolerance, {})
            )
            if not rouvrir:
                continue
            c.statut, c.solde_origine, c.solde_le, c.solde_par_id = (
                statut_parti(c),
                None,
                None,
                None,
            )
            action = "commande rouverte"
            detail = f"{nom_commande(c)} · {raison} : le reçu net ne couvre plus le bon"
        else:
            continue
        toucher(c, qui)
        journaliser(s, qui, action, bon, avant, detail=detail)
        changes.append(cid)
    return changes


def commandes_des_lots(s: Session, lots: Iterable[int]) -> set[int]:
    """Les bons dont une réception validée a fait entrer ces lots."""
    lots = set(lots)
    if not lots:
        return set()
    requete = (
        select(CommandeLigne.commande_id)
        .distinct()
        .join(ReceptionLigne, ReceptionLigne.commande_ligne_id == CommandeLigne.id)
        .join(Reception, Reception.id == ReceptionLigne.reception_id)
        .where(Reception.statut == StatutDocument.validee, ReceptionLigne.lot_id.in_(lots))
    )
    return set(s.scalars(requete))
