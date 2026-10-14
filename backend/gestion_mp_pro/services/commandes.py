"""Les gestes sur un bon de commande : créer (un bon par devise), modifier, supprimer un
brouillon, envoyer (ou soumettre à la direction), confirmer les prix, suivre l'expédition,
solder, rouvrir (REGLES § 2.5–2.14 ; `gestion_mp/api/achats.py`).

Chaque geste verrouille le bon, vérifie la `version` lue (409 sinon), écrit au journal et fait
monter la version. Un brouillon n'a pas de numéro : il le reçoit le jour où il part (M65), dans
la transaction de l'envoi. `recaler_soldes` (soldes automatiques) est appelé par les réceptions
et les opérations de stock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Commande, CommandeLigne, Matiere
from gestion_mp_pro.modeles.enums import (
    MotifVersionCommande,
    StatutCommande,
    UnitePrix,
)
from gestion_mp_pro.modeles.types import PRIX, QUANTITE, arrondir
from gestion_mp_pro.services import audit, horloge
from gestion_mp_pro.services import commandes_gestes as gestes
from gestion_mp_pro.services.approbation import (
    SEUIL,
    TOLERANCE_PRIX,
    controler_montant,
    demander,
    figer_version,
    montant_colonne,
    montant_en_mad,
)
from gestion_mp_pro.services.commandes_saisie import (
    LigneSaisie,
    changer_promesse,
    fournisseur_commandable,
    nombre_fr,
    verifier_lignes,
)
from gestion_mp_pro.services.commandes_socle import (
    PARTIS,
    Bon,
    charger,
    commandes_des_lots,
    completer,
    cours_du_bon,
    journaliser,
    mad,
    montant_estime,
    nom_commande,
    numeroter,
    photo,
    prix_catalogue_kg,
    prix_deja_confirmes,
    recaler_soldes,
    reglage_nombre,
    statut_parti,
    taux_des_devises,
    toucher,
    verifier,
)

__all__ = ["commandes_des_lots", "recaler_soldes"]


@dataclass(frozen=True)
class Creation:
    """Un ou plusieurs bons à créer chez un fournisseur (un par devise)."""

    fournisseur_id: int
    lignes: list[LigneSaisie]
    date_livraison_prevue: date | None = None
    prix_catalogue_a_confirmer: bool = False
    observations: str = ""


@dataclass(frozen=True)
class Modification:
    """Ce que la fiche modifie : promesse (absente = inchangée), remarques, lignes."""

    version: int
    lignes: list[LigneSaisie]
    observations: str = ""
    date_livraison_prevue: date | None = None
    promesse_envoyee: bool = False


@dataclass(frozen=True)
class PrixConfirme:
    """Un prix annoncé par le fournisseur, au kilo ou au mètre."""

    ligne_id: int
    prix: Decimal
    unite: str = "kg"


@dataclass(frozen=True)
class Confirmation:
    """Les prix confirmés, et la date que le fournisseur confirme avec eux."""

    version: int
    lignes: list[PrixConfirme]
    mettre_a_jour_catalogue: bool = True
    date_livraison_prevue: date | None = None


# ── Création, modification, suppression ──────────────────────────────────────


def _promesse_d_un_brouillon(nouvelle: date | None, jour: date) -> None:
    """Un brouillon ne promet pas une date d'avant sa propre date."""
    if nouvelle is not None and nouvelle < jour:
        raise Refus.saisie(
            f"La livraison prévue ({nouvelle:%d/%m/%Y}) précède la date du bon ({jour:%d/%m/%Y}).",
            code="date_invalide",
        )


def creer(s: Session, qui: audit.Qui, e: Creation) -> list[Bon]:
    """Un brouillon par devise des matières, sans numéro, dans l'ordre des devises ; sans prix
    sauf « prix du catalogue à confirmer » (R-CMD-26, R-CMD-27)."""
    f = fournisseur_commandable(s, e.fournisseur_id)
    fiches = verifier_lignes(s, f.id, e.lignes)
    jour = horloge.aujourd_hui()
    _promesse_d_un_brouillon(e.date_livraison_prevue, jour)
    par_devise: dict[str, list[LigneSaisie]] = {}
    for ligne in e.lignes:
        par_devise.setdefault(fiches[ligne.matiere_id].devise, []).append(ligne)
    crees: list[Bon] = []
    for devise, lignes in sorted(par_devise.items()):
        c = Commande(
            fournisseur_id=f.id,
            statut=StatutCommande.brouillon,
            date_commande=jour,
            date_livraison_prevue=e.date_livraison_prevue,
            devise=devise,
            observations=e.observations,
            cree_par_id=qui.id,
            cree_le=horloge.maintenant(),
        )
        c.lignes = [
            _nouvelle_ligne(x, fiches[x.matiere_id], e.prix_catalogue_a_confirmer) for x in lignes
        ]
        s.add(c)
        s.flush()
        bon = completer(s, c)
        detail = f"{nom_commande(c)} · {f.nom} · {len(lignes)} ligne(s)"
        journaliser(s, qui, "création commande", bon, {}, detail=detail)
        crees.append(bon)
    return crees


