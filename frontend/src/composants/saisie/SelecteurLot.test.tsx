/** Essais de SelecteurLot : lots présents à la date, ordre FIFO gardé, quarantaine écartée. */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { creerClientRequetes } from '../../lib/requetes'
import { optionsDeLots, SelecteurLot } from './SelecteurLot'

const LOTS = [
  { id: 7, numero: 'LOT-2026-0007', reste_kg: 120.5, date_entree: '2026-09-02' },
  { id: 9, numero: 'LOT-2026-0009', reste_kg: 80, date_entree: '2026-09-20', quarantaine: true },
  { id: 12, numero: 'LOT-2026-0012', reste_kg: 300, date_entree: '2026-10-01' },
]

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
  it('lit les lots de la matière à la date et au magasin, garde l’ordre FIFO, écarte la quarantaine', async () => {
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
    expect(surChange).toHaveBeenCalledWith(12, LOTS[2])
  })

  it('sans matière, le dit et ne lit rien', () => {
    const appel = vi.fn()
    vi.stubGlobal('fetch', appel)
    monter({ matiere: null })
    expect(screen.getByRole('combobox', { name: 'Lot' })).toBeDisabled()
    expect(screen.getByRole('combobox', { name: 'Lot' })).toHaveAttribute(
      'placeholder',
      'Choisir d’abord la matière, la date et le magasin',
    )
    expect(appel).not.toHaveBeenCalled()
  })

  it('les options disent le reste et la date d’entrée', () => {
    expect(optionsDeLots(LOTS)[0]?.sous).toBe('120,5\u00a0kg restants · entré le 02/09/2026')
  })
})
