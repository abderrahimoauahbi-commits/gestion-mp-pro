"""Noms de fichiers venus de l'extérieur (adresse demandée, membre d'une archive) : contrôle
lexical, avant tout accès au disque (lot Windows, docs/lots/WINDOWS-SERVEUR.md).

Sous Windows, `Path(racine) / nom` **remplace** la racine quand `nom` porte un lecteur (`C:`),
une racine (`\\`) ou un partage réseau (`\\\\serveur\\partage`) ; rien qu'interroger ce chemin
(`is_file`, `resolve`) ouvrirait alors une connexion vers un serveur choisi par l'appelant. Un
`:` désigne aussi un flux caché d'un fichier NTFS. Le contrôle vaut pour les deux systèmes à la
fois : un nom refusé sur le Mac l'est aussi sur le serveur Windows, et l'essai tourne partout.
"""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath


def relatif_sur(nom: str) -> bool:
    """Le nom est-il un chemin relatif simple (ni lecteur, ni racine, ni partage, ni `:`) ?"""
    if not nom or ":" in nom or "\x00" in nom:
        return False
    return not (PurePosixPath(nom).anchor or PureWindowsPath(nom).anchor)
