/**
 * La page Administration dans l'application entière, sur des réponses relevées au vrai serveur :
 * un changement de rôle exige un nouveau code (F-01, P8-11), désactiver n'envoie que l'état de la
 * fiche enregistrée (P8-10) ; la restauration — confirmation sur la ligne, fenêtre « J'ai
 * compris », mot RESTAURER et motif, suivi par la santé ; le journal avec l'avant et l'après ;
 * l'administrateur sans aucune donnée métier.
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
import parametres from '../reglages/essais/parametres.json'
import { changementsLisibles } from './changements'
import { defautDuCode, exigeNouveauCode, manquesCompte } from './compte'
import apercu from './essais/apercu.json'
import courriels from './essais/courriels.json'
import journal from './essais/journal.json'
import sante from './essais/sante.json'
import sauvegardes from './essais/sauvegardes.json'
import utilisateurs from './essais/utilisateurs.json'
import valeurs from './essais/valeurs.json'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const ligneParametre = {
  ...journal.elements[0],
  action: 'paramètre',
  objet: 'parametre',
  detail: 'Couverture critique : 60 jours → 70 jours',
  avant: { seuil_critique: '60' },
  apres: { seuil_critique: '70' },
}

function servir(role: Role, autres: Parameters<typeof reponsesConnecte>[1] = {}) {
  return fauxServeur(
    reponsesConnecte(role, {
      'GET /utilisateurs': { corps: utilisateurs },
      'PUT /utilisateurs/7': { corps: utilisateurs[0] },
      'GET /sauvegardes': { corps: sauvegardes },
      'GET /journal': { corps: { ...journal, elements: [ligneParametre, ...journal.elements] } },
      'GET /journal/valeurs': { corps: valeurs },
      'GET /parametres': {
        corps: parametres.filter((p) => role !== 'administrateur' || p.famille === 'Technique'),
      },
      'GET /courriels': { corps: courriels },
      'GET /courriel/apercu': { corps: apercu },
      ...autres,
    }),
  )
}

describe('Administration', () => {
  it('un compte qui change de rôle exige un nouveau code ; le bouton dit pourquoi', async () => {
    servir('direction')
    monterApp('/administration?compte=7')
    const fenetre = await screen.findByRole('dialog')
    await userEvent.selectOptions(within(fenetre).getByRole('combobox', { name: 'Rôle' }), 'alimentation')
    const bouton = within(fenetre).getByRole('button', { name: 'Enregistrer' })
    expect(bouton).toBeDisabled()
    expect(bouton.getAttribute('data-raison')).toContain('un nouveau code est nécessaire')
  })

  it('désactiver n’envoie que l’état, sur la fiche enregistrée', async () => {
    const appels = servir('direction')
    monterApp('/administration?compte=7')
    const fenetre = await screen.findByRole('dialog')
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Désactiver le compte' }))
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Oui, désactiver' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'PUT')).toBe(true))
    const achats = utilisateurs.find((u) => u.id === 7)
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toEqual({
      nom: achats?.nom,
      role: achats?.role,
      email: achats?.email,
      actif: false,
      version: achats?.version,
    })
  })

  it('restaurer : confirmer, « J’ai compris », RESTAURER et motif, puis suivre la santé', async () => {
    let tours = 0
    const appels = servir('direction', {
      'POST /sauvegardes/gestion-mp-pro-2026-10-09-113410-manuelle.dump/restaurer': {
        statut: 202,
        corps: { etat: 'en cours', fichier: 'x', avant: 'y', debut: '', message: '' },
      },
      'GET /sante': () => ({
        corps: { ...sante, taches: { restauration: tours++ === 0 ? 'en cours' : 'ok' } },
      }),
    })
    monterApp('/administration?onglet=sauvegardes')
    const tableau = await screen.findByRole('table', { name: 'Sauvegardes' })
    const ligne = within(tableau).getByText('gestion-mp-pro-2026-10-09-113410-manuelle.dump').closest('tr')
    await userEvent.click(within(ligne as HTMLElement).getByRole('button', { name: 'Restaurer…' }))
    await userEvent.click(within(ligne as HTMLElement).getByRole('button', { name: 'Oui, continuer…' }))
    const fenetre = await screen.findByRole('dialog')
    const continuer = within(fenetre).getByRole('button', { name: 'Continuer' })
    expect(continuer).toBeDisabled()
    await userEvent.click(within(fenetre).getByRole('checkbox'))
    await userEvent.click(continuer)
    tours = 0
    await userEvent.type(within(fenetre).getByRole('textbox', { name: /Taper RESTAURER/ }), 'restaurer')
    await userEvent.type(within(fenetre).getByRole('textbox', { name: /Motif/ }), 'Essai')
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Restaurer maintenant' }))
    expect(
      await within(fenetre).findByText(/La base est revenue à l’état du/, {}, { timeout: 6000 }),
    ).toBeInTheDocument()
    const post = appels.find((a) => a.methode === 'POST')
    expect(post?.corps).toEqual({ confirmation: 'restaurer', motif: 'Essai' })
  }, 10000)

  it('le journal montre l’avant et l’après, champ par champ', async () => {
    servir('direction')
    monterApp('/administration?onglet=journal')
    const tableau = await screen.findByRole('table', { name: 'Journal des actions' })
    expect(await within(tableau).findByText('seuil critique : 60')).toBeInTheDocument()
    expect(within(tableau).getByText('seuil critique : 70')).toBeInTheDocument()
  })

  it('administrateur : ni données brutes, ni aperçu chiffré du courriel', async () => {
    const appels = servir('administrateur')
    monterApp('/administration?onglet=courriel')
    await screen.findByText('À qui, et comment')
    expect(screen.queryByRole('tab', { name: /Données/ })).toBeNull()
    expect(appels.some((a) => a.chemin.startsWith('/courriel/apercu'))).toBe(false)
  })
})

describe('règles des comptes', () => {
  it('le code suit le rôle (4 chiffres, 8, 12) ; un changement de rôle peut en exiger un nouveau', () => {
    expect(defautDuCode('alimentation', '12345')).toMatch(/4 chiffres/)
    expect(defautDuCode('alimentation', '1234')).toBe('')
    expect(defautDuCode('administrateur', 'abcdefghij')).toBe('Le code doit faire au moins 12 caractères.')
    expect(exigeNouveauCode('achats', 'direction')).toBe(false)
    expect(exigeNouveauCode('achats', 'administrateur')).toBe(true)
    expect(exigeNouveauCode('alimentation', 'achats')).toBe(true)
    const forme = {
      nom: 'Sara',
      identifiant: 'sara',
      role: 'achats' as const,
      email: '',
      code: 'abc',
      code2: 'abd',
    }
    expect(manquesCompte(forme, true, null)).toEqual([
      'Le code doit faire au moins 8 caractères.',
      'Les deux codes diffèrent',
    ])
  })

  it('l’avant et l’après se lisent à la française', () => {
    expect(changementsLisibles({ taux: 0.035, date_cloture: '2025-12-31', actif: false })).toBe(
      'taux : 0,035 · date cloture : 31/12/2025 · actif : non',
    )
  })
})
