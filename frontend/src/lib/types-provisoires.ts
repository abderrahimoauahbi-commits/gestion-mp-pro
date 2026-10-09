/**
 * PROVISOIRE — formes de routes que l'OpenAPI ne publie pas encore (lots D) : elles se
 * remplacent par `Schema<'…'>` dès que `types.gen.ts` les contient, et ce fichier disparaît.
 */

/** GET /matieres (route 70, lot D1) : ce qu'en lit la fenêtre « Signaler un besoin ». */
export interface MatiereResumee {
  id: number
  reference: string
  designation?: string | null
  composition?: string | null
  type_fil?: string | null
  titrage?: string | null
  couleur?: string | null
  fournisseur?: string | null
  actif?: boolean
}

/** POST /signalements (route 222, lot D3). */
export interface SignalementCreation {
  matiere_id: number | null
  texte: string
  urgence: 'normale' | 'urgente'
}
