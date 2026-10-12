"""La petite usine du chargeur, seconde partie (lot S4) : réceptions, flux du stock par le seul
chemin d'écriture, dossier d'importation, métiers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fabriques.moteur_base import Monde, ajouter, ecrire, instant, motif, operation
from fabriques.stock import magasin
from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import (
    Dossier,
    DossierFacture,
    DossierFrais,
    DossierFraisPart,
    DossierLigne,
    Facture,
    Lot,
    Metier,
    MetierEtage,
    Montage,
    Mouvement,
    Ordre,
    OrdrePrevu,
    OrdreQualite,
    PosteFrais,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import (
    DocumentMouvement,
    OrigineCours,
    TypeMagasin,
    TypeMouvement,
    TypeOperation,
)
from gestion_mp_pro.services import lots, stock

LIGNES_RECUES = (("ppa", "L-PP1", 600, "conforme"), ("ppb", "L-PP2", 300, "reserve"))
"""(clé, lot, kg, qualité) : la réserve va en quarantaine."""


def _entrer(  # noqa: PLR0917 — décor d’essai
    s: Session, w: Monde, r: Reception, cle: str, numero: str, kg: int, qualite: str
) -> None:
    """Une ligne reçue : son lot, sa pesée, son entrée au journal."""
    g = magasin(s, TypeMagasin.quarantaine if qualite == "reserve" else TypeMagasin.stock_courant)
    x = lots.lot_ou_creer(
        s, w.ids["pp"], numero, r.date, fournisseur_id=w.ids["hasirci"], poids_bobine=Decimal("2.5")
    )
    ligne = ajouter(
        s,
        ReceptionLigne(
            reception_id=r.id, commande_ligne_id=w.ids["l1"], matiere_id=w.ids["pp"],
            lot_numero=numero, lot_id=x.id, quantite_attendue=kg, quantite_bl=kg,
            quantite_pesee=kg, nb_bobines=kg / 2.5, nb_palettes=kg / 100, magasin_id=g.id,
            qualite=qualite, prix=Decimal("2.4"), observations="RAS",
        ),
    )  # fmt: skip
    m = stock.ecrire(
        s, type=TypeMouvement.RECEPTION, lot=x, magasin_id=g.id, quantite=kg, jour=r.date,
        piece=stock.Piece(DocumentMouvement.reception, r.id, r.numero or ""),
        auteur_id=w.ids["sara"], prix=Decimal("2.4"), devise="USD", cours=Decimal("9.8"),
    )  # fmt: skip
    w.ids |= {cle: x.id, f"ligne_{cle}": ligne.id}
    w.mouvements[cle] = m.id


def receptions(s: Session, w: Monde) -> None:
    """Une réception validée (conforme, réserve, refus) et une réception en brouillon."""
    facture = ajouter(
        s, Facture(fournisseur_id=w.ids["hasirci"], numero="F-1", devise="USD", montant=2160)
    )
    r = ajouter(
        s,
        Reception(
            numero="REC-2026-0001", statut="validee", date=date(2026, 9, 22),
            fournisseur_id=w.ids["hasirci"], devise="USD", numero_bl="BL-9",
            facture_id=facture.id, cree_par_id=w.ids["karim"], validee_par_id=w.ids["sara"],
            validee_le=instant(2026, 9, 22, 15),
        ),
    )  # fmt: skip
    for cle, numero, kg, qualite in LIGNES_RECUES:
        _entrer(s, w, r, cle, numero, kg, qualite)
    ajouter(
        s,
        ReceptionLigne(
            reception_id=r.id, commande_ligne_id=w.ids["l2"], matiere_id=w.ids["jute"],
            quantite_pesee=50, qualite="refuse",
        ),
    )  # fmt: skip
    b = ajouter(
        s,
        Reception(
            date=date(2026, 9, 30), fournisseur_id=w.ids["local"], devise="MAD",
            controle_par="Nadia",
        ),
    )  # fmt: skip
    ajouter(
        s,
        ReceptionLigne(
            reception_id=b.id, matiere_id=w.ids["cuir"], lot_numero="C-9", quantite_pesee=10,
            quantite_attendue=12,
        ),
    )  # fmt: skip
    w.ids |= {"rec": r.id, "facture": facture.id, "rec_brouillon": b.id}


def _lot(s: Session, w: Monde, cle: str) -> Lot:
    x = s.get(Lot, w.ids[cle])
    assert x is not None
    return x


def _ouverture_et_retour(s: Session, w: Monde) -> None:
    """Le stock d'ouverture de jute ; 50 kg de PP renvoyés au fournisseur."""
    jute = lots.lot_ou_creer(s, w.ids["jute"], "J-1", date(2026, 9, 1))
    w.ids["j1"] = jute.id
    ouv = operation(s, w, TypeOperation.ouverture, "OUV-2026-0001", date(2026, 9, 1))
    ecrire(s, w, "ouverture", jute, 1000, date(2026, 9, 1), ouv, TypeMouvement.OUVERTURE, 12)
    rfo = operation(
        s, w, TypeOperation.retour_fournisseur, "RFO-2026-0001", date(2026, 9, 24),
        fournisseur_id=w.ids["hasirci"],
    )  # fmt: skip
    ecrire(
        s, w, "retour", _lot(s, w, "ppa"), -50, date(2026, 9, 24), rfo,
        TypeMouvement.RETOUR_FOURNISSEUR, motif_id=motif(s, "Non-conformité qualité"),
    )  # fmt: skip


