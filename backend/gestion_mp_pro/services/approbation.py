"""L'approbation de la direction au-delà d'un seuil, au montant approuvé et au cours figé :
versions parties, garde-fou du montant, décisions, approuver, renvoyer (REGLES § 2.3, 2.8,
2.9 ; `gestion_mp/api/achats.py` : `figer_version`, `_reference`, `_controler_montant`,
`approuver`, `_retablir`, `renvoyer`).

- La **version partie** est ce que le fournisseur a entre les mains (table `commande_version`,
  la plus récente) et le montant de référence (devise du bon) auquel toute hausse se mesure.
- Le **garde-fou** suit chaque changement de montant : un brouillon soumis que l'on modifie
  revient en brouillon ; un bon parti qui dépasse le seuil et son montant de référence repasse
  par la direction, sans perdre son numéro ; une baisse ne repasse jamais par elle.
- Chaque décision (demande, approbation, renvoi et motif, version rétablie…) est une ligne de
  `commande_decision`, en plus du journal.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Commande,
    CommandeDecision,
    CommandeLigne,
    CommandeVersion,
    CommandeVersionLigne,
)
from gestion_mp_pro.modeles.enums import (
    DecisionCommande,
    MotifVersionCommande,
    Role,
    StatutCommande,
    TonNotification,
)
from gestion_mp_pro.modeles.types import MONTANT, arrondir
from gestion_mp_pro.services import audit, horloge, notifications
from gestion_mp_pro.services import commandes_gestes as gestes
from gestion_mp_pro.services.commandes_socle import (
    PARTIS,
    Bon,
    charger,
    completer,
    cours_du_bon,
    journaliser,
    lignes_receptionnees,
    mad,
    montant_estime,
    nom_commande,
    numeroter,
    photo,
    recaler_soldes,
    reglage_nombre,
    statut_parti,
    taux_des_devises,
    toucher,
    verifier,
)

SEUIL = "seuil_approbation"
EPSILON = 0.005
"""Un centime d'arrondi ne fait pas une hausse (`achats.py:280`)."""
TOLERANCE_PRIX = 0.05
"""Un prix confirmé plus cher de 5 % au plus ne rouvre pas l'approbation (R-CMD-42)."""
CHAMPS_LIGNE = ("quantite", "unite_achat", "contenance", "prix", "prix_confirme")


def montant_en_mad(estime: float, bon: Bon, taux: dict[str, float]) -> float:
    """Le montant estimé en MAD au cours figé du bon (sinon du jour) : la mesure du seuil."""
    return estime * cours_du_bon(bon.commande, taux)


def montant_colonne(x: float) -> Decimal | None:
    """Un montant pour une colonne `> 0` : arrondi au centime, `None` s'il est nul."""
    valeur = arrondir(x, MONTANT)
    return valeur if valeur > 0 else None


def decider(
    s: Session,
    qui: audit.Qui | None,
    c: Commande,
    decision: DecisionCommande,
    *,
    motif: str = "",
    avant: float | None = None,
    apres: float | None = None,
) -> None:
    """Écrit une décision sur le bon (montants en MAD)."""
    s.add(
        CommandeDecision(
            commande_id=c.id,
            quand=horloge.maintenant(),
            par_id=qui.id if qui is not None else None,
            decision=decision,
            motif=motif,
            montant_avant=None if avant is None else arrondir(avant, MONTANT),
            montant_apres=None if apres is None else arrondir(apres, MONTANT),
        )
    )


# ── Versions parties ─────────────────────────────────────────────────────────


def version_partie(s: Session, cid: int) -> CommandeVersion | None:
    """La dernière version partie du bon (avec ses lignes), ou `None`."""
    requete = (
        select(CommandeVersion)
        .where(CommandeVersion.commande_id == cid)
        .options(selectinload(CommandeVersion.lignes))
        .order_by(CommandeVersion.figee_le.desc(), CommandeVersion.id.desc())
        .limit(1)
    )
    return s.scalars(requete).first()


def figer_version(
    s: Session,
    qui: audit.Qui | None,
    bon: Bon,
    motif: MotifVersionCommande,
    *,
    montant: bool,
    estime: float,
) -> CommandeVersion:
    """Retient la version que le fournisseur a. `montant` (envoi, approbation) fixe aussi le
    montant de référence ; un geste accepté sans la direction le garde — vingt hausses de
    4,9 % ne passent pas une à une (R-CMD-14)."""
    ancienne = version_partie(s, bon.commande.id)
    reference = estime if montant or ancienne is None else float(ancienne.montant_reference)
    v = CommandeVersion(
        commande_id=bon.commande.id,
        figee_le=horloge.maintenant(),
        montant_reference=arrondir(max(reference, 0.0), MONTANT),
        motif=motif,
        par_id=qui.id if qui is not None else None,
    )
    v.lignes = [
        CommandeVersionLigne(
            matiere_id=x.matiere_id,
            confirme_par_id=x.confirme_par_id,
            confirme_le=x.confirme_le,
            **{k: getattr(x, k) for k in CHAMPS_LIGNE},
        )
        for x in bon.commande.lignes
    ]
    s.add(v)
    s.flush()
    return v


