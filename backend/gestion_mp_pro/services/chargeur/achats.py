"""Bons de commande, réceptions et prix payés, pour le moteur (CALCULS A § 4.1–4.3, § 4.6).

Le reçu d'une ligne de bon est **net** des retours au fournisseur, répartis au prorata des
pesées du lot (`calcul.chargement.au_prorata`) ; ce qui attend en quarantaine se répartit de
même. Une réception annulée n'a rien livré : ni pesée, ni ponctualité, ni prix.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.chargement import (
    LigneRecue,
    au_prorata,
    statut_moteur,
)
from gestion_mp_pro.calcul.chargement import recu_par_ligne as recu_net
from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Devise,
    Magasin,
    Matiere,
    Mouvement,
    Reception,
    ReceptionLigne,
    Solde,
)
from gestion_mp_pro.modeles.enums import (
    OrigineSolde,
    QualiteReception,
    StatutCommande,
    StatutDocument,
    TypeMagasin,
    TypeMouvement,
)
from gestion_mp_pro.services.chargeur.contexte import Noms, a_l_usine, nombre

SEUIL_RETOUR = 1e-9
"""Un retour net plus petit n'est pas un retour (`depot.retours_par_ligne_reception`)."""


def lignes_recues(s: Session) -> list[LigneRecue]:
    """Les lignes entrées : réceptions validées, lignes non refusées."""
    requete = (
        select(
            ReceptionLigne.id,
            ReceptionLigne.commande_ligne_id,
            ReceptionLigne.lot_id,
            ReceptionLigne.quantite_pesee,
            ReceptionLigne.qualite,
        )
        .join(Reception, Reception.id == ReceptionLigne.reception_id)
        .where(
            Reception.statut == StatutDocument.validee,
            ReceptionLigne.qualite != QualiteReception.refuse,
        )
        .order_by(ReceptionLigne.id)
    )
    return [LigneRecue(i, cl, lot, float(kg), str(q)) for i, cl, lot, kg, q in s.execute(requete)]


def retours_par_ligne_reception(
    s: Session, lignes: list[LigneRecue] | None = None
) -> dict[int, float]:
    """Ce que chaque ligne reçue a vu repartir chez le fournisseur : les retours de son lot
    (nets de leurs annulations), au prorata des pesées du lot."""
    lignes = lignes_recues(s) if lignes is None else lignes
    requete = (
        select(Mouvement.lot_id, func.sum(Mouvement.quantite))
        .where(Mouvement.type == TypeMouvement.RETOUR_FOURNISSEUR)
        .group_by(Mouvement.lot_id)
    )
    retours = {lot: -float(kg) for lot, kg in s.execute(requete) if -kg > SEUIL_RETOUR}
    return au_prorata(retours, lignes)


def recu_par_ligne(s: Session, net: bool = True) -> dict[int, float]:
    """Ce que chaque ligne de bon a reçu : pesée des lignes entrées, moins (si `net`) ce qui
    en est reparti chez le fournisseur (une matière renvoyée est due à nouveau)."""
    lignes = lignes_recues(s)
    return recu_net(lignes, retours_par_ligne_reception(s, lignes) if net else {})


def en_quarantaine_par_ligne(s: Session) -> dict[int, float]:
    """Ce que chaque ligne de bon a reçu sous réserve et qui attend encore en quarantaine."""
    lignes = [x for x in lignes_recues(s) if x.qualite == "reserve" and x.lot_id is not None]
    if not lignes:
        return {}
    requete = (
        select(Solde.lot_id, func.sum(Solde.quantite))
        .join(Magasin, Magasin.id == Solde.magasin_id)
        .where(
            Magasin.type == TypeMagasin.quarantaine,
            Solde.lot_id.in_({x.lot_id for x in lignes}),
        )
        .group_by(Solde.lot_id)
    )
    attente = {lot: float(kg) for lot, kg in s.execute(requete) if kg > SEUIL_RETOUR}
    part = au_prorata(attente, lignes)
    bloque: dict[int, float] = defaultdict(float)
    for x in lignes:
        if x.commande_ligne_id is not None and x.id in part:
            bloque[x.commande_ligne_id] += part[x.id]
    return dict(bloque)


@dataclass(frozen=True)
class _Catalogue:
    """Le prix du catalogue d'une matière (au kilo), dans sa devise."""

    prix_kg: float
    devise: str


