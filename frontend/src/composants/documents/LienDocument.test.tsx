/** Essais de LienDocument : n° → fiche à adresse stable ; « Brouillon » sans numéro. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

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

function Fiche() {
  const { pathname, state } = useLocation() as { pathname: string; state: { retour?: string } | null }
  return <output>{`${pathname} ← ${state?.retour ?? ''}`}</output>
}

describe('LienDocument avec état', () => {
  it('emporte state.retour, et le clic ne remonte pas à la ligne qui le porte', async () => {
    const ligne = vi.fn()
    render(
      <MemoryRouter initialEntries={['/analyse?onglet=revient&q=fa']}>
        <Routes>
          <Route
            path="/analyse"
            element={
              <div onClick={ligne}>
                <LienDocument
                  genre="dossier"
                  id={5}
                  numero="12/26"
                  titre="Ouvrir le dossier"
                  state={{ retour: '/analyse?onglet=revient&q=fa' }}
                />
              </div>
            }
          />
          <Route path="/dossiers/:id" element={<Fiche />} />
        </Routes>
      </MemoryRouter>,
    )
    const lien = screen.getByRole('link', { name: '12/26' })
    expect(lien).toHaveAttribute('title', 'Ouvrir le dossier')
    await userEvent.click(lien)
    expect(screen.getByRole('status')).toHaveTextContent('/dossiers/5 ← /analyse?onglet=revient&q=fa')
    expect(ligne).not.toHaveBeenCalled()
  })
})
