/** Essais de SelecteurLot : lots présents à la date, ordre FIFO gardé, quarantaine écartée. */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { creerClientRequetes } from '../../lib/requetes'
import { optionsDeLots, SelecteurLot } from './SelecteurLot'

// La forme de la route 111 (`LotDisponible`) : une ligne par lot et magasin, FIFO, hors quarantaine.
const lot = (lot_id: number, quantite: number, entre_le: string, magasin_id = 1, magasin = 'MP1') => ({
  lot_id,
  lot: `LOT-2026-${String(lot_id).padStart(4, '0')}`,
  magasin_id,
  magasin,
  quantite,
  entre_le,
  poids_bobine: 5,
  fond_de_lot: false,
})
const LOTS = [lot(7, 120.5, '2026-09-02'), lot(12, 300, '2026-10-01')]

function monter(props: Partial<Parameters<typeof SelecteurLot>[0]> = {}) {
  const surChange = vi.fn()
  render(
    <QueryClientProvider client={creerClientRequetes({ delaiRelance: 0 })}>
      <SelecteurLot matiere={3} date="2026-10-08" magasin={1} valeur={null} onChange={surChange} {...props} />
    </QueryClientProvider>,
  )
  return surChange
}

describe('SelecteurLot', () => {
  it('lit les lots de la matière à la date et au magasin, dans l’ordre FIFO reçu', async () => {
    const appel = vi.fn(async (_adresse: string) => Response.json(LOTS))
    vi.stubGlobal('fetch', appel)
    const surChange = monter()
    const champ = await screen.findByRole('combobox', { name: 'Lot' })
    expect(String(appel.mock.calls[0]?.[0])).toBe('/api/lots/disponibles?matiere=3&date=2026-10-08&magasin=1')
    await userEvent.click(champ)
    expect(screen.getAllByRole('option').map((o) => o.textContent)).toEqual([
      expect.stringContaining('LOT-2026-0007'),
      expect.stringContaining('LOT-2026-0012'),
    ])
    await userEvent.click(screen.getByRole('option', { name: /0012/ }))
    expect(surChange).toHaveBeenCalledWith(12, [LOTS[1]])
  })

  it('sans matière, le dit et ne lit rien', () => {
    const appel = vi.fn()
    vi.stubGlobal('fetch', appel)
    monter({ matiere: null })
    expect(screen.getByRole('combobox', { name: 'Lot' })).toBeDisabled()
    expect(screen.getByRole('combobox', { name: 'Lot' })).toHaveAttribute(
      'placeholder',
      'Choisir d’abord la matière et la date',
    )
    expect(appel).not.toHaveBeenCalled()
  })

  it('les options disent le reste, la date d’entrée et le magasin', () => {
    expect(optionsDeLots(LOTS)[0]?.sous).toBe('120,5\u00a0kg restants · entré le 02/09/2026 · MP1')
  })

  it('sans magasin, un lot présent dans deux magasins est proposé une fois, ses kilos ajoutés', async () => {
    const lignes = [
      lot(7, 100, '2026-09-02'),
      lot(7, 20.5, '2026-09-02', 2, 'MP2'),
      lot(12, 300, '2026-10-01'),
    ]
    const appel = vi.fn(async (_adresse: string) => Response.json(lignes))
    vi.stubGlobal('fetch', appel)
    const surChange = monter({ magasin: null })
    const champ = await screen.findByRole('combobox', { name: 'Lot' })
    expect(String(appel.mock.calls[0]?.[0])).toBe('/api/lots/disponibles?matiere=3&date=2026-10-08')
    expect(optionsDeLots(lignes).map((o) => o.sous)).toEqual([
      '120,5\u00a0kg restants · entré le 02/09/2026 · MP1, MP2',
      '300\u00a0kg restants · entré le 01/10/2026 · MP1',
    ])
    await userEvent.click(champ)
    await userEvent.click(screen.getByRole('option', { name: /0007/ }))
    expect(surChange).toHaveBeenCalledWith(7, lignes.slice(0, 2))
  })
})
