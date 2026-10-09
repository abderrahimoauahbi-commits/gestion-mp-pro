/** Ouvrir un inventaire (périmètre, tolérance bornée, conflit) et l'encart « Lot trouvé ». */
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  contexteDe,
  fauxServeur,
  monterApp,
  prechargerPages,
  reponsesConnecte,
  stockageMemoire,
} from '../../essais/monter'
import { DEFAUTS, ficheEssai, lotEssai, MAGASINS, matiereEssai, resumeEssai } from './donneesEssai'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

function serveur(autres: Record<string, unknown> = {}) {
  return fauxServeur({
    ...reponsesConnecte('achats'),
    'GET /inventaires': { corps: [] },
    'GET /inventaires/defauts': { corps: DEFAUTS },
    'GET /inventaires/a-compter': {
      corps: [
        {
          article_id: 1,
          reference: 'IMP FRISÉ ROUGE',
          role: 'Poil',
          classe_abc: 'A',
          stock: 420,
          kg_par_ml: 0,
          dernier_comptage: null,
          jours: null,
          magasins: ['PRINCIPAL'],
        },
      ],
    },
    'GET /magasins': { corps: MAGASINS },
    'GET /matieres': { corps: [matiereEssai()] },
    'GET /lots': { corps: [lotEssai()] },
    'GET /inventaires/7': { corps: ficheEssai() },
    'POST /inventaires': { corps: ficheEssai() },
    ...Object.fromEntries(Object.entries(autres).map(([k, v]) => [k, { corps: v }])),
  })
}

describe('Ouvrir un inventaire', () => {
  it('propose la tolérance des réglages, la borne à la frappe, et ouvre avec le bon corps', async () => {
    const appels = serveur()
    const app = monterApp('/inventaires/nouveau')
    const tolerance = await screen.findByLabelText('Tolérance (%)')
    await waitFor(() => expect(tolerance).toHaveValue('2'))
    expect(screen.getByText(/1 lot\(s\) en stock seront figés au théorique/)).toBeInTheDocument()
    await userEvent.clear(tolerance)
    await userEvent.type(tolerance, '150')
    const ouvrir = screen.getByRole('button', { name: 'Ouvrir et figer le stock' })
    expect(ouvrir).toHaveAttribute('data-raison', 'À renseigner : la tolérance (0 à 100 %).')
    await userEvent.clear(tolerance)
    await userEvent.type(tolerance, '3')
    await userEvent.click(ouvrir)
    expect(
      screen.getByText('Figer 1 lot(s) de tous les magasins et suspendre leurs mouvements ?'),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Oui, ouvrir l’inventaire' }))
    await waitFor(() => expect(app.adresse()).toBe('/inventaires/7'))
    expect(appels.find((a) => a.methode === 'POST')?.corps).toMatchObject({
      magasin_id: null,
      libelle: 'Inventaire de tout le stock',
      tolerance: 0.03,
      criteres: { matieres: [], roles: [], compositions: [], classes_abc: [] },
    })
  })

  it('un critère au moins par famille ; le tournant liste les matières dues', async () => {
    serveur()
    monterApp('/inventaires/nouveau')
    await userEvent.click(await screen.findByRole('radio', { name: 'Par rôle, composition ou classe ABC' }))
    expect(screen.getByRole('button', { name: 'Ouvrir et figer le stock' })).toHaveAttribute(
      'data-raison',
      'À renseigner : au moins un critère coché.',
    )
    await userEvent.click(screen.getByRole('checkbox', { name: 'Classe A' }))
    expect(screen.getByText(/la classe ABC se calcule à l’ouverture/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('radio', { name: 'Inventaire tournant (matières dues)' }))
    expect(await screen.findByText('jamais compté')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Compter IMP FRISÉ ROUGE' }))
    expect(screen.getByRole('button', { name: 'Ouvrir et figer le stock' })).toHaveAttribute(
      'data-raison',
      'Aucune matière due retenue.',
    )
  })

  it('un inventaire déjà ouvert sur le magasin grise l’ouverture, avec le refus du serveur', async () => {
    fauxServeur({
      ...reponsesConnecte('achats'),
      'GET /contexte': {
        corps: contexteDe('achats', {
          inventaires_ouverts: [
            { id: 1, numero: 'INV-2026-0001', date: '2026-10-08', magasin: null, matieres: [1] },
          ],
        }),
      },
      'GET /inventaires': { corps: [resumeEssai()] },
      'GET /inventaires/defauts': { corps: DEFAUTS },
      'GET /magasins': { corps: MAGASINS },
      'GET /matieres': { corps: [] },
      'GET /lots': { corps: [] },
    })
    monterApp('/inventaires/nouveau')
    const ouvrir = await screen.findByRole('button', { name: 'Ouvrir et figer le stock' })
    expect(ouvrir.getAttribute('data-raison')).toContain(
      'L’inventaire INV-2026-0001 est déjà ouvert sur tous les magasins.',
    )
  })
})

describe('Lot trouvé', () => {
  it('dit ce qui manque, puis l’ajoute sans créer le lot (case « Lot interne »)', async () => {
    const appels = serveur({ 'POST /inventaires/7/lots-trouves': ficheEssai({ version: 4 }) })
    monterApp('/inventaires/7')
    await userEvent.click(await screen.findByRole('button', { name: 'Lot trouvé…' }))
    const ajouter = await screen.findByRole('button', { name: 'Ajouter le lot au comptage' })
    expect(ajouter.getAttribute('data-raison')).toBe(
      'À renseigner : la matière, le numéro de lot (ou cocher Lot interne), le poids compté, la justification (3 caractères au moins).',
    )
    await userEvent.click(screen.getByRole('combobox', { name: 'Matière' }))
    await userEvent.click(await screen.findByRole('option', { name: /IMP FRISÉ ROUGE/ }))
    await userEvent.click(screen.getByRole('switch', { name: 'Lot interne' }))
    await userEvent.type(screen.getByLabelText('Bobines'), '4')
    await userEvent.type(screen.getByLabelText('Justification'), 'Palette derrière le rayonnage')
    expect(screen.getByText(/× 2,50 kg \(poids du catalogue\)/)).toBeInTheDocument()
    await userEvent.click(ajouter)
    await waitFor(() => expect(appels.some((a) => a.chemin === '/inventaires/7/lots-trouves')).toBe(true))
    expect(appels.find((a) => a.chemin === '/inventaires/7/lots-trouves')?.corps).toEqual({
      version: 3,
      matiere_id: 1,
      lot_numero: '',
      lot_interne: true,
      magasin_id: 1,
      compte: 10,
      bobines: 4,
      justification: 'Palette derrière le rayonnage',
    })
  })
})
