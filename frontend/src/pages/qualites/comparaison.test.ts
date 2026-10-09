/** Comparer une version de la recette à celle en vigueur. */
import { describe, expect, it } from 'vitest'

import { nombre } from '../../lib/format'
import { ecartLisible, ecarts, ecartsPoids } from './comparaison'
import { versionEssai } from './donneesEssai'

describe('comparaison des versions', () => {
  it('ajoutée, retirée, écart en points', () => {
    const vigueur = versionEssai(3, {
      lignes: [{ matiere_id: 12, reference: 'A', role_id: 1, role: 'Poil', pourcentage: 100 }],
    })
    const ancienne = versionEssai(2, {
      lignes: [
        { matiere_id: 12, reference: 'A', role_id: 1, role: 'Poil', pourcentage: 90 },
        { matiere_id: 14, reference: 'B', role_id: 1, role: 'Poil', pourcentage: 10 },
      ],
      poids: [{ role_id: 1, role: 'Poil', poids: 1 }],
    })
    expect(ecarts(ancienne, vigueur).map((e) => `${e.reference} ${ecartLisible(e, nombre)}`)).toEqual([
      'A +10,00 pt',
      'B retirée depuis',
    ])
    expect(ecarts(vigueur, ancienne).map((e) => ecartLisible(e, nombre))).toEqual([
      '−10,00 pt',
      'ajoutée depuis',
    ])
    expect(ecartsPoids(ancienne, vigueur)).toEqual([{ role: 'Poil', ici: 1, enVigueur: 1.2 }])
    expect(ecartsPoids(versionEssai(1, { poids: null }), vigueur)).toEqual([])
  })
})
