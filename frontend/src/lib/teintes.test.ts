/** Essais des teintes : la couleur du fil, puis la palette, puis le trait. */
import { describe, expect, it } from 'vitest'

import { couleurDeSerie, PALETTE_FILS, PALETTE_SERIES, stylesDesFils, teinteDuFil, TRAITS } from './teintes'

describe('teinteDuFil', () => {
  it.each([
    ['Rouge', '#c62828'],
    ['RED', '#c62828'],
    ['Bleu marine', '#1b2f5e'],
    ['Navy', '#1b2f5e'],
    ['Bleu', '#2563b8'],
    ['D.Turkoi', '#1295a8'],
    ['L.Beige', '#cdb891'],
    ['Beige foncé', '#a98f63'],
    ['Crème', '#d1c089'],
    ['Écru', '#d1c089'],
    ['Dk Vison', '#5f4b3d'],
    ['Vison', '#8a6f5a'],
    ['Gris clair', '#a5aeb8'],
    ['Blanc', '#9fb0c2'],
    ['Or', '#c79a00'],
  ])('%s → %s', (nom, teinte) => {
    expect(teinteDuFil(nom)).toBe(teinte)
  })

  it('rien pour un nom qui ne dit pas de couleur', () => {
    expect(teinteDuFil('C5N')).toBeNull()
    expect(teinteDuFil('Cordon')).toBeNull()
    expect(teinteDuFil('')).toBeNull()
    expect(teinteDuFil(null)).toBeNull()
  })
})

describe('stylesDesFils', () => {
  it('la teinte du fil, la palette sinon, un autre trait à teinte égale', () => {
    const s = stylesDesFils([
      { cle: 'A', couleur: 'Rouge' },
      { cle: 'B', couleur: 'Red' },
      { cle: 'C', couleur: 'C5N' },
      { cle: 'D', couleur: null },
    ])
    expect(s.get('A')).toEqual({ couleur: '#c62828', trait: TRAITS[0] })
    expect(s.get('B')).toEqual({ couleur: '#c62828', trait: TRAITS[1] })
    expect(s.get('C')).toEqual({ couleur: PALETTE_FILS[0], trait: '' })
    expect(s.get('D')).toEqual({ couleur: PALETTE_FILS[1], trait: '' })
  })

  it('les séries de pilotage gardent leur ordre, huit au plus', () => {
    expect(PALETTE_SERIES).toHaveLength(8)
    expect(couleurDeSerie(0)).toBe('#2a78d6')
    expect(couleurDeSerie(8)).toBe('#2a78d6')
    expect(couleurDeSerie(-1)).toBe('#e34948')
  })
})
