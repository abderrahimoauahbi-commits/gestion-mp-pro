/**
 * Les réceptions dans l'application entière : liste à onglets ; saisie d'un camion à partir du n°
 * du bon (le fournisseur suit, les lignes à livrer se chargent) et enregistrement d'un camion en
 * deux devises en **une** requête ; fiche : validation dite avant le « Oui », annulation avec un
 * motif de trois caractères, règlement grisé avec sa raison ; pesées filtrées au serveur ;
 * réclamations ; l'alimentation n'a pas accès.
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
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
import { ficheEssai, resumeEssai } from '../commandes/donneesEssai'
import {
  BOBINES,
  MOTIFS,
  PESEES,
  receptionEssai,
  receptionResumeEssai,
  reclamationEssai,
} from './donneesEssai'
import { adresseNouvelle, apresEnregistrement } from './Receptions'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const FOURNISSEUR = {
  id: 3,
  nom: 'Filature du Souss',
  pays: 'MAROC',
  devise: 'MAD',
  delai_paiement_jours: 30,
  actif: true,
}
const MATIERE = {
  id: 1,
  reference: 'PP FRZ 2900 Ivoire 1002',
  designation: 'Ivoire',
  fournisseur: 'Beaulieu',
  fournisseur_id: 1,
  devise: 'EUR',
  prix_kg: 2.85,
  kg_par_ml: 0,
  poids_bobine: 2.5,
  bobines_palette: 96,
}
const MAGASINS = [
  {
    id: 1,
    code: 'Magasin principal',
    nom: '',
    type: 'stock_courant',
    contenu: '',
    actif: true,
    kg_detenus: 0,
    version: 1,
  },
  {
    id: 2,
    code: 'Quarantaine',
    nom: '',
    type: 'quarantaine',
    contenu: '',
    actif: true,
    kg_detenus: 0,
    version: 1,
  },
]

function serveur(role: 'direction' | 'achats' | 'alimentation', autres: Record<string, Reponse> = {}) {
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /receptions': {
      corps: {
        elements: [
          receptionResumeEssai({ id: 1, numero: 'REC-2026-0001', statut: 'validee', blocages: [] }),
          receptionResumeEssai({ id: 2, numero: null, statut: 'brouillon', blocages: ['a', 'b'] }),
        ],
        total: 2,
        suivant: null,
        pese_total: 0,
      },
    },
    'GET /receptions/apercu': {
      corps: {
        brouillon: 1,
        validee: 1,
        annulee: 0,
        total: 2,
        fournisseurs: [{ id: 2, nom: 'Polyfil Industries' }],
      },
    },
    'GET /receptions/1': { corps: receptionEssai() },
    'GET /reclamations': { corps: [reclamationEssai()] },
    'GET /reclamations/1': { corps: reclamationEssai() },
    'GET /receptions/pesees': { corps: PESEES },
    'GET /receptions/bobines': { corps: BOBINES },
    'GET /motifs': { corps: MOTIFS },
    'GET /commandes': {
      corps: [
        resumeEssai({
          id: 3,
          numero: 'BC-2026-0002',
          fournisseur_id: 3,
          fournisseur: 'Filature du Souss',
          statut: 'confirmee',
          reste_kg: 1017,
        }),
      ],
    },
    'GET /commandes/3': { corps: ficheEssai() },
    'GET /fournisseurs': { corps: [FOURNISSEUR] },
    'GET /matieres': { corps: [MATIERE] },
    'GET /magasins': { corps: MAGASINS },
    'GET /parametres': { corps: [] },
    'GET /devises': { corps: [] },
    ...autres,
  })
}

describe('Réceptions', () => {
  it('adresses : anciens liens sur la liste seulement ; message d’un camion en deux devises', () => {
    expect(adresseNouvelle('/receptions', new URLSearchParams('ouvrir=4'))).toBe('/receptions/4')
    expect(adresseNouvelle('/reclamations/nouvelle', new URLSearchParams('reception=4'))).toBeNull()
    expect(
      apresEnregistrement([receptionEssai({ devise: 'USD' }), receptionEssai({ devise: 'EUR' })]),
    ).toMatch(/2 réceptions enregistrées en brouillon \(USD, EUR\)/)
  })

  it('liste : brouillons d’abord, points à régler, « Corriger » rouvre la saisie du brouillon', async () => {
    serveur('achats')
    const { adresse } = monterApp('/receptions')
    const tableau = await screen.findByRole('table', { name: 'Réceptions — Brouillons' })
    expect(within(tableau).getAllByText('2 point(s) à régler').length).toBeGreaterThan(0)
    expect(screen.getByRole('tab', { name: /Validées/ })).toHaveTextContent('Validées1')
    await userEvent.click(within(tableau).getByRole('button', { name: 'Corriger' }))
    await waitFor(() => expect(adresse()).toBe('/receptions/nouvelle?brouillon=2'))
  })

  it('saisie : le n° du bon choisit le fournisseur et charge ses lignes ; deux devises en une requête', async () => {
    const appels = serveur('achats', {
      'POST /receptions': {
        statut: 201,
        corps: [
          receptionEssai({ id: 7, numero: null, statut: 'brouillon' }),
          receptionEssai({ id: 8, devise: 'EUR' }),
        ],
      },
      'GET /receptions/7': { corps: receptionEssai({ id: 7, numero: null, statut: 'brouillon' }) },
    })
    const { adresse } = monterApp('/receptions/nouvelle')
    const bon = await screen.findByRole('combobox', { name: /N° du bon de commande/ })
    const fenetre = screen.getByRole('dialog', { name: 'Nouvelle réception' })
    await userEvent.click(bon)
    await userEvent.type(bon, '0002{Enter}')
    expect(await within(fenetre).findByText('COTON TRAME 8/2 Écru')).toBeInTheDocument()
    const ajout = within(fenetre).getByRole('combobox', { name: /Ajouter une matière hors commande/ })
    await userEvent.click(ajout)
    await userEvent.type(ajout, 'ivoire{Enter}')
    fireEvent.change(
      await within(fenetre).findByRole('combobox', { name: /Devise du prix de PP FRZ 2900 Ivoire/ }),
      { target: { value: 'EUR' } },
    )
    expect(within(fenetre).getByText(/Ce camion porte deux devises \(EUR, MAD\)/)).toBeInTheDocument()
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Enregistrer le brouillon' }))
    await waitFor(() => expect(adresse()).toBe('/receptions/7?liste=brouillon'))
    const posts = appels.filter((a) => a.methode === 'POST' && a.chemin === '/receptions')
    expect(posts).toHaveLength(1)
    expect(posts[0]?.corps).toMatchObject({ fournisseur_id: 3, factures: {} })
    const lignes = (posts[0]?.corps as { lignes: { devise: string; commande_ligne_id: number | null }[] })
      .lignes
    expect(lignes.map((l) => l.devise).sort()).toEqual(['', '', 'EUR'])
  })

  it('fiche validée : règlement de la facture (route 229) ; annulation avec motif de 3 caractères', async () => {
    const appels = serveur('direction', {
      'POST /receptions/1/annuler': { corps: receptionEssai({ statut: 'annulee' }) },
      'PUT /echeancier/paiement': { corps: {} },
    })
    monterApp('/receptions/1')
    const fenetre = await screen.findByRole('dialog', { name: /Réception — REC-2026-0001/ })
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Marquer réglée' }))
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Oui, réglée' }))
    const facture = receptionEssai().facture
    await waitFor(() =>
      expect(appels.find((a) => a.chemin === '/echeancier/paiement')?.corps).toMatchObject({
        genre: 'facture',
        id: facture?.id,
        version: facture?.version,
      }),
    )
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Annuler (contre-passation)' }))
    await userEvent.type(within(fenetre).getByRole('textbox', { name: 'Motif' }), 'ok')
    expect(within(fenetre).getByRole('button', { name: 'Oui, annuler (contre-passation)' })).toBeDisabled()
    await userEvent.type(within(fenetre).getByRole('textbox', { name: 'Motif' }), ' double')
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Oui, annuler (contre-passation)' }))
    await waitFor(() =>
      expect(appels.find((a) => a.chemin === '/receptions/1/annuler')?.corps).toEqual({
        version: receptionEssai().version,
        motif: 'ok double',
      }),
    )
  })

  it('brouillon : « Valider » dit d’avance ce qui entre et ce qui bloque', async () => {
    serveur('achats', {
      'GET /receptions/1': {
        corps: receptionEssai({
          statut: 'brouillon',
          numero: null,
          blocages: ['« X » : la pesée est à zéro.'],
          actions: {
            ...receptionEssai().actions,
            valider: '« X » : la pesée est à zéro.',
            modifier: null,
            supprimer: null,
          },
        }),
      },
    })
    monterApp('/receptions/1')
    const fenetre = await screen.findByRole('dialog', { name: /Réception — Brouillon/ })
    expect(within(fenetre).getByText('Avant de valider :')).toBeInTheDocument()
    expect(within(fenetre).getByRole('button', { name: 'Valider la réception' }).dataset.raison).toContain(
      'la pesée est à zéro',
    )
  })

  it('pesées : « Écarts seulement » part au serveur ; un brouillon se dit « Brouillon »', async () => {
    const appels = serveur('achats')
    monterApp('/receptions?onglet=pesees')
    const tableau = await screen.findByRole('table', { name: 'Archive des pesées' })
    expect(within(tableau).queryByText(/brouillon n°/i)).toBeNull()
    await userEvent.click(screen.getByRole('switch', { name: /Écarts seulement/ }))
    await waitFor(() =>
      expect(
        appels.some((a) => a.chemin.startsWith('/receptions/pesees') && a.chemin.includes('ecarts=true')),
      ).toBe(true),
    )
  })

  it('réclamations : indicateurs, bascule dans l’adresse ; l’alimentation n’a pas accès', async () => {
    serveur('achats')
    const { adresse, unmount } = monterApp('/receptions?onglet=reclamations')
    expect(await screen.findByRole('table', { name: 'Réclamations' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Toutes/ }))
    await waitFor(() => expect(adresse()).toContain('etat=toutes'))
    unmount()
    vi.unstubAllGlobals()
    serveur('alimentation')
    const app = monterApp('/receptions')
    await waitFor(() => expect(app.adresse()).not.toBe('/receptions'))
  })
})
