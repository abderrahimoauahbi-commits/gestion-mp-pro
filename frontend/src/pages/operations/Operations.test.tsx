/** Opérations : onglets par rôle, aucun prix chez l'alimentation, fiche à adresse stable, saisie, blocages. */
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
import { lotEssai, MAGASINS, matiereEssai } from '../inventaire/donneesEssai'
import { ligneOperationEssai, MOTIFS, operationEssai } from './donneesEssai'
import type { OperationFiche } from './types'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const page = (elements: OperationFiche[]) => ({ corps: { elements, total: elements.length, suivant: null } })

function serveur(role: Role, autres: Record<string, Reponse> = {}) {
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /motifs': { corps: MOTIFS },
    'GET /magasins': { corps: [...MAGASINS, { ...MAGASINS[0]!, id: 3, code: 'ATELIER', nom: 'Atelier' }] },
    'GET /matieres': { corps: [matiereEssai()] },
    'GET /devises': {
      corps: [
        {
          code: 'MAD',
          nom: 'Dirham',
          cours: 1,
          cours_le: null,
          cours_repris: false,
          actif: true,
          version: 1,
        },
      ],
    },
    'GET /lots': { corps: [lotEssai()] },
    'GET /brouillons': { corps: { nombre: 1 } },
    'GET /operations': (_c, url) =>
      url.searchParams.get('type') === 'ouverture'
        ? page([
            operationEssai({
              id: 8,
              type: 'ouverture',
              numero: 'OUV-2026-0001',
              statut: 'validee',
              valeurs: [{ devise: 'EUR', montant: 1344 }],
              lignes: [ligneOperationEssai({ prix: 3.2, devise: 'EUR', quantite: 420 })],
            }),
          ])
        : page([
            operationEssai({
              blocages: ['l’inventaire INV-2026-0001 compte « IMP FRISÉ ROUGE » (PRINCIPAL)'],
            }),
          ]),
    'GET /operations/5': {
      corps: operationEssai({
        blocages: ['l’inventaire INV-2026-0001 compte « IMP FRISÉ ROUGE » (PRINCIPAL)'],
      }),
    },
    ...autres,
  })
}

describe('Opérations : la liste', () => {
  it('l’alimentation ne voit que les transferts et les retours des machines, sans aucun prix', async () => {
    serveur('alimentation')
    monterApp('/operations')
    const onglets = await screen.findByRole('tablist', { name: 'Types d’opération' })
    expect(
      within(onglets)
        .getAllByRole('tab')
        .map((o) => o.textContent),
    ).toEqual(['Transferts', 'Retours machine'])
    expect(await screen.findByText('sera refusée')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Nouveau transfert' })).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/MAD|EUR|USD|Prix|Valeur/)
  })

  it('l’alimentation n’ouvre pas l’onglet des ouvertures', async () => {
    serveur('alimentation')
    const app = monterApp('/operations?onglet=ouverture')
    await waitFor(() => expect(app.adresse()).not.toMatch(/onglet=ouverture/))
  })

  it('les achats voient la valeur d’une ouverture, par devise', async () => {
    serveur('achats')
    monterApp('/operations?onglet=ouverture')
    expect(await screen.findByText('OUV-2026-0001')).toBeInTheDocument()
    expect(screen.getByText('1 344 EUR')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Nouveau stock d’ouverture' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tout valider… (1)' })).toBeInTheDocument()
  })

  it('la recherche et l’état partent au serveur et restent au changement d’onglet', async () => {
    const appels = serveur('achats')
    monterApp('/operations?onglet=transfert&etat=brouillon&q=frise')
    await screen.findByText('sera refusée')
    expect(
      appels.some(
        (a) =>
          a.chemin.startsWith('/operations?') &&
          a.chemin.includes('statut=brouillon') &&
          a.chemin.includes('q=frise'),
      ),
    ).toBe(true)
    await userEvent.click(screen.getByRole('tab', { name: 'Ajustements' }))
    await waitFor(() =>
      expect(
        appels.some(
          (a) =>
            a.chemin.includes('type=ajustement') &&
            a.chemin.includes('statut=brouillon') &&
            a.chemin.includes('q=frise'),
        ),
      ).toBe(true),
    )
  })
})

