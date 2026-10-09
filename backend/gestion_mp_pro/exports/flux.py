"""Export d'un classeur en **flux** (`StreamingResponse`), pour les listes qui lisent tout
l'historique (route 106, le journal du stock, V4 § 6 : 313 000 lignes à ×30).

Le classeur ordinaire (`exports/classeur.py`) bâtit tout le tableau de valeurs **puis** tout le
classeur en mémoire ; à très gros volume il gardait l'historique entier deux fois. Ici, les
lignes sont consommées **une à une** (générateur paresseux depuis un curseur de base) et écrites
au fil de l'eau par `openpyxl` en mode `write_only`, puis le classeur part en flux depuis un
fichier temporaire : la mémoire reste bornée (aucune liste de toutes les lignes, aucun graphe de
cellules complet). Les conventions du classeur sont gardées : en-tête en gras sur fond gris, volet
figé, filtre automatique, vraies dates, formats des grandeurs, texte « dangereux » gardé en
texte, et **aucun prix** pour qui ne les voit pas (barrière 4).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Iterator
from tempfile import NamedTemporaryFile

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Border
from openpyxl.utils import get_column_letter
from starlette.responses import StreamingResponse

from gestion_mp_pro.exports.classeur import (
    COLONNES_AVANT_VOLET,
    FOND_ENTETE,
    FORMATS,
    GRAS,
    LARGEUR_MAX,
    TRAIT,
    TYPE_XLSX,
    Colonne,
    cellule,
    colonnes_permises,
    nom_de_fichier,
)
from gestion_mp_pro.exports.classeur import _format as format_colonne
from gestion_mp_pro.services.horloge import aujourd_hui

TAILLE_LOT = 64 * 1024
"""Les morceaux lus du fichier temporaire pour le flux (mémoire bornée côté serveur)."""


def _largeur(colonne: Colonne) -> float:
    """Largeur fixe (en flux, on ne relit pas les valeurs) : la largeur dite, sinon le titre."""
    if colonne.largeur is not None:
        return colonne.largeur
    fmt = format_colonne(colonne)
    if fmt in (FORMATS["date"], FORMATS["horodatage"]):
        return 12 if fmt == FORMATS["date"] else 17
    return min(LARGEUR_MAX, max(len(colonne.titre) * 0.9, 8) + 2)


def _cellule_entete(ws: object, titre: str) -> WriteOnlyCell:
    """Une cellule d'en-tête : gras, fond gris, trait du bas, texte centré et replié."""
    c = WriteOnlyCell(ws, value=titre)  # type: ignore[arg-type]
    c.font, c.fill, c.border = GRAS, FOND_ENTETE, Border(bottom=TRAIT)
    c.alignment = Alignment(vertical="center", wrap_text=True)
    return c


def _cellule_valeur(ws: object, valeur: object, fmt: str) -> WriteOnlyCell:
    """Une cellule de donnée : valeur sûre, format de la grandeur, formule gardée en texte."""
    c = WriteOnlyCell(ws, value=cellule(valeur))  # type: ignore[arg-type]
    if isinstance(c.value, str) and c.value[:1] in ("=", "+", "-", "@"):
        c.data_type = "s"
    elif fmt and isinstance(c.value, int | float) and not isinstance(c.value, bool):
        c.number_format = fmt
    elif fmt and hasattr(c.value, "year"):  # date / datetime
        c.number_format = fmt
    return c


def _ecrire(wb: Workbook, titre: str, colonnes: list[Colonne], lignes: Iterable[object]) -> None:
    """Écrit la feuille unique, ligne par ligne, et pose volet et filtre à la fin."""
    ws = wb.create_sheet(titre[:31] or "Feuille")
    for i, c in enumerate(colonnes, start=1):
        ws.column_dimensions[get_column_letter(i)].width = _largeur(c)
    ws.append([_cellule_entete(ws, c.titre) for c in colonnes])
    lecteurs: list[tuple[Callable[[object], object], str]] = [
        (c.valeur, format_colonne(c)) for c in colonnes
    ]
    rangs = 0
    for ligne in lignes:
        ws.append([_cellule_valeur(ws, lire(ligne), fmt) for lire, fmt in lecteurs])
        rangs += 1
    gele = 2 if len(colonnes) > COLONNES_AVANT_VOLET else 1
    ws.freeze_panes = f"{get_column_letter(gele)}2"
    if rangs and colonnes:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(colonnes))}{rangs + 1}"


def _flux_du_fichier(chemin: str) -> Iterator[bytes]:
    """Rend le classeur par morceaux puis efface le fichier temporaire (même en cas de coupure)."""
    try:
        with open(chemin, "rb") as f:
            while morceau := f.read(TAILLE_LOT):
                yield morceau
    finally:
        if os.path.exists(chemin):
            os.unlink(chemin)


def classeur_en_flux(
    titre: str,
    colonnes: Iterable[Colonne],
    lignes: Iterable[object],
    voit_prix: bool,
    prefixe: str,
) -> StreamingResponse:
    """Le classeur d'une feuille, écrit au fil des `lignes` (paresseuses) et rendu en flux.

    `colonnes` monétaires retirées pour qui ne voit pas les prix (barrière 4) ; `lignes` est un
    itérable consommé une seule fois (ne pas le matérialiser)."""
    gardees = colonnes_permises(list(colonnes), voit_prix)
    wb = Workbook(write_only=True)
    _ecrire(wb, titre, gardees, lignes)
    fichier = NamedTemporaryFile(suffix=".xlsx", delete=False)
    try:
        wb.save(fichier.name)
    finally:
        fichier.close()
    nom = nom_de_fichier(prefixe, aujourd_hui())
    return StreamingResponse(
        _flux_du_fichier(fichier.name),
        media_type=TYPE_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )
