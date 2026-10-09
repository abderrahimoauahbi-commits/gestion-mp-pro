/** Essais des onglets : sélection, libellé court + infobulle, compteur, saisie non enregistrée, clavier. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { useGardeSaisie } from '../coque/garde'
import { GardeNavigation } from '../coque/GardeNavigation'
import { Onglets, type Onglet } from './Onglets'

type Cle = 'valorisation' | 'opportunites' | 'controles'
const ONGLETS: Onglet<Cle>[] = [
  { cle: 'valorisation', libelle: 'Valorisation', compte: 1234 },
  { cle: 'opportunites', libelle: 'Opportunités d’économies', court: 'Opportunités' },
  { cle: 'controles', libelle: 'Contrôles', sale: true },
]

function Essai({ surChange = () => {} }: { surChange?: (c: Cle) => void }) {
  const [actif, setActif] = useState<Cle>('valorisation')
  return (
    <Onglets
      onglets={ONGLETS}
      actif={actif}
      onChange={(c) => {
        setActif(c)
        surChange(c)
      }}
    />
  )
}

describe('Onglets', () => {
  it('marque l’onglet actif, et le clic en choisit un autre', async () => {
    const vu = vi.fn()
    render(<Essai surChange={vu} />)
    expect(screen.getByRole('tab', { name: /Valorisation/ })).toHaveAttribute('aria-selected', 'true')
    await userEvent.click(screen.getByRole('tab', { name: 'Opportunités d’économies' }))
    expect(vu).toHaveBeenCalledWith('opportunites')
    expect(screen.getByRole('tab', { name: 'Opportunités d’économies' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })

  it('libellé court affiché, nom complet en infobulle ; compteur à la française ; « • » si non enregistré', () => {
    render(<Essai />)
    const court = screen.getByRole('tab', { name: 'Opportunités d’économies' })
    expect(court).toHaveTextContent('Opportunités')
    expect(court).toHaveAttribute('title', 'Opportunités d’économies')
    expect(screen.getByRole('tab', { name: /Valorisation/ })).toHaveTextContent('Valorisation1 234')
    expect(screen.getByRole('tab', { name: /Contrôles/ })).toHaveTextContent('saisie non enregistrée')
  })

  it('les flèches passent d’un onglet à l’autre et bouclent', async () => {
    render(<Essai />)
    screen.getByRole('tab', { name: /Valorisation/ }).focus()
    await userEvent.keyboard('{ArrowLeft}')
    expect(screen.getByRole('tab', { name: /Contrôles/ })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: /Contrôles/ })).toHaveFocus()
    await userEvent.keyboard('{Home}')
    expect(screen.getByRole('tab', { name: /Valorisation/ })).toHaveAttribute('aria-selected', 'true')
  })
})

function OngletsGardes({ sale }: { sale: boolean }) {
  const [actif, setActif] = useState<Cle>('valorisation')
  useGardeSaisie(sale)
  return <Onglets garde onglets={ONGLETS} actif={actif} onChange={setActif} />
}

function monterGardes(sale: boolean) {
  const routeur = createMemoryRouter(
    [
      {
        path: '*',
        element: (
          <>
            <OngletsGardes sale={sale} />
            <GardeNavigation />
          </>
        ),
      },
    ],
    { initialEntries: ['/analyse'] },
  )
  render(<RouterProvider router={routeur} />)
}

describe('Onglets gardés', () => {
  it('avec une saisie en cours, changer d’onglet demande d’abord de l’abandonner', async () => {
    monterGardes(true)
    const autre = screen.getByRole('tab', { name: 'Opportunités d’économies' })
    await userEvent.click(autre)
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Les abandonner ?')
    await userEvent.click(screen.getByRole('button', { name: 'Non, continuer la saisie' }))
    expect(screen.getByRole('tab', { name: /Valorisation/ })).toHaveAttribute('aria-selected', 'true')
    await userEvent.click(autre)
    await userEvent.click(screen.getByRole('button', { name: 'Oui, abandonner' }))
    expect(autre).toHaveAttribute('aria-selected', 'true')
  })

  it('sans saisie, l’onglet change tout de suite', async () => {
    monterGardes(false)
    await userEvent.click(screen.getByRole('tab', { name: 'Opportunités d’économies' }))
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(screen.getByRole('tab', { name: 'Opportunités d’économies' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })
})
