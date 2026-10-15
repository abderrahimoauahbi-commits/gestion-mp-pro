"""Le journal du stock et les soldes tenus, pour le moteur (CALCULS A § 4.7).

En base, une ligne par lot et par magasin, quantité signée ; le moteur veut une quantité
positive, le signe porté par le type, et un transfert en une seule ligne
(`calcul.chargement.journal_du_moteur`). Chaque entrée de réception retrouve sa ligne de
réception (`lignes_des_receptions`) : par sa réception, ou — reprise de l'ERP Fil, sans
réception — par lot, date et pesée.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.chargement import (
    EcritureLue,
    EntreeLue,
    LigneDeReception,
    journal_du_moteur,
    lignes_des_receptions,
)
from gestion_mp_pro.modeles import (
    Motif,
    Mouvement,
    Operation,
    Ordre,
    Reception,
    ReceptionLigne,
    Solde,
)
from gestion_mp_pro.modeles.enums import DocumentMouvement, QualiteReception, TypeMouvement
from gestion_mp_pro.services.chargeur.contexte import Noms, nombre

COLONNES = (
    Mouvement.id,
    Mouvement.type,
    Mouvement.date_effet,
    Mouvement.matiere_id,
    Mouvement.lot_id,
    Mouvement.magasin_id,
    Mouvement.quantite,
    Mouvement.prix,
    Mouvement.devise,
    Mouvement.cours,
    Mouvement.document,
    Mouvement.reception_id,
    Mouvement.ordre_id,
    Mouvement.operation_id,
    Mouvement.document_numero,
    Mouvement.paire_id,
    Mouvement.contrepasse_id,
    Mouvement.motif_id,
    Mouvement.motif_texte,
    Mouvement.auteur_id,
)
"""Les colonnes du journal que le moteur lit (pas d'objets ORM : dix mille lignes et plus)."""


def lignes_de_reception(s: Session) -> dict[int, int]:
    """{n° du mouvement : n° de la ligne de réception} de chaque entrée de réception."""
    lignes = [
        LigneDeReception(i, r, lot or 0, jour, float(kg))
        for i, r, lot, jour, kg in s.execute(
            select(
                ReceptionLigne.id,
                ReceptionLigne.reception_id,
                ReceptionLigne.lot_id,
                Reception.date,
                ReceptionLigne.quantite_pesee,
            )
            .join(Reception, Reception.id == ReceptionLigne.reception_id)
            .where(
                ReceptionLigne.lot_id.is_not(None),
                ReceptionLigne.qualite != QualiteReception.refuse,
            )
            .order_by(ReceptionLigne.id)
        )
    ]
    entrees = [
        EntreeLue(i, r, lot, cp, jour, float(kg))
        for i, r, lot, cp, jour, kg in s.execute(
            select(
                Mouvement.id,
                Mouvement.reception_id,
                Mouvement.lot_id,
                Mouvement.contrepasse_id,
                Mouvement.date_effet,
                Mouvement.quantite,
            )
            .where(
                Mouvement.type == TypeMouvement.RECEPTION,
                Mouvement.document.in_((DocumentMouvement.reception, DocumentMouvement.reprise)),
            )
            .order_by(Mouvement.id)
        )
    ]
    return lignes_des_receptions(lignes, entrees)


def _motifs(s: Session) -> dict[int, str]:
    """Le motif tel que le moteur le code : « R1 »… s'il en a un, sinon son libellé."""
    return {
        i: code or libelle
        for i, libelle, code in s.execute(select(Motif.id, Motif.libelle, Motif.code_r))
    }


def journal(s: Session, noms: Noms, ordres: Sequence[int] | None = None) -> list[c.Mouvement]:
    """Le journal du moteur, dans l'ordre (date d'effet, numéro).

    `ordres` : seulement les écritures de ces ordres et celles qui en annulent une (la fiche
    d'un ordre n'a pas besoin des 38 000 lignes du journal, stress « 3 ans » A4) — traduites
    exactement comme dans le journal entier, dans le même ordre."""
    requete = select(*COLONNES).order_by(Mouvement.date_effet, Mouvement.id)
    if ordres is not None:
        des_ordres = select(Mouvement.id).where(Mouvement.ordre_id.in_(ordres))
        requete = requete.where(
            Mouvement.ordre_id.in_(ordres) | Mouvement.contrepasse_id.in_(des_ordres)
        )
    numeros_of = dict(
        s.execute(select(Ordre.id, Ordre.numero).where(Ordre.numero.is_not(None))).all()
    )
    fournisseur_operation = dict(
        s.execute(
            select(Operation.id, Operation.fournisseur_id).where(
                Operation.fournisseur_id.is_not(None)
            )
        ).all()
    )
    motifs, lignes = _motifs(s), lignes_de_reception(s)
    ecritures = []
    for x in s.execute(requete):
        fournisseur = noms.fournisseur_du_lot.get(x.lot_id)
        ecritures.append(
            EcritureLue(
                id=x.id,
                type=str(x.type),
                date=x.date_effet,
                reference=noms.references[x.matiere_id],
                quantite=float(x.quantite),
                magasin=noms.magasin(x.magasin_id),
                prix=nombre(x.prix),
                devise=x.devise or "MAD",
                document_numero=x.document_numero,
                lot=noms.lots.get(x.lot_id, ""),
                numero_of=(numeros_of.get(x.ordre_id) or "") if x.ordre_id else "",
                motif=motifs.get(x.motif_id, "") if x.motif_id else x.motif_texte,
                auteur=noms.utilisateur(x.auteur_id),
                fournisseur=noms.fournisseur(fournisseur),
                contrepasse_id=x.contrepasse_id,
                cours=nombre(x.cours),
                paire=x.paire_id,
                document=str(x.document),
                fournisseur_operation=noms.fournisseur(
                    fournisseur_operation.get(x.operation_id) if x.operation_id else None
                ),
                ligne_reception_id=lignes.get(x.id),
            )
        )
    return journal_du_moteur(ecritures)


def soldes(s: Session, noms: Noms) -> dict[c.CleSolde, float]:
    """Les soldes tenus, par (référence, lot, magasin) : ce que C12 confronte au journal."""
    resultat: dict[c.CleSolde, float] = {}
    for lot, magasin, quantite in s.execute(
        select(Solde.lot_id, Solde.magasin_id, Solde.quantite).order_by(
            Solde.lot_id, Solde.magasin_id
        )
    ):
        cle = (noms.references[noms.matiere_du_lot[lot]], noms.lots[lot], noms.magasin(magasin))
        resultat[cle] = float(quantite)
    return resultat
