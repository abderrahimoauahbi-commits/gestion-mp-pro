/** Essais de Note : ton et tenue sur une ligne. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Note } from './Note'

describe('Note', () => {
  it('pose son ton ; sur une ligne, le texte entier en infobulle', () => {
    const methode = 'Coût moyen pondéré : chaque entrée recalcule le coût du stock restant.'
    const { container } = render(
      <Note ton="attention" uneLigne={methode}>
        {methode}
      </Note>,
    )
    expect(container.firstChild).toHaveClass('note', 'attention', 'uneLigne')
    expect(container.firstChild).toHaveAttribute('title', methode)
    expect(screen.getByText(methode)).toBeInTheDocument()
  })
})
