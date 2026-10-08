/** Essais de l'historique : différences avant → après lisibles, vide dit. */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { creerClientRequetes } from '../../lib/requetes'
import { Historique, valeurLisible } from './Historique'

function monter(reponse: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => Response.json(reponse)),
  )
  render(
    <QueryClientProvider client={creerClientRequetes({ delaiRelance: 0 })}>
      <Historique objet="commande" id={12} />
    </QueryClientProvider>,
  )
}

describe('Historique', () => {
  it('dit qui, quand, quoi, et chaque différence avant → après à la française', async () => {
    monter([
      {
        id: 1,
        quand: '2026-10-08T09:12:00',
        par: 'Karim',
        action: 'Bon modifié',
        changements: [
          { libelle: 'Livraison prévue', avant: '2026-10-20', apres: '2026-10-25' },
          { libelle: 'Quantité (kg)', avant: 5029.5, apres: 6000 },
          { libelle: 'Observations', avant: null, apres: 'Urgent' },
        ],
      },
    ])
    expect(await screen.findByText('Bon modifié')).toBeInTheDocument()
    expect(screen.getByText('08/10/2026 09:12 · Karim')).toBeInTheDocument()
    expect(screen.getByText('Livraison prévue', { exact: false })).toHaveTextContent(
      'Livraison prévue : 20/10/2026 → 25/10/2026',
    )
    expect(screen.getByText('Quantité (kg)', { exact: false })).toHaveTextContent('5 029,5 → 6 000')
    expect(screen.getByText('Observations', { exact: false })).toHaveTextContent('— → Urgent')
  })

  it('sans ligne, le dit', async () => {
    monter([])
    expect(await screen.findByText('Aucune modification enregistrée.')).toBeInTheDocument()
  })

  it('valeurLisible : oui/non, vide, horodatage', () => {
    expect(valeurLisible(true)).toBe('oui')
    expect(valeurLisible('')).toBe('—')
    expect(valeurLisible('2026-10-08T14:05:00')).toBe('08/10/2026 14:05')
  })
})
