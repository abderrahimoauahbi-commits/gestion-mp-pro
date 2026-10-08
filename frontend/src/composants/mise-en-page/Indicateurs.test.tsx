/** Essais d'Indicateurs : une région nommée qui porte la rangée. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Indicateurs } from './Indicateurs'

describe('Indicateurs', () => {
  it('est une région nommée qui contient ses indicateurs', () => {
    render(
      <Indicateurs>
        <div>a</div>
        <div>b</div>
      </Indicateurs>,
    )
    const region = screen.getByRole('region', { name: 'Indicateurs' })
    expect(region).toHaveClass('indicateurs')
    expect(region.children).toHaveLength(2)
  })
})