describe('Opérations : la fenêtre', () => {
  it('lue directement par son adresse, elle pose l’onglet de son type et le reprend à la fermeture', async () => {
    serveur('achats', {
      'GET /operations/9': {
        corps: operationEssai({
          id: 9,
          type: 'retour_fournisseur',
          numero: 'RFO-2026-0001',
          statut: 'validee',
          fournisseur_id: 4,
          fournisseur: 'LOMAT',
        }),
      },
    })
    const app = monterApp('/operations/9')
    expect(await screen.findByText(/RFO-2026-0001/)).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Retours au fournisseur' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByRole('link', { name: 'LOMAT' })).toHaveAttribute('href', '/fournisseurs/4')
    expect(screen.getByRole('button', { name: 'Annuler (contre-passation)' })).toBeInTheDocument()
    await userEvent.click(within(screen.getByRole('dialog')).getAllByRole('button', { name: 'Fermer' })[0]!)
    await waitFor(() => expect(app.adresse()).toBe('/operations?onglet=retour_fournisseur'))
  })

  it('Valider est grisé par les blocages du serveur ; le brouillon se supprime à sa version', async () => {
    const appels = serveur('alimentation', { 'DELETE /operations/5': { statut: 204 } })
    monterApp('/operations/5')
    const valider = await screen.findByRole('button', { name: 'Valider : le stock bouge' })
    expect(valider.getAttribute('data-raison')).toBe(
      'Sera refusé : l’inventaire INV-2026-0001 compte « IMP FRISÉ ROUGE » (PRINCIPAL).',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer le brouillon' }))
    await userEvent.click(screen.getByRole('button', { name: 'Oui, supprimer' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'DELETE')).toBe(true))
    expect(appels.find((a) => a.methode === 'DELETE')?.chemin).toBe('/operations/5?version=2')
  })

  it('un retour des machines en brouillon se modifie par l’alimentation (an. 24), se lit par les achats', async () => {
    const retour = operationEssai({
      type: 'retour_machine',
      ordre_id: 3,
      ordre: 'OF-2026-0003',
      motif_id: null,
    })
    serveur('alimentation', { 'GET /operations/5': { corps: retour } })
    monterApp('/operations/5')
    expect(await screen.findByRole('button', { name: 'Valider : le stock bouge' })).toBeInTheDocument()
    vi.unstubAllGlobals()
    stockageMemoire()
    serveur('achats', {
      'GET /operations/5': {
        corps: {
          ...retour,
          peut_agir: false,
          raison: '« Retour des machines » est réservé à : direction, alimentation.',
        },
      },
    })
    monterApp('/operations/5')
    expect(await screen.findByText(/est réservé à : direction, alimentation/)).toBeInTheDocument()
    expect(screen.queryAllByRole('button', { name: 'Valider : le stock bouge' })).toHaveLength(1)
  })

  it('un nouveau transfert : la ligne, l’enregistrement, puis l’adresse de l’opération (an. 22)', async () => {
    const appels = serveur('achats', {
      'POST /operations': { corps: operationEssai({ id: 12 }) },
      'GET /operations/12': { corps: operationEssai({ id: 12 }) },
    })
    const app = monterApp('/operations/nouvelle?type=transfert')
    await userEvent.click(await screen.findByRole('combobox', { name: 'Matière' }))
    await userEvent.click(await screen.findByRole('option', { name: /IMP FRISÉ ROUGE/ }))
    await userEvent.click(await screen.findByRole('combobox', { name: 'Lot et magasin de départ' }))
    await userEvent.click(await screen.findByRole('option', { name: /Lot L24-100 · PRINCIPAL/ }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Quantité' }), '40')
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter la ligne' }))
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer le brouillon' }))
    await waitFor(() => expect(app.adresse()).toBe('/operations/12'))
    expect(appels.find((a) => a.methode === 'POST')?.corps).toMatchObject({
      type: 'transfert',
      motif_id: null,
      lignes: [
        { matiere_id: 1, lot_id: 11, magasin_id: 1, magasin_destination_id: 2, quantite: 40, unite: 'kg' },
      ],
    })
  })
})
