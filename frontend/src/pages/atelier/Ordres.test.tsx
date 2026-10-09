/**
 * L'accueil de l'atelier, la liste des ordres et le détail d'un ordre : sorti net du jour (an. 22),
 * « Brouillon » et sa date (an. 6), brouillons d'abord, « charger les suivants » qui dit combien
 * (an. 18), gestes selon le statut (valider, supprimer, annuler avec ses retours), métier « CODE ·
 * Nom » (an. 20), « Pas de réseau » distinct d'une liste vide (an. 3), aucun prix.
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { aujourdhui } from '../../lib/heure'
import { astuce, compteSignalements } from './Accueil'
import { donnees, MONETAIRE, reponsesAtelier } from './essaiAtelier'
import { questionAnnuler } from './Ordre'
import { PAGE_ATELIER, trierOrdres } from './Ordres'
import type { OrdreResume } from './types'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
  sessionStorage.clear()
})
afterEach(() => vi.unstubAllGlobals())

const ordre = (m: Partial<OrdreResume>): OrdreResume => ({ ...donnees().ORDRE_VALIDE, ...m })

describe('Accueil de l’atelier', () => {
  it('sorti net du jour, tuiles, compteurs de mes signalements, aucun prix', async () => {
    const jour = aujourdhui()
    fauxServeur(
      reponsesAtelier('alimentation', {
        'GET /ordres': (_c, url) => ({
          corps:
            url.searchParams.get('statut') === 'brouillon'
              ? [ordre({ id: 5, statut: 'brouillon', numero: null })]
              : [ordre({ date: jour, total: 120, net: 100, revenu: 20 })],
        }),
      }),
    )
    monterApp('/atelier')
    expect(await screen.findByText(/1 ordre\(s\) validé\(s\), 100\skg sortis net\./)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Ordres.*1 brouillon\(s\) à finir/ })).toBeInTheDocument()
    expect(screen.getAllByRole('link')).toHaveLength(7 + 4)
    expect(document.body.textContent).not.toMatch(MONETAIRE)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Se déconnecter' }))
    expect(screen.getByText('Se déconnecter (Ahmed) ?')).toBeInTheDocument()
  })

  it('« Pas de réseau » au lieu de compteurs à zéro', async () => {
    fauxServeur(
      reponsesAtelier('alimentation', {
        'GET /ordres': () => {
          throw new TypeError('Failed to fetch')
        },
      }),
    )
    monterApp('/atelier')
    expect(await screen.findByText('Pas de réseau')).toBeInTheDocument()
    expect(screen.queryByText(/0 ordre\(s\) validé/)).toBeNull()
  })

  it('les signalements comptés sont les miens (identifiant), l’astuce dit ce qui est vrai en http', () => {
    const s = (par_id: number, traite_le: string | null) => ({
      id: par_id,
      quand: '',
      par_id,
      par: '',
      matiere_id: null,
      texte: 'x',
      urgence: 'normale' as const,
      traite_le,
    })
    const page = { elements: [s(3, null), s(3, '2026-10-08'), s(4, null)], total: 3, suivant: null }
    expect(compteSignalements(page, 3)).toBe('1 en attente · 1 réponse(s) des achats')
    expect(compteSignalements(undefined, 3)).toBe('Un fil qui manque, une palette qui finit.')
    expect(astuce(false)).toMatch(/crée un raccourci vers Gestion MP/)
  })
})

describe('Ordres de l’atelier', () => {
  it('brouillons d’abord, puis du plus récent ; « Brouillon » plutôt qu’un numéro', async () => {
    const liste = trierOrdres([
      ordre({ id: 1, date: '2026-10-01' }),
      ordre({ id: 2, date: '2026-10-05' }),
      ordre({ id: 3, statut: 'brouillon', numero: null, date: '2026-09-01' }),
    ])
    expect(liste.map((o) => o.id)).toEqual([3, 2, 1])
    fauxServeur(reponsesAtelier('alimentation'))
    monterApp('/atelier/ordres')
    const cartes = await screen.findAllByRole('listitem')
    expect(cartes[0]?.textContent).toMatch(/^Brouillon/)
    await waitFor(() =>
      expect(cartes[1]?.textContent).toMatch(/OF-2026-0001.*M1 · Van de Wiele n° 1.*sorti net/),
    )
  })

  it('au-delà de 50, « charger les suivants » dit combien il en reste', async () => {
    const beaucoup = Array.from({ length: 60 }, (_, i) => ordre({ id: 100 + i, numero: `OF-${i}` }))
    fauxServeur(reponsesAtelier('alimentation', { 'GET /ordres': { corps: beaucoup } }))
    monterApp('/atelier/ordres')
    expect(await screen.findAllByRole('listitem')).toHaveLength(PAGE_ATELIER)
    await userEvent.setup().click(screen.getByRole('button', { name: '50 sur 60 — charger les suivants' }))
    expect(screen.getAllByRole('listitem')).toHaveLength(60)
  })

  it('un ordre validé : retour et annulation (question qui nomme les retours) ; aucun prix', async () => {
    const appels = fauxServeur(
      reponsesAtelier('alimentation', {
        'POST /ordres/1/annuler': {
          corps: { ...donnees().ORDRE_VALIDE, statut: 'annule', message: 'Annulé.' },
        },
      }),
    )
    const u = userEvent.setup()
    monterApp('/atelier/ordres/1')
    expect(await screen.findByRole('heading', { name: 'OF-2026-0001' })).toBeInTheDocument()
    expect(await screen.findByText('M1 · Van de Wiele n° 1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Faire un retour sur cet ordre' })).toHaveAttribute(
      'href',
      '/atelier/retour?ordre=1',
    )
    expect(screen.getByRole('link', { name: 'lot L-2601' })).toHaveAttribute('href', '/atelier/lots/1')
    expect(document.body.textContent).not.toMatch(MONETAIRE)
    await u.click(screen.getByRole('button', { name: 'Annuler l’ordre (erreur de saisie)' }))
    await u.click(screen.getByRole('button', { name: 'Oui, annuler (contre-passation)' }))
    await waitFor(() => expect(appels.some((a) => a.chemin === '/ordres/1/annuler')).toBe(true))
    expect(appels.find((a) => a.chemin === '/ordres/1/annuler')?.corps).toEqual({ version: 2, motif: '' })
    const o = {
      ...donnees().ORDRE_VALIDE,
      retours: [{ id: 3, numero: 'RET-2026-0001', date: '', quantite: 1 }],
    }
    expect(questionAnnuler(o)).toMatch(/^Annuler tout l’ordre et ses retours \(RET-2026-0001\) \?/)
  })

  it('un brouillon : valider, modifier (rouvre ce brouillon), supprimer avec sa version', async () => {
    const appels = fauxServeur(reponsesAtelier('alimentation', { 'DELETE /ordres/5': { statut: 204 } }))
    const u = userEvent.setup()
    const app = monterApp('/atelier/ordres/5')
    expect(await screen.findByRole('heading', { name: 'Brouillon' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Modifier le brouillon' })).toHaveAttribute(
      'href',
      '/atelier/envoyer?ordre=5',
    )
    await u.click(screen.getByRole('button', { name: 'Supprimer le brouillon' }))
    const conf = screen.getByRole('group', { name: 'Confirmation' })
    expect(conf.textContent).toMatch('Supprimer ce brouillon ? Rien n’est sorti du stock.')
    await u.click(within(conf).getByRole('button', { name: 'Oui, supprimer' }))
    await waitFor(() => expect(app.adresse()).toBe('/atelier/ordres'))
    expect(appels.some((a) => a.methode === 'DELETE' && a.chemin === '/ordres/5?version=2')).toBe(true)
  })

  it('404 : « Ordre introuvable » avec l’en-tête et « ‹ »', async () => {
    fauxServeur(reponsesAtelier('alimentation'))
    monterApp('/atelier/ordres/404')
    expect(await screen.findByRole('heading', { name: 'Ordre introuvable' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retour' })).toBeInTheDocument()
  })
})
