/** Essais de Grille : nombre de colonnes. */
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Grille } from './Grille'

describe('Grille', () => {
  it('pose la classe du nombre de colonnes (deux par défaut)', () => {
    const a = render(<Grille>x</Grille>)
    expect(a.container.firstChild).toHaveClass('grille', 'c2')
    const b = render(<Grille colonnes={4}>x</Grille>)
    expect(b.container.firstChild).toHaveClass('c4')
  })
})
