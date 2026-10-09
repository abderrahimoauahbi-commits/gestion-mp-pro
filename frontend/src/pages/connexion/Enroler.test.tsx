/** L'enrôlement d'un téléphone : un seul envoi du jeton, le résultat dit. */
import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterApp } from '../../essais/monter'

afterEach(() => vi.unstubAllGlobals())

describe('Enroler', () => {
  it('envoie le jeton une fois et dit que le téléphone est enrôlé', async () => {
    const appels = fauxServeur({ 'POST /appareils/enroler': { statut: 204 } })
    monterApp('/enroler?jeton=abc')
    expect(await screen.findByText(/Ce téléphone est enrôlé/)).toBeInTheDocument()
    expect(appels.filter((a) => a.chemin === '/appareils/enroler')).toEqual([
      { methode: 'POST', chemin: '/appareils/enroler', corps: { jeton: 'abc' } },
    ])
  })

  it('dit un jeton refusé ou absent', async () => {
    fauxServeur({
      'POST /appareils/enroler': {
        statut: 404,
        corps: { detail: 'Ce lien d’enrôlement a expiré.', code: 'introuvable' },
      },
    })
    monterApp('/enroler?jeton=vieux')
    expect(await screen.findByText('Ce lien d’enrôlement a expiré.')).toBeInTheDocument()
  })

  it('sans jeton', async () => {
    fauxServeur({})
    monterApp('/enroler')
    expect(await screen.findByText(/lien d’enrôlement est incomplet/)).toBeInTheDocument()
  })
})
