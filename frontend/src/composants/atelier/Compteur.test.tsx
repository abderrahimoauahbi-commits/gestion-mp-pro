/** Essais du compteur : pas selon la quantité, − et + au multiple du pas, bornes dites, raisons des boutons grisés. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import type { Unite } from '../../lib/unites'
import { Compteur, pasSuivant } from './Compteur'

function Essai({ initial, unite = 'kg', max }: { initial: number | null; unite?: Unite; max?: number }) {
  const [v, setV] = useState<number | null>(initial)
  return (
    <>
      <Compteur valeur={v} onChange={setV} libelle="Quantité" unite={unite} max={max} />
      <output>{String(v)}</output>
    </>
  )
}

describe('Compteur', () => {
  it('pasSuivant ramène au multiple du pas', () => {
    expect(pasSuivant(2.37, 0.1, 1)).toBe(2.4)
    expect(pasSuivant(2.37, 0.1, -1)).toBe(2.3)
    expect(pasSuivant(2.4, 0.1, 1)).toBe(2.5)
    expect(pasSuivant(150, 10, -1)).toBe(140)
  })

  it('le pas suit la quantité : 0,1 kg sous 10, 1 kg sous 100, 10 kg au-delà', async () => {
    render(<Essai initial={9.95} />)
    await userEvent.click(screen.getByRole('button', { name: 'Plus 0,1' }))
    expect(screen.getByRole('status')).toHaveTextContent('10')
    await userEvent.click(screen.getByRole('button', { name: 'Plus 1' }))
    expect(screen.getByRole('status')).toHaveTextContent('11')
  })

  it('« − » est grisé au minimum, avec sa raison ; une frappe hors bornes est dite', async () => {
    render(<Essai initial={0} unite="bobine" max={12} />)
    const moins = screen.getByRole('button', { name: 'Moins 1' })
    expect(moins).toBeDisabled()
    expect(moins).toHaveAttribute('data-raison', 'Déjà au minimum (0).')
    const champ = screen.getByRole('textbox', { name: 'Quantité' })
    expect(champ).toHaveAttribute('inputmode', 'decimal')
    await userEvent.type(champ, '13')
    expect(champ).toHaveAccessibleDescription('Au plus 12.')
    await userEvent.clear(champ)
    await userEvent.type(champ, '2,5')
    expect(champ).toHaveAccessibleDescription('Un nombre entier est attendu.')
  })
})
