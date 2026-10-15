"""Les fonds de lot (lot FOND-DE-LOT ; décision de Mohamed du 15 octobre 2026, DECISIONS U22).

« À partir d'un certain poids, un fond de lot doit être mis au rebut : il ne sert à rien. » Ce
qui reste d'un lot **dans un magasin** (son solde) est un *fond de lot* quand il est > 0 et
plus petit que le réglage « Seuil de rebut (kg) » (`seuil_rebut`, défaut 0,100 kg ; 0 =
désactivé). Un fond de lot :

- n'est plus proposé par la proposition FIFO de « Envoyer aux machines » (`services/ordres/
  proposition`), bureau comme atelier ; il reste dans la liste des lots disponibles, marqué ;
- reste en stock, compté et valorisé, marqué « fond de lot (< 100 g) » dans Stock › Lots, la
  fiche du lot et « Stock des fils » de l'atelier (`lots.lister`, `LotSolde.fond_de_lot`) ;
- se met au rebut par le geste `services.operations.rebut.mettre_au_rebut` (ajustement en
  moins au motif « Rebut »).

Le fil monté sur un métier n'est pas concerné. Ce module ne lit que le réglage et ne calcule
que la règle ; il n'écrit rien.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from gestion_mp_pro.documents import format as fmt
from gestion_mp_pro.modeles.types import QUANTITE, arrondir
from gestion_mp_pro.services import reglages

CLE = "seuil_rebut"
ZERO = Decimal(0)
UN_KILO = Decimal(1)


def seuil(s: Session) -> Decimal:
    """Le seuil de rebut en kg, arrondi au gramme ; 0 : désactivé."""
    return max(ZERO, arrondir(Decimal(str(reglages.nombre(s, CLE))), QUANTITE))


def est_fond(quantite: Decimal | float, seuil_kg: Decimal) -> bool:
    """Un reste > 0 et strictement sous le seuil ; jamais quand le seuil est 0."""
    return seuil_kg > 0 and ZERO < Decimal(str(quantite)) < seuil_kg


def seuil_lisible(seuil_kg: Decimal) -> str:
    """« 100 g » sous le kilo, « 2 kg » au-dessus (l'écran dit la même chose)."""
    if seuil_kg < UN_KILO:
        return f"{fmt.nombre(seuil_kg * 1000, 0, 0)} g"
    return fmt.kg(seuil_kg)


def poids_lisible(quantite: Decimal) -> str:
    """Un fond de lot se lit en grammes sous le kilo (« 56 g »), en kilos au-dessus."""
    return seuil_lisible(arrondir(Decimal(str(quantite)), QUANTITE))


def marque(seuil_kg: Decimal) -> str:
    """La marque des écrans : « fond de lot (< 100 g) »."""
    return f"fond de lot (< {seuil_lisible(seuil_kg)})"
