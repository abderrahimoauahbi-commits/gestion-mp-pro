/**
 * Prix du fournisseur (U2, audit n° 2 des achats) : une matière dont la fiche est au mètre se confirme
 * au mètre — le corps envoyé dit `unite: 'ml'`, le catalogue se compare au kilo, « reprendre le
 * catalogue » propose le prix au mètre — ; une matière au kilo ne change pas.
 */
import { describe, expect, it } from 'vitest'

import { ficheEssai } from './donneesEssai'
import type { CommandeFiche, LigneCommande } from './types'
import {
  changeantAuCatalogue,
  corpsPrix,
  depuisKg,
  enKg,
  reprendreCatalogue,
  uniteDe,
  versFormePrix,
} from './VoletPrix'

/** Un cuir au mètre : densité 0,014 kg/ml, 5,285714 / kg confirmé (soit 0,074 / ml). */
function cuir(c: CommandeFiche, autres: Partial<LigneCommande> = {}): LigneCommande {
  return {
    ...c.lignes[0]!,
    id: 7,
    reference: 'CUIR 10 mm',
    unite_prix: 'ml',
    kg_par_ml: 0.014,
    quantite: 140,
    prix: 5.285714,
    prix_confirme: true,
    prix_catalogue: 5.285714,
    devise_catalogue: c.devise,
    ...autres,
  }
}

describe('VoletPrix : un prix au mètre se confirme au mètre', () => {
  const base = ficheEssai()
  const c: CommandeFiche = { ...base, lignes: [base.lignes[0]!, cuir(base)] }

  it('l’unité suit la fiche : au mètre seulement avec une densité', () => {
    expect(uniteDe({ unite_prix: 'ml', kg_par_ml: 0.014 })).toBe('ml')
    expect(uniteDe({ unite_prix: 'ml', kg_par_ml: 0 })).toBe('kg')
    expect(uniteDe({ unite_prix: 'kg', kg_par_ml: 0.014 })).toBe('kg')
  })

  it('aller-retour kilo ↔ mètre par la densité', () => {
    const l = c.lignes[1]!
    expect(depuisKg(l, 5.285714)).toBeCloseTo(0.074, 6)
    expect(enKg(l, 0.074)).toBeCloseTo(5.285714, 5)
    expect(depuisKg(c.lignes[0]!, 27.5)).toBe(27.5)
  })

  it('la forme part du prix confirmé lu au mètre, le corps envoyé dit l’unité', () => {
    const f = versFormePrix(c)
    expect(f.prix['7']).toBeCloseTo(0.074, 6)
    expect(f.prix['5']).toBe(27.5)
    const corps = corpsPrix(c, { ...f, prix: { '5': null, '7': 0.08 } }, 3)
    expect(corps.lignes).toEqual([{ ligne_id: 7, prix: 0.08, unite: 'ml' }])
    expect(corpsPrix(c, { ...f, prix: { '5': 28, '7': null } }, 3).lignes).toEqual([
      { ligne_id: 5, prix: 28, unite: 'kg' },
    ])
  })

  it('le catalogue se compare au kilo : 0,074 / ml ne change rien, 0,08 / ml le change', () => {
    const f = versFormePrix(c)
    expect(changeantAuCatalogue(c, { ...f, prix: { '5': null, '7': 0.074 } })).toEqual([])
    expect(changeantAuCatalogue(c, { ...f, prix: { '5': null, '7': 0.08 } })).toEqual(['CUIR 10 mm'])
  })

  it('« reprendre le catalogue » propose le prix au mètre pour une fiche au mètre', () => {
    const f = { ...versFormePrix(c), prix: { '5': null, '7': null } }
    const repris = reprendreCatalogue(c, f)
    expect(repris.prix['7']).toBeCloseTo(0.074, 6)
    expect(repris.prix['5']).toBe(c.lignes[0]!.prix_catalogue)
  })
})
