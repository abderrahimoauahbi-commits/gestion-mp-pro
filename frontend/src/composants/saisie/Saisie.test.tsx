/** Essais de Saisie : nom accessible hors d'un Champ, longueur maximale, désactivée. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Saisie } from './Saisie'

describe('Saisie', () => {
  it('hors d’un Champ, `libelle` la nomme ; max et désactivation passent au contrôle', () => {
    render(<Saisie valeur="BL-12" onChange={() => {}} libelle="N° de BL" max={40} desactive />)
    const s = screen.getByRole('textbox', { name: 'N° de BL' })
    expect(s).toHaveAttribute('maxlength', '40')
    expect(s).toBeDisabled()
    expect(s).toHaveAttribute('autocomplete', 'off')
  })
})
