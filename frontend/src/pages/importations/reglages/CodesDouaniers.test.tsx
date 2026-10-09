/**
 * Réglages › Codes douaniers : taux affiché en %, saisi en % et envoyé en fraction, contrôlé de 0
 * à 100 % à la frappe ; code contrôlé à la frappe ; lien vers les matières ; filtre d'état ;
 * suppression grisée tant qu'une matière porte le code ; les achats lisent.
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
} from '../../../essais/monter'
import type { Role } from '../../../lib/types'
import type { CodeDouanier } from '../types'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const CODES: CodeDouanier[] = [
  {
    id: 1,
    code: '5402.47.00.00',
    libelle: 'Fils de polypropylène',
    taux_droits: 0.1,
    actif: true,
    nb_matieres: 2,
    version: 3,
  },
  { id: 2, code: '5402.33.00.00', libelle: '', taux_droits: 0.025, actif: false, nb_matieres: 0, version: 1 },
]

function serveur(role: Role, autres = {}) {
  return fauxServeur({ ...reponsesConnecte(role), 'GET /codes-douaniers': { corps: CODES }, ...autres })
}

describe('Codes douaniers', () => {
  it('liste : taux en %, lien vers les matières, filtre d’état, recherche', async () => {
    serveur('direction')
    monterApp('/reglages?onglet=codes')
    const tableau = await screen.findByRole('table', { name: 'Codes douaniers' })
    expect(within(tableau).getByText('10,0 %')).toBeInTheDocument()
    expect(within(tableau).getByText('2,5 %')).toBeInTheDocument()
    expect(within(tableau).getByRole('link', { name: '2' })).toHaveAttribute(
      'href',
      '/catalogue?onglet=matieres&q=5402.47.00.00',
    )
    expect(screen.getByText(/taux × valeur en douane \(achat \+ fret \+ assurance\)/)).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'État' }), 'désactivé')
    expect(within(tableau).queryByText('Fils de polypropylène')).not.toBeInTheDocument()
    expect(within(tableau).getByText('5402.33.00.00')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'État' }), '')
    await userEvent.type(screen.getByRole('searchbox'), 'polyprop')
    expect(within(tableau).queryByText('5402.33.00.00')).not.toBeInTheDocument()
    await userEvent.type(screen.getByRole('searchbox'), 'zzz')
    expect(screen.getByText('Aucun code ne correspond.')).toBeInTheDocument()
  })

  it('nouveau code : code et taux contrôlés à la frappe, taux en % envoyé en fraction', async () => {
    const appels = serveur('direction', {
      'POST /codes-douaniers': { statut: 201, corps: { ...CODES[1], id: 7, code: '5503.10.00.00' } },
    })
    monterApp('/reglages?onglet=codes&code=nouveau')
    const fenetre = await screen.findByRole('dialog', { name: 'Nouveau code douanier' })
    const creer = within(fenetre).getByRole('button', { name: 'Créer le code' })
    expect(creer.dataset.raison).toContain('À renseigner : Code, Taux de 0 à 100 %')
    const code = within(fenetre).getByRole('textbox', { name: /Code/ })
    await userEvent.type(code, '55A')
    expect(within(fenetre).getAllByText(/Un code douanier s’écrit en chiffres/)[0]).toBeVisible()
    await userEvent.clear(code)
    await userEvent.type(code, '5503.10.00.00')
    const taux = within(fenetre).getByRole('textbox', { name: /Taux de droits/ })
    await userEvent.type(taux, '120')
    expect(within(fenetre).getByText('Un taux de droits va de 0 à 100 %.')).toBeInTheDocument()
    expect(creer).toBeDisabled()
    await userEvent.clear(taux)
    await userEvent.type(taux, '12,5')
    expect(within(fenetre).queryByText('Un taux de droits va de 0 à 100 %.')).not.toBeInTheDocument()
    await userEvent.click(creer)
    await waitFor(() =>
      expect(appels.some((a) => a.methode === 'POST' && a.chemin === '/codes-douaniers')).toBe(true),
    )
    expect(appels.find((a) => a.methode === 'POST' && a.chemin === '/codes-douaniers')?.corps).toEqual({
      code: '5503.10.00.00',
      libelle: '',
      taux_droits: 0.125,
      actif: true,
    })
  })

  it('modifier : PUT avec la version ; supprimer grisé tant que des matières le portent', async () => {
    const appels = serveur('direction', {
      'PUT /codes-douaniers/1': { corps: { ...CODES[0], taux_droits: 0.12, version: 4 } },
    })
    const app = monterApp('/reglages?onglet=codes&code=1')
    const fenetre = await screen.findByRole('dialog', { name: 'Code douanier 5402.47.00.00' })
    const supprimer = within(fenetre).getByRole('button', { name: 'Supprimer' })
    expect(supprimer.dataset.raison).toContain(
      '2 matière(s) portent ce code : le leur retirer, ou le désactiver',
    )
    expect(within(fenetre).getByRole('button', { name: 'Enregistrer' }).dataset.raison).toContain(
      'Rien n’a changé',
    )
    const taux = within(fenetre).getByRole('textbox', { name: /Taux de droits/ })
    await userEvent.clear(taux)
    await userEvent.type(taux, '12')
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(app.adresse()).toBe('/reglages?onglet=codes'))
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toEqual({
      code: '5402.47.00.00',
      libelle: 'Fils de polypropylène',
      taux_droits: 0.12,
      actif: true,
      version: 3,
    })
    expect(await screen.findByText('Code douanier 5402.47.00.00 enregistré.')).toBeInTheDocument()
  })

  it('les achats lisent : pas de « Nouveau code », fenêtre sans saisie ; volet Historique', async () => {
    serveur('achats', { 'GET /historique/code_douanier/1': { corps: [] } })
    const app = monterApp('/reglages?onglet=codes')
    await screen.findByRole('table', { name: 'Codes douaniers' })
    expect(screen.queryByRole('button', { name: 'Nouveau code' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('Fils de polypropylène'))
    const fenetre = await screen.findByRole('dialog', { name: 'Code douanier 5402.47.00.00' })
    expect(within(fenetre).queryByRole('textbox')).not.toBeInTheDocument()
    expect(within(fenetre).queryByRole('button', { name: 'Enregistrer' })).not.toBeInTheDocument()
    expect(within(fenetre).getByText('10,0 %')).toBeInTheDocument()
    await userEvent.click(within(fenetre).getByRole('tab', { name: 'Historique' }))
    expect(app.adresse()).toBe('/reglages?onglet=codes&code=1&volet=historique')
    expect(await within(fenetre).findByText('Aucune modification enregistrée.')).toBeInTheDocument()
  })
})
