/** Un texte d'aide : liens filtrés par rôle, « (réservé : …) » pour un écran refusé. */
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import { TexteAide } from './TexteAide'

const texte = 'Voir le [Cockpit](/cockpit), le **stock** et [Mode d’emploi](/aide).'

describe('TexteAide', () => {
  it('un écran permis est un lien', () => {
    render(
      <MemoryRouter>
        <TexteAide texte={texte} role="direction" />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: 'Cockpit' })).toHaveAttribute('href', '/cockpit')
    expect(screen.getByText('stock').tagName).toBe('STRONG')
  })

  it('un écran refusé est nommé sans lien, avec les rôles qui l’ouvrent', () => {
    render(
      <MemoryRouter>
        <TexteAide texte={texte} role="alimentation" />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('link', { name: 'Cockpit' })).toBeNull()
    expect(screen.getByText('(réservé : Direction)', { exact: false })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Mode d’emploi' })).toBeInTheDocument()
  })
})
