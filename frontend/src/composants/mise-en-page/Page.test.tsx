/** Essais de Page : titre de l'onglet du navigateur. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Page, titreDOnglet } from './Page'

describe('Page', () => {
  it('pose le titre de l’onglet et le rend en partant', () => {
    document.title = 'avant'
    const { unmount } = render(
      <Page titre="Commandes">
        <p>contenu</p>
      </Page>,
    )
    expect(document.title).toBe('Commandes — Gestion MP PRO')
    expect(screen.getByText('contenu')).toBeInTheDocument()
    unmount()
    expect(document.title).toBe('avant')
  })

  it('sans titre, le nom de l’application seul', () => {
    expect(titreDOnglet('')).toBe('Gestion MP PRO')
  })
})
