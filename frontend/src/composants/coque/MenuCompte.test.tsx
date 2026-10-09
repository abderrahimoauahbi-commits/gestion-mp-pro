/** Le menu du compte : nom et rôle, Mon compte, Aide, Signaler un besoin (rôles métier), déconnexion confirmée. */
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterDansSession } from '../../essais/monter'
import { initiales, MenuCompte } from './MenuCompte'

afterEach(() => vi.unstubAllGlobals())

describe('MenuCompte', () => {
  it('donne les initiales', () => {
    expect(initiales('Karim BENALI')).toBe('KB')
    expect(initiales('Ahmed')).toBe('A')
    expect(initiales('  ')).toBe('?')
  })

  it('« Se déconnecter » demande d’abord, puis ferme la session', async () => {
    const { session } = monterDansSession(<MenuCompte />, 'achats')
    await userEvent.click(screen.getByRole('button', { name: 'Mon compte : Karim BENALI, Achats' }))
    expect(screen.getByRole('button', { name: 'Signaler un besoin' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Se déconnecter' }))
    expect(screen.getByText('Se déconnecter ?')).toBeInTheDocument()
    expect(session.deconnecter).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Oui, me déconnecter' }))
    await waitFor(() => expect(session.deconnecter).toHaveBeenCalled())
  })

  it('l’administrateur ne signale pas de besoin ; « Mon compte » ouvre /compte', async () => {
    const { routeur } = monterDansSession(<MenuCompte />, 'administrateur')
    await userEvent.click(screen.getByRole('button', { name: /Mon compte : Service informatique/ }))
    expect(screen.queryByRole('button', { name: 'Signaler un besoin' })).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: 'Mon compte' }))
    expect(routeur.state.location.pathname).toBe('/compte')
  })

  it('« Signaler un besoin » ouvre sa fenêtre', async () => {
    fauxServeur({ 'GET /matieres': { corps: [] } })
    monterDansSession(<MenuCompte />, 'alimentation')
    await userEvent.click(screen.getByRole('button', { name: /Mon compte : Ahmed/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Signaler un besoin' }))
    expect(screen.getByRole('dialog', { name: 'Signaler un besoin' })).toBeInTheDocument()
  })
})
