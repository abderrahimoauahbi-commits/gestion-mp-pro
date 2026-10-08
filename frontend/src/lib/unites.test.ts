/** Essais des unités : kg ↔ bobines ↔ palettes, arrondi dit. */
import { describe, expect, it } from 'vitest'

import {
  bobinesApprochees,
  contenance,
  depuisKg,
  direArrondi,
  direConversion,
  libelleUnite,
  pasPour,
  quantiteEnUnites,
  toutRendre,
  unitesPossibles,
  versKg,
  type Conditionnement,
} from './unites'

const n = (texte: string) => texte.replace(/~/g, ' ')

const fil: Conditionnement = { poidsBobine: 2.4952, bobinesPalette: 40 }
const sansPalette: Conditionnement = { poidsBobine: 2.5, bobinesPalette: 0 }
const cuir: Conditionnement = { poidsBobine: null, bobinesPalette: null, kgParMl: 0.014 }

describe('Unités possibles et contenances', () => {
  it('kilo toujours ; bobine si son poids est connu ; palette si en plus ses bobines le sont', () => {
    expect(unitesPossibles(fil)).toEqual(['kg', 'bobine', 'palette'])
    expect(unitesPossibles(sansPalette)).toEqual(['kg', 'bobine'])
    expect(unitesPossibles(cuir)).toEqual(['kg'])
    expect(unitesPossibles({})).toEqual(['kg'])
  })

  it('une bobine vaut son poids, une palette ses bobines', () => {
    expect(contenance(fil, 'kg')).toBe(1)
    expect(contenance(fil, 'bobine')).toBe(2.4952)
    expect(contenance(fil, 'palette')).toBeCloseTo(99.808, 9)
    expect(contenance(cuir, 'bobine')).toBeNull()
    expect(contenance(sansPalette, 'palette')).toBeNull()
  })

  it('libellés', () => {
    expect(libelleUnite(fil, 'bobine')).toBe(n('bobines (2,4952~kg)'))
    expect(libelleUnite(fil, 'palette')).toBe(n('palettes (40~bob.)'))
    expect(libelleUnite(fil, 'kg')).toBe('kg')
  })
})

describe('kg ↔ bobines ↔ palettes', () => {
  it('vers les kilos, au gramme', () => {
    expect(versKg(3, 'bobine', fil)).toBe(7.486)
    expect(versKg(2.5, 'palette', fil)).toBe(249.52)
    expect(versKg(12.3456, 'kg', fil)).toBe(12.346)
    expect(versKg(3, 'bobine', cuir)).toBeNull()
  })

  it('une bobine se compte entière, et l’arrondi est dit', () => {
    const c = depuisKg(7.5, 'bobine', fil)
    expect(c).toEqual({ quantite: 3, kg: 7.486, arrondi: true })
    expect(direArrondi(c, 7.5)).toBe(n('arrondi : 7,49~kg au lieu de 7,50~kg'))
  })

  it('une palette se compte au centième', () => {
    const c = depuisKg(250, 'palette', fil)
    expect(c?.quantite).toBe(2.5)
    expect(c?.kg).toBe(249.52)
    // 249,52 kg au lieu de 250 : au téléphone les deux se lisent « 250 kg », rien à dire.
    expect(direArrondi(c, 250)).toBe('')
  })

  it('une conversion exacte ne dit rien', () => {
    const c = depuisKg(7.486, 'bobine', fil)
    expect(c?.arrondi).toBe(false)
    expect(direArrondi(c, 7.486)).toBe('')
    expect(direArrondi(null, 7.486)).toBe('')
  })

  it('en kilos, on garde le gramme ; sous le gramme, ce n’est pas un arrondi', () => {
    expect(depuisKg(12.3456, 'kg', fil)).toEqual({ quantite: 12.346, kg: 12.346, arrondi: false })
    expect(depuisKg(12.3466, 'kg', fil)).toEqual({ quantite: 12.347, kg: 12.347, arrondi: false })
  })

  it('impossible sans poids de bobine', () => {
    expect(depuisKg(10, 'bobine', cuir)).toBeNull()
  })

  it('dit ce que vaut une saisie : « 3 bobines = 7,49 kg »', () => {
    expect(direConversion(3, 'bobine', fil)).toBe(n('3~bobines = 7,49~kg'))
    expect(direConversion(1, 'palette', fil)).toBe(n('1~palette = 99,8~kg'))
    expect(direConversion(3, 'kg', fil)).toBe('')
    expect(direConversion(3, 'bobine', cuir)).toBe('')
  })
})

describe('Tout rendre : vers le bas, jamais plus que le net parti', () => {
  it('au gramme : 581,65 kg partis → 581,65, pas 581,7', () => {
    expect(toutRendre(fil, 581.65, 'kg')).toBe(581.65)
  })

  it('à la bobine entière et au centième de palette', () => {
    expect(toutRendre(fil, 7.48, 'bobine')).toBe(2)
    expect(toutRendre(fil, 7.486, 'bobine')).toBe(3)
    expect(toutRendre(fil, 250, 'palette')).toBe(2.5)
    expect(toutRendre(fil, 249.5, 'palette')).toBe(2.49)
  })

  it('rien à rendre, ou unité impossible : 0', () => {
    expect(toutRendre(fil, 0, 'kg')).toBe(0)
    expect(toutRendre(fil, -3, 'kg')).toBe(0)
    expect(toutRendre(cuir, 10, 'bobine')).toBe(0)
  })
})

describe('Pas des compteurs et accords', () => {
  it('pas : 0,1 kg sous 10 kg, 1 sous 100, puis 10 ; 1 bobine ; 1 palette', () => {
    expect(pasPour(9.9, 'kg')).toBe(0.1)
    expect(pasPour(10, 'kg')).toBe(1)
    expect(pasPour(100, 'kg')).toBe(10)
    expect(pasPour(500, 'bobine')).toBe(1)
    expect(pasPour(0.5, 'palette')).toBe(1)
  })

  it('« 3 palettes », « 1,5 bobine », « 2 076 kg »', () => {
    expect(quantiteEnUnites(3, 'palette')).toBe(n('3~palettes'))
    expect(quantiteEnUnites(1.5, 'bobine')).toBe(n('1,5~bobine'))
    expect(quantiteEnUnites(1, 'palette')).toBe(n('1~palette'))
    expect(quantiteEnUnites(2076, 'kg')).toBe(n('2~076~kg'))
    expect(quantiteEnUnites(3, 'Fût')).toBe(n('3~fûts'))
    expect(quantiteEnUnites(2, 'Sacs')).toBe(n('2~sacs'))
    expect(quantiteEnUnites(4, 'ml')).toBe(n('4~ml'))
  })

  it('« ≈ 12 bobines »', () => {
    expect(bobinesApprochees(30, fil)).toBe(n('≈~12~bobines'))
    expect(bobinesApprochees(30, cuir)).toBe('')
  })
})
