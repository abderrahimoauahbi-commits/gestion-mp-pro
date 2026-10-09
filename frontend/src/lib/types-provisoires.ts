/**
 * PROVISOIRE — formes de routes que l'OpenAPI ne publie pas encore (lots D) : elles se
 * remplacent par `Schema<'…'>` dès que `types.gen.ts` les contient, et ce fichier disparaît.
 */

/** POST /signalements (route 222, lot D8) : pas encore servie. */
export interface SignalementCreation {
  matiere_id: number | null
  texte: string
  urgence: 'normale' | 'urgente'
}
