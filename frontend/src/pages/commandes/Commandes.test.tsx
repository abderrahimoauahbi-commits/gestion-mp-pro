/**
 * Les commandes dans l'application entière : liste à onglets (badge « Brouillon » / « À
 * approuver », jamais un faux numéro), fiche à adresse stable ; gestes annoncés par le serveur
 * (`actions`) ; « Envoyer, ou demander l'approbation » au-delà du seuil ; approbation et renvoi
 * réservés à la direction, motif de trois caractères ; bon imprimé dans un nouvel onglet ; Excel
 * grisé sans raison sociale ; conflit de version affiché sur la fiche.
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
  type Reponse,
} from '../../essais/monter'
import { adresseNouvelle } from './Commandes'
import { ficheEssai, resumeEssai } from './donneesEssai'
import type { CommandeFiche } from './types'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const ACTIONS_BROUILLON = {
  modifier: null,
  supprimer: null,
  envoyer: null,
  approuver: 'Ce bon n’attend pas d’approbation.',
  renvoyer: 'Seul un bon qui attend l’approbation se renvoie aux achats.',
  prix: 'Le brouillon n’est pas encore parti.',
  expedition: 'Ce bon n’est pas encore parti : son expédition se suit après l’envoi.',
  solder: 'Ce bon n’est pas parti : il se supprime, il ne se solde pas.',
  rouvrir: 'Ce bon n’est pas clos.',
  imprimer: null,
}

function brouillon(autres: Partial<CommandeFiche> = {}): CommandeFiche {
  return ficheEssai({
    id: 9,
    numero: null,
    parti: false,
    statut: 'brouillon',
    modifiable: true,
    fin_possible: null,
    receptions: [],
    decisions: [],
    actions: ACTIONS_BROUILLON,
    ...autres,
  })
}

function serveur(role: 'direction' | 'achats', fiche: CommandeFiche, autres: Record<string, Reponse> = {}) {
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /commandes': {
      corps: [
        resumeEssai({ id: 9, numero: null, statut: fiche.statut, parti: false }),
        resumeEssai({ id: 3 }),
      ],
    },
    [`GET /commandes/${fiche.id}`]: { corps: fiche },
    'GET /matieres': { corps: [] },
    ...autres,
  })
}

describe('Commandes', () => {
  it('les anciennes adresses de Gestion MP mènent à la fiche (sur la liste seulement)', () => {
    expect(adresseNouvelle('/commandes', new URLSearchParams('ouvrir=12'))).toBe('/commandes/12')
    expect(adresseNouvelle('/commandes', new URLSearchParams('commande=3'))).toBe('/commandes/3')
    expect(adresseNouvelle('/commandes/nouvelle', new URLSearchParams('commande=3'))).toBeNull()
  })

  it('liste : onglets comptés, badge « Brouillon » pour un bon sans numéro, indicateurs', async () => {
    serveur('achats', brouillon())
    monterApp('/commandes')
    const tableau = await screen.findByRole('table', { name: /Commandes — Brouillons/ })
    expect(within(tableau).getAllByText('Brouillon').length).toBeGreaterThan(0)
    expect(screen.getByRole('tab', { name: /Brouillons/ })).toHaveTextContent('Brouillons1')
    expect(screen.getByRole('tab', { name: /Confirmées/ })).toHaveTextContent('Confirmées1')
    expect(screen.getAllByText('Bons ouverts').length).toBeGreaterThan(0)
  })

  it('brouillon au-delà du seuil : « Envoyer, ou demander l’approbation », question au montant', async () => {
    const appels = serveur(
      'achats',
      brouillon({ approbation_requise: true, montant_estime_mad: 300672, seuil_approbation: 200000 }),
      {
        'POST /commandes/9/envoyer': { corps: brouillon({ statut: 'a_approuver' }) },
      },
    )
    monterApp('/commandes/9')
    const fenetre = await screen.findByRole('dialog', {
      name: /Bon de commande — Polyfil|Bon de commande — /,
    })
    await userEvent.click(
      await within(fenetre).findByRole('button', { name: 'Envoyer, ou demander l’approbation' }),
    )
    const question = within(fenetre).getByRole('group', { name: 'Confirmation' })
    expect(question.textContent?.replace(/\s+/g, ' ')).toContain('au-delà du seuil de 200 000 MAD')
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Oui, demander l’approbation' }))
    await waitFor(() => expect(appels.some((a) => a.chemin === '/commandes/9/envoyer')).toBe(true))
    expect(appels.find((a) => a.chemin === '/commandes/9/envoyer')?.corps).toEqual({
      version: brouillon().version,
      date: null,
    })
  })

  it('à approuver : la direction approuve ou renvoie (motif de 3 caractères) ; les achats attendent', async () => {
    const fiche = brouillon({
      statut: 'a_approuver',
      actions: {
        ...ACTIONS_BROUILLON,
        approuver: null,
        renvoyer: null,
        envoyer: 'Ce bon attend l’approbation de la direction.',
      },
    })
    serveur('achats', fiche)
    const { unmount } = monterApp('/commandes/9')
    const f1 = await screen.findByRole('dialog', { name: /Bon de commande — / })
    await within(f1).findByText(/il attend l’accord de la direction avant de partir/)
    expect(within(f1).queryByRole('button', { name: 'Approuver et envoyer' })).toBeNull()
    unmount()
    vi.unstubAllGlobals()
    serveur('direction', fiche)
    monterApp('/commandes/9')
    const f2 = await screen.findByRole('dialog', { name: /Bon de commande — / })
    expect(await within(f2).findByRole('button', { name: 'Approuver et envoyer' })).toBeEnabled()
    await userEvent.click(within(f2).getByRole('button', { name: 'Renvoyer aux achats…' }))
    await userEvent.type(within(f2).getByRole('textbox', { name: 'Motif du renvoi aux achats' }), 'ok')
    expect(within(f2).getByRole('button', { name: 'Oui, renvoyer aux achats' }).dataset.raison).toContain(
      '3 caractères',
    )
  })

  it('bon parti : gestes grisés avec la phrase du serveur ; imprimer dans un nouvel onglet ; Excel sans raison sociale', async () => {
    serveur('achats', ficheEssai({ raison_sociale_reglee: false }))
    monterApp('/commandes/3')
    const fenetre = await screen.findByRole('dialog', { name: /Bon de commande BC-2026-0002/ })
    const imprimer = within(fenetre).getByRole('link', { name: /Imprimer le bon/ })
    expect(imprimer).toHaveAttribute('target', '_blank')
    expect(imprimer).toHaveAttribute('href', '/api/documents/commandes/3/bon')
    expect(within(fenetre).getByRole('button', { name: 'Excel pour le fournisseur' }).dataset.raison).toMatch(
      /raison sociale/,
    )
    expect(within(fenetre).getByText(/elle manque en tête du bon/)).toBeInTheDocument()
    expect(within(fenetre).queryByRole('button', { name: 'Supprimer le bon' })).toBeNull()
    expect(within(fenetre).getByRole('button', { name: 'Solder (ne plus attendre le reste)' })).toBeEnabled()
    expect(within(fenetre).getByText(/ses lignes sont figées/)).toBeInTheDocument()
  })

  it('date promise figée : le champ est grisé et dit la phrase du serveur (promesse_figee)', async () => {
    const phrase = 'figée avec les prix : une nouvelle date va dans l’ETA (Suivi de l’expédition)'
    serveur('achats', brouillon({ parti: true, promesse_figee: phrase }))
    monterApp('/commandes/9')
    const fenetre = await screen.findByRole('dialog')
    expect(await within(fenetre).findByText(phrase)).toBeInTheDocument()
  })

  it('reçu sous réserve : la ligne et la fiche disent la part en quarantaine, attendue jusqu’à sa libération', async () => {
    serveur('achats', ficheEssai())
    monterApp('/commandes/3')
    const fenetre = await screen.findByRole('dialog', { name: /Bon de commande BC-2026-0002/ })
    const tableau = within(fenetre).getByRole('table', { name: 'Lignes du bon' })
    expect(
      within(tableau).getByText(
        'dont 505 kg reçus sous réserve, en quarantaine : attendus jusqu’à leur libération',
      ),
    ).toBeInTheDocument()
    expect(
      within(fenetre).getByText(
        /Reçu : Dont 505 kg reçus sous réserve, en quarantaine : attendus jusqu’à leur libération\./,
      ),
    ).toBeInTheDocument()
  })

  it('409 à l’enregistrement : le message du serveur et « Recharger la fiche », la saisie reste', async () => {
    serveur('achats', brouillon(), {
      'PUT /commandes/9': {
        statut: 409,
        corps: {
          detail: 'Ce bon a été modifié entre-temps par Karim (09/10/2026 10:40).',
          code: 'conflit_version',
        },
      },
    })
    monterApp('/commandes/9')
    const fenetre = await screen.findByRole('dialog', { name: /Bon de commande — / })
    const zone = await within(fenetre).findByRole('textbox', { name: /Remarques au fournisseur/ })
    await userEvent.type(zone, ' Thanks.')
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Enregistrer' }))
    expect(await within(fenetre).findByText(/modifié entre-temps par Karim/)).toBeInTheDocument()
    expect(within(fenetre).getByRole('button', { name: 'Recharger la fiche' })).toBeInTheDocument()
    expect(zone).toHaveValue(' Thanks.')
  })
})
