/** Essais de Definitions : libellés, valeurs, vide. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Definitions } from './Definitions'

describe('Definitions', () => {
  it('écrit chaque paire et « — » pour une valeur absente', () => {
    render(
      <Definitions
        items={[
          ['Fournisseur', 'HASIRCI'],
          ['Observations', ''],
          ['Livraison prévue', null],
        ]}
      />,
    )
    expect(screen.getByText('Fournisseur').nextSibling).toHaveTextContent('HASIRCI')
    expect(screen.getAllByText('—')).toHaveLength(2)
  })
})
