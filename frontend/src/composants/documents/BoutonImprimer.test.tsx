/** Essais de BoutonImprimer : nouvel onglet, adresse du document. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { BoutonImprimer } from './BoutonImprimer'

describe('BoutonImprimer', () => {
  it('ouvre le document du serveur dans un nouvel onglet', () => {
    render(
      <BoutonImprimer
        route="/documents/etiquettes"
        parametres={{ lots: '1,2,3' }}
        libelle="Imprimer les étiquettes"
      />,
    )
    const lien = screen.getByRole('link', { name: 'Imprimer les étiquettes' })
    expect(lien).toHaveAttribute('href', '/api/documents/etiquettes?lots=1%2C2%2C3')
    expect(lien).toHaveAttribute('target', '_blank')
    expect(lien).toHaveAttribute('rel', 'noopener')
  })
})
