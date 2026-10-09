/** Le calcul de la recette à la frappe, comme le serveur (CALCULS § 3.5). */
import { describe, expect, it } from 'vitest'

import { aCorriger, bilan, calculer, etatRole, grouper, reste } from './recette'
import { depuisFiche } from './formeQualite'
import { qualiteEssai } from './donneesEssai'

const F = { perte: 1.05, cours: { USD: 10, MAD: 1 } }

describe('recette', () => {
  it('rôle au poids : kg/m² = part × poids ; coût = kg × prix × cours × perte', () => {
    const l = calculer(depuisFiche(qualiteEssai().recette[0]!), 1.2, false, F)
    expect(l.ml_m2).toBeNull()
    expect(l.kg_m2).toBeCloseTo(1.2)
    expect(l.cout_m2).toBeCloseTo(1.2 * 2.5 * 10 * 1.05)
  })

  it('rôle au mètre : le poids est en ml/m², les kg viennent de la densité', () => {
    const cuir = { ...depuisFiche(qualiteEssai().recette[1]!), pourcentage: 50 }
    const l = calculer(cuir, 2, true, F)
    expect(l.ml_m2).toBeCloseTo(1)
    expect(l.kg_m2).toBeCloseTo(0.014)
  })

  it('sans les cours (alimentation), pas de coût', () => {
    expect(calculer(depuisFiche(qualiteEssai().recette[0]!), 1.2, false, null).cout_m2).toBeNull()
  })

  it('état d’un rôle à 0,01 point près ; reste pour une matière ajoutée', () => {
    expect(etatRole(99.995, 2)).toBe('complet')
    expect(etatRole(98, 1)).toBe('manque')
    expect(etatRole(102, 2)).toBe('trop')
    expect(etatRole(0, 0)).toBe('vide')
    expect(reste(60)).toBe(40)
    expect(reste(130)).toBe(0)
  })

  it('un rôle pesant sans matière bloque une qualité en service dont la recette change ou est commencée (D-05)', () => {
    const roles = [
      { role_id: 1, role: 'Poil', lineaire: false },
      { role_id: 7, role: 'Ruban', lineaire: true },
    ]
    const poids = new Map([
      [1, 1.2],
      [7, 0.5],
    ])
    const b = bilan(grouper(roles, poids, [depuisFiche(qualiteEssai().recette[0]!)], F))
    expect(b.sansMatiere).toEqual(['Ruban'])
    expect(aCorriger(b, true, false)).toEqual(['Ruban'])
    expect(aCorriger(b, false, true)).toEqual([])
    const vide = bilan(grouper(roles, poids, [], F))
    expect(aCorriger(vide, true, false)).toEqual([])
    expect(aCorriger(vide, true, true)).toEqual(['Poil', 'Ruban'])
  })
})
