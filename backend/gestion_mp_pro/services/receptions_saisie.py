"""La saisie d'une réception : en-tête, lignes, factures par devise, vérifiées ligne par ligne
(REGLES § 3.2, X-RCP-04 à 14 ; A-11, D-08 corrigés) et rangées **par devise** : un camion qui
apporte des bons en deux devises donne une réception par devise (R8r), enregistrées ensemble.

Sur un bon : le bon est du fournisseur, la matière est celle de la ligne, le bon est parti,
non annulé, envoyé au plus tard le jour de la réception ; la devise est la sienne ; le prix est
celui saisi, sinon le catalogue dans la devise du bon, et un prix confirmé l'emporte toujours.
Hors commande : la devise est celle saisie, sinon celle du fournisseur ; une matière désactivée
ne se reçoit plus (sur un bon, le camion est là : la réception l'annonce seulement).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Devise,
    Fournisseur,
    Magasin,
    Matiere,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import QualiteReception
from gestion_mp_pro.modeles.types import PRIX, QUANTITE, UNITES, arrondir
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services.commandes_socle import (
    nom_commande,
    prix_catalogue_en,
    taux_des_devises,
)
from gestion_mp_pro.services.receptions_socle import LOT_INTERNE, probleme_du_bon, refuser

ZERO = Decimal(0)


@dataclass(frozen=True)
class LigneSaisie:
    """Une ligne saisie au quai : matière, bon, lot, pesée, conditionnement, qualité, prix."""

    matiere_id: int
    commande_ligne_id: int | None = None
    lot_numero: str = ""
    lot_interne: bool = False
    quantite_bl: Decimal = ZERO
    quantite_pesee: Decimal = ZERO
    nb_palettes: Decimal = ZERO
    bobines_en_plus: Decimal = ZERO
    magasin_id: int | None = None
    qualite: QualiteReception = QualiteReception.conforme
    observations: str = ""
    prix: Decimal | None = None
    devise: str = ""


@dataclass(frozen=True)
class FactureSaisie:
    """La facture saisie avec la réception (un champ vide n'efface rien)."""

    numero: str
    date: dt.date | None = None
    montant: Decimal | None = None
    echeance: dt.date | None = None


@dataclass(frozen=True)
class Saisie:
    """Ce que le poste de pesée envoie : un camion."""

    date: dt.date
    fournisseur_id: int
    lignes: list[LigneSaisie]
    numero_bl: str = ""
    controle_par: str = ""
    observations: str = ""
    factures: dict[str, FactureSaisie] = field(default_factory=dict)


@dataclass
class Prepare:
    """Une saisie vérifiée : le fournisseur et les lignes rangées par devise (ordre de saisie)."""

    fournisseur: Fournisseur
    par_devise: dict[str, list[ReceptionLigne]]


@dataclass
class _Lus:
    """Les fiches citées par la saisie, lues en une fois."""

    matieres: dict[int, Matiere]
    magasins: set[int]
    lignes: dict[int, CommandeLigne]
    commandes: dict[int, Commande]
    taux: dict[str, float]


def _lire(s: Session, lignes: list[LigneSaisie]) -> _Lus:
    """Matières, magasins, lignes de bon et bons cités (quatre requêtes)."""
    mids = {x.matiere_id for x in lignes}
    gids = {x.magasin_id for x in lignes if x.magasin_id is not None}
    clids = {x.commande_ligne_id for x in lignes if x.commande_ligne_id is not None}
    matieres = {m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(mids)))}
    magasins = set(s.scalars(select(Magasin.id).where(Magasin.id.in_(gids)))) if gids else set()
    cls = {x.id: x for x in s.scalars(select(CommandeLigne).where(CommandeLigne.id.in_(clids)))}
    cids = {x.commande_id for x in cls.values()}
    commandes = {c.id: c for c in s.scalars(select(Commande).where(Commande.id.in_(cids)))}
    return _Lus(matieres, magasins, cls, commandes, taux_des_devises(s))


def verifier_entete(s: Session, e: Saisie) -> Fournisseur:
    """Le fournisseur (X-RCP-13) et la date, jamais dans le futur (X-RCP-14) ; la période
    close n'est contrôlée qu'à la validation (annoncée parmi les blocages)."""
    f = s.get(Fournisseur, e.fournisseur_id)
    if f is None:
        raise Refus.saisie("Fournisseur inconnu.", code="valeur_inconnue")
    if e.date > horloge.aujourd_hui():
        raise Refus.saisie("Une réception ne se date pas dans le futur.", code="date_future")
    return f


def _sur_un_bon(
    x: LigneSaisie, m: Matiere, f: Fournisseur, lus: _Lus, jour: dt.date
) -> tuple[str, Decimal]:
    """Devise et prix d'une ligne sur un bon (X-RCP-07 à 11)."""
    cl = lus.lignes.get(x.commande_ligne_id or 0)
    if cl is None:
        raise Refus.saisie("Ligne de commande inconnue.", code="valeur_inconnue")
    c = lus.commandes[cl.commande_id]
    if c.fournisseur_id != f.id:
        raise Refus.saisie(
            f"La commande {nom_commande(c)} n'est pas de {f.nom} : une réception ne mêle pas "
            "deux fournisseurs."
        )
    if cl.matiere_id != m.id:
        raise Refus.saisie(
            f"« {m.reference} » n'est pas sur la ligne choisie de {nom_commande(c)}."
        )
    probleme = probleme_du_bon(c, jour)
    if probleme is not None:
        raise refuser(probleme)
    if x.devise and x.devise.upper() != c.devise:
        raise Refus.saisie(
            f"Le bon {nom_commande(c)} est en {c.devise} : sa réception aussi.",
            code="devise_incompatible",
        )
    if cl.prix_confirme and cl.prix:
        return c.devise, cl.prix
    prix = x.prix if x.prix is not None else prix_catalogue_en(m, c.devise, lus.taux)
    return c.devise, Decimal(str(prix))


