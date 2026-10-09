/**
 * La page Réglages dans l'application entière, sur des réponses relevées au vrai serveur : un
 * ordre de seuils refusé à la frappe (phrase du serveur, bouton grisé avec sa raison), le
 * brouillon gardé d'un onglet à l'autre (P8-8), l'écriture tout ou rien en fraction et à la
 * version lue ; les achats en lecture sauf les devises ; la clôture de période confirmée en
 * fenêtre avec un motif (P8-9).
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fauxServeur,
  type Reponse,
  monterApp,
  prechargerPages,
  reponsesConnecte,
  stockageMemoire,
} from '../../essais/monter'
import type { Role } from '../../lib/types'
import devises from './essais/devises.json'
import magasins from './essais/magasins.json'
import parametres from './essais/parametres.json'
import { ORDRES_STRICTS } from './parametres/logique'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const date = parametres.find((p) => p.cle === 'date_cloture')

function servir(role: Role, autres: Record<string, Reponse> = {}) {
  return fauxServeur(
    reponsesConnecte(role, {
      ...autres,
      'GET /parametres': { corps: parametres },
      'PUT /parametres': { corps: parametres },
      'GET /devises': { corps: devises },
      'GET /magasins': { corps: magasins },
      'GET /parametres/historique': { corps: { elements: [], total: 0, suivant: null } },
      'PUT /periode-close': { corps: { date_cloture: '2026-06-30', par: 'MAZARI', quand: null, version: 2 } },
    }),
  )
}

const champ = (nom: string) => screen.getByRole('textbox', { name: new RegExp(`^${nom}`) })

describe('Réglages', () => {
  it('un ordre de seuils se refuse à la frappe, avec la phrase du serveur', async () => {
    servir('direction')
    monterApp('/reglages')
    await screen.findByRole('navigation', { name: 'Familles de réglages' })
    await userEvent.clear(champ('Couverture critique'))
    await userEvent.type(champ('Couverture critique'), '500')
    const phrase = ORDRES_STRICTS[0]?.[2] ?? ''
    expect(screen.getAllByText(phrase).length).toBeGreaterThan(0)
    const bouton = screen.getByRole('button', { name: 'Enregistrer 1 modification(s)' })
    expect(bouton).toBeDisabled()
    expect(bouton.getAttribute('data-raison')).toContain(phrase)
  })

  it('le brouillon survit au changement d’onglet ; il part en une écriture, à la version lue', async () => {
    const appels = servir('direction')
    monterApp('/reglages')
    await screen.findByRole('navigation', { name: 'Familles de réglages' })
    await userEvent.click(screen.getByRole('button', { name: /Approvisionnement/ }))
    await userEvent.clear(champ('Taux de perte matière'))
    await userEvent.type(champ('Taux de perte matière'), '3,5')
    await userEvent.click(screen.getByRole('tab', { name: /Devises/ }))
    await screen.findByRole('table', { name: 'Devises' })
    await userEvent.click(screen.getByRole('tab', { name: /Paramètres/ }))
    const famille = await screen.findByRole('button', { name: /Approvisionnement/ })
    expect(famille).toHaveTextContent('1')
    await userEvent.click(famille)
    expect(await screen.findByDisplayValue('3,5')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer 1 modification(s)' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'PUT')).toBe(true))
    const put = appels.find((a) => a.methode === 'PUT' && a.chemin === '/parametres')
    expect(put?.corps).toEqual({
      valeurs: { taux_perte: 0.035 },
      version_globale: parametres[0]?.version_globale,
    })
  })

  it('achats : les paramètres en lecture, les devises en écriture', async () => {
    servir('achats')
    monterApp('/reglages')
    await screen.findByRole('navigation', { name: 'Familles de réglages' })
    expect(champ('Couverture critique')).toBeDisabled()
    expect(screen.queryByRole('button', { name: /Enregistrer/ })).toBeNull()
    await userEvent.click(screen.getByRole('tab', { name: /Devises/ }))
    const tableau = await screen.findByRole('table', { name: 'Devises' })
    const cours = within(tableau).getByRole('textbox', { name: 'Cours de EUR' })
    expect(cours).toBeEnabled()
    expect(within(tableau).getByRole('textbox', { name: 'Cours de MAD' })).toBeDisabled()
  })

  it('clore la période : les brouillons datés de la période sont annoncés avant la fenêtre (route 246)', async () => {
    const message =
      'La période jusqu’au 30/06/2026 garde 3 brouillon(s) : les valider ou les supprimer avant de la clore.'
    const appels = servir('direction', {
      'GET /periode-close/brouillons': {
        corps: {
          jusqu_au: '2026-06-30',
          total: 3,
          genres: [
            { genre: 'reception', libelle: 'réception', nombre: 2 },
            { genre: 'ordre', libelle: 'ordre de fabrication', nombre: 1 },
            { genre: 'inventaire', libelle: 'inventaire', nombre: 0 },
          ],
          message,
        },
      },
    })
    monterApp('/reglages?onglet=periode')
    await userEvent.type(await screen.findByLabelText('Clore jusqu’au'), '2026-06-30')
    expect(
      await screen.findByText(
        /3 brouillon\(s\) datés jusqu’au 30\/06\/2026 : 2 réception\(s\), 1 ordre de fabrication\(s\)\. Les/,
      ),
    ).toBeInTheDocument()
    const clore = screen.getByRole('button', { name: 'Clore la période…' })
    expect(clore).toBeDisabled()
    expect(clore.dataset.raison).toContain(message)
    expect(appels.some((a) => a.chemin === '/periode-close/brouillons?date=2026-06-30')).toBe(true)
  })

  it('clore la période : une fenêtre qui dit l’effet, motif obligatoire, version lue', async () => {
    const appels = servir('direction')
    monterApp('/reglages?onglet=periode')
    const jour = await screen.findByLabelText('Clore jusqu’au')
    await userEvent.type(jour, '2026-06-30')
    await userEvent.click(screen.getByRole('button', { name: 'Clore la période…' }))
    const fenetre = await screen.findByRole('dialog')
    expect(within(fenetre).getByText(/plus rien ne s’écrira au 30\/06\/2026 ni avant/)).toBeInTheDocument()
    const oui = within(fenetre).getByRole('button', { name: 'Clore la période' })
    expect(oui).toBeDisabled()
    await userEvent.type(within(fenetre).getByRole('textbox', { name: /Motif/ }), 'Clôture du semestre')
    await userEvent.click(oui)
    await waitFor(() => expect(appels.some((a) => a.chemin === '/periode-close')).toBe(true))
    expect(appels.find((a) => a.chemin === '/periode-close')?.corps).toEqual({
      date_cloture: '2026-06-30',
      motif: 'Clôture du semestre',
      version: date?.version,
    })
  })
})
