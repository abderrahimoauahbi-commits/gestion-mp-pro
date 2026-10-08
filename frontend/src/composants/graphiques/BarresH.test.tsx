/** Essais des barres horizontales : proportion au plus grand, unité dite. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { BarresH } from './BarresH'

describe('BarresH', () => {
  it('chaque barre est proportionnelle au plus grand, la valeur dit son unité', () => {
    const { container } = render(
      <BarresH
        libelle="Achats par fournisseur"
        unite="MAD"
        lignes={[
          { libelle: 'HASIRCI', valeur: 2000, detail: '42 %' },
          { libelle: 'BELKA', valeur: 500 },
        ]}
      />,
    )
    expect(screen.getByRole('list', { name: 'Achats par fournisseur' })).toBeInTheDocument()
    expect(screen.getByText(/^2 000 MAD/)).toBeInTheDocument()
    const barres = container.querySelectorAll<HTMLElement>('.barre')
    expect(barres[0]?.style.width).toBe('100%')
    expect(barres[1]?.style.width).toBe('25%')
  })
})
