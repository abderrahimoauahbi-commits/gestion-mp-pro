/** Essais du gabarit d'écran de l'atelier : titre, « ‹ » vers l'adresse donnée, bandeau, pied, barre du bas. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'

import { EcranAtelier } from './EcranAtelier'

describe('EcranAtelier', () => {
  it('« ‹ » mène à l’adresse de retour ; la barre du bas est là', async () => {
    render(
      <MemoryRouter initialEntries={['/atelier/retour?ordre=4']}>
        <Routes>
          <Route
            path="/atelier/retour"
            element={
              <EcranAtelier
                titre="Retour des machines"
                retour="/atelier"
                enTete={<p>bandeau</p>}
                pied={<p>résumé</p>}
              >
                corps
              </EcranAtelier>
            }
          />
          <Route path="/atelier" element={<p>accueil de l’atelier</p>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { level: 1, name: 'Retour des machines' })).toBeInTheDocument()
    expect(screen.getByText('bandeau')).toBeInTheDocument()
    expect(screen.getByText('résumé')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Atelier' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Retour' }))
    expect(screen.getByText('accueil de l’atelier')).toBeInTheDocument()
  })

  it('sans retour à l’accueil ; sans barre si demandé', () => {
    render(
      <MemoryRouter>
        <EcranAtelier titre="Atelier" retour={false} sansBarre>
          corps
        </EcranAtelier>
      </MemoryRouter>,
    )
    expect(screen.queryByRole('button', { name: 'Retour' })).toBeNull()
    expect(screen.queryByRole('navigation')).toBeNull()
  })
})
