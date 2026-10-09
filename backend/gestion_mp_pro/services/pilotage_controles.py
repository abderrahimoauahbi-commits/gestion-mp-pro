"""Les contrôles de cohérence (routes 212, 216, 235) et les pastilles du menu (route 3).

Les 38 contrôles du moteur (`calcul.controles`), rejoués au soir de la date : les données à
la date (fil monté compris), l'intégrité sur **toutes** les données (C12, C14, C27, C37), le
futur jugé à aujourd'hui. Chaque ligne du détail reçoit l'identifiant des fiches qu'elle nomme
(matière, lot, ordre, métier, bon, dossier, réception, qualité, fournisseur) : l'écran ouvre la
fiche par son id, plus par une recherche de texte. La liste (212) rend les 200 premières lignes
de chaque contrôle en le disant ; le détail (235) les rend toutes, cherchées et paginées.

Pastilles (`contexte.COMPTEURS`) : `alerte_rouge` = matières en rupture ou critiques (H-07,
direction, achats, alimentation) ; `anomalies` = contrôles à corriger, ceux « pour
information » à part (E-08 : `a_corriger`, direction et achats).
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul.controles import Colonne, Controle, Ligne, Synthese, controler, synthese
from gestion_mp_pro.modeles import (
    Commande,
    Dossier,
    Lot,
    Matiere,
    Metier,
    Ordre,
    Qualite,
    Reception,
)
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.services import contexte, courriel_contenu, donnees_moteur, horloge, pilotage
from gestion_mp_pro.services.pilotage import alerte_rouge, ids_fournisseurs, ids_matieres, lire

LIGNES_DE_LA_LISTE = 200
"""La liste des contrôles rend les 200 premières lignes de chacun (le détail les rend toutes)."""
VOIENT_LES_CONTROLES = frozenset({Role.direction, Role.achats})
VOIENT_L_ALERTE = frozenset({Role.direction, Role.achats, Role.alimentation})


@dataclass
class ControleLu:
    """Un contrôle tel que la route le rend."""

    code: str
    libelle: str
    gravite: str
    garanti: str
    anomalies: int
    conforme: bool
    quoi_faire: str
    lien: str
    colonnes: list[Colonne]
    lignes: list[Ligne] = field(default_factory=list)
    lignes_total: int = 0
    tronque: bool = False


@dataclass
class Controles:
    """La synthèse et les 38 contrôles au soir d'une date."""

    date_reference: date
    synthese: Synthese
    controles: list[ControleLu]


def rejouer(s: Session, jour: date) -> list[Controle]:
    """Les 38 contrôles au soir de `jour` (intégrité sur toutes les données), rejoués une
    fois tant que la base n'a pas changé (`donnees_moteur.deriver`)."""

    def _calcul() -> list[Controle]:
        lecture = lire(s, jour)
        complet = donnees_moteur.charger(s)
        return controler(
            lecture.donnees, lecture.lignes, jour, complet=complet, aujourdhui=horloge.aujourd_hui()
        )

    return donnees_moteur.deriver(s, "controles", (jour,), _calcul)


Index = dict[str, Callable[[Ligne], int | None]]


def _index(s: Session) -> Index:
    """Pour chaque clé du détail, la façon d'en tirer l'id de la fiche (une requête par table)."""
    matieres = ids_matieres(s)
    fournisseurs = ids_fournisseurs(s)
    lots = {
        (ref, num): i
        for ref, num, i in s.execute(
            select(Matiere.reference, Lot.numero, Lot.id).join(
                Matiere, Matiere.id == Lot.matiere_id
            )
        )
    }

    def par(
        modele: type[Ordre] | type[Commande] | type[Reception] | type[Dossier],
    ) -> dict[str, int]:
        """Numéro → id des documents numérotés de ce modèle."""
        requete = select(modele.numero, modele.id).where(modele.numero.is_not(None))
        return {str(n): i for n, i in s.execute(requete)}

    ordres, bons, receptions, dossiers = par(Ordre), par(Commande), par(Reception), par(Dossier)
    metiers = dict(s.execute(select(Metier.code, Metier.id)).all())
    qualites = dict(s.execute(select(Qualite.code, Qualite.id)).all())
    return {
        "matiere_id": lambda x: matieres.get(str(x.get("reference") or "")),
        "lot_id": lambda x: lots.get((str(x.get("reference") or ""), str(x.get("lot") or ""))),
        "ordre_id": lambda x: ordres.get(str(x.get("numero_of") or "")),
        "metier_id": lambda x: metiers.get(str(x.get("metier") or "")),
        "commande_id": lambda x: bons.get(str(x.get("numero") or "")),
        "dossier_id": lambda x: dossiers.get(str(x.get("dossier") or "")),
        "reception_id": lambda x: receptions.get(str(x.get("reception") or "")),
        "qualite_id": lambda x: qualites.get(str(x.get("qualite") or "")),
        "fournisseur_id": lambda x: fournisseurs.get(str(x.get("fournisseur") or "")),
    }


