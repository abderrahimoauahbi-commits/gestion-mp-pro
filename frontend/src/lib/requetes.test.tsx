/** Essais des requêtes : relance sur statut seulement, invalidation globale après écriture. */
import { QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ErreurApi } from './api'
import { cleApi, creerClientRequetes, relancer, useEcriture, useLecture } from './requetes'

afterEach(() => vi.unstubAllGlobals())

describe('relancer', () => {
  it.each([0, 500, 502, 503, 504])('relance une fois sur le statut %s', (statut) => {
    expect(relancer(0, new ErreurApi('x', statut))).toBe(true)
    expect(relancer(1, new ErreurApi('x', statut))).toBe(false)
  })

  it.each([400, 401, 403, 404, 409, 422, 429])('ne relance jamais un refus %s', (statut) => {
    expect(relancer(0, new ErreurApi('x', statut))).toBe(false)
  })

  it('décide sur le statut, pas sur le message', () => {
    expect(relancer(0, new ErreurApi('Le serveur ne répond pas : 404 introuvable', 503))).toBe(true)
    expect(relancer(0, new ErreurApi('Erreur 500', 404))).toBe(false)
  })

  it('ne relance pas une erreur du programme', () => {
    expect(relancer(0, new TypeError('x is undefined'))).toBe(false)
  })
})

describe('cleApi', () => {
  it('une clé par route, puis ses paramètres', () => {
    expect(cleApi('/matieres')).toEqual(['/matieres'])
    expect(cleApi('/stock', {})).toEqual(['/stock'])
    expect(cleApi('/stock', { date: '2026-10-08' })).toEqual(['/stock', { date: '2026-10-08' }])
  })
})

/** Un faux serveur : une file de statuts par chemin, et le compte des appels. */
function fauxServeur(statuts: Record<string, number[]>) {
  const appels: Record<string, number> = {}
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const chemin = url.replace(/^\/api/, '').split('?')[0]!
      appels[chemin] = (appels[chemin] ?? 0) + 1
      const statut = statuts[chemin]?.shift() ?? 200
      return new Response(
        JSON.stringify(statut < 300 ? { appel: appels[chemin] } : { detail: 'Refus', code: 'x' }),
        {
          status: statut,
          headers: { 'Content-Type': 'application/json' },
        },
      )
    }),
  )
  return appels
}

function enveloppe() {
  const client = creerClientRequetes({ delaiRelance: 0 })
  const Enveloppe = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  return { client, Enveloppe }
}

describe('useLecture', () => {
  it('relance une lecture après un 503, puis réussit', async () => {
    const appels = fauxServeur({ '/stock': [503] })
    const { Enveloppe } = enveloppe()
    const { result } = renderHook(() => useLecture<{ appel: number }>('/stock'), { wrapper: Enveloppe })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(appels['/stock']).toBe(2)
  })

  it('ne relance pas un 409 : l’erreur est rendue telle quelle', async () => {
    const appels = fauxServeur({ '/stock': [409] })
    const { Enveloppe } = enveloppe()
    const { result } = renderHook(() => useLecture('/stock'), { wrapper: Enveloppe })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(appels['/stock']).toBe(1)
    expect(result.current.error).toMatchObject({ statut: 409, message: 'Refus' })
  })

  it('n’abandonne qu’après une seule relance (deux 500)', async () => {
    const appels = fauxServeur({ '/stock': [500, 500, 200] })
    const { Enveloppe } = enveloppe()
    const { result } = renderHook(() => useLecture('/stock'), { wrapper: Enveloppe })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(appels['/stock']).toBe(2)
  })

  it('ne lit rien tant que le chemin est nul', async () => {
    const appels = fauxServeur({})
    const { Enveloppe } = enveloppe()
    const { result } = renderHook(() => useLecture(null), { wrapper: Enveloppe })
    expect(result.current.fetchStatus).toBe('idle')
    expect(appels).toEqual({})
  })
})

describe('useEcriture', () => {
  it('relit toutes les lectures ouvertes après une écriture réussie, avant de rendre la main', async () => {
    const appels = fauxServeur({})
    const { Enveloppe } = enveloppe()
    const { result } = renderHook(
      () => ({
        stock: useLecture<{ appel: number }>('/stock'),
        commandes: useLecture<{ appel: number }>('/commandes'),
        valider: useEcriture(() => fetch('/api/receptions/4/valider').then((r) => r.json())),
      }),
      { wrapper: Enveloppe },
    )
    await waitFor(() =>
      expect(result.current.stock.isSuccess && result.current.commandes.isSuccess).toBe(true),
    )
    await result.current.valider.mutateAsync()
    expect(appels['/stock']).toBe(2)
    expect(appels['/commandes']).toBe(2)
    await waitFor(() => expect(result.current.stock.data?.appel).toBe(2))
  })

  it('ne relit rien avec invalider: false', async () => {
    const appels = fauxServeur({})
    const { Enveloppe } = enveloppe()
    const { result } = renderHook(
      () => ({
        stock: useLecture('/stock'),
        connexion: useEcriture(() => Promise.resolve('ok'), { invalider: false }),
      }),
      { wrapper: Enveloppe },
    )
    await waitFor(() => expect(result.current.stock.isSuccess).toBe(true))
    await result.current.connexion.mutateAsync()
    expect(appels['/stock']).toBe(1)
  })

  it('ne relance jamais une écriture, même sur un 503', async () => {
    let essais = 0
    const { Enveloppe } = enveloppe()
    const { result } = renderHook(
      () =>
        useEcriture(() => {
          essais += 1
          return Promise.reject(new ErreurApi('Indisponible', 503))
        }),
      { wrapper: Enveloppe },
    )
    await expect(result.current.mutateAsync()).rejects.toMatchObject({ statut: 503 })
    expect(essais).toBe(1)
  })
})
