"""Le journal du moteur que le chargeur doit lire de la petite usine (lot S4) : quantités
positives, signe porté par le type, un transfert en une ligne, l'annulation en négatif
(CALCULS A § 4.7)."""

from __future__ import annotations

from datetime import date, datetime

from fabriques.moteur_base import Monde

from gestion_mp_pro.calcul import modele as c

PRINCIPAL, QUARANTAINE = "Magasin principal", "Quarantaine"
OUVERTURE = date(2026, 9, 1)
RECU, SORTI = date(2026, 9, 22), date(2026, 9, 25)
KARIM, SARA = "Karim — magasin", "Sara"
OF = "OF-2026-0001"


def heure(*champs: int) -> datetime:
    """Un instant du moteur : heure de l'usine, sans fuseau (comme Gestion MP)."""
    return datetime(*champs)  # noqa: DTZ001


def _ligne(  # noqa: PLR0913, PLR0917 — une ligne du journal attendu
    w: Monde,
    cle: str,
    jour: date,
    type_: str,
    ref: str,
    kg: float,
    lot: str,
    doc: str,
    qui: str,
    **champs: object,
) -> c.Mouvement:
    """Une écriture du journal du moteur ; `fournisseur` HASIRCI pour le PP (celui du lot)."""
    prix = float(champs.pop("prix_unite", 0.0))  # type: ignore[arg-type]
    if ref == "PP Rouge":
        champs.setdefault("fournisseur", "HASIRCI")
    return c.Mouvement(
        date=jour, type=type_, reference=ref, quantite=kg, prix_unite=prix,
        total_devise=kg * prix, reference_doc=doc, lot_fournisseur=lot, utilisateur=qui,
        id=w.mouvements[cle], **champs,  # type: ignore[arg-type]
    )  # fmt: skip


def _entrees(w: Monde) -> list[c.Mouvement]:
    """Ouverture, réception (conforme, réserve en quarantaine), retour au fournisseur."""
    rec = "REC-2026-0001"
    return [
        _ligne(w, "ouverture", OUVERTURE, "STOCK_INITIAL", "Jute", 1000, "J-1", "OUV-2026-0001",
               KARIM, prix_unite=12, magasin_destination=PRINCIPAL),
        _ligne(w, "ppa", RECU, "ENTREE_RECEPTION", "PP Rouge", 600, "L-PP1", rec, SARA,
               prix_unite=2.4, devise="USD", magasin_destination=PRINCIPAL, cours=9.8,
               ligne_reception_id=w.ids["ligne_ppa"]),
        _ligne(w, "ppb", RECU, "ENTREE_RECEPTION", "PP Rouge", 300, "L-PP2", rec, SARA,
               prix_unite=2.4, devise="USD", magasin_destination=QUARANTAINE, cours=9.8,
               ligne_reception_id=w.ids["ligne_ppb"]),
        _ligne(w, "retour", date(2026, 9, 24), "RETOUR_FOURNISSEUR", "PP Rouge", 50, "L-PP1",
               "RFO-2026-0001", KARIM, motif_retour="R3", magasin_source=PRINCIPAL),
    ]  # fmt: skip


def _suite(w: Monde) -> list[c.Mouvement]:
    """Sorties de l'ordre, retour des machines, libération, ajustement et son annulation."""
    aju = "AJU-2026-0001"
    return [
        _ligne(w, "sortie_pp", SORTI, "SORTIE_PROD", "PP Rouge", 100, "L-PP1", OF, KARIM,
               numero_of=OF, magasin_source=PRINCIPAL),
        _ligne(w, "sortie_jute", SORTI, "SORTIE_PROD", "Jute", 40, "J-1", OF, KARIM,
               numero_of=OF, magasin_source=PRINCIPAL),
        _ligne(w, "retour_machine", date(2026, 9, 26), "RETOUR_PRODUCTION", "PP Rouge", 10,
               "L-PP1", "RET-2026-0001", KARIM, numero_of=OF, motif_retour="R1",
               magasin_destination=PRINCIPAL),
        _ligne(w, "depart", date(2026, 9, 27), "TRANSFERT_MAGASIN", "PP Rouge", 100, "L-PP2",
               "TRF-2026-0001", SARA, magasin_source=QUARANTAINE, magasin_destination=PRINCIPAL),
        _ligne(w, "ajustement", date(2026, 9, 28), "AJUSTEMENT_INVENTAIRE", "Jute", 5, "J-1", aju,
               KARIM, magasin_destination=PRINCIPAL),
        _ligne(w, "annulation", date(2026, 9, 28), "AJUSTEMENT_INVENTAIRE", "Jute", -5, "J-1",
               aju, SARA, magasin_destination=PRINCIPAL,
               contrepasse_id=w.mouvements["ajustement"]),
    ]  # fmt: skip


def journal(w: Monde) -> list[c.Mouvement]:
    """Le journal attendu, dans l'ordre (date d'effet, numéro)."""
    return [*_entrees(w), *_suite(w)]