def reference(s: Session, bon: Bon, avant: float, taux: dict[str, float]) -> float:
    """Le montant (devise du bon) auquel une hausse se mesure : la version partie ; à défaut,
    le montant approuvé ramené au cours du bon ; sinon celui d'avant le geste (R-CMD-15)."""
    v = version_partie(s, bon.commande.id)
    if v is not None:
        return float(v.montant_reference)
    if bon.commande.montant_approuve:
        return float(bon.commande.montant_approuve) / cours_du_bon(bon.commande, taux)
    return avant


def retablir(s: Session, bon: Bon, version: CommandeVersion) -> Bon:
    """Remet les lignes du bon dans la version partie ; une ligne déjà nommée par une
    réception reste, et reprend seulement sa quantité et son prix d'alors (R-CMD-38)."""
    c = bon.commande
    recues = lignes_receptionnees(s, [x.id for x in c.lignes])
    voulues = {v.matiere_id: v for v in version.lignes}
    for x in list(c.lignes):
        if x.matiere_id not in voulues and x.id not in recues:
            c.lignes.remove(x)
    s.flush()
    actuelles = {x.matiere_id: x for x in c.lignes}
    for mid, v in voulues.items():
        trouvee = actuelles.get(mid)
        x = trouvee if trouvee is not None else CommandeLigne(matiere_id=mid)
        if trouvee is None:
            c.lignes.append(x)
        for k in CHAMPS_LIGNE:
            setattr(x, k, getattr(v, k))
        x.confirme_par_id, x.confirme_le = v.confirme_par_id, v.confirme_le
    s.flush()
    return completer(s, c)


# ── Le garde-fou ─────────────────────────────────────────────────────────────


def demander(s: Session, qui: audit.Qui | None, bon: Bon, avant: float, apres: float) -> None:
    """Le bon part à la direction : décision, notification de la direction (montants MAD)."""
    c = bon.commande
    decider(s, qui, c, DecisionCommande.demande_approbation, avant=avant, apres=apres)
    notifications.notifier(
        s,
        Role.direction,
        f"Bon {nom_commande(c)} à approuver : ≈ {mad(apres)} chez {bon.fournisseur.nom}.",
        lien=f"/commandes/{c.id}",
        ton=TonNotification.alerte,
        objet="commande",
        objet_id=c.id,
        monetaire=True,
    )


def _retour_en_brouillon(
    s: Session, qui: audit.Qui | None, bon: Bon, geste: str, montants: tuple[float, float]
) -> None:
    """Un brouillon soumis que l'on modifie revient en brouillon (R-CMD-16 a)."""
    c = bon.commande
    avant, apres = montants
    c.statut = StatutCommande.brouillon
    decider(s, qui, c, DecisionCommande.retour_brouillon, motif=geste, avant=avant, apres=apres)
    detail = (
        f"{nom_commande(c)} · modifié pendant l'approbation ({geste}) · {mad(avant)} → {mad(apres)}"
    )
    journaliser(s, qui, "retour en brouillon", bon, None, detail=detail)


def controler_montant(
    s: Session,
    qui: audit.Qui | None,
    bon: Bon,
    avant: float,
    geste: str,
    *,
    tolerance: float = 0.0,
) -> StatutCommande:
    """Le garde-fou de l'approbation après tout changement de montant (`avant` : le montant du
    bon dans sa devise, avant le geste) ; rend le statut final (R-CMD-16)."""
    c = bon.commande
    seuil = reglage_nombre(s, SEUIL)
    taux = taux_des_devises(s)
    apres, cours = montant_estime(bon, taux), cours_du_bon(c, taux)
    if c.statut == StatutCommande.a_approuver and not c.numero:
        _retour_en_brouillon(s, qui, bon, geste, (avant * cours, apres * cours))
        return c.statut
    if not c.numero or c.statut not in {*PARTIS, StatutCommande.a_approuver}:
        return c.statut
    ref = reference(s, bon, avant, taux)
    sous_le_seuil = bool(c.montant_approuve) and float(c.montant_approuve or 0) <= seuil
    marge = 0.0 if sous_le_seuil else tolerance
    requise = bool(seuil) and apres * cours > seuil and apres > ref * (1 + marge) + EPSILON
    if c.statut == StatutCommande.a_approuver:
        if not requise:
            c.statut = statut_parti(c)
            figer_version(
                s, qui, bon, MotifVersionCommande.geste_accepte, montant=False, estime=apres
            )
            decider(
                s,
                qui,
                c,
                DecisionCommande.approbation_plus_necessaire,
                motif=geste,
                apres=apres * cours,
            )
            detail = f"{nom_commande(c)} · {geste} · ramené à {mad(apres * cours)}"
            journaliser(s, qui, "approbation plus nécessaire", bon, None, detail=detail)
        return c.statut
    if requise:
        c.statut, c.approuvee_par_id, c.approuvee_le = StatutCommande.a_approuver, None, None
        demander(s, qui, bon, avant * cours, apres * cours)
        detail = (
            f"{nom_commande(c)} · {geste} · {mad(avant * cours)} → {mad(apres * cours)} "
            f"(seuil {mad(seuil)})"
        )
        journaliser(s, qui, "commande à approuver", bon, None, detail=detail)
    else:
        figer_version(s, qui, bon, MotifVersionCommande.geste_accepte, montant=False, estime=apres)
    return c.statut


