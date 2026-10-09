"""Ce qui entre comme pièce jointe (G-10 ; décision X4 : « .exe refusé »).

Une liste blanche : chaque type permis, ses extensions, et les premiers octets qu'un fichier de
ce type porte. Le type déclaré par le navigateur ne suffit pas : l'extension doit lui
correspondre (un « .exe » déclaré PDF est refusé), le contenu doit commencer comme son type (un
programme renommé « facture.pdf » est refusé) et rien d'exécutable n'entre — ni par le type, ni
par l'extension, ni par les premiers octets (Windows, Linux, macOS, script). Les types Office
sont écrits en entier (plus de `vnd.*` générique) ; une image SVG (qui peut porter du script),
une page HTML, un classeur à macros sont refusés.
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from gestion_mp_pro.api.erreurs import Refus

PDF = (b"%PDF",)
JPEG = (b"\xff\xd8\xff",)
PNG = (b"\x89PNG\r\n\x1a\n",)
GIF = (b"GIF87a", b"GIF89a")
ZIP = (b"PK\x03\x04", b"PK\x05\x06")
OLE = (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",)
TIFF = (b"II*\x00", b"MM\x00*")
BMP = (b"BM",)
WEBP, HEIF = "webp", "heif"
"""Signatures à une position (RIFF…WEBP, …ftyp) : vérifiées à part."""


@dataclass(frozen=True)
class Genre:
    """Un type permis : ses extensions, ses premiers octets (ou un contrôle à part), et s'il
    peut être un simple texte (qui n'a pas de signature, seulement aucun octet nul)."""

    extensions: frozenset[str]
    signatures: tuple[bytes, ...] | str
    texte: bool = False


def _g(extensions: str, signatures: tuple[bytes, ...] | str = (), texte: bool = False) -> Genre:
    return Genre(frozenset(extensions.split()), signatures, texte)


OFFICE = "application/vnd.openxmlformats-officedocument"
OPEN = "application/vnd.oasis.opendocument"
PERMIS: dict[str, Genre] = {
    "application/pdf": _g(".pdf", PDF),
    "image/jpeg": _g(".jpg .jpeg .jfif", JPEG),
    "image/png": _g(".png", PNG),
    "image/gif": _g(".gif", GIF),
    "image/webp": _g(".webp", WEBP),
    "image/heic": _g(".heic", HEIF),
    "image/heif": _g(".heif", HEIF),
    "image/tiff": _g(".tif .tiff", TIFF),
    "image/bmp": _g(".bmp", BMP),
    "text/plain": _g(".txt", texte=True),
    "text/csv": _g(".csv .txt", texte=True),
    "message/rfc822": _g(".eml", texte=True),
    "application/msword": _g(".doc", OLE),
    "application/vnd.ms-excel": _g(".xls .csv", OLE, texte=True),
    "application/vnd.ms-powerpoint": _g(".ppt", OLE),
    "application/vnd.ms-outlook": _g(".msg", OLE),
    f"{OFFICE}.wordprocessingml.document": _g(".docx", ZIP),
    f"{OFFICE}.spreadsheetml.sheet": _g(".xlsx", ZIP),
    f"{OFFICE}.presentationml.presentation": _g(".pptx", ZIP),
    f"{OPEN}.text": _g(".odt", ZIP),
    f"{OPEN}.spreadsheet": _g(".ods", ZIP),
    f"{OPEN}.presentation": _g(".odp", ZIP),
    "application/zip": _g(".zip", ZIP),
    "application/x-zip-compressed": _g(".zip", ZIP),
}
"""Les types permis (X4) : PDF, images « à points », texte, tableurs et documents sans macros,
archives zip, courriels enregistrés."""

PROGRAMMES = (
    b"MZ",
    b"\x7fELF",
    b"\xfe\xed\xfa\xce",
    b"\xfe\xed\xfa\xcf",
    b"\xce\xfa\xed\xfe",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"#!",
)
"""Les premiers octets d'un programme : Windows (MZ), Linux (ELF), macOS (Mach-O), script."""

TYPE_REFUSE = "Type de fichier refusé : PDF, image, tableur, texte ou document seulement."
PROGRAMME = (
    "Ce fichier est un programme : refusé. PDF, image, tableur, texte ou document seulement."
)
CONTENU = "Le contenu de « {nom} » n'est pas celui d'un fichier {ext} : refusé."


def nom_sur(nom: str | None) -> str:
    """Le nom d'origine, sans chemin (« ../../x.pdf » → « x.pdf »), sans caractère de contrôle,
    200 caractères au plus ; vide : « document »."""
    brut = PureWindowsPath(PurePosixPath(nom or "").name).name
    propre = "".join(c for c in brut if c.isprintable()).strip().lstrip(".")
    return propre[:200] or "document"


def _suffixe(nom: str) -> str:
    return PurePosixPath(nom).suffix.lower()


def type_retenu(nom: str, declare: str | None) -> tuple[str, str]:
    """(type, extension) de la pièce, ou 422 `fichier_refuse` : le type déclaré (sinon celui
    que dit l'extension) doit être permis et l'extension être l'une des siennes."""
    suffixe = _suffixe(nom)
    genre = (declare or "").split(";")[0].strip().lower()
    if genre in {"", "application/octet-stream"}:
        genre = mimetypes.guess_type(f"x{suffixe}", strict=False)[0] or genre
    permis = PERMIS.get(genre)
    if permis is None or (suffixe and suffixe not in permis.extensions):
        raise Refus.saisie(TYPE_REFUSE, code="fichier_refuse", champs={"fichier": "type refusé"})
    return genre, suffixe or sorted(permis.extensions)[0]


def _signature_vue(genre: Genre, tete: bytes) -> bool:
    """Le fichier commence-t-il comme son type ?"""
    if genre.texte and b"\x00" not in tete:
        return True
    if genre.signatures == WEBP:
        return tete[:4] == b"RIFF" and tete[8:12] == b"WEBP"
    if genre.signatures == HEIF:
        return tete[4:8] == b"ftyp"
    signatures = genre.signatures
    return isinstance(signatures, tuple) and bool(signatures) and tete.startswith(signatures)


def verifier_tete(nom: str, genre: str, extension: str, tete: bytes) -> None:
    """Les premiers octets : jamais un programme ; toujours ceux de son type (422)."""
    if tete.startswith(PROGRAMMES):
        raise Refus.saisie(PROGRAMME, code="fichier_refuse", champs={"fichier": "programme"})
    if not _signature_vue(PERMIS[genre], tete):
        raise Refus.saisie(
            CONTENU.format(nom=nom, ext=extension.lstrip(".").upper()),
            code="fichier_refuse",
            champs={"fichier": "contenu d'un autre type"},
        )
