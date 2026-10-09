/**
 * « Demande pendant le délai » : l'addition affichée tombe juste (critère du lot F2). Les termes
 * arrondis au dixième de kilo s'additionnent exactement au total affiché, lui-même l'arrondi du
 * total du serveur ; les indicateurs de la fiche et la carte lisent les mêmes chiffres.
 */
import { describe, expect, it } from 'vitest'

import { arrondi } from '../../lib/format'
import { affichageMatiere, repartir, tableauJuste } from './addition'
import fiche from './essais/fiche-matiere.json'
import type { LigneStock } from './types'

const somme = (v: readonly number[]) =>
  arrondi(
    v.reduce((a, b) => a + b, 0),
    3,
  )

const ligne = (p: Partial<LigneStock>): LigneStock => ({ ...(fiche.ligne as LigneStock), ...p })

describe('repartir', () => {
  it('porte le reste de l’arrondi sur le terme qui en a perdu le plus', () => {
    // 33,34 + 33,33 + 33,33 = 100 ; arrondis séparément : 33,3 × 3 = 99,9.
    expect(repartir([33.34, 33.33, 33.33], 100)).toEqual([33.4, 33.3, 33.3])
    expect(somme(repartir([33.34, 33.33, 33.33], 100))).toBe(100)
  })

  it('garde les termes fixés et tombe sur l’arrondi du total', () => {
    const r = repartir([1737.9, 0.04, -340.143], 1397.797, { fixes: [0] })
    expect(r[0]).toBe(1737.9)
    expect(somme(r)).toBe(1397.8)
  })

  it('termes signés : une soustraction se reporte aussi', () => {
    for (const [d, c, x] of [
      [100.04, 0.04, 33.33],
      [12.25, 7.25, 0.45],
      [0.05, 0.05, 0.05],
      [999.95, 0.05, 1000],
    ] as const) {
      const projete = d + c - x
      const r = repartir([arrondi(d, 1), c, -x], projete, { fixes: [0] })
      expect(somme(r)).toBe(arrondi(projete, 1))
    }
  })
})

describe('affichageMatiere (fiche matière, carte « Où se trouve la matière »)', () => {
  const types = new Map([
    ['Magasin principal', 'stock_courant'],
    ['ATELIER', 'stock_courant'],
    ['Quarantaine', 'quarantaine'],
  ])

  it('les trois additions tombent juste avec les vrais chiffres du serveur', () => {
    const a = affichageMatiere(fiche.ligne as LigneStock, types)
    const courants = a.magasins.filter((m) => !m.quarantaine).map((m) => m.kg)
    const bloques = a.magasins.filter((m) => m.quarantaine).map((m) => m.kg)
    expect(somme([...courants, a.metiers])).toBe(a.disponible)
    expect(somme([a.disponible, ...bloques])).toBe(a.stock)
    expect(somme([a.disponible, a.commande, -a.demande])).toBe(a.projete)
  })

  it('des chiffres qui ne tombent pas juste une fois arrondis séparément', () => {
    const l = ligne({
      par_magasin: { 'Magasin principal': 50.04, ATELIER: 50.04, Quarantaine: 10.04 },
      stock_net: 110.12,
      stock_machine: 0.04,
      stock_quarantaine: 10.04,
      stock_disponible: 100.12,
      bc_en_cours: 0.04,
      demande_delai: 33.33,
      stock_projete: 100.12 + 0.04 - 33.33,
    })
    const a = affichageMatiere(l, types)
    expect(a.disponible).toBe(100.1)
    expect(a.projete).toBe(66.8)
    expect(somme([a.disponible, a.commande, -a.demande])).toBe(a.projete)
    expect(somme([...a.magasins.filter((m) => !m.quarantaine).map((m) => m.kg), a.metiers])).toBe(
      a.disponible,
    )
    expect(somme([a.disponible, a.quarantaine])).toBe(a.stock)
  })
})

describe('tableauJuste (d’où vient le besoin)', () => {
  it('chaque colonne tombe sur son total, et les totaux sur le total général', () => {
    const lignes = [
      [0.4, 10.4, 5.5],
      [0.4, 10.4, 5.5],
      [0.4, 0.4, 0.4],
    ]
    const totaux = [1.2, 21.2, 11.4]
    const t = tableauJuste(lignes, totaux)
    t.totaux.forEach((tot, i) => expect(somme(t.lignes.map((l) => l[i] ?? 0))).toBe(tot))
    expect(somme(t.totaux)).toBe(Math.round(somme(totaux)))
  })
})
