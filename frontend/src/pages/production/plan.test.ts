/**
 * Le plan de production à la frappe (base × saisonnalité, m² → base moyenne), l'état d'une qualité
 * au plan, et l'écart des mois clos depuis la mise en service.
 */
import { describe, expect, it } from 'vitest'

import realise from './essais/realise.json'
import { prorata } from './IndicateursProduction'
import { teinteMois } from './OngletRealise'
import {
  debutCompte,
  depuisM2,
  ecartClos,
  etatAuPlan,
  horsBornes,
  modifier,
  oublier,
  saisieDe,
  type PlanEtRealise,
  type QualitePlan,
} from './plan'

const q = (p: Partial<QualitePlan> = {}) =>
  ({
    id: 1,
    code: 'Q',
    nom: '',
    actif: true,
    version: 1,
    base_mensuelle: 100,
    saisonnalite: Array(12).fill(1),
    lignes_recette: 2,
    recette_conforme: true,
    ...p,
  }) as QualitePlan

describe('plan à la frappe', () => {
  it('les m² d’un mois font de la base la moyenne des douze mois', () => {
    const s = depuisM2(saisieDe(q()), 0, 220)
    expect(s.base_mensuelle).toBe(110)
    expect(s.saisonnalite[0]).toBe(2)
    expect(s.saisonnalite[1]).toBe(0.909091)
    expect(depuisM2({ base_mensuelle: 0, saisonnalite: Array(12).fill(0) }, 0, 0)).toEqual({
      base_mensuelle: 0,
      saisonnalite: Array(12).fill(1),
    })
  })

  it('une ligne revenue à son état enregistré n’est plus modifiée ; oublier la retire', () => {
    const b = modifier({}, q(), { base_mensuelle: 120, saisonnalite: Array(12).fill(1) })
    expect(Object.keys(b)).toEqual(['1'])
    expect(modifier(b, q(), saisieDe(q()))).toEqual({})
    expect(oublier(b, [1])).toEqual({})
  })

  it('un coefficient hors de 0 à 20 est dit avant l’envoi (P2-12)', () => {
    expect(horsBornes({ base_mensuelle: 1, saisonnalite: [21, ...Array(11).fill(1)] })).toBe(true)
    expect(horsBornes({ base_mensuelle: 1, saisonnalite: [-0.1, ...Array(11).fill(1)] })).toBe(true)
    expect(horsBornes({ base_mensuelle: 1, saisonnalite: [20, ...Array(11).fill(0)] })).toBe(false)
  })

  it('l’état d’une qualité au plan', () => {
    expect(etatAuPlan(q({ actif: false }), saisieDe(q()))).toBe('inactive')
    expect(etatAuPlan(q({ lignes_recette: 0 }), saisieDe(q()))).toBe('sans_recette')
    expect(etatAuPlan(q({ recette_conforme: false }), saisieDe(q()))).toBe('recette_incomplete')
    expect(etatAuPlan(q(), saisieDe(q()))).toBe('au_plan')
    expect(etatAuPlan(q(), { base_mensuelle: 0, saisonnalite: Array(12).fill(1) })).toBe('pas_de_plan')
  })
})

describe('plan et réalisé', () => {
  const r = realise as PlanEtRealise

  it('l’écart des mois clos se compte depuis la mise en service', () => {
    const debut = debutCompte(r)
    expect(r.mois[debut]! >= (r.debut_service ?? '')).toBe(true)
    const e = ecartClos(r)
    expect(e.mois).toBe(r.mois_clos - debut)
    expect(e.fait).toBeGreaterThan(0)
  })

  it('un mois clos loin du plan se voit dans sa cellule ; avant la mise en service, rien', () => {
    expect(teinteMois(100, 80, 5, 2, 10)).toBe('bas')
    expect(teinteMois(100, 120, 5, 2, 10)).toBe('haut')
    expect(teinteMois(100, 95, 5, 2, 10)).toBeNull()
    expect(teinteMois(100, 0, 1, 2, 10)).toBeNull()
    expect(teinteMois(100, 0, 11, 2, 10)).toBeNull()
  })

  it('la part du mois écoulée', () => {
    expect(prorata('2026-10-15')).toBeCloseTo(15 / 31)
    expect(prorata('2026-02-28')).toBe(1)
  })
})