def _avec_ids(lignes: list[Ligne], index: Index) -> list[Ligne]:
    """Les lignes du détail, complétées des ids des fiches nommées (absentes : non posées)."""
    resultat = []
    for x in lignes:
        ids = {cle: trouve for cle, lire_id in index.items() if (trouve := lire_id(x)) is not None}
        resultat.append({**x, **ids})
    return resultat


def _lu(c: Controle, lignes: list[Ligne], total: int) -> ControleLu:
    return ControleLu(
        code=c.code,
        libelle=c.libelle,
        gravite=c.gravite,
        garanti=c.garanti,
        anomalies=c.anomalies,
        conforme=c.conforme,
        quoi_faire=c.quoi_faire,
        lien=c.lien,
        colonnes=c.colonnes,
        lignes=lignes,
        lignes_total=total,
        tronque=total > len(lignes),
    )


def controles(s: Session, jour: date) -> Controles:
    """Route 212 : la synthèse et chaque contrôle avec ses 200 premières lignes."""
    rejoues = rejouer(s, jour)
    index = _index(s)
    return Controles(
        date_reference=jour,
        synthese=synthese(rejoues),
        controles=[
            _lu(c, _avec_ids(c.detail[:LIGNES_DE_LA_LISTE], index), len(c.detail)) for c in rejoues
        ],
    )


def _texte(x: Ligne) -> str:
    return normaliser(" ".join(str(v) for v in x.values() if v is not None))


def detail(s: Session, jour: date, code: str, q: str = "") -> tuple[ControleLu, list[Ligne]]:
    """Route 235 : un contrôle et **toutes** ses lignes, cherchées sur tous les mots (sans
    accents) ; 404 pour un code inconnu."""
    rejoues = {c.code: c for c in rejouer(s, jour)}
    c = rejoues.get(code.strip().upper())
    if c is None:
        raise Refus.introuvable(f"Contrôle inconnu : {code}.")
    mots = normaliser(q).split()
    lignes = [x for x in c.detail if all(m in _texte(x) for m in mots)]
    return _lu(c, [], len(lignes)), _avec_ids(lignes, _index(s))


def cockpit(s: Session, jour: date) -> dict[str, Any]:
    """Route 209 : le Cockpit, avec la note des contrôles et les bons en retard (la règle de
    l'écran Commandes et du courriel du lundi)."""

    def _calcul() -> dict[str, Any]:
        retards = courriel_contenu.retards(s, donnees_moteur.charger_au(s, jour), jour)
        return pilotage.cockpit(s, jour, synthese(rejouer(s, jour)), len(retards))

    return deepcopy(donnees_moteur.deriver(s, "cockpit", (jour,), _calcul))


# ── Pastilles du menu ────────────────────────────────────────────────────────────────


def compteur_alerte_rouge(s: Session, role: str) -> int | None:
    """Matières en rupture ou critiques, aujourd'hui (direction, achats, alimentation)."""
    if role not in VOIENT_L_ALERTE:
        return None
    return alerte_rouge(lire(s, horloge.aujourd_hui()).lignes)


def compteur_anomalies(s: Session, role: str) -> int | None:
    """Contrôles à corriger aujourd'hui, hors information (direction et achats)."""
    if role not in VOIENT_LES_CONTROLES:
        return None
    return synthese(rejouer(s, horloge.aujourd_hui())).a_corriger


contexte.COMPTEURS["alerte_rouge"] = compteur_alerte_rouge
contexte.COMPTEURS["anomalies"] = compteur_anomalies
