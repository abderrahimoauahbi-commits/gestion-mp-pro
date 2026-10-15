/**
 * La date du dernier ordre lue sur les deux plus récents validés et les deux plus récents annulés
 * (`useDernierOrdre`) est celle que donnait la liste entière, quel que soit l'ordre écarté.
 */
import { describe, expect, it } from 'vitest'

import { DERNIERS } from './dernierOrdre'
import { dernierOrdre } from './ordreBlocages'

type O = { id: number; date: string; statut: 'brouillon' | 'valide' | 'annule' }

/** Un hasard reproductible (essais). */
function hasard(graine: number): () => number {
  let x = graine
  return () => {
    x = (x * 1103515245 + 12345) % 2 ** 31
    return x / 2 ** 31
  }
}

/** Les `n` plus récents d'un statut, comme la route 135 (date, puis n° d'entrée). */
const recents = (tous: readonly O[], statut: O['statut'], n: number) =>
  tous
    .filter((o) => o.statut === statut)
    .sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id)
    .slice(0, n)

describe('useDernierOrdre', () => {
  it('deux par statut suffisent : même date que sur la liste entière, même en écartant un ordre', () => {
    const tirer = hasard(2029)
    const statuts: O['statut'][] = ['brouillon', 'valide', 'valide', 'valide', 'annule']
    for (let essai = 0; essai < 300; essai++) {
      const tous: O[] = Array.from({ length: Math.floor(tirer() * 12) }, (_, i) => ({
        id: i + 1,
        date: `2029-10-${String(1 + Math.floor(tirer() * 5)).padStart(2, '0')}`,
        statut: statuts[Math.floor(tirer() * statuts.length)] ?? 'valide',
      }))
      const lus = [...recents(tous, 'valide', DERNIERS), ...recents(tous, 'annule', DERNIERS)]
      for (const sauf of [undefined, null, ...tous.map((o) => o.id)])
        expect(dernierOrdre(lus, sauf)).toBe(dernierOrdre(tous, sauf))
    }
  })
})
