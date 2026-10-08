/** Essais de Bascule : vue choisie, vue dans l'adresse. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router'
import { describe, expect, it } from 'vitest'

import { Bascule, useVueAdresse } from './Bascule'

const VUES = [
  { cle: 'clos', libelle: 'Clos' },
  { cle: 'annules', libelle: 'Annulés' },
] as const

function Essai() {
  const [vue, choisir] = useVueAdresse(['clos', 'annules'], 'clos')
  const { search } = useLocation()
  return (
    <>
      <Bascule vues={VUES} valeur={vue} onChange={choisir} />
      <output>{search}</output>
    </>
  )
}

describe('Bascule', () => {
  it('marque la vue choisie et l’écrit dans ?vue= (la vue par défaut n’écrit rien)', async () => {
    render(
      <MemoryRouter initialEntries={['/importations?onglet=clos']}>
        <Essai />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: 'Clos' })).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(screen.getByRole('button', { name: 'Annulés' }))
    expect(screen.getByRole('status')).toHaveTextContent('?onglet=clos&vue=annules')
    expect(screen.getByRole('button', { name: 'Annulés' })).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(screen.getByRole('button', { name: 'Clos' }))
    expect(screen.getByRole('status')).toHaveTextContent('?onglet=clos')
  })
})
