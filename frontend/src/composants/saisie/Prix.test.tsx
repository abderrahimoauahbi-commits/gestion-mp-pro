/** Essais de Prix : unité et devise dites, équivalent au kilo d'un prix au mètre. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Prix, prixAuKg } from './Prix'

describe('Prix', () => {
  it('un prix au mètre dit son équivalent au kilo', () => {
    render(<Prix valeur={0.5} onChange={() => {}} devise="USD" unite="ml" densite={0.014} libelle="Prix" />)
    expect(screen.getByText('USD / ml')).toBeInTheDocument()
    expect(screen.getByText('soit 35,71 USD / kg')).toBeInTheDocument()
    expect(prixAuKg(0.5, 0)).toBeNull()
  })

  it('au mètre sans densité, le dit ; au kilo, rien de plus', () => {
    const { rerender } = render(
      <Prix valeur={0.5} onChange={() => {}} devise="EUR" unite="ml" libelle="Prix" />,
    )
    expect(screen.getByText(/Densité inconnue/)).toBeInTheDocument()
    rerender(<Prix valeur={2.8} onChange={() => {}} devise="USD" unite="kg" libelle="Prix" />)
    expect(screen.queryByText(/soit/)).toBeNull()
    expect(screen.getByRole('textbox', { name: 'Prix' })).toHaveValue('2,8')
  })
})
