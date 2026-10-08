/** Essais de Chargement : texte honnête, région annoncée. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Chargement } from './Chargement'

describe('Chargement', () => {
  it('dit ce qui se charge', () => {
    render(<Chargement quoi="les lots" />)
    expect(screen.getByRole('status')).toHaveTextContent('Un instant — chargement : les lots…')
  })
})
