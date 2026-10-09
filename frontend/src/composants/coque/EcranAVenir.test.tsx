/** La page « à venir » d'un écran déclaré : titre, aide, onglets permis au rôle, lot qui la réalise. */
import { screen } from '@testing-library/react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterApp, prechargerPages, reponsesConnecte } from '../../essais/monter'

beforeAll(prechargerPages)
afterEach(() => vi.unstubAllGlobals())

describe('EcranAVenir', () => {
  it('ne montre que les onglets permis au rôle', async () => {
    fauxServeur(reponsesConnecte('alimentation'))
    monterApp('/operations?onglet=retour_machine')
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Ouvertures, transferts, ajustements' }),
    ).toBeInTheDocument()
    expect(screen.getAllByRole('tab').map((t) => t.textContent)).toEqual([
      'Transferts',
      'Retours des machines',
    ])
    expect(
      screen.getByText(/Cet écran arrive avec le lot F6 \(onglet « Retours des machines »\)/),
    ).toBeInTheDocument()
    expect(document.title).toBe('Ouvertures, transferts, ajustements — Gestion MP PRO')
  })
})
