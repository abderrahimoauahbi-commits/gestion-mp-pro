/** Inventaire : liste, fenêtres à adresse stable, comptage (justification, quatre yeux, feuilles), annulation. */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fauxServeur,
  monterApp,
  prechargerPages,
  reponsesConnecte,
  stockageMemoire,
  type Reponse,
} from '../../essais/monter'
import type { Role } from '../../lib/types'
import {
  DEFAUTS,
  ficheEssai,
  ligneEssai,
  lotEssai,
  MAGASINS,
  matiereEssai,
  resumeEssai,
} from './donneesEssai'
import type { InventaireFiche } from './types'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

function serveur(role: Role, fiche: InventaireFiche = ficheEssai(), autres: Record<string, Reponse> = {}) {
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /inventaires': {
      corps: [
        resumeEssai(),
        resumeEssai({
          id: 3,
          numero: 'INV-2026-0003',
          statut: 'valide',
          valide_par: 'MAZARI',
          valide_le: '2026-10-01T12:00:00+01:00',
        }),
      ],
    },
    'GET /inventaires/7': { corps: fiche },
    'GET /inventaires/defauts': { corps: DEFAUTS },
    'GET /magasins': { corps: MAGASINS },
    'GET /matieres': { corps: [matiereEssai()] },
    'GET /lots': { corps: [lotEssai()] },
    ...autres,
  })
}

const bouton = (nom: string | RegExp) => screen.findByRole('button', { name: nom })

describe('Inventaire : la liste', () => {
  it('montre les inventaires en cours, ouvre la fiche à son adresse et y revient', async () => {
    serveur('achats')
    const app = monterApp('/inventaire')
    expect(await screen.findByText('INV-2026-0007')).toBeInTheDocument()
    expect(screen.queryByText('INV-2026-0003')).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('INV-2026-0007'))
    await waitFor(() => expect(app.adresse()).toBe('/inventaires/7'))
    expect(await screen.findByText(/Comptage en cours/)).toBeInTheDocument()
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Fermer' }))
    await waitFor(() => expect(app.adresse()).toBe('/inventaire'))
  })

  it('l’onglet des clos a sa recherche et son filtre d’état ; la fiche ouverte dessus y revient', async () => {
    serveur('achats', ficheEssai({ id: 3, statut: 'valide' }), {
      'GET /inventaires/3': {
        corps: ficheEssai({ id: 3, numero: 'INV-2026-0003', statut: 'valide', blocages: [] }),
      },
    })
    const app = monterApp('/inventaire?onglet=passes')
    expect(await screen.findByText('INV-2026-0003')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'État' })).toBeInTheDocument()
    await userEvent.click(screen.getByText('INV-2026-0003'))
    await waitFor(() => expect(app.adresse()).toBe('/inventaires/3?onglet=passes'))
    await screen.findByRole('link', { name: /Feuille de comptage/ })
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Fermer' }))
    await waitFor(() => expect(app.adresse()).toBe('/inventaire?onglet=passes'))
  })

  it('l’alimentation n’y entre pas', async () => {
    serveur('alimentation')
    const app = monterApp('/inventaire')
    await waitFor(() => expect(app.adresse()).not.toBe('/inventaire'))
  })
})

