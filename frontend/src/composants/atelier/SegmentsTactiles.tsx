/** Des segments à l'atelier : toute la largeur, chaque segment ≥ 44 × 44 px, police de 15 px. */
import { Segments, type SegmentsProps } from '../saisie/Segments'

export function SegmentsTactiles<T extends string | number>(props: Omit<SegmentsProps<T>, 'tactile'>) {
  return <Segments {...props} tactile />
}
