"""Extraire les sorties du moteur de Gestion MP, en lecture seule (lot C1 ; ARCHITECTURE § 14.3).

Lancé par l'interpréteur de Gestion MP (`~/gestion-mp/.venv/bin/python`), sur son code en
lecture seule, pour le **mode « moteurs »** du comparateur :

    ~/gestion-mp/.venv/bin/python outils/gestion_mp_extraire.py donnees <url_copie> <sortie.json>
    ~/gestion-mp/.venv/bin/python outils/gestion_mp_extraire.py sorties <aujourdhui> <d1,d2,…> \\
        <dossier> <jeu.json>…

C'est l'outil d'extraction côté Gestion MP du lot C1. Il délègue à `essais/gestion_mp_parite.py`
(outil frère, déjà éprouvé par R2 : `donnees` fige les `Donnees` chargées de la copie, `sorties`
rejoue chaque date avec le moteur de Gestion MP) ; la connexion est en lecture seule
(`default_transaction_read_only=on`), aucune écriture dans `gestion_mp`. Le comparateur
l'appelle par l'intermédiaire de `parite_statique`, qui le pilote pour PRO en miroir.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

ESSAIS = Path(__file__).resolve().parents[1] / "backend" / "essais"


def main(arguments: list[str] | None = None) -> int:
    """Rejoue l'extraction de `gestion_mp_parite.py` (donnees / sorties), en lecture seule."""
    args = list(sys.argv[1:] if arguments is None else arguments)
    if not args or args[0] not in ("donnees", "sorties"):
        sys.stderr.write(__doc__ or "")
        return 2
    sys.argv = [str(ESSAIS / "gestion_mp_parite.py"), *args]
    sys.path.insert(0, str(ESSAIS))
    runpy.run_path(str(ESSAIS / "gestion_mp_parite.py"), run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main())
