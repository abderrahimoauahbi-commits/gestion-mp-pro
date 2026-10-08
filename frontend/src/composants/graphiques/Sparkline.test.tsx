/** Essais de la sparkline : tendance dite en texte. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Sparkline } from './Sparkline'

describe('Sparkline', () => {
  it('dit sa tendance et trace ses morceaux', () => {
    const { container } = render(<Sparkline libelle="Couverture" valeurs={[12, 14, null, 18]} />)
    expect(screen.getByRole('img', { name: 'Couverture : de 12 à 18' })).toBeInTheDocument()
    expect(container.querySelectorAll('polyline')).toHaveLength(2)
  })
})
