/** Essais de l'interrupteur : rôle switch, bascule au clic et au clavier. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { Interrupteur } from './Interrupteur'

describe('Interrupteur', () => {
  it('bascule au clic et à la barre d’espace', async () => {
    function Essai() {
      const [v, setV] = useState(false)
      return <Interrupteur valeur={v} onChange={setV} libelle="Prix du catalogue, à confirmer" />
    }
    render(<Essai />)
    const s = screen.getByRole('switch', { name: 'Prix du catalogue, à confirmer' })
    expect(s).toHaveAttribute('aria-checked', 'false')
    await userEvent.click(s)
    expect(s).toHaveAttribute('aria-checked', 'true')
    s.focus()
    await userEvent.keyboard(' ')
    expect(s).toHaveAttribute('aria-checked', 'false')
  })
})