# ── Approuver, renvoyer ──────────────────────────────────────────────────────


def approuver(s: Session, qui: audit.Qui, cid: int, version: int, jour: date | None) -> Bon:
    """La direction accepte le montant : le bon reçoit son numéro et part, daté du jour réel de
    l'envoi (A-27), ou — déjà parti — reprend sa route avec ce montant (R-CMD-35, R-CMD-36)."""
    bon = charger(s, cid, verrou=True)
    verifier(s, bon.commande, version)
    c = bon.commande
    gestes.exiger("approuver", gestes.etat(s, bon))
    avant = photo(bon)
    numeroter(s, bon, jour, recompter_promesse=True)
    taux = taux_des_devises(s)
    estime = montant_estime(bon, taux)
    en_mad = montant_en_mad(estime, bon, taux)
    c.statut, c.approuvee_par_id, c.approuvee_le = statut_parti(c), qui.id, horloge.maintenant()
    c.montant_approuve = montant_colonne(en_mad)
    figer_version(s, qui, bon, MotifVersionCommande.approbation, montant=True, estime=estime)
    decider(s, qui, c, DecisionCommande.approbation, apres=en_mad)
    toucher(c, qui)
    detail = f"{nom_commande(c)} · {mad(en_mad)} approuvés"
    journaliser(s, qui, "approbation commande", bon, avant, detail=detail)
    _notifier_achats(s, bon, f"Bon {nom_commande(c)} approuvé ({mad(en_mad)}) : il est parti.")
    recaler_soldes(s, qui, {c.id}, "approbation")
    return charger(s, cid)


def renvoyer(s: Session, qui: audit.Qui, cid: int, version: int, motif: str) -> Bon:
    """La direction n'approuve pas : un brouillon redevient brouillon ; un bon parti revient à
    sa version partie et reste chez le fournisseur (R-CMD-37, R-CMD-38)."""
    bon = charger(s, cid, verrou=True)
    verifier(s, bon.commande, version)
    c = bon.commande
    gestes.exiger("renvoyer", gestes.etat(s, bon))
    motif = motif.strip()
    avant = photo(bon)
    if not c.numero:
        c.statut = StatutCommande.brouillon
        decider(s, qui, c, DecisionCommande.renvoi, motif=motif)
        toucher(c, qui)
        journaliser(s, qui, "renvoi aux achats", bon, avant, detail=f"{nom_commande(c)} · {motif}")
        _notifier_achats(s, bon, f"Bon {nom_commande(c)} renvoyé par la direction : « {motif} ».")
        return charger(s, cid)
    v = version_partie(s, c.id)
    if v is None:
        raise Refus.etat(
            f"Le bon {c.numero} est parti, mais sa version d'alors n'est pas connue : "
            "l'approuver, ou demander aux achats de le ramener à ce qui était accepté."
        )
    bon = retablir(s, bon, v)
    c.statut = statut_parti(c)
    taux = taux_des_devises(s)
    en_mad = montant_en_mad(montant_estime(bon, taux), bon, taux)
    decider(s, qui, c, DecisionCommande.renvoi, motif=motif)
    decider(s, qui, c, DecisionCommande.version_retablie, apres=en_mad)
    toucher(c, qui)
    journaliser(s, qui, "renvoi aux achats", bon, avant, detail=f"{nom_commande(c)} · {motif}")
    detail = (
        f"{nom_commande(c)} · {mad(en_mad)} : le bon reste chez le fournisseur tel qu'il "
        "était parti"
    )
    journaliser(s, qui, "version partie rétablie", bon, None, detail=detail)
    _notifier_achats(s, bon, f"Bon {nom_commande(c)} renvoyé par la direction : « {motif} ».")
    recaler_soldes(s, qui, {c.id}, "renvoi")
    return charger(s, cid)


def _notifier_achats(s: Session, bon: Bon, texte: str) -> None:
    """Les achats apprennent la décision de la direction."""
    notifications.notifier(
        s,
        Role.achats,
        texte,
        lien=f"/commandes/{bon.commande.id}",
        ton=TonNotification.info,
        objet="commande",
        objet_id=bon.commande.id,
        monetaire=True,
    )


def a_approuver(s: Session, role: str) -> int | None:
    """La pastille « Commandes » du menu : les bons qui attendent la direction (elle seule)."""
    if role != Role.direction:
        return None
    requete = select(func.count()).where(Commande.statut == StatutCommande.a_approuver)
    return int(s.scalar(requete) or 0)
