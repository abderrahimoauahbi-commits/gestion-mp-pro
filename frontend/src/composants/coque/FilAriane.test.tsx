/** Le fil d'Ariane dérivé du registre : groupe, liste parente (lien), écran. */
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import { ecranParChemin } from '../../routes'
import { etapesDuFil, FilAriane } from './FilAriane'

describe('FilAriane', () => {
  it('un écran du menu : groupe › écran', () => {
    const e = ecranParChemin('/commandes')
    expect(e && etapesDuFil(e)).toEqual([{ libelle: 'Achats' }, { libelle: 'Commandes' }])
  })

  it('une fiche : groupe › liste (lien) › fiche', () => {
    const e = ecranParChemin('/lots/:id')
    expect(e && etapesDuFil(e)).toEqual([
      { libelle: 'Tous les jours' },
      { libelle: 'Stock, lots & mouvements', vers: '/stock' },
      { libelle: 'Fiche de lot' },
    ])
    render(
      <MemoryRouter>
        <FilAriane ecran={e ?? null} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: 'Stock, lots & mouvements' })).toHaveAttribute('href', '/stock')
    expect(screen.getByText('Fiche de lot').closest('li')).toHaveAttribute('aria-current', 'page')
  })

  it('un écran hors menu : son titre seul', () => {
    const e = ecranParChemin('/compte')
    expect(e && etapesDuFil(e)).toEqual([{ libelle: 'Mon compte' }])
  })
})
