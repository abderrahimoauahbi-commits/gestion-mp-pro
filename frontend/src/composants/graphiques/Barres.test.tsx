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

describe('Barres empilées', () => {
  it('une seule barre par étiquette : chaque série part du haut de la précédente, l’axe va au total', () => {
    const { container } = render(
      <Barres
        libelle="Plan glissant"
        empiler
        etiquettes={['oct.', 'nov.']}
        series={[
          { nom: 'Q1', valeurs: [600, 300], unite: 'm²' },
          { nom: 'Q2', valeurs: [400, 0], unite: 'm²' },
          { nom: 'Autres', valeurs: [200, 100], unite: 'm²' },
        ]}
      />,
    )
    const barres = [...container.querySelectorAll('svg[role="img"] rect')].map((r) => ({
      x: Number(r.getAttribute('x')),
      haut: Number(r.getAttribute('y')),
      bas: Number(r.getAttribute('y')) + Number(r.getAttribute('height')),
      titre: r.textContent,
    }))
    // Le zéro n'est pas dessiné : 3 morceaux en octobre, 2 en novembre.
    expect(barres).toHaveLength(5)
    const [q1, q2, autres] = barres
    // Même colonne, posées l'une sur l'autre (le haut d'une barre = le bas de la suivante).
    expect(q1?.x).toBe(q2?.x)
    expect(q2?.bas).toBeCloseTo(q1?.haut ?? 0)
    expect(autres?.bas).toBeCloseTo(q2?.haut ?? 0)
    expect(q2?.titre).toBe('oct. · Q2 : 400 m² (total 1 200 m²)')
    // L'axe couvre le total (1 200), pas la plus grande série (600).
    const graduations = [...container.querySelectorAll('text')].map((t) => t.textContent)
    expect(graduations).toContain('1 500')
  })
})
