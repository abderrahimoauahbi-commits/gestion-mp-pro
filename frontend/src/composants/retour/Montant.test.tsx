/** Essais de Montant : devise dite, exact en infobulle, devises jamais additionnées. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Montant } from './Montant'

describe('Montant', () => {
  it('entier avec la devise, le centime en infobulle ; abrégé au-delà du million', () => {
    const { rerender } = render(<Montant valeur={1234.56} devise="MAD" />)
    expect(screen.getByText('1 235 MAD')).toHaveAttribute('title', '1\u00a0234,56\u00a0MAD')
    rerender(<Montant valeur={17398184.2} devise="MAD" court />)
    expect(screen.getByText('17,4 M MAD')).toHaveAttribute('title', '17\u00a0398\u00a0184,20\u00a0MAD')
    rerender(<Montant valeur={12.5} devise="USD" precis />)
    expect(screen.getByText('12,50 USD')).not.toHaveAttribute('title')
  })

  it('plusieurs devises côte à côte, jamais additionnées', () => {
    render(<Montant parDevise={{ EUR: 53132, USD: 61888 }} />)
    expect(screen.getByText('61 888 USD · 53 132 EUR')).toBeInTheDocument()
  })
})
