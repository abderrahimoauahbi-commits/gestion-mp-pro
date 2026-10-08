/** La garde d'un écran : page chargée une fois par écran, refus vers l'accueil (voir aussi App.test.tsx). */
import { describe, expect, it } from 'vitest'

import { ecranParChemin } from '../../routes'
import { pageDe } from './GardeEcran'

describe('GardeEcran', () => {
  it('charge la page d’un écran une seule fois', () => {
    const e = ecranParChemin('/aide')
    expect(e).toBeDefined()
    if (e) expect(pageDe(e)).toBe(pageDe(e))
  })
})
