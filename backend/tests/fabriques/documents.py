"""Fabriques des documents et des exports (lot D9) : réglages « Société » posés puis rendus, lecture
d'un QR imprimé (décodé par zxing-cpp, un décodeur indépendant de segno), textes d'un document
par classe, classeur relu.

    from fabriques.documents import reglages, lire_qr, textes, classeur
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from html.parser import HTMLParser
from io import BytesIO

import zxingcpp
from openpyxl import Workbook, load_workbook
from sqlalchemy import select

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import Parametre

SOCIETE = {
    "nom_entreprise": "TAPIS ESSAI SA",
    "forme_juridique": "SOCIETE ANONYME AU CAPITAL DE 20 000 000 DH",
    "secteur": "Fabrication de tapis mécaniques",
    "adresse": "Zone industrielle, lot 12",
    "ville": "FES",
    "telephone": "05 35 00 00 00",
    "banques": "ATTIJARIWAFA BANK : 90D012433 · B.M.C.I : 01063 000619 001 82",
    "ice": "001122334455667",
    "rc": "12345",
    "identifiant_fiscal": "4011223",
    "cnss": "7654321",
    "patente": "13300000",
}
"""Un papier à en-tête complet (les valeurs de l'exemple de REGLAGES § 3.9)."""


@contextmanager
def reglages(valeurs: Mapping[str, str]) -> Iterator[None]:
    """Pose des réglages en base (validés : la route les lit), puis remet les anciennes valeurs."""
    with fabrique()() as s, s.begin():
        anciens = {
            p.cle: p.valeur
            for p in s.scalars(select(Parametre).where(Parametre.cle.in_(list(valeurs))))
        }
        for cle, valeur in valeurs.items():
            s.get_one(Parametre, cle).valeur = valeur
    try:
        yield
    finally:
        with fabrique()() as s, s.begin():
            for cle, valeur in anciens.items():
                s.get_one(Parametre, cle).valeur = valeur


# ── QR ───────────────────────────────────────────────────────────────────────────────────────

ECHELLE = 6
MARGE = 4  # modules blancs autour (la marge de l'étiquette imprimée)
_COMMANDE = re.compile(r"([MmHhVv])\s*(-?[\d.]+)(?:\s+(-?[\d.]+))?")


def _modules(svg: str) -> list[list[bool]]:
    """La grille d'un QR de segno (chemin « ligne » : `M x y`, `h n`, `m dx dy`)."""
    taille_vue = float(re.search(r'viewBox="0 0 ([\d.]+)', svg).group(1))  # type: ignore[union-attr]
    echelle = float(re.search(r"scale\(([\d.]+)\)", svg).group(1))  # type: ignore[union-attr]
    n = round(taille_vue / echelle)
    grille = [[False] * n for _ in range(n)]
    chemin = re.search(r' d="([^"]+)"', svg).group(1)  # type: ignore[union-attr]
    x = y = 0.0
    for lettre, a, b in _COMMANDE.findall(chemin):
        if lettre in "Mm":
            dx, dy = float(a), float(b)
            x, y = (dx, dy) if lettre == "M" else (x + dx, y + dy)
        elif lettre in "hH":
            fin = x + float(a) if lettre == "h" else float(a)
            for colonne in range(round(min(x, fin)), round(max(x, fin))):
                grille[int(y)][colonne] = True
            x = fin
    return grille


def lire_qr(svg: str) -> str:
    """Le texte d'un QR imprimé : la grille du SVG mise en image, puis décodée par zxing-cpp."""
    grille = _modules(svg)
    cote = (len(grille) + 2 * MARGE) * ECHELLE
    image = bytearray([255]) * (cote * cote)
    for rang, ligne in enumerate(grille):
        for colonne, noir in enumerate(ligne):
            if noir:
                for dy in range(ECHELLE):
                    debut = ((rang + MARGE) * ECHELLE + dy) * cote + (colonne + MARGE) * ECHELLE
                    image[debut : debut + ECHELLE] = bytes(ECHELLE)
    lus = zxingcpp.read_barcodes(memoryview(image).cast("B", shape=[cote, cote]))
    assert len(lus) == 1, "un QR, et un seul, doit se lire"
    return str(lus[0].text)


def svgs(html: str) -> list[str]:
    """Les SVG en ligne d'un document."""
    return re.findall(r"<svg.*?</svg>", html, flags=re.S)


# ── Textes d'un document ─────────────────────────────────────────────────────────────────────


BLOCS = {"div", "p", "footer", "section", "main", "h1", "h2", "br", "li", "td", "th", "tr"}


class _Lecteur(HTMLParser):
    """Le texte de chaque élément qui porte une classe donnée."""

    def __init__(self, classe: str) -> None:
        super().__init__()
        self.classe, self.pile, self.textes = classe, [], []  # type: ignore[var-annotated]

    def _separer(self, tag: str) -> None:
        """Un élément de bloc sépare les mots (comme à l'écran)."""
        if tag in BLOCS:
            self.handle_data(" ")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._separer(tag)
        if tag in {"br", "meta", "img", "input", "hr", "link"}:
            return
        classes = (dict(attrs).get("class") or "").split()
        if self.classe in classes:
            self.textes.append("")
            self.pile.append(len(self.textes) - 1)
        else:
            self.pile.append(None)

    def handle_endtag(self, tag: str) -> None:
        self._separer(tag)
        if tag not in {"br", "meta", "img", "input", "hr", "link"} and self.pile:
            self.pile.pop()

    def handle_data(self, data: str) -> None:
        for rang in {r for r in self.pile if r is not None}:
            self.textes[rang] += data


def textes(html: str, classe: str) -> list[str]:
    """Le texte (espaces resserrés) des éléments de cette classe, dans l'ordre du document."""
    lecteur = _Lecteur(classe)
    lecteur.feed(html)
    espaces = str.maketrans({"\u2003": " ", "\u2002": " "})
    return [re.sub(r"[ \t\n]+", " ", t.translate(espaces)).strip() for t in lecteur.textes]


def classeur(contenu: bytes) -> Workbook:
    """Un classeur rendu par une route, relu."""
    assert contenu[:2] == b"PK", "un classeur xlsx est une archive zip"
    return load_workbook(BytesIO(contenu))
