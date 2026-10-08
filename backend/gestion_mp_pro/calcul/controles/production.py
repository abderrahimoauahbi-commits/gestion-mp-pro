"""Contrôles de la production : sorties vers les machines, retours, fil monté, ordres
(C02, C03, C25, C31, C32)."""

from __future__ import annotations

from datetime import date

from gestion_mp_pro.calcul.constantes import POUSSIERE, TYPES_MOUVEMENT
from gestion_mp_pro.calcul.controles.base import Contexte, Ligne, colonne, controle
from gestion_mp_pro.calcul.controles.textes import GARANTI_C02, GARANTI_C31, GARANTI_C32

MOTIFS_PERMIS: dict[str, tuple[str, ...]] = {
    "RETOUR_PRODUCTION": ("R1", "R2", "R4"),
    "RETOUR_FOURNISSEUR": ("R3", "R5", "R6"),
}
"""Les motifs de retour de chaque famille (codes de l'ERP Fil)."""

PARTIES_NUMERO_OF = 3
"""« OF-2026-0042 » : préfixe, année, rang."""

_DATE_FR = "%d/%m/%Y"


@controle(
    "C02",
    gravite="avertissement",
    lien="/sorties",
    colonnes=(colonne("date", "date"), colonne("reference", "texte")),
    garanti=GARANTI_C02,
)
def sortie_sans_ordre(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Une sortie de production doit porter son ordre de fabrication (T02)."""
    lignes: list[Ligne] = [
        {"date": m.date.isoformat(), "reference": m.reference}
        for m in ctx.donnees.mouvements
        if m.type == "SORTIE_PROD" and not m.numero_of
    ]
    return "Sortie vers les machines sans ordre (n° OF)", lignes


@controle(
    "C03",
    gravite="avertissement",
    lien="/operations?onglet=retour_machine",
    colonnes=(
        colonne("date", "date"),
        colonne("reference", "texte"),
        colonne("type", "texte"),
        colonne("motif", "texte"),
    ),
)
def retour_sans_motif(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un retour porte un motif de sa famille : R1, R2, R4 des machines ; R3, R5, R6 au
    fournisseur (T03). Un retour des machines marqué R3 se lit comme un retour au fournisseur."""
    lignes: list[Ligne] = [
        {
            "date": m.date.isoformat(),
            "reference": m.reference,
            "type": TYPES_MOUVEMENT.get(m.type, (m.type, 1))[0],
            "motif": m.motif_retour or "—",
        }
        for m in ctx.donnees.mouvements
        if m.type in MOTIFS_PERMIS and m.motif_retour not in MOTIFS_PERMIS[m.type]
    ]
    return "Retour sans motif, ou avec le motif d'une autre famille", lignes


@controle(
    "C25",
    gravite="avertissement",
    lien="/sorties",
    colonnes=(
        colonne("metier", "texte"),
        colonne("etage", "nombre"),
        colonne("reference", "texte"),
        colonne("poids", "kg"),
        colonne("monte", "kg"),
        colonne("sorties", "kg"),
    ),
)
def fil_monte_non_sorti(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Le fil monté doit avoir été sorti vers les machines, net des retours et des
    annulations : une seule sortie, même annulée, ne suffit pas."""
    sorti_net: dict[str, float] = {}
    for m in ctx.complet.mouvements:
        if m.type in ("SORTIE_PROD", "RETOUR_PRODUCTION"):
            sorti_net[m.reference] = sorti_net.get(m.reference, 0.0) - m.quantite_signee
    montes = [f for f in ctx.fils if f.poids]
    monte: dict[str, float] = {}
    for f in montes:
        monte[f.reference] = monte.get(f.reference, 0.0) + f.poids
    lignes: list[Ligne] = [
        {
            "metier": f.metier,
            "etage": f.etage,
            "reference": f.reference,
            "poids": f.poids,
            "monte": round(monte[f.reference], 1),
            "sorties": round(sorti_net.get(f.reference, 0.0), 1),
        }
        for f in montes
        if monte[f.reference] > sorti_net.get(f.reference, 0.0) + POUSSIERE
    ]
    return (
        "Fil monté plus lourd que le sorti net vers les machines (le magasin le compte encore)",
        lignes,
    )


@controle(
    "C31",
    gravite="avertissement",
    lien="/sorties",
    colonnes=(
        colonne("numero_of", "texte"),
        colonne("dates", "texte"),
        colonne("nb_dates", "nombre"),
    ),
    garanti=GARANTI_C31,
)
def ordre_a_plusieurs_dates(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un ordre sert une fois : servi à deux dates, c'est une saisie à revoir."""
    lignes: list[Ligne] = [
        {
            "numero_of": numero,
            "dates": " · ".join(jour.strftime(_DATE_FR) for jour in sorted(jours)),
            "nb_dates": len(jours),
        }
        for numero, jours in sorted(ctx.jours_par_of.items())
        if len(jours) > 1
    ]
    return "Ordre de fabrication servi à plusieurs dates", lignes


def rang_ordre(numero: str) -> tuple[int, int] | None:
    """« OF-2026-0042 » → (2026, 42) ; un numéro libre ne se classe pas."""
    parties = numero.split("-")
    if len(parties) == PARTIES_NUMERO_OF and parties[1].isdigit() and parties[2].isdigit():
        return int(parties[1]), int(parties[2])
    return None


@controle(
    "C32",
    gravite="information",
    lien="/sorties",
    colonnes=(
        colonne("numero_of", "texte"),
        colonne("date", "texte"),
        colonne("apres", "texte"),
        colonne("date_apres", "texte"),
    ),
    garanti=GARANTI_C32,
)
def ordre_dans_le_desordre(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Les numéros suivent le temps : un numéro plus grand daté avant un plus petit est un
    numéro retapé à la main, ou une sortie antidatée."""
    numerotes = sorted(
        (rang, min(jours), numero)
        for numero, jours in ctx.jours_par_of.items()
        if (rang := rang_ordre(numero)) is not None
    )
    lignes: list[Ligne] = []
    plus_tard: tuple[date, str] | None = None
    for _, jour, numero in numerotes:
        if plus_tard is not None and jour < plus_tard[0]:
            lignes.append(
                {
                    "numero_of": numero,
                    "date": jour.strftime(_DATE_FR),
                    "apres": plus_tard[1],
                    "date_apres": plus_tard[0].strftime(_DATE_FR),
                }
            )
        if plus_tard is None or jour > plus_tard[0]:
            plus_tard = (jour, numero)
    return "Ordre de fabrication daté avant un ordre de numéro inférieur", lignes
