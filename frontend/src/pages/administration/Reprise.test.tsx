/**
 * Administration › Reprise (lot C1, routes 243–244) : l'état du miroir en une phrase, la liste des
 * reprises et leur rapport ; la direction rafraîchit (une activité saisie dans PRO ne se remplace
 * qu'en cochant et en tapant REMPLACER) ; l'administrateur voit l'état sans geste.
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
import { verdict } from './Reprise'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const execution = {
  id: 3,
  debut: '2026-10-09T10:00:00+01:00',
  fin: '2026-10-09T10:00:05+01:00',
  statut: 'reussie',
  mode: 'tout',
  base_source: 'gestion_mp',
  empreinte_source: 'af08c36c24e20ffc8ed1c49ff4c7c2e7',
  duree_s: 4.6,
  creees: 1204,
  tables: { matiere: { lues: 124, creees: 124 } },
  rapport: 'REPRISE DE GESTION MP DANS GESTION MP PRO\nCONTRÔLES\n[tenu] Comptes de lignes par table',
}

const etat = {
  base: 'gestion_mp_pro',
  base_source: 'gestion_mp',
  signature_source: 'af08c36c24e20ffc8ed1c49ff4c7c2e7',
  source_lisible: true,
  message_source: '',
  a_jour: true,
  activite_propre: false,
  en_cours: false,
  derniere_reussie: execution,
  executions: [execution],
}

function servir(role: Role, e: object = etat) {
  return fauxServeur(
    reponsesConnecte(role, {
      'GET /reprise': { corps: e },
      'POST /reprise': {
        statut: 202,
        corps: { etat: 'en_cours', debut: '', mode: 'tout', remplacer_activite: false, message: '' },
      },
    }),
  )
}

describe('Administration › Reprise', () => {
  it('dit que le miroir est à jour, liste les reprises et montre le rapport', async () => {
    servir('direction')
    monterApp('/administration?onglet=reprise')
    expect(await screen.findByText(/Le miroir est à jour/)).toBeInTheDocument()
    const tableau = screen.getByRole('table', { name: 'Reprises' })
    expect(within(tableau).getByText('réussie')).toBeInTheDocument()
    await userEvent.click(within(tableau).getByRole('button', { name: 'Rapport' }))
    expect(await screen.findByText(/\[tenu\] Comptes de lignes/)).toBeInTheDocument()
  })

  it('rafraîchir : une activité saisie dans PRO exige la case et le mot REMPLACER', async () => {
    const appels = servir('direction', { ...etat, a_jour: false, activite_propre: true })
    monterApp('/administration?onglet=reprise')
    await userEvent.click(await screen.findByRole('button', { name: 'Rafraîchir le miroir…' }))
    const fenetre = await screen.findByRole('dialog')
    const lancer = within(fenetre).getByRole('button', { name: 'Rafraîchir maintenant' })
    expect(lancer).toBeDisabled()
    await userEvent.click(within(fenetre).getByRole('checkbox'))
    await userEvent.type(within(fenetre).getByRole('textbox', { name: /Taper REMPLACER/ }), 'remplacer')
    await userEvent.click(lancer)
    await waitFor(() => expect(appels.some((a) => a.methode === 'POST')).toBe(true))
    expect(appels.find((a) => a.methode === 'POST')?.corps).toEqual({
      mode: 'tout',
      remplacer_activite: true,
      confirmation: 'remplacer',
    })
  })

  it('administrateur : l’état, sans geste ni rapport', async () => {
    servir('administrateur', {
      ...etat,
      derniere_reussie: { ...execution, rapport: null },
      executions: [{ ...execution, rapport: null }],
    })
    monterApp('/administration?onglet=reprise')
    expect(await screen.findByText(/Le miroir est à jour/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Rafraîchir le miroir…' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Rapport' })).toBeNull()
  })

  it('le verdict suit l’état', () => {
    expect(verdict({ ...etat, en_cours: true }).ton).toBe('info')
    expect(verdict({ ...etat, a_jour: false }).texte).toMatch(/Gestion MP a changé/)
    expect(verdict({ ...etat, derniere_reussie: null, executions: [] }).texte).toMatch(/Aucune reprise/)
    expect(verdict({ ...etat, source_lisible: false, message_source: 'illisible' }).ton).toBe('critique')
  })
})
