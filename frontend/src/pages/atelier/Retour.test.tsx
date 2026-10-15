/**
 * Retour des machines au téléphone : le choix de l'ordre (10 derniers, recherche au serveur au-delà),
 * puis la saisie lot par lot — « Sorti net » (an. 21), bobines arrondies vers le bas pour ne jamais
 * rendre plus que le sorti (an. 24), création et validation en une requête (`valider: true`),
 * saisie gardée (an. 17), raison sous le bouton grisé.
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { donnees, MONETAIRE, pageOrdres, reponsesAtelier } from './essaiAtelier'
import { motsDe, piedRetour } from './Retour'
import type { OrdreResume } from './types'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
  sessionStorage.clear()
})
afterEach(() => vi.unstubAllGlobals())

const lotRouge = () => {
  const section = screen.getByRole('region', { name: 'Lot L-2601' })
  return within(section)
}

describe('Retour des machines', () => {
  it('le pied de la liste dit ce qui n’est pas montré', () => {
    expect(piedRetour(10, 25, false)).toBe('les 10 derniers sur 25 : chercher un ordre plus ancien')
    expect(piedRetour(30, 32, true)).toBe('2 autre(s) : préciser la recherche')
    expect(piedRetour(5, 5, false)).toBe('')
  })

  it('le choix de l’ordre : les validés ; toucher une carte ouvre le retour', async () => {
    fauxServeur(reponsesAtelier('alimentation'))
    const u = userEvent.setup()
    const app = monterApp('/atelier/retour')
    expect(await screen.findByText('De quel ordre revient la matière ?')).toBeInTheDocument()
    await u.click(await screen.findByRole('link', { name: /OF-2026-0001/ }))
    await waitFor(() => expect(app.adresse()).toBe('/atelier/retour?ordre=1'))
    expect(await screen.findByRole('heading', { name: 'Retour — OF-2026-0001' })).toBeInTheDocument()
  })

  it('25 validés : les 10 derniers, le total, la suite et la recherche lus au serveur', async () => {
    const valides: OrdreResume[] = Array.from({ length: 25 }, (_, i) => ({
      ...donnees().ORDRE_VALIDE,
      id: 100 + i,
      numero: `OF-2026-${String(100 + i)}`,
      date: `2026-10-${String(1 + i).padStart(2, '0')}`,
    }))
    const appels = fauxServeur(reponsesAtelier('alimentation', { 'GET /ordres': pageOrdres(valides) }))
    const u = userEvent.setup()
    monterApp('/atelier/retour')
    expect(
      await screen.findByText('les 10 derniers sur 25 : chercher un ordre plus ancien'),
    ).toBeInTheDocument()
    const cartes = screen.getAllByRole('listitem')
    expect(cartes.map((c) => c.textContent?.slice(0, 11))).toEqual(
      Array.from({ length: 10 }, (_, i) => `OF-2026-${String(124 - i)}`),
    )
    await u.click(screen.getByRole('button', { name: '10 sur 25 — charger les suivants' }))
    expect(
      await screen.findByText('les 20 derniers sur 25 : chercher un ordre plus ancien'),
    ).toBeInTheDocument()
    await u.type(screen.getByRole('searchbox', { name: 'Chercher un ordre' }), 'OF')
    await waitFor(() => expect(appels.some((a) => a.chemin.includes('q=OF'))).toBe(true))
    expect(appels.filter((a) => a.chemin.startsWith('/ordres?')).map((a) => a.chemin)).toEqual([
      '/ordres?statut=valide&limite=10',
      '/ordres?statut=valide&limite=20',
      '/ordres?statut=valide&q=OF&limite=30',
    ])
    expect(appels.some((a) => a.chemin.startsWith('/ordres/ouverts'))).toBe(false)
    expect(motsDe(['/ordres', { statut: 'valide', q: 'OF' }])).toBe('OF')
    expect(motsDe(['/ordres'])).toBeUndefined()
  })

  it('« Tout ce qui est parti » en bobines arrondit vers le bas ; un seul envoi, validé', async () => {
    const appels = fauxServeur(
      reponsesAtelier('alimentation', {
        'POST /operations': (corps) => ({
          corps: { numero: 'RET-2026-0001', total: 72.361, corps },
        }),
      }),
    )
    const u = userEvent.setup()
    monterApp('/atelier/retour?ordre=1')
    await screen.findByRole('heading', { name: 'Retour — OF-2026-0001' })
    expect(lotRouge().getByText('Sorti net : 73,4 kg')).toBeInTheDocument()
    expect(screen.getByText('Saisir ce qui revient, lot par lot.')).toBeInTheDocument()
    await u.click(lotRouge().getByRole('radio', { name: 'Bobines' }))
    await u.click(lotRouge().getByRole('button', { name: 'Tout ce qui est parti' }))
    expect(lotRouge().getByText(/29 bobines = 72,4\skg/)).toBeInTheDocument()
    expect(JSON.parse(sessionStorage.getItem('gestion-mp-pro:saisie:retour:1') ?? '{}').lignes).toBeTruthy()
    expect(document.body.textContent).not.toMatch(MONETAIRE)
    await u.click(screen.getByRole('button', { name: /Remettre 72,4\skg en stock/ }))
    await u.click(screen.getByRole('button', { name: 'Oui, enregistrer le retour' }))
    expect(
      await screen.findByRole('heading', { name: /Retour enregistré — RET-2026-0001/ }),
    ).toBeInTheDocument()
    const envoi = appels.find((a) => a.methode === 'POST' && a.chemin === '/operations')
    expect(envoi?.corps).toMatchObject({
      type: 'retour_machine',
      ordre_id: 1,
      motif_id: 1,
      valider: true,
      lignes: [{ matiere_id: 1, lot_id: 1, magasin_id: 1, quantite: 72.361, unite: 'kg' }],
    })
    expect(appels.filter((a) => a.methode !== 'GET')).toHaveLength(1)
    expect(sessionStorage.getItem('gestion-mp-pro:saisie:retour:1')).not.toMatch(/72\.361/)
  })

  it('plus que le sorti net : refusé d’avance, la raison nomme le lot', async () => {
    fauxServeur(reponsesAtelier('alimentation'))
    const u = userEvent.setup()
    monterApp('/atelier/retour?ordre=1')
    await screen.findByRole('heading', { name: 'Retour — OF-2026-0001' })
    const champ = lotRouge().getByRole('textbox', { name: 'Revient du lot L-2601' })
    await u.type(champ, '80')
    expect(lotRouge().getByText('On ne rend pas plus que ce qui est parti.')).toBeInTheDocument()
    expect(
      screen.getByText('1 lot(s) dépassent ce qui est parti : POIL ROUGE 2900 (lot L-2601)'),
    ).toBeInTheDocument()
  })

  it('tout est revenu : la liste le dit', async () => {
    const d = donnees()
    fauxServeur(
      reponsesAtelier('alimentation', {
        'GET /ordres/1/lots-sortis': { corps: d.LOTS_SORTIS.map((l) => ({ ...l, sorti_net: 0 })) },
      }),
    )
    monterApp('/atelier/retour?ordre=1')
    expect(
      await screen.findByText('Tout ce qui est parti sur cet ordre est déjà revenu.'),
    ).toBeInTheDocument()
  })
})
