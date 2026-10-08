/** Essai de fumée du socle : l'application se monte, interroge le serveur et dit ce qu'elle obtient. */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { creerClientRequetes } from './lib/requetes'

afterEach(() => vi.unstubAllGlobals())

function monter() {
  render(
    <QueryClientProvider client={creerClientRequetes({ delaiRelance: 0 })}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Socle de l’écran', () => {
  it('dit la version du serveur joint', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Response.json({ version: '0.1.0' })),
    )
    monter()
    expect(screen.getByRole('heading', { name: 'Gestion MP PRO' })).toBeInTheDocument()
    expect(await screen.findByText('Serveur joint — version 0.1.0.')).toBeInTheDocument()
  })

  it('dit « pas de réseau » comme tel', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))),
    )
    monter()
    expect(await screen.findByText(/Le serveur ne répond pas/)).toBeInTheDocument()
  })
})
