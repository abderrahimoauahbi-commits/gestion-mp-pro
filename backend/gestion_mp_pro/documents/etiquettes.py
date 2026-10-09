"""Les étiquettes QR des lots (route 114 ; ECRANS-PRO « Étiquettes de lots » ; DEFAUTS C-18).

Une étiquette par page de 100 × 70 mm (rouleau d'étiquettes) : le QR de l'adresse du lot, la
référence, « Lot {n°} », le fournisseur, « Entré le … », ce qui reste à l'impression (kilos à
la règle § 9.3, « ≈ N bobines » si le poids d'une bobine est connu), « N° {id} »,
et « QUARANTAINE — NE PAS SORTIR » encadré pour un lot en quarantaine (« dont … en quarantaine »
s'il n'y est qu'en partie). Les identifiants inconnus sont dits en tête de page (écran seulement) ;
sans aucun lot connu, une page lisible « Aucun lot à étiqueter. » (404), jamais un JSON brut.
Les données (textes compris) viennent de `services.lots_lecture.etiquettes` (lot S4) : ce module
ne fait que les mettre en page.
"""

from __future__ import annotations

from dataclasses import dataclass

from gestion_mp_pro.documents import qr, rendu
from gestion_mp_pro.services.lots_lecture import Etiquette, Etiquettes

AUCUN_LOT = "Aucun lot à étiqueter."


@dataclass(frozen=True)
class EtiquetteImprimee:
    """Une étiquette prête à imprimer : les données du lot, son adresse et son QR."""

    lot: Etiquette
    adresse: str
    qr_svg: str


@dataclass(frozen=True)
class PageEtiquettes:
    """Le document rendu et son statut HTTP (404 sans aucun lot connu)."""

    html: str
    statut: int


def rendre(donnees: Etiquettes, adresse_qr: str, alerte_localhost: str | None) -> PageEtiquettes:
    """La page des étiquettes ; `adresse_qr` est la base des adresses (sans « / » final)."""
    etiquettes = [
        EtiquetteImprimee(e, adresse, qr.svg(adresse))
        for e in donnees.lots
        for adresse in (qr.adresse_du_lot(adresse_qr, e.lot_id),)
    ]
    html = (
        rendu.environnement()
        .get_template("etiquettes.html")
        .render(
            titre="Étiquettes de lots",
            langue="fr",
            etiquettes=etiquettes,
            ignores=donnees.ignores,
            alerte_localhost=alerte_localhost,
            aucun_lot=AUCUN_LOT,
            script_imprimer=rendu.script_imprimer(),
        )
    )
    return PageEtiquettes(html, 200 if etiquettes else 404)
