"""Les QR des documents (segno → SVG en ligne) : l'adresse d'un lot sur son étiquette.

Le QR d'une étiquette porte `{adresse pour les téléphones}/lot/{id}` (réglage
`adresse_publique`, sinon l'adresse d'appel, jamais `localhost` : `services.appareils.acces`) ;
l'appareil photo de l'atelier l'ouvre, et `GET /lots/scan` (route 110) relit la même adresse.
Correction d'erreur « M » (une étiquette un peu abîmée se lit encore), comme Gestion MP.
"""

from __future__ import annotations

import segno
from markupsafe import Markup


def adresse_du_lot(base: str, lot_id: int) -> str:
    """« http://mac-usine:8050/lot/123 » (sans « / » doublé)."""
    return f"{base.rstrip('/')}/lot/{lot_id}"


def svg(texte: str, *, echelle: int = 4, marge: int = 0) -> Markup:
    """Le QR d'un texte en SVG en ligne, prêt pour un gabarit (sa taille est posée par le CSS)."""
    code = segno.make(texte, error="m")
    return Markup(  # noqa: S704 — SVG de segno, titre échappé par segno
        code.svg_inline(scale=echelle, border=marge, title=texte, omitsize=True)
    )
