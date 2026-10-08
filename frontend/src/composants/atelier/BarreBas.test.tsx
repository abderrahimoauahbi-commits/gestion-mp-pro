/** Essais de la barre du bas : quatre cases, l'accueil actif seulement à l'exact. */
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import { BarreBas } from './BarreBas'

describe('BarreBas', () => {
  it('quatre cases ; la case de l’écran ouvert est active, l’accueil seulement à l’exact', () => {
    render(
      <MemoryRouter initialEntries={['/atelier/envoyer?ordre=3']}>
        <BarreBas />
      </MemoryRouter>,
    )
    const liens = screen.getAllByRole('link')
    expect(liens.map((l) => l.textContent)).toEqual(['Accueil', 'Envoyer', 'Retour', 'Lots'])
    expect(screen.getByRole('link', { name: 'Envoyer' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Accueil' })).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('link', { name: 'Lots' })).toHaveAttribute('href', '/atelier/chercher')
  })
})
