/** Essais des barres : graduations rondes, une barre par valeur avec infobulle, un axe par unité. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Barres } from './Barres'
import { court, graduation, tracer } from './echelle'

describe('échelles', () => {
  it('graduations rondes, zéro compris, nombres courts', () => {
    expect(graduation(0, 870)).toEqual([0, 250, 500, 750, 1000])
    expect(graduation(-120, 300)).toEqual([-200, 0, 200, 400])
    expect(graduation(0, 0)).toEqual([0, 1])
    expect(graduation(2.6, 2.9, 4, false)).toEqual([2.6, 2.7, 2.8, 2.9])
    expect(court(17_398_184)).toBe('17,4\u00a0M')
    expect(court(12_500)).toBe('12,5\u00a0k')
  })

  it('deux séries de même teinte n’ont pas le même trait', () => {
    const [a, b] = tracer([
      { nom: 'Rouge HASIRCI', valeurs: [1], couleur: '#c62828' },
      { nom: 'Rouge BELKA', valeurs: [2], couleur: '#c62828' },
    ])
    expect(a?.couleur).toBe(b?.couleur)
    expect(a?.trait).not.toBe(b?.trait)
  })
})

describe('Barres', () => {
  it('une barre par valeur, qui dit sa valeur et son unité', () => {
    const { container } = render(
      <Barres
        libelle="Achats par mois"
        etiquettes={['août', 'sept.', 'oct.']}
        series={[{ nom: 'Achats', valeurs: [1200, null, 870.5], unite: 'MAD' }]}
      />,
    )
    expect(screen.getByRole('img', { name: 'Achats par mois (MAD)' })).toBeInTheDocument()
    const barres = container.querySelectorAll('rect')
    expect(barres).toHaveLength(2)
    expect(barres[1]?.querySelector('title')?.textContent).toBe('oct. · Achats : 870,5 MAD')
  })

  it('deux devises : deux axes, jamais un seul', () => {
    render(
      <Barres
        libelle="Achats"
        etiquettes={['sept.', 'oct.']}
        series={[
          { nom: 'En USD', valeurs: [61888, 1000], unite: 'USD' },
          { nom: 'En EUR', valeurs: [53132, 900], unite: 'EUR' },
        ]}
      />,
    )
    expect(screen.getByRole('img', { name: 'Achats (USD)' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Achats (EUR)' })).toBeInTheDocument()
    expect(screen.getByText('En USD (USD)')).toBeInTheDocument()
  })

  it('sans données, le dit', () => {
    render(<Barres libelle="Rien" etiquettes={[]} series={[]} />)
    expect(screen.getByText('Pas de données à montrer.')).toBeInTheDocument()
  })
})
