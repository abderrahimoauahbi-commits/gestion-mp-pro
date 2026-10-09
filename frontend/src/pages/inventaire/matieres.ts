/** Une matière du catalogue (`GET matieres`) ramenée à ce qu'en lit `SelecteurMatiere`. */
import type { MatiereChoix } from '../../composants/saisie/SelecteurMatiere'
import type { Schema } from '../../lib/types'

export function choixMatiere(m: Schema<'MatiereResume'>): MatiereChoix {
  return {
    id: m.id,
    reference: m.reference,
    designation: m.designation,
    composition: m.composition,
    type: m.type_fil,
    titrage: m.titrage,
    couleur: m.couleur,
    fournisseur: m.fournisseur,
  }
}