def _ordre(s: Session, w: Monde) -> None:
    """Un ordre au prévu figé, ses deux sorties, son retour des machines."""
    of = ajouter(
        s,
        Ordre(
            numero="OF-2026-0001", statut="valide", date=date(2026, 9, 25),
            magasin_id=magasin(s).id, valide_le=instant(2026, 9, 25, 8), prevu_fige=True,
            taux_perte_fige=Decimal("0.02"),
        ),
    )  # fmt: skip
    s.add(OrdreQualite(ordre_id=of.id, qualite_id=w.ids["8f"], m2=100))
    s.add(OrdrePrevu(ordre_id=of.id, matiere_id=w.ids["pp"], kg_hors_perte=153))
    s.add(OrdrePrevu(ordre_id=of.id, matiere_id=w.ids["jute"], kg_hors_perte=40))
    piece = stock.Piece(DocumentMouvement.ordre, of.id, of.numero or "")
    pp1, jute = _lot(s, w, "ppa"), _lot(s, w, "j1")
    ecrire(s, w, "sortie_pp", pp1, -100, of.date, piece, TypeMouvement.SORTIE)
    ecrire(s, w, "sortie_jute", jute, -40, of.date, piece, TypeMouvement.SORTIE)
    ret = operation(
        s, w, TypeOperation.retour_machine, "RET-2026-0001", date(2026, 9, 26), ordre_id=of.id
    )
    ecrire(
        s, w, "retour_machine", pp1, 10, date(2026, 9, 26), ret, TypeMouvement.RETOUR_MACHINE,
        ordre_id=of.id, motif_id=motif(s, "Reliquat de fin d'ordre"),
    )  # fmt: skip
    w.ids["of"] = of.id


def _liberation_et_ajustement(s: Session, w: Monde) -> None:
    """100 kg libérés de la quarantaine ; un ajustement de jute, puis son annulation."""
    trf = operation(s, w, TypeOperation.transfert, "TRF-2026-0001", date(2026, 9, 27))
    depart, arrivee = stock.transferer(
        s, lot=_lot(s, w, "ppb"), source_id=magasin(s, TypeMagasin.quarantaine).id,
        destination_id=magasin(s).id, quantite=100, jour=date(2026, 9, 27), piece=trf,
        auteur_id=w.ids["sara"], motif_id=motif(s, "Libération de quarantaine"),
    )  # fmt: skip
    aju = operation(
        s, w, TypeOperation.ajustement, "AJU-2026-0001", date(2026, 9, 28),
        commentaire="Matière retrouvée au fond",
    )  # fmt: skip
    ecrire(
        s, w, "ajustement", _lot(s, w, "j1"), 5, date(2026, 9, 28), aju, TypeMouvement.AJUSTEMENT
    )
    stock.contrepasser(s, aju, w.ids["sara"])
    annulation = s.scalars(
        select(Mouvement.id).where(Mouvement.contrepasse_id == w.mouvements["ajustement"])
    ).one()
    w.mouvements |= {"depart": depart.id, "arrivee": arrivee.id, "annulation": annulation}


def flux(s: Session, w: Monde) -> None:
    """Ouverture, retour au fournisseur, ordre et son retour, libération, ajustement annulé."""
    _ouverture_et_retour(s, w)
    _ordre(s, w)
    _liberation_et_ajustement(s, w)


def dossiers(s: Session, w: Monde) -> None:
    """Un dossier ouvert (marchandise, droits à part figée, fret rattaché) et un annulé."""
    postes = {p.code: p.id for p in s.scalars(select(PosteFrais))}
    d = ajouter(
        s,
        Dossier(
            numero="01/26", annee=2026, rang=1, libelle="Fil turc", date_arrivee=date(2026, 9, 21),
            banque="BMCE", commentaire="Premier",
        ),
    )  # fmt: skip
    ajouter(s, DossierFacture(dossier_id=d.id, facture_id=w.ids["facture"]))
    ligne = ajouter(
        s,
        DossierLigne(
            dossier_id=d.id, reception_ligne_id=w.ids["ligne_ppa"], matiere_id=w.ids["pp"],
            lot_id=w.ids["ppa"], fournisseur_id=w.ids["hasirci"], quantite_kg=600,
            valeur_devise=1440, devise="USD", cours=Decimal("9.8"), cours_origine=OrigineCours.bon,
        ),
    )  # fmt: skip
    dd = ajouter(
        s, DossierFrais(dossier_id=d.id, poste_id=postes["DD"], montant=3000, piece="DD-1")
    )
    s.add(
        DossierFraisPart(frais_id=dd.id, ligne_id=ligne.id, montant=3000, origine="changement_cle")
    )
    ajouter(
        s,
        DossierFrais(
            dossier_id=d.id, poste_id=postes["FRET"], montant=1200, ligne_id=ligne.id,
            commentaire="Camion",
        ),
    )  # fmt: skip
    ajouter(
        s,
        Dossier(
            numero="ANC-1", saisi_a_la_main=True, statut="annule", annule_le=instant(2026, 9, 30),
            libelle="Annulé",
        ),
    )  # fmt: skip
    w.ids |= {"dossier": d.id, "dossier_ligne": ligne.id}


def metiers(s: Session, w: Monde) -> None:
    """Un métier monté (PP Rouge sur l'étage 1), un métier arrêté."""
    metier = ajouter(
        s, Metier(code="CRM 1", nom="Métier 1", laize=Decimal("4.2"), bobines_par_metre=320)
    )
    ajouter(s, MetierEtage(metier_id=metier.id, etage=1))
    s.add(Montage(metier_id=metier.id, etage=1, matiere_id=w.ids["pp"], metres=4, pourcentage=60))
    ajouter(s, Metier(code="CRM 2", nom="Métier 2", actif=False))
