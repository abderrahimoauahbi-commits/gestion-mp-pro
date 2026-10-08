/** Essais des parties du DataTable : cycle du tri, pied de totaux par unité, colonnes cachées. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { Colonne } from './colonnes'
import { piedDeColonne, totalLisible } from './colonnes'
import { Pied, triSuivant } from './DataTableParties'

type L = { kg: number; u: string; code: string }
const COLS: Colonne<L>[] = [
  { cle: 'code', titre: 'Code', cache: true },
  { cle: 'libelle', titre: 'Matière', valeur: () => 'x' },
  { cle: 'kg', titre: 'Sorti', droite: true, total: true, unite: (l) => l.u },
]

describe('DataTableParties', () => {
  it('tri : croissant, décroissant, puis plus de tri ; une autre colonne repart en croissant', () => {
    expect(triSuivant(null, 'a')).toEqual({ cle: 'a', sens: 1 })
    expect(triSuivant({ cle: 'a', sens: 1 }, 'a')).toEqual({ cle: 'a', sens: -1 })
    expect(triSuivant({ cle: 'a', sens: -1 }, 'a')).toBeNull()
    expect(triSuivant({ cle: 'a', sens: -1 }, 'b')).toEqual({ cle: 'b', sens: 1 })
  })

  it('le pied additionne par unité, sans la colonne cachée ; rien sans lignes', () => {
    const lignes = [
      { kg: 251.3, u: 'kg', code: 'A' },
      { kg: 1.9, u: 'ml', code: 'B' },
      { kg: -27.8, u: 'kg', code: 'C' },
    ]
    expect(piedDeColonne(COLS[2]!, lignes)).toBe('223,5\u00a0kg · 1,9\u00a0ml')
    expect(totalLisible(1234.4, 'MAD')).toBe('1\u00a0234\u00a0MAD')
    const { container, rerender } = render(
      <table>
        <Pied colonnes={COLS} lignes={lignes} />
      </table>,
    )
    expect(screen.getAllByRole('cell').map((c) => c.textContent)).toEqual([
      'Total',
      '223,5\u00a0kg · 1,9\u00a0ml',
    ])
    rerender(
      <table>
        <Pied colonnes={COLS} lignes={[]} />
      </table>,
    )
    expect(container.querySelector('tfoot')).toBeNull()
  })
})
