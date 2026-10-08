/** Essais de Carte : titre, actions à droite, ton. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Carte } from './Carte'

describe('Carte', () => {
  it('rend le titre en h2, le sous-titre et les actions', () => {
    render(
      <Carte titre="Lots" sous="du magasin principal" actions={<button type="button">Exporter</button>}>
        corps
      </Carte>,
    )
    expect(screen.getByRole('heading', { level: 2, name: 'Lots' })).toBeInTheDocument()
    expect(screen.getByText('du magasin principal')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Exporter' })).toBeInTheDocument()
  })

  it('sans titre ni actions, pas d’en-tête ; le ton pose son filet', () => {
    const { container } = render(<Carte ton="critique">corps</Carte>)
    expect(container.querySelector('header')).toBeNull()
    expect(container.querySelector('section')).toHaveClass('ton-critique')
  })
})
