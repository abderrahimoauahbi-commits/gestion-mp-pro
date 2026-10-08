/** Essais de Zone : lignes, nom hors d'un Champ. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Zone } from './Zone'

describe('Zone', () => {
  it('a le nombre de lignes demandé et son nom', () => {
    render(<Zone valeur="" onChange={() => {}} lignes={5} libelle="Motif" />)
    expect(screen.getByRole('textbox', { name: 'Motif' })).toHaveAttribute('rows', '5')
  })
})
