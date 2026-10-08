/** Essais de LienDocument : n° → fiche à adresse stable ; « Brouillon » sans numéro. */
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import { adresseDocument, LienDocument } from './LienDocument'

describe('LienDocument', () => {
  it('mène à la fiche ; sans numéro, « Brouillon » ou « À approuver »', () => {
    render(
      <MemoryRouter>
        <LienDocument genre="commande" id={12} numero="BC-2026-0012" />
        <LienDocument genre="reception" id={4} numero={null} />
        <LienDocument genre="commande" id={7} numero={null} statut="a_approuver" />
        <LienDocument genre="ordre" id={null} numero="OF-2026-0001" />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: 'BC-2026-0012' })).toHaveAttribute('href', '/commandes/12')
    expect(screen.getByRole('link', { name: 'Brouillon' })).toHaveAttribute('href', '/receptions/4')
    expect(screen.getByRole('link', { name: 'À approuver' })).toHaveAttribute('href', '/commandes/7')
    expect(screen.getByText('OF-2026-0001').tagName).toBe('SPAN')
    expect(adresseDocument('lot', 3)).toBe('/lots/3')
  })
})
