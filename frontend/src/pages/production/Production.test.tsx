/**
 * Production & besoins dans l'application entière, sur des réponses relevées au vrai serveur : le
 * plan saisi par la direction (un coefficient hors bornes grise l'enregistrement avec sa raison,
 * la saisie survit au changement d'onglet), la lecture seule des autres rôles, les besoins sans
 * conseil d'achat pour l'alimentation, d'où vient le besoin d'une matière (l'addition tombe juste).
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fauxServeur,
  monterApp,
  prechargerPages,
  reponsesConnecte,
  stockageMemoire,
} from '../../essais/monter'
import type { Role } from '../../lib/types'
import besoins from './essais/besoins.json'
import plan from './essais/plan.json'
import realise from './essais/realise.json'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

function servir(role: Role) {
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /production/plan': { corps: plan },
    'GET /production/realise': { corps: realise },
    'GET /production/besoins': { corps: besoins },
  })
}

const lire = (texte: string | null | undefined) =>
  Number((texte ?? '').replace(/[\s\u00a0\u202f]/g, '').replace(',', '.'))

describe('Production › Plan de production', () => {
  it('direction : un coefficient hors de 0 à 20 grise l’enregistrement, avec la raison', async () => {
    servir('direction')
    monterApp('/production')
    const champ = await screen.findByRole('textbox', { name: 'ATLAS, coefficient de Janv.' })
    await userEvent.clear(champ)
    await userEvent.type(champ, '25')
    const tout = await screen.findByRole('button', { name: 'Enregistrer tout (1)' })
    expect(tout).toBeDisabled()
    expect(tout.getAttribute('data-raison')).toMatch(/Un coefficient reste entre 0 et 20 : corriger ATLAS/)
    expect(screen.getByRole('button', { name: 'Enregistrer' }).getAttribute('data-raison')).toMatch(
      /entre 0 et 20/,
    )
    // La saisie survit au changement d'onglet, et l'onglet le dit.
    await userEvent.click(screen.getByRole('tab', { name: /Plan glissant/ }))
    expect(
      await screen.findByText(/1 qualité\(s\) modifiée\(s\) dans le plan de production/),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: /Plan de production \(1 modifiée\)/ }))
    expect(await screen.findByRole('textbox', { name: 'ATLAS, coefficient de Janv.' })).toHaveValue('25')
  })

  it('achats : lecture seule, sans champ ni geste', async () => {
    servir('achats')
    monterApp('/production')
    await screen.findByRole('table', { name: 'Plan de production' })
    expect(screen.queryAllByRole('textbox', { name: /coefficient/ })).toHaveLength(0)
    expect(screen.getAllByText(/Lecture seule : seule la direction modifie le plan/)).not.toHaveLength(0)
  })
})

describe('Production › Plan glissant', () => {
  it('le graphique empile les qualités : une barre par mois, chaque qualité posée sur la précédente', async () => {
    servir('achats')
    monterApp('/production?onglet=glissant&vue=graphique')
    const panneau = await screen.findByRole('img', { name: 'Plan glissant (m²)' })
    const morceaux = [...panneau.querySelectorAll('rect')]
    const premierMois = morceaux.filter((r) => r.textContent?.startsWith('oct.'))
    expect(premierMois.map((r) => r.textContent?.split(' (')[0])).toEqual([
      'oct. 2026 · ATLAS : 132 m²',
      'oct. 2026 · SAHARA : 60 m²',
    ])
    // Même colonne (empilées), pas côte à côte.
    expect(new Set(premierMois.map((r) => r.getAttribute('x'))).size).toBe(1)
    expect(screen.getByText('ATLAS (m²)')).toBeInTheDocument()
  })

  it('au-delà de sept qualités, les plus petites se regroupent en « Autres »', async () => {
    const { seriesGlissant } = await import('./OngletGlissant')
    const base = plan.qualites[0]!
    const qualites = Array.from({ length: 9 }, (_, i) => ({
      ...base,
      code: `Q${i}`,
      total_glissant: 100 - i,
      glissant: base.glissant.map(() => 10 - i),
    }))
    const series = seriesGlissant(plan as never, qualites as never)
    expect(series.map((s) => s.nom)).toEqual([
      'Q0',
      'Q1',
      'Q2',
      'Q3',
      'Q4',
      'Q5',
      'Q6',
      'Autres',
      'Matière nécessaire',
    ])
    expect(series[7]?.valeurs[0]).toBe(3 + 2)
  })
})

describe('Production › Besoins matière', () => {
  it('alimentation : les besoins, sans « À commander » (H-03)', async () => {
    servir('alimentation')
    monterApp('/production?onglet=besoins')
    const tableau = await screen.findByRole('table', { name: 'Besoins matière' })
    expect(within(tableau).getByText('PP FRZ-2900 Rouge')).toBeInTheDocument()
    expect(document.querySelector('main')?.textContent).not.toMatch(/À commander|\b(MAD|USD|EUR)\b/)
  })

  it('d’où vient le besoin : chaque mois, les qualités s’additionnent au besoin du plan', async () => {
    servir('direction')
    const { adresse } = monterApp('/production?onglet=besoins')
    await userEvent.click(await screen.findByText('PP FRZ-2900 Rouge'))
    await waitFor(() => expect(adresse()).toBe('/production/besoins/1?onglet=besoins'))
    const tableau = await screen.findByRole('table', { name: 'D’où vient le besoin' })
    const corps = [...tableau.querySelectorAll('tbody tr')].map((tr) =>
      [...tr.children].slice(2).map((td) => lire(td.textContent === '—' ? '0' : td.textContent)),
    )
    const pied = [...(tableau.querySelector('tfoot tr')?.children ?? [])]
      .slice(2)
      .map((td) => lire(td.textContent))
    pied.forEach((total, i) => expect(corps.reduce((t, l) => t + (l[i] ?? 0), 0)).toBe(total))
    const ligne = besoins.lignes.find((x) => x.matiere_id === 1)
    expect(pied.at(-1)).toBe(Math.round(ligne?.total ?? 0))
  })

  it('filtrer par qualité : la quantité devient la consommation de cette seule qualité', async () => {
    servir('direction')
    monterApp('/production?onglet=besoins')
    const ref = 'COTON CHAINE 12/6' // tirée par ATLAS (440,64) et SAHARA (220,32) → total 660,96
    const tableau = await screen.findByRole('table', { name: 'Besoins matière' })
    expect(within(tableau).getByText(ref).closest('tr')?.textContent).toContain('660,96')

    await userEvent.selectOptions(screen.getByLabelText('Qualité'), 'ATLAS')
    const ligne = within(tableau).getByText(ref).closest('tr')!
    const cellules = [...ligne.querySelectorAll('td')].map((td) => lire(td.textContent))
    expect(cellules.some((v) => Math.abs(v - 440.64) < 0.01)).toBe(true) // la part d'ATLAS
    expect(cellules.some((v) => Math.abs(v - 660.96) < 0.01)).toBe(false) // plus le total de toutes
  })
})

describe('Production › Plan et réalisé', () => {
  it('un clic sur une qualité ouvre son graphique', async () => {
    servir('achats')
    const { adresse } = monterApp('/production?onglet=realise')
    await userEvent.click(await screen.findByText('ATLAS'))
    await waitFor(() => expect(adresse()).toBe('/production?onglet=realise&qualite=ATLAS&vue=graphique'))
    expect(await screen.findByRole('figure', { name: 'Plan et tissé de ATLAS' })).toBeInTheDocument()
  })
})
