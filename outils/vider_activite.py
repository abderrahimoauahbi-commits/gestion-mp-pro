"""Vide l'activité d'une base de Gestion MP PRO en gardant **intacts** tous les référentiels.

    GESTIONMPPRO_BASE=postgresql+psycopg:///gestion_mp_pro \\
        backend/.venv/bin/python outils/vider_activite.py --oui-vider-l-activite

Pour la mise en service : l'année d'essai (ou le miroir de Gestion MP) part, les référentiels
réels restent. Arrêter le serveur d'abord (le vidage verrouille les tables d'activité).

Ce qui part : les 31 tables marquées `__activite__` dans les modèles (bons, factures,
réceptions, réclamations, lots, stock et mouvements, ordres, opérations, inventaires, dossiers
et leurs frais, besoins signalés, photos des indicateurs, notifications, compteurs) et les
pièces jointes de ces documents (la ligne ; le fichier reste dans le dossier des pièces).
Ce qui reste, intact (empreinte vérifiée avant et après, sinon tout est annulé) : comptes,
réglages et leur historique, devises et cours, classification, fournisseurs, matières,
qualités, recettes et leurs versions, plans versionnés, magasins, métiers, étages et fils
montés, postes de frais, codes douaniers, motifs, pièces des matières et des fournisseurs ;
le journal (qui reçoit une ligne « activité vidée »), les sessions, les sauvegardes.

1. Sauvegarde complète d'abord (« avant vidage », jamais purgée), relue ; sans elle, rien n'est
   fait.
2. Un seul `TRUNCATE` de toutes les tables d'activité (leçon de G-01 : aucune clé étrangère ne
   peut l'arrêter à mi-chemin), sans remise à 1 des identifiants.
3. Les correspondances de la reprise vers l'activité sont oubliées (une reprise suivante
   réécrit l'activité de zéro).
4. La base vide qui en résulte est sauvegardée comme **base vide de référence**.
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import Verrou, verrouiller
from gestion_mp_pro.modeles import tables_d_activite
from gestion_mp_pro.modeles.enums import GenreSauvegarde, ObjetJournal
from gestion_mp_pro.reprise import sauvegarde, vidage
from gestion_mp_pro.reprise.execution import RepriseRefusee, cible_permise

journal = logging.getLogger("vider_activite")
CONFIRMATION = "--oui-vider-l-activite"


def vider_la_base(url: str, sauvegarder: bool = True) -> dict[str, int]:
    """Sauvegarde, vide l'activité, sauvegarde la base vide ; rend les lignes retirées."""
    nom = cible_permise(url)
    avant = sauvegarde.sauvegarder(url, GenreSauvegarde.avant_vidage) if sauvegarder else None
    moteur = create_engine(url, poolclass=NullPool)
    with moteur.connect() as c, c.begin():
        verrouiller(c, Verrou.REPRISE)
        if avant:
            sauvegarde.inscrire(c, avant, GenreSauvegarde.avant_vidage, nom)
        retirees = vidage.vider(c)
        c.execute(
            text(
                "DELETE FROM reprise_correspondance WHERE table_cible = ANY(:t)"
                " OR (table_cible = 'piece_jointe' AND id_cible NOT IN"
                " (SELECT id FROM piece_jointe))"
            ),
            {"t": tables_d_activite()},
        )
        detail = ", ".join(f"{t} {n}" for t, n in sorted(retirees.items()) if n)
        c.execute(
            text(
                "INSERT INTO journal (utilisateur_nom, action, objet, detail)"
                " VALUES ('outil', 'activité vidée', :o, :d)"
            ),
            {"o": ObjetJournal.systeme.value, "d": f"lignes retirées : {detail}"[:2000]},
        )
    if sauvegarder:
        vide = sauvegarde.sauvegarder(url, GenreSauvegarde.reference_vide)
        with moteur.connect() as c, c.begin():
            sauvegarde.inscrire(c, vide, GenreSauvegarde.reference_vide, nom)
    moteur.dispose()
    return retirees


def main(arguments: list[str] | None = None) -> int:
    """Ligne de commande : rien n'est fait sans la confirmation explicite."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument(CONFIRMATION, dest="oui", action="store_true", help="confirme le vidage")
    p.add_argument("--base", default=reglages().base, help="défaut : GESTIONMPPRO_BASE")
    a = p.parse_args(arguments)
    if not a.oui:
        journal.info("Rien n'a été fait : ajouter %s pour confirmer.", CONFIRMATION)
        return 2
    try:
        retirees = vider_la_base(a.base)
    except (RepriseRefusee, sauvegarde.SauvegardeImpossible, vidage.ReferentielModifie) as exc:
        journal.error("Vidage refusé : %s", exc)
        return 1
    base = make_url(a.base).database
    journal.info("Activité de %s vidée : %s lignes retirées.", base, sum(retirees.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