def _hors_commande(x: LigneSaisie, m: Matiere, f: Fournisseur, lus: _Lus) -> tuple[str, Decimal]:
    """Devise et prix d'une ligne hors commande (X-RCP-12 ; A-11 : matière désactivée refusée).
    La devise est celle du prix payé : par défaut celle du fournisseur (un fil LOMAT en USD
    acheté chez un fournisseur marocain se paie en MAD)."""
    if not m.actif:
        raise Refus.etat(
            f"« {m.reference} » est désactivée : elle ne se reçoit plus hors commande. "
            "La réactiver d'abord (Catalogue › Matières).",
            code="fiche_inactive",
        )
    devise = (x.devise or f.devise or "MAD").upper()
    if devise not in lus.taux:
        raise Refus.saisie(f"Devise inconnue : {devise}.", code="valeur_inconnue")
    prix = x.prix if x.prix is not None else prix_catalogue_en(m, devise, lus.taux)
    return devise, Decimal(str(prix))


def _lot(x: LigneSaisie) -> tuple[str, bool]:
    """Le numéro du lot et la case « lot interne » : la case l'emporte sur un numéro ; l'ancien
    texte « LOT INTERNE » vaut la case ; une ligne refusée n'a pas de lot (aucun numéro donné)."""
    numero = x.lot_numero.strip()
    interne = x.lot_interne or numero.upper() == LOT_INTERNE
    if interne:
        numero = ""
    if x.qualite == QualiteReception.refuse:
        return numero, False
    if re.search(r"\s", numero):
        raise Refus.saisie(
            f"Un numéro de lot s'écrit sans espace : « {numero} ».",
            champs={"lot_numero": "numéro du lot avec un espace"},
        )
    return numero, interne


def _bobines(x: LigneSaisie, m: Matiere) -> Decimal:
    """Le nombre de bobines : palettes × bobines par palette (fiche) + bobines en plus ; une
    bobine se compte entière (U20, D-08), une palette peut être entamée."""
    if x.bobines_en_plus != x.bobines_en_plus.to_integral_value():
        raise Refus.saisie(
            f"« {m.reference} » : une bobine se compte entière — saisir un nombre entier de "
            "bobines en plus des palettes.",
            code="quantite_invalide",
        )
    bobines = x.nb_palettes * (m.bobines_palette or ZERO) + x.bobines_en_plus
    if bobines != bobines.to_integral_value():
        raise Refus.saisie(
            f"« {m.reference} » : {x.nb_palettes.normalize():f} palette(s) de "
            f"{m.bobines_palette.normalize():f} bobines ne font pas un nombre entier de bobines "
            "(une bobine se compte entière) : saisir les palettes pleines, et le reste en "
            "bobines en plus.",
            code="quantite_invalide",
        )
    return arrondir(bobines, UNITES)


def _ligne(x: LigneSaisie, f: Fournisseur, lus: _Lus, jour: dt.date) -> tuple[str, ReceptionLigne]:
    """Une ligne vérifiée et sa devise."""
    m = lus.matieres.get(x.matiere_id)
    if m is None:
        raise Refus.saisie("Matière inconnue dans la réception.", code="valeur_inconnue")
    if x.magasin_id is not None and x.magasin_id not in lus.magasins:
        raise Refus.saisie("Magasin inconnu.", code="valeur_inconnue")
    if x.commande_ligne_id is not None:
        devise, prix = _sur_un_bon(x, m, f, lus, jour)
    else:
        devise, prix = _hors_commande(x, m, f, lus)
    numero, interne = _lot(x)
    return devise, ReceptionLigne(
        commande_ligne_id=x.commande_ligne_id,
        matiere_id=m.id,
        lot_numero=numero,
        lot_interne=interne,
        quantite_bl=arrondir(x.quantite_bl, QUANTITE),
        quantite_pesee=arrondir(x.quantite_pesee, QUANTITE),
        nb_palettes=arrondir(x.nb_palettes, UNITES),
        bobines_en_plus=arrondir(x.bobines_en_plus, UNITES),
        nb_bobines=_bobines(x, m),
        magasin_id=x.magasin_id,
        qualite=x.qualite,
        observations=x.observations.strip(),
        prix=arrondir(prix, PRIX),
    )


def preparer(s: Session, e: Saisie) -> Prepare:
    """La saisie vérifiée, ses lignes rangées par devise. Une facture saisie pour une devise
    qu'aucune ligne ne porte est refusée (X-RCP-02)."""
    f = verifier_entete(s, e)
    lus = _lire(s, e.lignes)
    par_devise: dict[str, list[ReceptionLigne]] = {}
    for x in e.lignes:
        devise, ligne = _ligne(x, f, lus, e.date)
        par_devise.setdefault(devise, []).append(ligne)
    for devise in e.factures:
        if devise.upper() not in par_devise:
            portee = next(iter(par_devise))
            raise Refus.saisie(
                f"Cette réception est en {portee} : sa facture aussi. Une facture en "
                f"{devise.upper()} va sur la réception de cette devise.",
                code="devise_incompatible",
            )
    return Prepare(f, par_devise)


def devise_existe(s: Session, code: str) -> bool:
    """La devise est-elle connue ?"""
    return s.get(Devise, code) is not None
