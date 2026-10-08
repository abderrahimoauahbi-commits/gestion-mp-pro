/** Essais de Quantite : conversions kg ↔ bobines ↔ palettes, arrondi dit, borne arrondie vers le bas (P3). */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import type { Unite } from '../../lib/unites'
import { Quantite } from './Quantite'

function Essai({
  initial = null as number | null,
  borne,
  tactile = false,
  kgParMl,
}: {
  initial?: number | null
  borne?: number
  tactile?: boolean
  kgParMl?: number
}) {
  const [kg, setKg] = useState<number | null>(initial)
  const [unite, setUnite] = useState<Unite>('kg')
  return (
    <>
      <Quantite
        libelle="Quantité"
        kg={kg}
        onChange={setKg}
        unite={unite}
        onUnite={setUnite}
        poidsBobine={kgParMl ? null : 2.4952}
        bobinesPalette={kgParMl ? null : 40}
        kgParMl={kgParMl}
        borne={borne}
        tactile={tactile}
      />
      <output>{kg == null ? 'vide' : String(kg)}</output>
    </>
  )
}

describe('Quantite', () => {
  it('3 bobines valent 7,49 kg : les kilos remontent, la conversion est dite', async () => {
    render(<Essai />)
    await userEvent.click(screen.getByRole('radio', { name: /^bobines/ }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Quantité' }), '3')
    expect(screen.getByRole('status')).toHaveTextContent('7.486')
    expect(screen.getByText('3 bobines = 7,49 kg')).toBeInTheDocument()
  })

  it('changer d’unité dit l’arrondi', async () => {
    render(<Essai initial={7.5} />)
    await userEvent.click(screen.getByRole('radio', { name: /^bobines/ }))
    expect(screen.getByRole('textbox', { name: 'Quantité' })).toHaveValue('3')
    expect(screen.getByText(/arrondi : 7,49\skg au lieu de 7,50\skg/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('radio', { name: /^palettes/ }))
    expect(screen.getByRole('textbox', { name: 'Quantité' })).toHaveValue('0,08')
  })

  it('avec une borne, la conversion arrondit vers le bas (jamais plus que ce qui est parti)', async () => {
    render(<Essai initial={8.7} borne={8.7} />)
    await userEvent.click(screen.getByRole('radio', { name: /^bobines/ }))
    expect(screen.getByRole('textbox', { name: 'Quantité' })).toHaveValue('3')
    expect(Number(screen.getByRole('status').textContent)).toBeLessThanOrEqual(8.7)
  })

  it('une matière au mètre : kilos seulement, mètres indicatifs', () => {
    render(<Essai initial={14.3} kgParMl={0.014} />)
    expect(screen.queryByRole('radiogroup')).toBeNull()
    expect(screen.getByText(/14,3 kg ≈ 1 021 ml/)).toBeInTheDocument()
  })

  it('en mode tactile, le compteur et les segments de l’atelier', async () => {
    render(<Essai initial={2.3} tactile />)
    await userEvent.click(screen.getByRole('button', { name: 'Plus 0,1' }))
    expect(screen.getByRole('status')).toHaveTextContent('2.4')
    expect(screen.getByRole('radio', { name: 'Bobines' })).toBeInTheDocument()
  })
})
