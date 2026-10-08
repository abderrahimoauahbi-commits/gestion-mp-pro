/** Essais de Progression : valeur bornée, dite en pourcentage. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Progression } from './Progression'

describe('Progression', () => {
  it('dit sa part et se borne entre 0 et 100 %', () => {
    const { rerender } = render(<Progression part={0.625} libelle="Reçu" />)
    const barre = screen.getByRole('progressbar', { name: 'Reçu' })
    expect(barre).toHaveAttribute('aria-valuenow', '63')
    expect(barre).toHaveAttribute('aria-valuetext', '63\u00a0%')
    rerender(<Progression part={1.4} libelle="Reçu" />)
    expect(barre).toHaveAttribute('aria-valuenow', '100')
  })
})
