/** La coque : barre latérale, barre du haut (fil, recherche pour les rôles métier, cloche, compte), main borné, aide. */
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fauxServeur,
  monterApp,
  prechargerPages,
  reponsesConnecte,
  stockageMemoire,
} from '../../essais/monter'
import { CLE_REPLIEE } from './Coque'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

describe('Coque', () => {
  it('pose le menu, le fil d’Ariane, la recherche, la cloche, le compte et un seul main', async () => {
    fauxServeur(reponsesConnecte('direction'))
    monterApp('/stock?onglet=lots')
    expect(await screen.findByRole('navigation', { name: 'Fil d’Ariane' })).toHaveTextContent(
      'Tous les joursStock, lots & mouvements',
    )
    expect(screen.getByRole('combobox', { name: 'Recherche globale' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Notifications/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Mon compte : MAZARI/ })).toBeInTheDocument()
    expect(screen.getAllByRole('main')).toHaveLength(1)
  })

  it('l’administrateur n’a pas la recherche globale', async () => {
    fauxServeur(reponsesConnecte('administrateur'))
    monterApp('/administration')
    await screen.findByRole('navigation', { name: 'Menu principal' })
    expect(screen.queryByRole('combobox', { name: 'Recherche globale' })).toBeNull()
  })

  it('le menu se replie et le poste s’en souvient', async () => {
    fauxServeur(reponsesConnecte('achats'))
    monterApp('/accueil')
    await userEvent.click(await screen.findByRole('button', { name: 'Masquer le menu' }))
    expect(window.localStorage.getItem(CLE_REPLIEE)).toBe('1')
    expect(screen.getByRole('button', { name: 'Afficher le menu' })).toHaveAttribute('aria-expanded', 'false')
  })

  it('le « ? » ouvre l’aide de l’écran courant', async () => {
    fauxServeur(reponsesConnecte('achats'))
    monterApp('/commandes')
    await userEvent.click(await screen.findByRole('button', { name: 'Aide de l’écran' }))
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Aide — Commandes' })).toBeInTheDocument())
  })
})
