/**
 * Le badge de l'écart à la recette ; la règle est celle du moteur `lib/ordre` (P2-8, P2-25) : à
 * 5 % près c'est juste (ok) ; au-delà, un excès est à surveiller (attention), un manque est
 * critique. Sorties, ordres de fabrication, suivi de traçabilité et saisie d'ordre lisent ce badge.
 */
import { Badge } from '../../composants/retour/Badge'
import { partSignee, VIDE } from '../../lib/format'
import { tonEcart } from '../../lib/ordre'

export { ecartRelatif, SEUIL_ECART, tonEcart } from '../../lib/ordre'

export function EcartRecette({ relatif }: { relatif: number | null | undefined }) {
  const ton = tonEcart(relatif)
  if (relatif == null || !ton) return <span>{VIDE}</span>
  return <Badge ton={ton}>{partSignee(relatif)}</Badge>
}
