/** Essais de ChargerPlus : libellé, pages lues au curseur avec les paramètres. */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { creerClientRequetes } from '../../lib/requetes'
import { ChargerPlus, libelleChargerPlus, useListePaginee } from './ChargerPlus'

describe('ChargerPlus', () => {
  it('dit ce qui est chargé et ce que le bouton chargera ; rien quand tout est là', () => {
    expect(libelleChargerPlus(500, 2000)).toBe('Charger les 500 suivants')
    expect(libelleChargerPlus(1500, 1512)).toBe('Charger les 12 derniers')
    const { rerender, container } = render(<ChargerPlus charges={500} total={1234} onCharger={() => {}} />)
    expect(screen.getByText('500 lignes chargées sur 1 234')).toBeInTheDocument()
    rerender(<ChargerPlus charges={1234} total={1234} onCharger={() => {}} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('useListePaginee lit la page suivante avec ?apres= et garde la recherche', async () => {
    const appel = vi.fn(async (adresse: string) =>
      Response.json(
        adresse.includes('apres=')
          ? { elements: [{ id: 3 }], total: 3, suivant: null }
          : { elements: [{ id: 1 }, { id: 2 }], total: 3, suivant: 'c2' },
      ),
    )
    vi.stubGlobal('fetch', appel)
    function Liste() {
      const { lignes, chargerPlus } = useListePaginee<{ id: number }>('/mouvements', { q: 'rouge' })
      return (
        <>
          <output>{lignes.map((l) => l.id).join(',')}</output>
          <ChargerPlus {...chargerPlus} />
        </>
      )
    }
    render(
      <QueryClientProvider client={creerClientRequetes({ delaiRelance: 0 })}>
        <Liste />
      </QueryClientProvider>,
    )
    await screen.findByText('1,2')
    await userEvent.click(screen.getByRole('button', { name: 'Charger le dernier' }))
    await screen.findByText('1,2,3')
    expect(appel.mock.calls.map((c) => c[0])).toEqual([
      '/api/mouvements?q=rouge',
      '/api/mouvements?q=rouge&apres=c2',
    ])
  })
})
