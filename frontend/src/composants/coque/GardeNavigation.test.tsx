/** La garde de navigation : `proteger`, les liens retenus, la saisie de page. */
import { act, render, renderHook, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, Link, RouterProvider } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { proteger, saisieEnCours, useGardeSaisie } from './garde'
import { GardeNavigation } from './GardeNavigation'

function Page({ sale }: { sale: boolean }) {
  useGardeSaisie(sale)
  return (
    <>
      <Link to="/ailleurs">Ailleurs</Link>
      <button type="button" onClick={() => proteger(() => undefined)}>
        Geste
      </button>
    </>
  )
}

function monter(sale: boolean) {
  const routeur = createMemoryRouter(
    [
      {
        path: '*',
        element: (
          <>
            <Page sale={sale} />
            <GardeNavigation />
          </>
        ),
      },
    ],
    { initialEntries: ['/ici'] },
  )
  render(<RouterProvider router={routeur} />)
  return routeur
}

describe('GardeNavigation', () => {
  it('sans saisie, rien n’est retenu', async () => {
    const action = vi.fn()
    proteger(action)
    expect(action).toHaveBeenCalled()
    const routeur = monter(false)
    await userEvent.click(screen.getByRole('link', { name: 'Ailleurs' }))
    expect(routeur.state.location.pathname).toBe('/ailleurs')
  })

  it('avec une saisie, un lien est retenu jusqu’à « Oui, abandonner »', async () => {
    const routeur = monter(true)
    expect(saisieEnCours()).toBe(true)
    await userEvent.click(screen.getByRole('link', { name: 'Ailleurs' }))
    expect(routeur.state.location.pathname).toBe('/ici')
    await userEvent.click(screen.getByRole('button', { name: 'Non, continuer la saisie' }))
    expect(screen.queryByRole('alertdialog')).toBeNull()
    await userEvent.click(screen.getByRole('link', { name: 'Ailleurs' }))
    await userEvent.click(screen.getByRole('button', { name: 'Oui, abandonner' }))
    expect(routeur.state.location.pathname).toBe('/ailleurs')
  })

  it('un geste protégé attend la réponse', async () => {
    const action = vi.fn()
    monter(true)
    act(() => proteger(action))
    expect(action).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Oui, abandonner' }))
    expect(action).toHaveBeenCalled()
  })

  it('la saisie de page se lève au démontage', () => {
    const { unmount } = renderHook(() => useGardeSaisie(true))
    expect(saisieEnCours()).toBe(true)
    unmount()
    expect(saisieEnCours()).toBe(false)
  })
})
