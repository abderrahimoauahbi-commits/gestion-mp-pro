/**
 * Envoyer aux machines au téléphone, dans l'application entière : la demande, la proposition, la
 * vue repliée « tout est conforme », la validation en deux requêtes (brouillon puis validation),
 * la saisie gardée et reprise, l'abandon, et jamais d'ordre vierge à la place d'un ordre qui ne se
 * lit pas (404 → « Ordre introuvable », coupure → « Pas de réseau », validé → sa fiche, an. 10).
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { donnees, MONETAIRE, reponsesAtelier } from './essaiAtelier'
import type { OrdreFiche } from './types'
import { etatInitial } from './useSaisieSortie'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
  sessionStorage.clear()
})
afterEach(() => vi.unstubAllGlobals())

const valide = (): OrdreFiche => ({ ...donnees().ORDRE_VALIDE, id: 9, numero: 'OF-2026-0009' })

async function demander(u: ReturnType<typeof userEvent.setup>) {
  await screen.findByRole('heading', { name: 'Envoyer aux machines' })
  const qualite = await screen.findByRole('combobox', { name: 'Qualité à fabriquer' })
  await u.click(qualite)
  await u.type(qualite, 'ATL{Enter}')
  const m2 = screen.getByRole('textbox', { name: 'Mètres carrés' })
  await u.clear(m2)
  await u.type(m2, '100')
  await u.click(screen.getByRole('button', { name: 'Voir les fils et les lots à prendre' }))
  await screen.findByRole('heading', { name: 'Lots à prendre' })
}

describe('Envoyer aux machines', () => {
  it('demande → lots proposés repliés → validation : brouillon puis validation, sans prix', async () => {
    const appels = fauxServeur(
      reponsesAtelier('alimentation', {
        'POST /ordres': { corps: { ...valide(), statut: 'brouillon', numero: null, version: 1 } },
        'POST /ordres/9/valider': { corps: valide() },
      }),
    )
    const u = userEvent.setup()
    monterApp('/atelier/envoyer')
    expect(
      await screen.findByText(
        /^À renseigner : la qualité de chaque ligne, les m² à tisser de chaque qualité\.$/,
      ),
    ).toBeInTheDocument()
    await demander(u)
    expect(screen.getByRole('button', { name: /Tout est conforme : 4 fils/ })).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(MONETAIRE)
    await u.click(screen.getByRole('button', { name: 'Valider la sortie' }))
    const question = screen.getByRole('group', { name: 'Confirmation' })
    expect(question.textContent).toMatch(/Sortir 194\skg le .* · Magasin principal \? Le stock est débité/)
    await u.click(within(question).getByRole('button', { name: 'Oui, valider la sortie' }))
    expect(await screen.findByRole('heading', { name: 'Sortie enregistrée' })).toBeInTheDocument()
    expect(screen.getByText('Ordre OF-2026-0009 validé')).toBeInTheDocument()
    const creation = appels.find((a) => a.methode === 'POST' && a.chemin === '/ordres')
    expect(creation?.corps).toMatchObject({
      magasin_id: 1,
      qualites: [{ qualite_id: 1, m2: 100 }],
      lignes: expect.arrayContaining([expect.objectContaining({ lot_id: 1, unite: 'kg' })]),
    })
    expect(appels.find((a) => a.chemin === '/ordres/9/valider')?.corps).toEqual({ version: 1 })
    expect(sessionStorage.getItem('gestion-mp-pro:saisie:envoyer2')).toBeNull()
  })

  it('un refus à la validation garde le brouillon et le dit', async () => {
    fauxServeur(
      reponsesAtelier('alimentation', {
        'POST /ordres': { corps: { ...valide(), statut: 'brouillon', numero: null, version: 1 } },
        'POST /ordres/9/valider': {
          statut: 409,
          corps: { detail: 'Un ordre daté du 09/10/2026 existe déjà.', code: 'ordre_des_dates' },
        },
      }),
    )
    const u = userEvent.setup()
    monterApp('/atelier/envoyer')
    await demander(u)
    await u.click(screen.getByRole('button', { name: 'Valider la sortie' }))
    await u.click(screen.getByRole('button', { name: 'Oui, valider la sortie' }))
    expect(
      await screen.findByText(
        'Un ordre daté du 09/10/2026 existe déjà. — l’ordre est gardé en brouillon, modifiable.',
      ),
    ).toBeInTheDocument()
    const garde = JSON.parse(sessionStorage.getItem('gestion-mp-pro:saisie:envoyer2') ?? '{}')
    expect(garde).toMatchObject({ id: 9, version: 1 })
  })

  it('la saisie est gardée en quittant, reprise au retour ; « Abandonner » repart à vide', async () => {
    fauxServeur(reponsesAtelier('alimentation'))
    const u = userEvent.setup()
    const app = monterApp('/atelier/envoyer')
    await demander(u)
    await u.click(screen.getByRole('link', { name: 'Accueil' }))
    await screen.findByRole('heading', { name: 'Atelier' })
    await u.click(screen.getByRole('link', { name: 'Envoyer' }))
    expect(await screen.findByRole('heading', { name: 'Lots à prendre' })).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: 'Abandonner cette sortie' }))
    await u.click(screen.getByRole('button', { name: 'Oui, abandonner' }))
    await waitFor(() => expect(app.adresse()).toBe('/atelier'))
    expect(sessionStorage.getItem('gestion-mp-pro:saisie:envoyer2')).toBeNull()
  })

  it('un ordre hors recette se choisit à la main, au disponible du jour dans le magasin', async () => {
    fauxServeur(reponsesAtelier('alimentation'))
    const u = userEvent.setup()
    monterApp('/atelier/envoyer')
    await screen.findByRole('heading', { name: 'Envoyer aux machines' })
    await u.click(screen.getByRole('radio', { name: 'Ordre hors recette' }))
    await u.click(screen.getByRole('button', { name: 'Choisir les fils et les lots' }))
    const ajout = await screen.findByRole('combobox', { name: 'Ajouter un fil' })
    await u.click(ajout)
    await u.type(ajout, 'L-2602{Enter}')
    expect(await screen.findByText('hors recette · pris 0,00 kg')).toBeInTheDocument()
    expect(
      screen.getAllByText('À renseigner : au moins une ligne de plus d’un gramme.').length,
    ).toBeGreaterThanOrEqual(2)
  })

  it('?ordre= : 404 → « Ordre introuvable » ; coupure → « Pas de réseau » ; validé → sa fiche', async () => {
    fauxServeur(
      reponsesAtelier('alimentation', {
        'GET /ordres/77': () => {
          throw new TypeError('Failed to fetch')
        },
      }),
    )
    const app = monterApp('/atelier/envoyer?ordre=99')
    expect(await screen.findByRole('heading', { name: 'Ordre introuvable' })).toBeInTheDocument()
    await app.routeur.navigate('/atelier/envoyer?ordre=77')
    expect(await screen.findByText('Pas de réseau')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Envoyer aux machines' })).toBeNull()
    await app.routeur.navigate('/atelier/envoyer?ordre=1')
    await waitFor(() => expect(app.adresse()).toBe('/atelier/ordres/1'))
    expect(
      await screen.findByText(
        'Cet ordre est déjà validé : il ne se modifie plus (l’annuler, puis en refaire un).',
      ),
    ).toBeInTheDocument()
  })

  it('un brouillon rouvert garde ses lignes, en bobines quand le compte tombe juste', () => {
    const o = { ...donnees().ORDRE_VALIDE, statut: 'brouillon' as const }
    const ligne = o.lignes[0]
    if (!ligne) throw new Error('fixture')
    const e = etatInitial({ ...o, lignes: [{ ...ligne, bobines: 29 }] })
    expect(e).toMatchObject({ id: 1, etape: 'lots', besoinsRelus: false })
    expect(e.prises[0]).toMatchObject({ unite: 'bobine', kg: ligne.quantite })
  })
})
