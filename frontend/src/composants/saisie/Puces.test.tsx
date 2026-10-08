/** Essais des puces : choisir, retirer, voir les autres, valeur libre. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { Puces } from './Puces'

describe('Puces', () => {
  it('choisit, retire, montre les autres et accepte une valeur nouvelle', async () => {
    function Essai() {
      const [v, setV] = useState('')
      return (
        <>
          <Puces
            valeur={v}
            onChange={setV}
            options={['Rouge', 'Bleu', 'Beige', 'Noir']}
            max={2}
            libre
            libelle="Couleur"
          />
          <output>{v}</output>
        </>
      )
    }
    render(<Essai />)
    expect(screen.queryByRole('button', { name: 'Beige' })).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: '+ 2 autres' }))
    await userEvent.click(screen.getByRole('button', { name: 'Beige' }))
    expect(screen.getByRole('status')).toHaveTextContent('Beige')
    await userEvent.click(screen.getByRole('button', { name: 'Beige' }))
    expect(screen.getByRole('status')).toHaveTextContent('')
    await userEvent.click(screen.getByRole('button', { name: 'Autre…' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Nouvelle valeur' }), 'Vison{Enter}')
    expect(screen.getByRole('status')).toHaveTextContent('Vison')
  })
})
