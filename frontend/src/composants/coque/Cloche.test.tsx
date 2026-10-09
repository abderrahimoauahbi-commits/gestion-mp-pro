/** La cloche : non lues, « Tout marquer comme lu », une notification ouvre son document (jamais un écran refusé). */
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterDansSession } from '../../essais/monter'
import { Cloche } from './Cloche'

afterEach(() => vi.unstubAllGlobals())

const PAGE = {
  elements: [
    {
      id: 1,
      texte: 'Rupture : PP FRZ-2900',
      lien: '/stock?onglet=matieres',
      ton: 'danger',
      quand: '2026-10-08T08:12:00+01:00',
      lue: false,
    },
    {
      id: 2,
      texte: 'BC-0412 à approuver',
      lien: '/cockpit',
      ton: 'alerte',
      quand: '2026-10-07T16:40:00+01:00',
      lue: true,
    },
  ],
  total: 2,
  suivant: null,
  non_lues: 1,
}

describe('Cloche', () => {
  it('compte les non lues, ouvre une notification et la marque lue', async () => {
    const appels = fauxServeur({
      'GET /notifications': { corps: PAGE },
      'POST /notifications/1/lue': { statut: 204 },
      'POST /notifications/lues': { statut: 204 },
    })
    const { routeur } = monterDansSession(<Cloche role="achats" />, 'achats', '/accueil')
    const bouton = await screen.findByRole('button', { name: 'Notifications : 1 non lue(s)' })
    await userEvent.click(bouton)
    expect(screen.getByRole('dialog', { name: 'Notifications' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Rupture : PP FRZ-2900/ }))
    await waitFor(() => expect(routeur.state.location.search).toBe('?onglet=matieres'))
    expect(appels.some((a) => a.methode === 'POST' && a.chemin === '/notifications/1/lue')).toBe(true)
  })

  it('une notification vers un écran refusé ne navigue pas ; « Tout marquer comme lu »', async () => {
    const appels = fauxServeur({
      'GET /notifications': { corps: PAGE },
      'POST /notifications/lues': { statut: 204 },
    })
    const { routeur } = monterDansSession(<Cloche role="achats" />, 'achats', '/accueil')
    await userEvent.click(await screen.findByRole('button', { name: /Notifications/ }))
    await userEvent.click(screen.getByRole('button', { name: /BC-0412/ }))
    expect(routeur.state.location.pathname).toBe('/accueil')
    await userEvent.click(screen.getByRole('button', { name: /Notifications/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Tout marquer comme lu' }))
    await waitFor(() => expect(appels.some((a) => a.chemin === '/notifications/lues')).toBe(true))
  })

  it('dit « Aucune notification. »', async () => {
    fauxServeur({ 'GET /notifications': { corps: { elements: [], total: 0, suivant: null, non_lues: 0 } } })
    monterDansSession(<Cloche role="administrateur" />, 'administrateur')
    await userEvent.click(await screen.findByRole('button', { name: 'Notifications' }))
    expect(await screen.findByText('Aucune notification.')).toBeInTheDocument()
  })
})
