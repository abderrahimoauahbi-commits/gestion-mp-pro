"""`python -m gestion_mp_pro.securite matrice` : la matrice des droits en CSV sur la sortie.

`make matrice` l'écrit dans `backend/tests/matrice_droits.csv` (jamais édité à la main).
"""

from __future__ import annotations

import sys

from gestion_mp_pro.securite.matrice import en_csv, matrice


def principal(arguments: list[str]) -> int:
    """Écrit la matrice ; code 2 si la commande est inconnue."""
    if arguments != ["matrice"]:
        sys.stderr.write("usage : python -m gestion_mp_pro.securite matrice\n")
        return 2
    from gestion_mp_pro.main import creer_application

    sys.stdout.write(en_csv(matrice(creer_application())))
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