def _catalogue(s: Session) -> dict[int, _Catalogue]:
    """Prix au kilo (un prix au mètre se ramène par la densité) et devise de chaque matière."""
    resultat: dict[int, _Catalogue] = {}
    for i, prix, unite, densite, devise in s.execute(
        select(Matiere.id, Matiere.prix, Matiere.unite_prix, Matiere.densite, Matiere.devise)
    ):
        if unite == "ml":
            prix_kg = float(prix) / float(densite) if densite else 0.0
        else:
            prix_kg = float(prix)
        resultat[i] = _Catalogue(prix_kg, devise)
    return resultat


def prix_estime(
    ligne: CommandeLigne, devise: str, catalogue: _Catalogue, taux: dict[str, float]
) -> float:
    """Le prix confirmé, sinon celui du catalogue converti dans la devise du bon."""
    if ligne.prix_confirme:
        return float(ligne.prix)
    prix = catalogue.prix_kg
    if not prix or catalogue.devise == devise:
        return prix
    return prix * taux.get(catalogue.devise, 1.0) / (taux.get(devise) or 1.0)


def _clos_le(cmd: Commande) -> tuple[datetime | None, datetime | None]:
    """(soldé à la main le, annulé le) : un solde automatique ou repris n'a pas de date."""
    if cmd.solde_origine is None or cmd.solde_origine == OrigineSolde.reprise:
        return None, None
    if cmd.statut == StatutCommande.soldee and cmd.solde_origine == OrigineSolde.manuel:
        return a_l_usine(cmd.solde_le), None
    if cmd.statut == StatutCommande.annulee:
        return None, a_l_usine(cmd.solde_le)
    return None, None


@dataclass
class Achats:
    """Ce que le chargeur rend pour les achats ; `numeros` : bon par identifiant."""

    commandes: list[c.Commande]
    numeros: dict[int, str]
    commande_de_ligne: dict[int, int]


@dataclass(frozen=True)
class _Lus:
    """Ce que les lignes de bon lisent d'ailleurs : reçu net, quarantaine, catalogue, cours."""

    recu: dict[int, float]
    attente: dict[int, float]
    catalogue: dict[int, _Catalogue]
    taux: dict[str, float]


def _ligne(x: CommandeLigne, cmd: Commande, numero: str, noms: Noms, lus: _Lus) -> c.LigneCommande:
    """Une ligne de bon pour le moteur (reçu net, quarantaine, prix estimé)."""
    return c.LigneCommande(
        numero_bc=numero,
        reference=noms.references[x.matiere_id],
        quantite_commandee=nombre(x.quantite),
        quantite_recue=lus.recu.get(x.id, 0.0),
        quantite_en_quarantaine=lus.attente.get(x.id, 0.0),
        prix_unite=nombre(x.prix),
        devise=cmd.devise,
        prix_confirme=x.prix_confirme,
        unite_commande=x.unite_achat,
        contenance_commande=nombre(x.contenance),
        prix_estime=prix_estime(x, cmd.devise, lus.catalogue[x.matiere_id], lus.taux),
        cours=nombre(cmd.cours),
    )


def commandes(s: Session, noms: Noms) -> Achats:
    """Les bons par identifiant (un brouillon : `BC-brouillon-{id}`)."""
    taux = {
        code: float(v)
        for code, v in s.execute(select(Devise.code, Devise.cours).order_by(Devise.code))
    }
    lus = _Lus(recu_par_ligne(s), en_quarantaine_par_ligne(s), _catalogue(s), taux)
    lignes: dict[int, list[CommandeLigne]] = defaultdict(list)
    for x in s.scalars(select(CommandeLigne).order_by(CommandeLigne.commande_id, CommandeLigne.id)):
        lignes[x.commande_id].append(x)
    resultat = Achats([], {}, {x.id: x.commande_id for xs in lignes.values() for x in xs})
    for cmd in s.scalars(select(Commande).order_by(Commande.id)):
        numero = cmd.numero or f"BC-brouillon-{cmd.id}"
        resultat.numeros[cmd.id] = numero
        a_la_main, annulee = _clos_le(cmd)
        resultat.commandes.append(
            c.Commande(
                numero=numero,
                date_bc=cmd.date_commande,
                fournisseur=noms.fournisseur(cmd.fournisseur_id),
                date_livraison_prevue=cmd.date_livraison_prevue,
                eta=cmd.eta,
                statut=statut_moteur(
                    str(cmd.statut), cmd.numero, [x.prix_confirme for x in lignes[cmd.id]]
                ),
                observations=cmd.observations,
                solde_a_la_main_le=a_la_main,
                annulee_le=annulee,
                lignes=[_ligne(x, cmd, numero, noms, lus) for x in lignes[cmd.id]],
            )
        )
    return resultat
