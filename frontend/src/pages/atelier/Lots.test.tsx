/**
 * Trouver un lot, sa fiche, le déplacer : recherche au serveur après la frappe (sans accents),
 * « Lot introuvable » sur un 404 seulement, « Pas de réseau » sinon (an. 3), étiquette 100 × 70 mm
 * en nouvel onglet, aucun prix (an. 27) ; déplacement en une requête validée, mise en quarantaine
 * au motif imposé avec observations obligatoires, libération jamais proposée ((d)).
 */
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { donnees, MONETAIRE, reponsesAtelier } from './essaiAtelier'
import { libelleMagasin, recents } from './LotFiche'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
  sessionStorage.clear()
})
afterEach(() => vi.unstubAllGlobals())

describe('Trouver un lot et sa fiche', () => {
  it('la recherche part au serveur après la frappe ; la carte mène à la fiche', async () => {
    const appels = fauxServeur(reponsesAtelier('alimentation'))
    const u = userEvent.setup()
    monterApp('/atelier/chercher')
    await screen.findAllByRole('listitem')
    await u.type(screen.getByRole('searchbox', { name: 'Chercher un lot' }), 'rouge')
    await waitFor(() => expect(appels.some((a) => a.chemin.includes('q=rouge'))).toBe(true))
    expect(screen.getByRole('link', { name: /POIL ROUGE 2900.*lot L-2601/ })).toHaveAttribute(
      'href',
      '/atelier/lots/1',
    )
    expect(document.body.textContent).not.toMatch(MONETAIRE)
  })

  it('la fiche : reste, magasins, ordres servis, étiquette, déplacer ; aucun prix', async () => {
    fauxServeur(reponsesAtelier('alimentation'))
    monterApp('/atelier/lots/1')
    expect(await screen.findByRole('heading', { name: 'Lot L-2601' })).toBeInTheDocument()
    for (const lien of screen.getAllByRole('link', { name: 'OF-2026-0001' }))
      expect(lien).toHaveAttribute('href', '/atelier/ordres/1')
    // Un retour des machines, dans ce qu'il a vécu, mène à sa fiche d'opération.
    expect(screen.getByRole('link', { name: 'RET-2026-0001' })).toHaveAttribute('href', '/operations/2')
    expect(screen.getByRole('link', { name: /Imprimer l’étiquette/ })).toHaveAttribute(
      'href',
      '/api/documents/etiquettes?lots=1',
    )
    expect(screen.getByRole('link', { name: 'Déplacer ce lot' })).toHaveAttribute(
      'href',
      '/atelier/deplacer?lot=1',
    )
    expect(document.body.textContent).not.toMatch(MONETAIRE)
  })

  it('un lot en quarantaine ne se déplace pas d’ici, et le dit', async () => {
    const d = donnees()
    fauxServeur(
      reponsesAtelier('alimentation', {
        'GET /lots/1': { corps: { ...d.LOT, disponible: 0, quarantaine: 10, statut: 'quarantaine' } },
      }),
    )
    monterApp('/atelier/lots/1')
    expect(await screen.findByText('Rien de disponible hors quarantaine')).toBeInTheDocument()
    expect(screen.getByText('En quarantaine')).toBeInTheDocument()
  })

  it('404 : « Lot introuvable » ; coupure : « Pas de réseau »', async () => {
    fauxServeur(
      reponsesAtelier('alimentation', {
        'GET /lots/8': () => {
          throw new TypeError('Failed to fetch')
        },
      }),
    )
    const app = monterApp('/atelier/lots/404')
    expect(await screen.findByRole('heading', { name: 'Lot introuvable' })).toBeInTheDocument()
    await app.routeur.navigate('/atelier/lots/8')
    expect(await screen.findByText('Pas de réseau')).toBeInTheDocument()
  })

  it('un seul libellé de quarantaine ; mouvements du plus récent au plus ancien', () => {
    expect(libelleMagasin({ magasin: 'Quarantaine', type: 'quarantaine' }).quarantaine).toBe(false)
    expect(libelleMagasin({ magasin: 'Q2', type: 'quarantaine' }).quarantaine).toBe(true)
    const m = donnees().LOT.mouvements
    expect(recents(m)[0]?.type).toBe('RETOUR_MACHINE')
  })
})

describe('Déplacer un lot', () => {
  it('vers la quarantaine : motif imposé, observations exigées, une requête validée', async () => {
    const appels = fauxServeur(
      reponsesAtelier('alimentation', {
        'POST /operations': { corps: { numero: 'TRF-2026-0001', total: 10 } },
      }),
    )
    const u = userEvent.setup()
    monterApp('/atelier/deplacer?lot=1')
    expect(await screen.findByRole('heading', { name: 'Déplacer un lot' })).toBeInTheDocument()
    expect(await screen.findByText('Choisir le magasin d’arrivée')).toBeInTheDocument()
    const vers = screen.getByRole('combobox', { name: 'Vers' })
    await u.click(vers)
    await u.type(vers, 'quarant{Enter}')
    expect(screen.getByText('Pourquoi ? Mise en quarantaine (motif imposé).')).toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: 'Libération de quarantaine' })).toBeNull()
    expect(screen.getByText('Écrire ce qui est douteux, dans les observations')).toBeInTheDocument()
    const quantite = screen.getByRole('textbox', { name: 'Quantité à déplacer' })
    await u.clear(quantite)
    await u.type(quantite, '10')
    await u.type(
      screen.getByRole('textbox', { name: /Observations \(ce qui est douteux\)/ }),
      'Bobines tachées',
    )
    await u.click(screen.getByRole('button', { name: /Déplacer 10,0\skg/ }))
    await u.click(screen.getByRole('button', { name: 'Oui, déplacer' }))
    expect(await screen.findByRole('heading', { name: /Fait — TRF-2026-0001/ })).toBeInTheDocument()
    expect(appels.find((a) => a.methode === 'POST')?.corps).toMatchObject({
      type: 'transfert',
      motif_id: 14,
      commentaire: 'Bobines tachées',
      valider: true,
      lignes: [{ lot_id: 1, magasin_id: 1, magasin_destination_id: 2, quantite: 10, unite: 'kg' }],
    })
  })

  it('le choix du lot : seulement ce qui est disponible hors quarantaine', async () => {
    fauxServeur(reponsesAtelier('alimentation'))
    const u = userEvent.setup()
    const app = monterApp('/atelier/deplacer')
    const choix = await screen.findByRole('combobox', { name: 'Quel lot ?' })
    await u.click(choix)
    expect(screen.queryByRole('option', { name: /L-2607/ })).toBeNull()
    await u.type(choix, 'L-2602{Enter}')
    await waitFor(() => expect(app.adresse()).toBe('/atelier/deplacer?lot=2'))
  })
})
