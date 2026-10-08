/** Essais de l'état dans l'adresse : onglet, recherche, filtres, fiche par adresse stable. */
import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { describe, expect, it } from 'vitest'

import {
  avecParametre,
  useFicheAdresse,
  useFiltresAdresse,
  useOngletAdresse,
  useRechercheAdresse,
} from './adresse'

function dans(adresse: string, motif = '*') {
  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[adresse]}>
      <Routes>
        <Route path={motif} element={children} />
      </Routes>
    </MemoryRouter>
  )
}

const useIci = () => {
  const l = useLocation()
  return `${l.pathname}${l.search}`
}

describe('avecParametre', () => {
  it('pose, remplace, retire sans toucher aux autres', () => {
    const p = new URLSearchParams('onglet=lots&q=rouge')
    expect(avecParametre(p, 'q', 'bleu').toString()).toBe('onglet=lots&q=bleu')
    expect(avecParametre(p, 'q', '').toString()).toBe('onglet=lots')
    expect(avecParametre(p, 'statut', 'envoyee').toString()).toBe('onglet=lots&q=rouge&statut=envoyee')
    expect(p.toString()).toBe('onglet=lots&q=rouge')
  })
})

describe('useOngletAdresse', () => {
  const ONGLETS = ['matieres', 'lots', 'mouvements'] as const

  it('lit l’onglet de l’adresse, et le défaut pour un onglet inconnu', () => {
    const a = renderHook(() => useOngletAdresse(ONGLETS, 'matieres'), { wrapper: dans('/stock?onglet=lots') })
    expect(a.result.current[0]).toBe('lots')
    const b = renderHook(() => useOngletAdresse(ONGLETS, 'matieres'), {
      wrapper: dans('/stock?onglet=pirate'),
    })
    expect(b.result.current[0]).toBe('matieres')
  })

  it('écrit l’onglet en gardant la recherche et les filtres', () => {
    const { result } = renderHook(() => ({ o: useOngletAdresse(ONGLETS, 'matieres'), ici: useIci() }), {
      wrapper: dans('/stock?q=rouge&fournisseur=3'),
    })
    act(() => result.current.o[1]('mouvements'))
    expect(result.current.ici).toBe('/stock?q=rouge&fournisseur=3&onglet=mouvements')
    act(() => result.current.o[1]('matieres'))
    expect(result.current.ici).toBe('/stock?q=rouge&fournisseur=3')
  })
})

describe('useRechercheAdresse', () => {
  it('la recherche vit dans ?q=', () => {
    const { result } = renderHook(() => ({ r: useRechercheAdresse(), ici: useIci() }), {
      wrapper: dans('/stock?onglet=lots'),
    })
    expect(result.current.r[0]).toBe('')
    act(() => result.current.r[1]('frise rouge'))
    expect(result.current.r[0]).toBe('frise rouge')
    expect(result.current.ici).toBe('/stock?onglet=lots&q=frise+rouge')
    act(() => result.current.r[1](''))
    expect(result.current.ici).toBe('/stock?onglet=lots')
  })
})

describe('useFiltresAdresse', () => {
  it('pose, compte et efface les filtres, en gardant onglet et recherche', () => {
    const { result } = renderHook(
      () => ({ f: useFiltresAdresse(['fournisseur', 'statut'] as const), ici: useIci() }),
      { wrapper: dans('/commandes?onglet=envoyee&q=hasi&fournisseur=3') },
    )
    expect(result.current.f.valeur('fournisseur')).toBe('3')
    expect(result.current.f.valeur('statut')).toBe('')
    expect(result.current.f.nombre).toBe(1)
    act(() => result.current.f.poser('statut', 'confirmee'))
    expect(result.current.f.nombre).toBe(2)
    expect(result.current.f.poses).toEqual({ fournisseur: '3', statut: 'confirmee' })
    act(() => result.current.f.effacer())
    expect(result.current.ici).toBe('/commandes?onglet=envoyee&q=hasi')
    expect(result.current.f.nombre).toBe(0)
  })
})

describe('useFicheAdresse', () => {
  it('ouvre la fiche à son adresse et la ferme sur la liste, filtres gardés', () => {
    const { result } = renderHook(() => ({ f: useFicheAdresse('/commandes'), ici: useIci() }), {
      wrapper: dans('/commandes?onglet=envoyee&q=hasi', '/commandes/:id?'),
    })
    expect(result.current.f.id).toBeNull()
    act(() => result.current.f.ouvrir(12))
    expect(result.current.ici).toBe('/commandes/12?onglet=envoyee&q=hasi')
    expect(result.current.f.id).toBe(12)
    act(() => result.current.f.fermer())
    expect(result.current.ici).toBe('/commandes?onglet=envoyee&q=hasi')
    expect(result.current.f.id).toBeNull()
  })

  it('reconnaît la saisie d’un nouveau document', () => {
    const { result } = renderHook(() => useFicheAdresse('/ordres'), {
      wrapper: dans('/ordres/nouveau', '/ordres/:id'),
    })
    expect(result.current).toMatchObject({ id: null, nouveau: true })
  })

  it('un identifiant illisible n’ouvre rien', () => {
    const { result } = renderHook(() => useFicheAdresse('/ordres'), {
      wrapper: dans('/ordres/abc', '/ordres/:id'),
    })
    expect(result.current).toMatchObject({ id: null, nouveau: false })
  })
})