def _nouvelle_ligne(x: LigneSaisie, m: Matiere, catalogue: bool) -> CommandeLigne:
    """Une ligne neuve : sans prix, sauf le prix saisi ou celui du catalogue à confirmer."""
    prix = Decimal(0)
    if catalogue:
        prix = x.prix if x.prix is not None else Decimal(str(prix_catalogue_kg(m)))
    return CommandeLigne(
        matiere_id=x.matiere_id,
        quantite=arrondir(x.quantite, QUANTITE),
        unite_achat=x.unite_achat,
        contenance=arrondir(x.contenance, QUANTITE),
        prix=arrondir(prix, PRIX),
        prix_confirme=False,
    )


def _remplacer_lignes(c: Commande, lignes: list[LigneSaisie]) -> None:
    """Les lignes du bon deviennent celles saisies ; une ligne gardée garde son id. Un prix
    confirmé que l'on change redemande confirmation (R-CMD-30)."""
    anciennes = {x.matiere_id: x for x in c.lignes}
    voulues = {x.matiere_id for x in lignes}
    for x in list(c.lignes):
        if x.matiere_id not in voulues:
            c.lignes.remove(x)
    for ligne in lignes:
        trouvee = anciennes.get(ligne.matiere_id)
        x = trouvee or CommandeLigne(matiere_id=ligne.matiere_id, prix=Decimal(0))
        if trouvee is None:
            x.prix_confirme = False
            c.lignes.append(x)
        prix = arrondir(ligne.prix, PRIX) if ligne.prix is not None else Decimal(x.prix or 0)
        if x.prix_confirme and prix != x.prix:
            x.prix_confirme, x.confirme_le, x.confirme_par_id = False, None, None
        x.prix = prix
        x.quantite = arrondir(ligne.quantite, QUANTITE)
        x.unite_achat, x.contenance = ligne.unite_achat, arrondir(ligne.contenance, QUANTITE)


def modifier(s: Session, qui: audit.Qui, cid: int, e: Modification) -> Bon:
    """Un bon se modifie tant que rien n'est reçu ; ensuite on le solde ou on en crée un autre
    (R-CMD-28 à R-CMD-31), puis le garde-fou de l'approbation."""
    bon = charger(s, cid, verrou=True)
    c = bon.commande
    verifier(s, c, e.version)
    gestes.exiger("modifier", gestes.etat(s, bon))
    avant_photo = photo(bon)
    if not c.numero:
        _promesse_d_un_brouillon(e.date_livraison_prevue, c.date_commande)
    fige = prix_deja_confirmes(s, c)
    changer_promesse(c, e.date_livraison_prevue, vider=e.promesse_envoyee, fige=fige)
    taux = taux_des_devises(s)
    avant = montant_estime(bon, taux)
    fiches = verifier_lignes(s, c.fournisseur_id, e.lignes, {x.matiere_id: x for x in c.lignes})
    if any(m.devise != c.devise for m in fiches.values()):
        raise Refus.saisie(
            f"Ce bon est en {c.devise} : une matière d'une autre devise va sur un autre bon.",
            code="devise_incompatible",
        )
    _remplacer_lignes(c, e.lignes)
    c.observations = e.observations
    s.flush()
    bon = completer(s, c)
    if c.statut in PARTIS:
        c.statut = statut_parti(c)
    cours = cours_du_bon(c, taux)
    toucher(c, qui)
    detail = f"{nom_commande(c)} · {mad(avant * cours)} → {mad(montant_estime(bon, taux) * cours)}"
    journaliser(s, qui, "modification commande", bon, avant_photo, detail=detail)
    controler_montant(s, qui, bon, avant, "lignes modifiées")
    return bon


def supprimer(s: Session, qui: audit.Qui, cid: int, version: int) -> None:
    """Seul un bon jamais parti et sans réception se supprime ; parti, il s'annule (M33)."""
    bon = charger(s, cid, verrou=True)
    c = bon.commande
    verifier(s, c, version)
    gestes.exiger("supprimer", gestes.etat(s, bon))
    audit.journal(
        s,
        qui,
        "suppression commande",
        "commande",
        c.id,
        detail=nom_commande(c),
        avant=photo(bon),
    )
    s.delete(c)
    s.flush()


# ── Envoi ────────────────────────────────────────────────────────────────────


