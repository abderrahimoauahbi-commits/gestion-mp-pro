"""`python -m gestion_mp_pro.reprise` : la reprise rejouable depuis la base de Gestion MP.

    python -m gestion_mp_pro.reprise --source postgresql+psycopg:///gestion_mp \\
        --mode referentiels|activite|tout [--remplacer-activite] [--mettre-a-jour] [--essai]

La cible est `GESTIONMPPRO_BASE` (ou `--cible`) ; la source n'est lue qu'en lecture seule.
Code de sortie : 0 reprise réussie ; 1 contrôle non tenu ; 2 reprise refusée (rien n'est écrit).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from gestion_mp_pro.config import reglages
from gestion_mp_pro.modeles.enums import ModeReprise, SourceReprise
from gestion_mp_pro.reprise.activite import ActiviteRefusee
from gestion_mp_pro.reprise.contexte import Options
from gestion_mp_pro.reprise.etapes import ReferentielsAbsents
from gestion_mp_pro.reprise.execution import RepriseRefusee, executer
from gestion_mp_pro.reprise.sauvegarde import SauvegardeImpossible
from gestion_mp_pro.reprise.source import SourceRefusee, nom_de_base

journal = logging.getLogger("gestion_mp_pro.reprise")
REFUS = (ActiviteRefusee, ReferentielsAbsents, RepriseRefusee, SauvegardeImpossible, SourceRefusee)


def lire_options(arguments: list[str] | None = None) -> Options:
    """Les options de la ligne de commande (défauts : variables GESTIONMPPRO_*)."""
    r = reglages()
    p = argparse.ArgumentParser(prog="python -m gestion_mp_pro.reprise", description=__doc__)
    p.add_argument(
        "--source", default=r.source_gestion_mp, help="base de Gestion MP (lue seulement)"
    )
    p.add_argument(
        "--cible", default=r.base, help="base de PRO (gestion_mp_pro ou gestion_mp_pro_*)"
    )
    p.add_argument("--mode", choices=[m.value for m in ModeReprise], default=ModeReprise.tout.value)
    p.add_argument(
        "--remplacer-activite", action="store_true", help="remplace une activité saisie dans PRO"
    )
    p.add_argument(
        "--mettre-a-jour", action="store_true", help="écrase une fiche modifiée dans PRO"
    )
    p.add_argument("--essai", action="store_true", help="à blanc : tout est fait puis annulé")
    p.add_argument("--genre", choices=[g.value for g in SourceReprise], help="défaut : détecté")
    p.add_argument("--pieces-source", help="dossier des pièces de Gestion MP de cette base")
    p.add_argument("--sans-sauvegarde", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--rapport", help="écrit aussi le rapport dans ce fichier")
    a = p.parse_args(arguments)
    base_source = nom_de_base(a.source)
    return Options(
        source=a.source,
        cible=a.cible,
        mode=ModeReprise(a.mode),
        remplacer_activite=a.remplacer_activite,
        mettre_a_jour=a.mettre_a_jour,
        essai=a.essai,
        genre=SourceReprise(a.genre) if a.genre else None,
        sauvegarder=not a.sans_sauvegarde,
        rapport=a.rapport,
        pieces_source=a.pieces_source or str(r.pieces_gestion_mp / base_source),
        pieces_cible=str(r.pieces / (nom_de_base(a.cible) or "gestion_mp_pro")),
    )


def main(arguments: list[str] | None = None) -> int:
    """Lance la reprise, écrit le rapport sur la sortie (et dans un fichier si demandé)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    options = lire_options(arguments)
    try:
        resultat = executer(options)
    except REFUS as exc:
        journal.error("Reprise refusée : %s", exc)
        return 2
    if options.rapport:
        Path(options.rapport).write_text(resultat.rapport, encoding="utf-8")
    journal.info("%s", resultat.rapport)
    return 0 if resultat.reussie else 1


if __name__ == "__main__":
    sys.exit(main())
