/** L'aide de l'écran : le tiroir dit l'écran, ses points, et mène au Mode d'emploi. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { SUR_LES_METIERS } from '../../lib/aide'
import { AideEcran } from './AideEcran'

describe('AideEcran', () => {
  it('ouvre l’aide de l’écran depuis aide.json, texte unique « Sur les métiers » compris', async () => {
    const fermer = vi.fn()
    render(
      <MemoryRouter>
        <AideEcran cle="stock" role="alimentation" onFermer={fermer} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('dialog', { name: 'Aide — Stock, lots & mouvements' })).toBeInTheDocument()
    expect(screen.getByText(SUR_LES_METIERS)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: 'Tout le Mode d’emploi' }))
    expect(fermer).toHaveBeenCalled()
  })
})
