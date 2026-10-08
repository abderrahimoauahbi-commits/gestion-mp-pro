/** Essais des courbes : couleur du fil, trait à teinte égale, un vide coupe la courbe. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { teinteDuFil } from '../../lib/teintes'
import { Courbes, morceaux } from './Courbes'

describe('Courbes', () => {
  it('un vide coupe la courbe', () => {
    expect(morceaux([[0, 1], [1, 2], null, [3, 4]])).toEqual(['0,1 1,2', '3,4'])
    expect(morceaux([null])).toEqual([])
  })

  it('la courbe d’un fil rouge est rouge ; deux rouges se distinguent par le trait', () => {
    const rouge = teinteDuFil('Rouge') ?? ''
    const { container } = render(
      <Courbes
        libelle="Prix payés"
        etiquettes={['juil.', 'août', 'sept.']}
        series={[
          { nom: 'PP Rouge HASIRCI', valeurs: [2.8, 2.9, 2.85], couleur: rouge, unite: 'USD / kg' },
          { nom: 'PP Rouge BELKA', valeurs: [2.6, null, 2.7], couleur: rouge, unite: 'USD / kg' },
        ]}
      />,
    )
    expect(screen.getByRole('img', { name: 'Prix payés (USD / kg)' })).toBeInTheDocument()
    const hasirci = container.querySelector('[data-serie="PP Rouge HASIRCI"] polyline')
    const belka = container.querySelectorAll('[data-serie="PP Rouge BELKA"] polyline')
    expect(hasirci).toHaveStyle({ stroke: rouge })
    expect(belka).toHaveLength(2)
    expect(belka[0]?.getAttribute('stroke-dasharray')).toBeTruthy()
    expect(hasirci?.getAttribute('stroke-dasharray')).toBeNull()
    expect(screen.getByText('PP Rouge BELKA (USD / kg)')).toBeInTheDocument()
  })
})
