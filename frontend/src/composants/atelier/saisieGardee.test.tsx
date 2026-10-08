/** Essais de la saisie gardée : reprise après démontage, oubli, forme étrangère ignorée. */
import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { saisieGardee, useSaisieGardee } from './saisieGardee'

afterEach(() => sessionStorage.clear())

describe('useSaisieGardee', () => {
  it('garde la saisie en quittant l’écran et la reprend au retour ; oublier l’efface', () => {
    const a = renderHook(() => useSaisieGardee('retour', { ordre: 0, kg: '' }))
    act(() => a.result.current[1]((s) => ({ ...s, ordre: 4, kg: '52,4' })))
    a.unmount()
    expect(saisieGardee('retour')).toBe(true)
    const b = renderHook(() => useSaisieGardee('retour', { ordre: 0, kg: '' }))
    expect(b.result.current[0]).toEqual({ ordre: 4, kg: '52,4' })
    act(() => b.result.current[2]())
    expect(saisieGardee('retour')).toBe(false)
  })

  it('une saisie d’une autre forme est ignorée', () => {
    sessionStorage.setItem('gestion-mp-pro:saisie:signaler', '"texte"')
    const { result } = renderHook(() => useSaisieGardee('signaler', { texte: '' }))
    expect(result.current[0]).toEqual({ texte: '' })
  })
})
