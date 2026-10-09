/** Les paramètres de la référence composée (route 75). */
import { describe, expect, it } from 'vitest'

import { parametresReference } from './useReference'

describe('parametresReference', () => {
  it('rien de la classification : pas de demande', () => {
    expect(
      parametresReference({
        composition_id: null,
        type_fil_id: null,
        titrage_id: null,
        couleur_id: null,
        couleur_code: 'A',
        suffixe: 'Hs',
      }),
    ).toBeNull()
  })

  it('les parties choisies, code couleur et suffixe nettoyés', () => {
    expect(
      parametresReference({
        composition_id: 1,
        type_fil_id: null,
        titrage_id: 3,
        couleur_id: null,
        couleur_code: ' 7001 ',
        suffixe: '',
      }),
    ).toEqual({
      composition_id: 1,
      type_fil_id: undefined,
      titrage_id: 3,
      couleur_id: undefined,
      couleur_code: '7001',
      suffixe: undefined,
    })
  })
})
