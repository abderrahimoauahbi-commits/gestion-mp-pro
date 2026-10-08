"""Numéros des pièces, sans trou ni doublon (ARCHITECTURE § 8 ; héritage REGLES § 0.4, B.6.5).

- `numero(s, serie, jour)` : le numéro suivant de la série pour l'**année de la pièce**
  (`jour.year`), pris sous verrou de ligne du compteur (`SELECT … FOR UPDATE`), dans la
  transaction du geste : un refus l'annule avec lui (M65, aucun trou) ; deux validations
  simultanées obtiennent N et N+1, jamais deux fois N.
- Format `SERIE-AAAA-NNNN` (`BC-2026-0001`) ; `DOS` : `NN/AA` (`01/26`, le numéro de la maison).
- Qui numérote et quand (à l'envoi, à la validation, à l'ouverture pour INV, RCL, DOS) est dit
  par chaque domaine ; ce module ne fait que donner le numéro.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import Compteur
from gestion_mp_pro.modeles.enums import SerieNumero

LARGEUR = 4
"""Chiffres du rang : `BC-2026-0001` (le code de Gestion MP en donne 4, cahier I75)."""

ESSAIS_MAX = 10_000
"""Garde-fou de `deja_pris` : au-delà, la série est pleine de numéros saisis à la main."""


def formater(serie: SerieNumero | str, annee: int, rang: int) -> str:
    """`BC-2026-0007` ; `DOS` : `07/26`."""
    serie = SerieNumero(serie)
    if serie is SerieNumero.DOS:
        return f"{rang:02d}/{annee % 100:02d}"
    return f"{serie.value}-{annee}-{rang:0{LARGEUR}d}"


def _compteur(s: Session, serie: SerieNumero, annee: int) -> Compteur:
    """Le compteur de la série et de l'année, créé au besoin, verrouillé jusqu'à la fin."""
    s.execute(
        insert(Compteur)
        .values(serie=serie, annee=annee, dernier=0)
        .on_conflict_do_nothing(index_elements=["serie", "annee"])
    )
    requete = (
        select(Compteur)
        .where(Compteur.serie == serie, Compteur.annee == annee)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return s.scalars(requete).one()


def numero(
    s: Session,
    serie: SerieNumero | str,
    jour_ou_annee: date | int,
    *,
    deja_pris: Callable[[str], bool] | None = None,
) -> str:
    """Le numéro suivant de la série pour l'année de la pièce (`date` ou année entière).

    `deja_pris(numero)` : un numéro saisi à la main (dossier repris) est sauté (`SEC:195-196`).
    """
    serie = SerieNumero(serie)
    annee = _annee(jour_ou_annee)
    compteur = _compteur(s, serie, annee)
    for _ in range(ESSAIS_MAX):
        compteur.dernier += 1
        texte = formater(serie, annee, compteur.dernier)
        if deja_pris is None or not deja_pris(texte):
            s.flush()
            return texte
    raise RuntimeError(f"Série {serie.value} {annee} : aucun numéro libre.")


def _annee(jour_ou_annee: date | int) -> int:
    """L'année d'une date (ou l'année donnée telle quelle)."""
    return jour_ou_annee if isinstance(jour_ou_annee, int) else jour_ou_annee.year


def rattraper(s: Session, serie: SerieNumero | str, annee: int, au_moins: int) -> int:
    """Porte le compteur au moins à `au_moins` (lots repris, reprise) ; rend sa valeur."""
    compteur = _compteur(s, SerieNumero(serie), annee)
    if compteur.dernier < au_moins:
        compteur.dernier = au_moins
        s.flush()
    return compteur.dernier


def dernier(s: Session, serie: SerieNumero | str, annee: int) -> int:
    """Le dernier rang donné (0 si la série n'a encore rien numéroté cette année)."""
    requete = select(Compteur.dernier).where(
        Compteur.serie == SerieNumero(serie), Compteur.annee == annee
    )
    return int(s.scalar(requete) or 0)


def libelle_brouillon(ident: int) -> str:
    """Le libellé d'un document sans numéro : « brouillon n° 12 » (héritage X41)."""
    return f"brouillon n° {ident}"
