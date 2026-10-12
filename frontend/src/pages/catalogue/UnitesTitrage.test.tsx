/**
 * La vue « Unités de titrage » de la classification (décision de Mohamed du 12/10/2026) : la liste
 * (désactivées cachées, « Supprimer » grisé avec la raison du serveur), l'ajout, et le champ
 * « Unité » d'un titrage qui propose aussitôt une unité ajoutée (et plus une unité désactivée).
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
import { unitesProposees } from './ChampsValeur'
import { classificationEssai, reponsesCatalogue, uniteEssai } from './donneesEssai'
import type { Classification, UniteTitrage } from './types'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

/** Un faux serveur dont la classification garde les unités ajoutées par `POST`. */
function serveurAvecAjout() {
  const c: Classification = classificationEssai()
  const appels = fauxServeur({
    ...reponsesConnecte('achats'),
    ...reponsesCatalogue({ 'GET /classification': () => ({ corps: c }) }),
    'POST /classification/unites-titrage': (corps) => {
      const { code, libelle } = corps as { code: string; libelle: string }
      const nouvelle: UniteTitrage = { ...uniteEssai(8, code, 70), libelle }
      c.unites_titrage = [...c.unites_titrage, nouvelle]
      return { statut: 201, corps: nouvelle }
    },
  })
  return appels
}

describe('Unités de titrage', () => {
  it('la vue liste les unités actives ; « Supprimer » grisé par la raison du serveur', async () => {
    fauxServeur({ ...reponsesConnecte('achats'), ...reponsesCatalogue() })
    monterApp('/catalogue?onglet=classification&liste=unites-titrage')
    const tableau = await screen.findByRole('table', { name: 'Unités de titrage' })
    expect(screen.getByRole('button', { name: 'Unités de titrage · 4' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    for (const code of ['Dtex', 'Deniers', 'Nm', 'lbs'])
      expect(within(tableau).getByText(code)).toBeInTheDocument()
    expect(within(tableau).queryByText('Nec')).not.toBeInTheDocument()
    const ligne = within(tableau).getByText('Dtex').closest('tr')
    if (!ligne) throw new Error('ligne absente')
    expect(within(ligne).getByRole('button', { name: 'Supprimer' }).dataset.raison).toContain(
      'Écrite sur 1 titrage(s) (3 matière(s))',
    )
    await userEvent.click(screen.getByRole('switch', { name: /Montrer les unités désactivées \(1\)/ }))
    expect(await within(tableau).findByText('Nec')).toBeInTheDocument()
  })

  it('« Ajouter une unité » envoie le code et le libellé ; l’unité rejoint la liste', async () => {
    const appels = serveurAvecAjout()
    monterApp('/catalogue?onglet=classification&liste=unites-titrage')
    await userEvent.click(await screen.findByRole('button', { name: 'Ajouter une unité' }))
    const fenetre = await screen.findByRole('dialog')
    await userEvent.type(within(fenetre).getByRole('textbox', { name: 'Code' }), 'Ne')
    await userEvent.type(within(fenetre).getByRole('textbox', { name: 'Libellé' }), 'numéro anglais')
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Ajouter' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'POST')).toBe(true))
    expect(appels.find((a) => a.methode === 'POST')?.corps).toEqual({
      code: 'Ne',
      libelle: 'numéro anglais',
      ordre: null,
      actif: true,
    })
    const tableau = await screen.findByRole('table', { name: 'Unités de titrage' })
    expect(await within(tableau).findByText('Ne')).toBeInTheDocument()
  })

  it('le champ « Unité » d’un titrage propose l’unité ajoutée, pas l’unité désactivée', async () => {
    serveurAvecAjout()
    monterApp('/catalogue?onglet=classification&liste=unites-titrage')
    await userEvent.click(await screen.findByRole('button', { name: 'Ajouter une unité' }))
    const fenetre = await screen.findByRole('dialog')
    await userEvent.type(within(fenetre).getByRole('textbox', { name: 'Code' }), 'Ne')
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Ajouter' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await userEvent.click(await screen.findByRole('button', { name: /^Titrages · / }))
    await userEvent.click(await screen.findByRole('button', { name: 'Ajouter un titrage' }))
    const titrage = await screen.findByRole('dialog')
    await userEvent.click(within(titrage).getByRole('combobox', { name: 'Unité' }))
    const options = screen.getAllByRole('option').map((o) => o.textContent)
    expect(options).toEqual(['Dtex', 'Deniers', 'Nm', 'lbs', 'Ne'])
  })

  it('l’unité déjà posée reste proposée même désactivée, une fois, sans tenir compte de la casse', () => {
    const unites = classificationEssai().unites_titrage
    expect(unitesProposees(unites, 'Nec')).toEqual(['Dtex', 'Deniers', 'Nm', 'lbs', 'Nec'])
    expect(unitesProposees(unites, 'dtex')).toEqual(['Dtex', 'Deniers', 'Nm', 'lbs'])
    expect(unitesProposees(unites, '')).toEqual(['Dtex', 'Deniers', 'Nm', 'lbs'])
  })
})
