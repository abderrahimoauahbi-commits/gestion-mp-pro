/**
 * L'écart à la recette, une seule règle partout (P2-8, P2-25) : à 5 % près c'est juste (ok) ; au-delà,
 * un excès est à surveiller (attention), un manque est critique. Sorties, ordres de fabrication,
 * suivi de traçabilité et saisie d'ordre lisent ce badge.
 */
import { Badge } from '../../composants/retour/Badge'
import { partSignee, VIDE } from '../../lib/format'
import type { Ton } from '../../lib/statuts'

/** Le seuil au-delà duquel un écart se signale (5 %). */
export const SEUIL_ECART = 0.05

export function tonEcart(relatif: number | null | undefined): Ton | undefined {
  if (relatif == null) return undefined
  if (Math.abs(relatif) <= SEUIL_ECART) return 'ok'
  return relatif > 0 ? 'attention' : 'critique'
}

/** L'écart relatif (sorti − prévu) ÷ prévu, ou `null` sans prévu. */
export function ecartRelatif(sorti: number, prevu: number): number | null {
  return prevu ? (sorti - prevu) / prevu : null
}

export function EcartRecette({ relatif }: { relatif: number | null | undefined }) {
  const ton = tonEcart(relatif)
  if (relatif == null || !ton) return <span>{VIDE}</span>
  return <Badge ton={ton}>{partSignee(relatif)}</Badge>
}
