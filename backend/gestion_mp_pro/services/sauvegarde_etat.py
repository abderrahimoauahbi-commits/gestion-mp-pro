"""État et alerte des sauvegardes de **cette** base (G-06), recalage du registre sur le disque.

Alerte, par priorité (reprise de Gestion MP, X7–X8, lue dans l'état partagé des tâches) :
« Les sauvegardes sont arrêtées : pg_dump est introuvable sur le serveur. » ; « La sauvegarde
automatique a échoué : … » ; « Aucune sauvegarde récente. » (plus de 26 h, ou aucune, après un
premier passage de la tâche) ; « Aucune sauvegarde de la base « X » : le dossier ne contient que
d'autres bases. ». Elle est surveillée dès que ce serveur porte des tâches
(`GESTIONMPPRO_TACHES=1`) ou que la tâche a déjà tourné sur cette base.

Importer ce module inscrit l'alerte au bandeau rouge de la direction et de l'administrateur
(`services.contexte.ALERTES_SERVEUR`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.modeles.enums import ObjetJournal
from gestion_mp_pro.services import audit, execution, horloge
from gestion_mp_pro.services import sauvegarde_outils as o
from gestion_mp_pro.services import sauvegarde_registre as registre
from gestion_mp_pro.services.contexte import ALERTES_SERVEUR
from gestion_mp_pro.services.sauvegarde import (
    ALERTE_HEURES,
    FICHIERS_LISTES,
    POLITIQUE,
    FichierSauvegarde,
    dossier,
    dossier_copie,
    lister,
    sauvegarder,
)

ARRETEES = "Les sauvegardes sont arrêtées : pg_dump est introuvable sur le serveur."
AUCUNE_RECENTE = "Aucune sauvegarde récente."


@dataclass(frozen=True)
class EtatSauvegardes:
    """L'état des sauvegardes de cette base (route 43, `/api/sante`, bandeau)."""

    base: str
    derniere: datetime | None
    age_h: float | None
    alerte: str | None
    politique: str
    dossier: str
    copie: str | None
    nb: int
    autres: int
    outils: bool
    fichiers: list[FichierSauvegarde]


def _alerte(
    s: Session, derniere: datetime | None, age_h: float | None, seulement_autres: bool
) -> str | None:
    """L'alerte des sauvegardes (voir le module), ou `None`."""
    tache = execution.lire(s, "sauvegarde")
    surveillee = reglages().taches or tache is not None
    if not surveillee:
        return None
    if o.outil("pg_dump") is None:
        return ARRETEES
    if tache is not None and tache.erreur:
        return f"La sauvegarde automatique a échoué : {tache.erreur}"
    if tache is not None and (derniere is None or (age_h or 0) > ALERTE_HEURES):
        return AUCUNE_RECENTE
    if seulement_autres:
        return (
            f"Aucune sauvegarde de la base « {reglages().nom_base} » : le dossier ne contient "
            "que d'autres bases."
        )
    return None


def etat(s: Session, nb_fichiers: int = FICHIERS_LISTES) -> EtatSauvegardes:
    """L'état des sauvegardes : seules celles de cette base comptent (nombre, dernière, âge)."""
    fichiers = lister(s)
    ici = [f for f in fichiers if not f.autre_base]
    derniere = max((f.quand for f in ici), default=None)
    age_h = None
    if derniere is not None:
        age_h = round((horloge.maintenant() - derniere).total_seconds() / 3600, 2)
    copie = dossier_copie()
    return EtatSauvegardes(
        base=reglages().nom_base,
        derniere=derniere,
        age_h=age_h,
        alerte=_alerte(s, derniere, age_h, bool(fichiers) and not ici),
        politique=POLITIQUE,
        dossier=str(dossier()),
        copie=str(copie) if copie is not None else None,
        nb=len(ici),
        autres=len(fichiers) - len(ici),
        outils=o.outil("pg_dump") is not None and o.outil("pg_restore") is not None,
        fichiers=fichiers[:nb_fichiers],
    )


def alerte_serveur(s: Session) -> str | None:
    """L'alerte des sauvegardes pour le bandeau rouge (direction, administrateur)."""
    return etat(s, nb_fichiers=0).alerte


def recaler(s: Session) -> int:
    """Ajoute au registre les fichiers de cette base qu'il ne connaît pas ; rend leur nombre."""
    connus = registre.lire(s)
    ajoutes = 0
    for f in lister(s):
        if f.autre_base or f.nom in connus:
            continue
        registre.enregistrer(
            s,
            registre.Entree(
                fichier=f.nom,
                genre=f.genre,
                base=f.base,
                taille=f.taille,
                tables=f.tables or 0,
                pieces_incluses=f.pieces,
                copie_externe=f.copie,
                cree_le=f.quand,
            ),
        )
        ajoutes += 1
    return ajoutes


def sauvegarde_manuelle(s: Session, qui: audit.Qui) -> EtatSauvegardes:
    """« Sauvegarder maintenant » (route 44) : la sauvegarde, sa ligne au journal, l'état."""
    fichier = sauvegarder("manuelle", par_id=qui.id)
    audit.journal(s, qui, "sauvegarde", ObjetJournal.sauvegarde, detail=fichier.nom)
    return etat(s)


def _fichier(nom: str) -> Path:
    """Le fichier nommé, dans le dossier de cette base seulement (pas de remontée de dossier)."""
    fichier = dossier() / Path(nom).name
    if not fichier.is_file() or o.lire_nom(fichier.name) is None:
        raise Refus.introuvable("Sauvegarde introuvable.")
    return fichier


def supprimer(s: Session, qui: audit.Qui, nom: str) -> EtatSauvegardes:
    """Supprimer une sauvegarde (demande de Mohamed, 15/10/2026) : le fichier et ses pièces.

    La plus récente de cette base se garde toujours (il en reste au moins une à jour) ; rien ne
    s'efface pendant une restauration ; la copie de sécurité, elle, n'est pas touchée. Journal
    « sauvegarde supprimée ».
    """
    from gestion_mp_pro.services import restauration

    fichier = _fichier(nom)
    ici = [f for f in lister(s) if not f.autre_base]
    if ici and ici[0].nom == fichier.name:
        raise Refus.etat(
            "C'est la sauvegarde la plus récente de cette base : elle se garde. "
            "Supprimer une plus ancienne.",
            code="derniere_sauvegarde",
        )
    verrou = restauration._prendre_le_verrou()
    try:
        fichier.unlink(missing_ok=True)
        o.archive_de(fichier).unlink(missing_ok=True)
    finally:
        restauration._rendre_le_verrou(verrou)
    registre.oublier(s, [fichier.name])
    audit.journal(s, qui, "sauvegarde supprimée", ObjetJournal.sauvegarde, detail=fichier.name)
    return etat(s)


if alerte_serveur not in ALERTES_SERVEUR:
    ALERTES_SERVEUR.append(alerte_serveur)