describe('Inventaire : le comptage', () => {
  it('justification exigée au-delà de la tolérance : Valider grisé avec la raison', async () => {
    serveur('achats')
    monterApp('/inventaires/7')
    const compte = await screen.findByLabelText('Compté (kg) de IMP FRISÉ ROUGE, lot L24-100')
    await userEvent.type(compte, '380')
    const valider = await bouton('Valider l’inventaire')
    await waitFor(() =>
      expect(valider).toHaveAttribute(
        'data-raison',
        expect.stringMatching(/1 écart\(s\) hors tolérance sans justification/),
      ),
    )
    await userEvent.type(screen.getByLabelText('Justification de IMP FRISÉ ROUGE, lot L24-100'), 'casse')
    await waitFor(() => expect(valider).not.toHaveAttribute('data-raison'))
  })

  it('enregistre les lignes modifiées avec la version', async () => {
    const appels = serveur('achats', ficheEssai(), {
      'PUT /inventaires/7/comptages': { corps: ficheEssai({ version: 4 }) },
    })
    monterApp('/inventaires/7')
    await userEvent.type(await screen.findByLabelText('Compté (kg) de IMP FRISÉ ROUGE, lot L24-101'), '260')
    await userEvent.click(await bouton('Enregistrer le comptage'))
    await waitFor(() => expect(appels.some((a) => a.methode === 'PUT')).toBe(true))
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toEqual({
      version: 3,
      lignes: [
        { ligne_id: 2, compte: 260, palettes: null, bobines: null, second_compte: null, justification: '' },
      ],
    })
    expect(await screen.findByText('1 comptage(s) enregistré(s).')).toBeInTheDocument()
  })

  it('un recomptage par la même personne est signalé (ligne, indicateur, confirmation), pas refusé', async () => {
    const fiche = ficheEssai({
      a_recompter: 1,
      blocages: [],
      lignes: [
        ligneEssai({
          compte: 400,
          compte_par: 'Karim BENALI',
          retenu: 400,
          ecart: -20,
          hors_tolerance: true,
          a_recompter: true,
          justification: 'casse',
        }),
      ],
    })
    serveur('achats', fiche)
    monterApp('/inventaires/7')
    await userEvent.type(await screen.findByLabelText('Recompté (kg) de IMP FRISÉ ROUGE, lot L24-100'), '402')
    expect(await screen.findByText('même personne que le premier comptage')).toBeInTheDocument()
    expect(screen.getByText('1 par la même personne')).toBeInTheDocument()
    await userEvent.click(await bouton('Valider l’inventaire'))
    expect(await screen.findByText(/1 recomptage\(s\) faits par la même personne/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Oui, valider l’inventaire' })).not.toBeDisabled()
  })

  it('feuille de comptage à l’aveugle ; recomptage sur ce qui est enregistré ; théorique pour la direction', async () => {
    serveur('achats', ficheEssai({ a_recompter: 1 }))
    monterApp('/inventaires/7')
    const comptage = await screen.findByRole('link', { name: /Feuille de comptage/ })
    expect(comptage.getAttribute('href')).toBe('/api/documents/inventaires/7/feuille')
    expect(screen.getByRole('link', { name: /Feuille de recomptage/ }).getAttribute('href')).toContain(
      'recomptage=true',
    )
    expect(screen.queryByRole('link', { name: /Feuille avec le théorique/ })).not.toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Compté (kg) de IMP FRISÉ ROUGE, lot L24-101'), '1')
    expect(await bouton('Feuille de recomptage')).toHaveAttribute(
      'data-raison',
      'Enregistrer d’abord le comptage : la feuille ne lit que ce qui est enregistré',
    )
  })

  it('la direction a la feuille avec le théorique', async () => {
    serveur('direction')
    monterApp('/inventaires/7')
    const lien = await screen.findByRole('link', { name: /Feuille avec le théorique/ })
    expect(lien.getAttribute('href')).toContain('theorique=true')
    expect(await bouton('Feuille de recomptage')).toHaveAttribute('data-raison', 'Aucun lot à recompter')
  })

  it('abandonner : motif exigé, numéro gardé', async () => {
    const appels = serveur('achats', ficheEssai(), {
      'POST /inventaires/7/abandonner': { corps: ficheEssai({ statut: 'abandonne' }) },
    })
    monterApp('/inventaires/7')
    await userEvent.click(await bouton('Abandonner'))
    expect(screen.getByRole('button', { name: 'Oui, abandonner' })).toHaveAttribute(
      'data-raison',
      'À renseigner : le motif.',
    )
    await userEvent.type(screen.getByLabelText('Motif (obligatoire)'), 'Comptage reporté')
    await userEvent.click(screen.getByRole('button', { name: 'Oui, abandonner' }))
    await waitFor(() => expect(appels.some((a) => a.chemin === '/inventaires/7/abandonner')).toBe(true))
    expect(appels.find((a) => a.chemin === '/inventaires/7/abandonner')?.corps).toEqual({
      version: 3,
      motif: 'Comptage reporté',
    })
  })
})

describe('Inventaire : l’annulation d’un inventaire validé', () => {
  const valide = ficheEssai({
    statut: 'valide',
    valide_par: 'MAZARI',
    valide_le: '2026-10-08T12:00:00+01:00',
    blocages: [],
  })

  it('motif de 3 caractères au moins, puis « Annulé », numéro gardé', async () => {
    const appels = serveur('achats', valide, {
      'POST /inventaires/7/annuler': { corps: { ...valide, statut: 'annule', annule_par: 'Karim BENALI' } },
    })
    monterApp('/inventaires/7')
    expect(await screen.findByText('Validé par MAZARI')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Valider l’inventaire' })).not.toBeInTheDocument()
    await userEvent.click(await bouton('Annuler l’inventaire'))
    await userEvent.type(screen.getByLabelText('Motif (obligatoire)'), 'ab')
    await userEvent.click(screen.getByRole('button', { name: 'Oui, annuler l’inventaire' }))
    expect(
      await screen.findByText('Le motif de l’annulation fait au moins 3 caractères.'),
    ).toBeInTheDocument()
    expect(appels.some((a) => a.chemin === '/inventaires/7/annuler')).toBe(false)
    await userEvent.type(screen.getByLabelText('Motif (obligatoire)'), 'c pesée fausse')
    await userEvent.click(screen.getByRole('button', { name: 'Oui, annuler l’inventaire' }))
    await waitFor(() => expect(appels.some((a) => a.chemin === '/inventaires/7/annuler')).toBe(true))
    expect(appels.find((a) => a.chemin === '/inventaires/7/annuler')?.corps).toEqual({
      version: 3,
      motif: 'abc pesée fausse',
    })
  })
})
