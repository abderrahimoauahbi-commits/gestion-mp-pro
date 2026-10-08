/** Essais des tuiles : un lien par geste, détail, ton. */
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import { Tuile, Tuiles } from './Tuile'

describe('Tuile', () => {
  it('mène à son écran et dit son détail', () => {
    render(
      <MemoryRouter>
        <Tuiles>
          <Tuile
            titre="Envoyer aux machines"
            detail="2 brouillons"
            vers="/atelier/envoyer"
            icone="envoyer"
            ton="attention"
          />
          <Tuile titre="Trouver un lot" vers="/atelier/chercher" />
        </Tuiles>
      </MemoryRouter>,
    )
    expect(screen.getByRole('navigation', { name: 'Gestes de l’atelier' })).toBeInTheDocument()
    const tuile = screen.getByRole('link', { name: /Envoyer aux machines/ })
    expect(tuile).toHaveAttribute('href', '/atelier/envoyer')
    expect(tuile).toHaveTextContent('2 brouillons')
    expect(tuile).toHaveClass('tuile', 'attention')
  })
})
