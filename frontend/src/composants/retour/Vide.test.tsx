/** Essais de Vide : dit pourquoi, propose une action. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Vide } from './Vide'

describe('Vide', () => {
  it('dit pourquoi la liste est vide', () => {
    render(<Vide action={<button type="button">Joindre un document…</button>}>Aucun document joint.</Vide>)
    expect(screen.getByText('Aucun document joint.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Joindre un document…' })).toBeInTheDocument()
  })
})
