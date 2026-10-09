/** L'en-tête d'une page : titre, sous-titre, « ? » qui ouvre l'aide, fil au second niveau, actions. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { EnTete } from './EnTete'
import { ContexteAide } from './ouvrirAide'

describe('EnTete', () => {
  it('le « ? » ouvre l’aide de l’écran, ou celle donnée', async () => {
    const ouvrir = vi.fn()
    render(
      <MemoryRouter>
        <ContexteAide.Provider value={ouvrir}>
          <EnTete
            titre="Commandes"
            sous="Les bons de commande"
            actions={<button type="button">Nouvelle commande</button>}
          />
          <EnTete titre="Fiche" aide="commandes" fil={[{ libelle: 'Commandes', vers: '/commandes' }]} />
        </ContexteAide.Provider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { level: 1, name: 'Commandes' })).toBeInTheDocument()
    expect(screen.getByText('Les bons de commande')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Nouvelle commande' })).toBeInTheDocument()
    const aides = screen.getAllByRole('button', { name: 'Aide de l’écran' })
    await userEvent.click(aides[0] as HTMLElement)
    expect(ouvrir).toHaveBeenLastCalledWith(undefined)
    await userEvent.click(aides[1] as HTMLElement)
    expect(ouvrir).toHaveBeenLastCalledWith('commandes')
    expect(screen.getByRole('navigation', { name: 'Fil d’Ariane de la page' })).toHaveTextContent('Commandes')
    expect(screen.getByRole('link', { name: 'Commandes' })).toHaveAttribute('href', '/commandes')
  })

  it('hors coque, pas de « ? »', () => {
    render(<EnTete titre="Connexion" />)
    expect(screen.queryByRole('button', { name: 'Aide de l’écran' })).toBeNull()
  })
})
