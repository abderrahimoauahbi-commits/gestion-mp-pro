/**
 * Les fonds de lot qu'une proposition « Envoyer aux machines » a laissés en stock (lot
 * FOND-DE-LOT) : chaque lot disponible marqué `fond_de_lot` et jamais proposé, écrit « HT-… (56 g,
 * POIL ROUGE) ». Lu dans les lignes de la proposition (bureau et atelier).
 */
import type { Schema } from '../../lib/types'
import { poidsFond } from './fonds'

type LigneProposee = Schema<'LigneProposee'>

/** « HT-280502-0427 (56 g, POIL ROUGE 2900) », un par fond de lot laissé en stock. */
export function fondsLaisses(besoins: readonly LigneProposee[]): string[] {
  const textes: string[] = []
  for (const b of besoins)
    for (const d of b.disponibles)
      if (d.fond_de_lot && d.disponible > 0)
        textes.push(`${d.lot} (${poidsFond(d.disponible)}, ${b.reference})`)
  return textes
}
