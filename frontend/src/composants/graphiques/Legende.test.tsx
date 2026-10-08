/** Essais de la légende : couleur et trait de chaque série, unité dite. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Legende } from './Legende'

describe('Legende', () => {
  it('montre le trait de chaque série et son unité', () => {
    const { container } = render(
      <Legende
        series={[
          { nom: 'Rouge A', valeurs: [], couleur: '#c62828', trait: '', unite: 'kg' },
          { nom: 'Rouge B', valeurs: [], couleur: '#c62828', trait: '8 5', unite: 'kg' },
        ]}
      />,
    )
    expect(screen.getByText('Rouge A (kg)')).toBeInTheDocument()
    const traits = container.querySelectorAll('line')
    expect(traits[0]?.getAttribute('stroke-dasharray')).toBeNull()
    expect(traits[1]?.getAttribute('stroke-dasharray')).toBe('8 5')
  })
})