def envoyer(s: Session, qui: audit.Qui, cid: int, version: int, jour: date | None) -> Bon:
    """Le bon part (il reçoit son numéro, daté du jour réel de l'envoi) ou, au-delà du seuil,
    attend la direction sans numéro (R-CMD-32 à R-CMD-34)."""
    bon = charger(s, cid, verrou=True)
    c = bon.commande
    verifier(s, c, version)
    gestes.exiger("envoyer", gestes.etat(s, bon))
    avant = photo(bon)
    seuil = reglage_nombre(s, SEUIL)
    taux = taux_des_devises(s)
    estime = montant_estime(bon, taux)
    en_mad = montant_en_mad(estime, bon, taux)
    if seuil and en_mad > seuil and c.approuvee_par_id is None:
        envoi = jour or horloge.aujourd_hui()
        if c.date_livraison_prevue and c.date_livraison_prevue < envoi:
            raise Refus.saisie(
                f"La livraison prévue ({c.date_livraison_prevue:%d/%m/%Y}) est déjà passée : la "
                "corriger, ou la vider (date d'envoi + délai du fournisseur).",
                code="date_invalide",
            )
        c.statut = StatutCommande.a_approuver
        demander(s, qui, bon, en_mad, en_mad)
        action = "commande à approuver"
    else:
        numeroter(s, bon, jour)
        c.statut = statut_parti(c)
        c.montant_approuve = montant_colonne(en_mad)
        figer_version(s, qui, bon, MotifVersionCommande.envoi, montant=True, estime=estime)
        action = "envoi commande"
    toucher(c, qui)
    journaliser(s, qui, action, bon, avant, detail=f"{nom_commande(c)} · {mad(en_mad)}")
    return bon


# ── Prix confirmés ───────────────────────────────────────────────────────────


def _prix_au_kg(m: Matiere, p: PrixConfirme) -> Decimal:
    """Le prix au kilo d'un prix annoncé au mètre (densité de la fiche)."""
    if p.unite == "kg":
        return p.prix
    if not m.densite:
        raise Refus.saisie(
            f"« {m.reference} » n'a pas de densité : son prix se confirme au kilo.",
            code="unite_invalide",
        )
    return p.prix / Decimal(m.densite)


def _au_catalogue(s: Session, qui: audit.Qui, bon: Bon, m: Matiere, prix_kg: float) -> None:
    """Le prix confirmé passe au catalogue, dans la devise de la fiche (au cours figé du bon)
    et dans son unité (× densité au mètre) — c'est ce qui fait vivre la matrice des prix."""
    c = bon.commande
    prix = prix_kg
    if m.devise != c.devise:
        taux = taux_des_devises(s)
        prix = prix_kg * float(c.cours or taux.get(c.devise, 1.0)) / (taux.get(m.devise) or 1.0)
    if m.unite_prix == UnitePrix.ml and m.densite:
        prix *= float(m.densite)
    nouveau = arrondir(prix, PRIX)
    if nouveau == m.prix:
        return
    detail = (
        f"{m.reference} · prix {nombre_fr(m.prix, 4)} → {nombre_fr(nouveau, 4)} {m.devise} / "
        f"{m.unite_prix} (prix confirmé, {nom_commande(c)})"
    )
    with audit.suivre(s, qui, "modification matière", m, detail=detail):
        m.prix, m.modifie_par_id = nouveau, qui.id


def confirmer_prix(s: Session, qui: audit.Qui, cid: int, e: Confirmation) -> Bon:
    """Les prix du fournisseur : le cours se fige à la première confirmation, la date promise
    aussi ; hausse de 5 % au plus sans la direction (R-CMD-39 à R-CMD-42)."""
    bon = charger(s, cid, verrou=True)
    c = bon.commande
    verifier(s, c, e.version)
    gestes.exiger("prix", gestes.etat(s, bon))
    avant_photo = photo(bon)
    changer_promesse(c, e.date_livraison_prevue, fige=prix_deja_confirmes(s, c))
    taux = taux_des_devises(s)
    avant = montant_estime(bon, taux)
    avant_mad = avant * cours_du_bon(c, taux)
    if not c.cours and c.devise != "MAD":
        c.cours, c.cours_fige_le = Decimal(str(taux.get(c.devise, 1.0))), horloge.maintenant()
    lignes = {x.id: x for x in c.lignes}
    for p in e.lignes:
        x = lignes.get(p.ligne_id)
        if x is None:
            raise Refus.saisie("Ligne étrangère à ce bon.", code="valeur_inconnue")
        m = bon.matieres[x.matiere_id]
        x.prix = arrondir(_prix_au_kg(m, p), PRIX)
        if x.prix <= 0:
            raise Refus.saisie(
                f"« {m.reference} » : {nombre_fr(p.prix, 7)} {c.devise} / {p.unite} vaut 0 au kilo "
                "une fois arrondi au millionième : saisir le prix réel."
            )
        x.prix_confirme, x.confirme_le, x.confirme_par_id = True, horloge.maintenant(), qui.id
        if e.mettre_a_jour_catalogue:
            _au_catalogue(s, qui, bon, m, float(x.prix))
    if c.statut == StatutCommande.envoyee and all(x.prix_confirme for x in c.lignes):
        c.statut = StatutCommande.confirmee
    toucher(c, qui)
    apres_mad = montant_estime(bon, taux) * cours_du_bon(c, taux)
    detail = f"{nom_commande(c)} · {len(e.lignes)} prix · {mad(avant_mad)} → {mad(apres_mad)}"
    journaliser(s, qui, "prix confirmés", bon, avant_photo, detail=detail)
    controler_montant(s, qui, bon, avant, "prix confirmés", tolerance=TOLERANCE_PRIX)
    return bon
