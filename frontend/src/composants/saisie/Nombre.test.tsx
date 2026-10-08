/** Essais de Nombre : saisie à la française, affichage avec milliers, bornes et décimales à la frappe. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { Champ } from './Champ'
import { lireNombre, messageNombre, Nombre, texteDeSaisie } from './Nombre'

function Essai({
  initial = null as number | null,
  ...bornes
}: {
  initial?: number | null
  min?: number
  max?: number
  decimales?: number
}) {
  const [v, setV] = useState<number | null>(initial)
  return (
    <>
      <Champ libelle="Quantité">
        <Nombre valeur={v} onChange={setV} unite="kg" {...bornes} />
      </Champ>
      <output>{v == null ? 'vide' : String(v)}</output>
    </>
  )
}

describe('lireNombre', () => {
  it('accepte virgule, point, espaces des milliers, « − » ; refuse le reste', () => {
    expect(lireNombre('1 234,5')).toBe(1234.5)
    expect(lireNombre('1\u00a0234.5')).toBe(1234.5)
    expect(lireNombre('−3,25')).toBe(-3.25)
    expect(lireNombre(',5')).toBe(0.5)
    expect(lireNombre('12,')).toBe(12)
    expect(lireNombre('')).toBeNull()
    expect(lireNombre('12a')).toBeUndefined()
    expect(lireNombre('1,2,3')).toBeUndefined()
    expect(texteDeSaisie(2.5)).toBe('2,5')
    expect(texteDeSaisie(0)).toBe('')
  })

  it('messageNombre dit les bornes et les décimales', () => {
    expect(messageNombre(5, { min: 0.1, max: 10 })).toBe('')
    expect(messageNombre(0, { min: 0.1 })).toBe('Au moins 0,1.')
    expect(messageNombre(581.66, { max: 581.65 })).toBe('Au plus 581,65.')
    expect(messageNombre(1.2345, { decimales: 3 })).toBe('3 décimales au plus.')
    expect(messageNombre(1.5, { decimales: 0 })).toBe('Un nombre entier est attendu.')
    expect(messageNombre(undefined, {})).toMatch(/Un nombre est attendu/)
  })
})

describe('Nombre', () => {
  it('se tape à la française et s’affiche avec ses milliers hors saisie', async () => {
    render(<Essai />)
    const champ = screen.getByRole('textbox', { name: 'Quantité' })
    expect(champ).toHaveAttribute('inputmode', 'decimal')
    await userEvent.type(champ, '1234,5')
    expect(screen.getByRole('status')).toHaveTextContent('1234.5')
    await userEvent.tab()
    expect(champ).toHaveValue('1\u00a0234,5')
  })

  it('un champ à zéro s’ouvre vide : « 139 » ne devient pas « 0139 »', async () => {
    render(<Essai initial={0} />)
    const champ = screen.getByRole('textbox', { name: 'Quantité' })
    expect(champ).toHaveValue('0')
    await userEvent.click(champ)
    expect(champ).toHaveValue('')
    await userEvent.type(champ, '139')
    expect(screen.getByRole('status')).toHaveTextContent('139')
  })

  it('les bornes se contrôlent à la frappe, le message décrit le champ', async () => {
    render(<Essai max={100} decimales={1} />)
    const champ = screen.getByRole('textbox', { name: 'Quantité' })
    await userEvent.type(champ, '150')
    expect(champ).toHaveAttribute('aria-invalid', 'true')
    expect(champ).toHaveAccessibleDescription('Au plus 100.')
    await userEvent.clear(champ)
    await userEvent.type(champ, '12,25')
    expect(champ).toHaveAccessibleDescription('1 décimale au plus.')
    await userEvent.clear(champ)
    await userEvent.type(champ, 'abc')
    expect(screen.getByText(/Un nombre est attendu/)).toBeInTheDocument()
  })
})
