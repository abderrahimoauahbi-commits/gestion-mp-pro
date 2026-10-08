/** Essais de l'écran centré : il pose un `<main>` et garde son contenu. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { EcranCentre } from './EcranCentre'

describe('EcranCentre', () => {
  it('pose le contenu dans un main', () => {
    render(
      <EcranCentre>
        <p>Bonjour</p>
      </EcranCentre>,
    )
    expect(screen.getByRole('main')).toHaveTextContent('Bonjour')
  })
})
