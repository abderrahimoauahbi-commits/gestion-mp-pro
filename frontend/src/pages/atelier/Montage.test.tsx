/**
 * Monter les fils au téléphone : métiers en service « sur les métiers » (an. 7), grille d'étages,
 * montage d'un étage avec la carte de confirmation qui annonce l'effet (texte unique (a)), l'effet
 * envoyé pour confirmation (`confirme_effet_kg`), la saisie gardée avec sa version, le conflit de
 * version qui se recharge ; signaler un besoin (saisie gardée, raison sous le bouton).
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { donnees, MONETAIRE, reponsesAtelier } from './essaiAtelier'
import { noteMetier } from './Montage'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
  sessionStorage.clear()
})
afterEach(() => vi.unstubAllGlobals())

const M1 = () => {
  const m = donnees().METIERS.find((x) => x.id === 1)
  if (!m) throw new Error('fixture')
  return m
}

describe('Monter les fils', () => {
  it('les métiers en service, « sur les métiers », puis les étages', async () => {
    fauxServeur(reponsesAtelier('alimentation'))
    const u = userEvent.setup()
    monterApp('/atelier/montage')
    expect(
      await screen.findByRole('link', { name: /M1 · Van de Wiele n° 1.*sur les métiers/ }),
    ).toBeInTheDocument()
    expect(screen.queryByText(/M3 · Ancien métier/)).toBeNull()
    expect(noteMetier({ ...M1(), densite_a_saisir: true })).toMatch(/densité à saisir \(direction\)$/)
    await u.click(screen.getByRole('link', { name: /M1 · Van de Wiele n° 1/ }))
    expect(await screen.findByRole('link', { name: /Étage 1.*1,50 \/ 4,20 m/ })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /^Étage \d\s*vide$/ })).toHaveLength(5)
  })

  it('monter un étage : effet annoncé (texte unique), confirmé au serveur', async () => {
    const m = M1()
    const appels = fauxServeur(
      reponsesAtelier('alimentation', {
        'PUT /metiers/1/etages/1': (corps) => ({
          corps: {
            metier: m,
            effet_kg: 798.5,
            avant_kg: 1197.7,
            apres_kg: 1996.2,
            alertes: [],
            message: 'Message du serveur.',
            corps,
          },
        }),
      }),
    )
    const u = userEvent.setup()
    monterApp('/atelier/montage?metier=1&etage=1')
    const metres = await screen.findByRole('textbox', { name: 'Mètres montés de POIL ROUGE 2900' })
    expect(screen.getByText('Aucune modification')).toBeInTheDocument()
    await u.clear(metres)
    await u.type(metres, '2,5')
    expect(JSON.parse(sessionStorage.getItem('gestion-mp-pro:saisie:montage:1:1') ?? '{}').version).toBe(
      m.etages_detail[0]?.version,
    )
    await u.click(screen.getByRole('button', { name: 'Enregistrer l’étage 1…' }))
    const carte = screen.getByRole('region', { name: 'Confirmation du montage' })
    expect(carte.textContent).toMatch(
      /Monter n’écrit aucun mouvement : ce fil est déjà sorti par un ordre\. Le stock sur les métiers passe de 1\s197,7 à 1\s996,16 kg \(\+798,46 kg\) ; il compte dans le stock global, sa valeur, le disponible et le projeté\./,
    )
    expect(carte.textContent).toMatch(/Attention : POIL ROUGE 2900 : 1\s996,16 kg sur les métiers/)
    await u.click(within(carte).getByRole('button', { name: 'Oui, enregistrer' }))
    expect(
      await screen.findByText(/Étage 1 enregistré : 1 fil\(s\).*Message du serveur\./),
    ).toBeInTheDocument()
    const envoi = appels.find((a) => a.methode === 'PUT')
    expect(envoi?.corps).toMatchObject({
      version: m.etages_detail[0]?.version,
      fils: [{ matiere_id: 1, metres: 2.5, pourcentage: 100, commentaire: '' }],
      confirme_effet_kg: 798.464,
    })
    expect(document.body.textContent).not.toMatch(MONETAIRE)
  })

  it('version périmée : le message dit de recharger, « Recharger l’étage » repart du serveur', async () => {
    fauxServeur(
      reponsesAtelier('alimentation', {
        'PUT /metiers/1/etages/1': {
          statut: 409,
          corps: { detail: 'L’étage 1 a été modifié entre-temps.', code: 'conflit_version' },
        },
      }),
    )
    const u = userEvent.setup()
    monterApp('/atelier/montage?metier=1&etage=1')
    await u.click(await screen.findByRole('button', { name: 'Retirer ce fil' }))
    await u.click(screen.getByRole('button', { name: 'Enregistrer l’étage 1…' }))
    expect(screen.getByText('Vider l’étage 1 ?')).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: 'Oui, vider l’étage' }))
    expect(
      await screen.findByText(/L’étage 1 a été modifié entre-temps sur un autre poste : rechargez/),
    ).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: 'Recharger l’étage' }))
    expect(
      await screen.findByRole('textbox', { name: 'Mètres montés de POIL ROUGE 2900' }),
    ).toBeInTheDocument()
  })

  it('une saisie gardée d’une version plus ancienne se signale et se recharge', async () => {
    const m = M1()
    sessionStorage.setItem(
      'gestion-mp-pro:saisie:montage:1:1',
      JSON.stringify({ version: (m.etages_detail[0]?.version ?? 2) - 1, fils: [] }),
    )
    fauxServeur(reponsesAtelier('alimentation'))
    monterApp('/atelier/montage?metier=1&etage=1')
    expect(
      await screen.findByText('L’étage a été modifié ailleurs depuis : le recharger.'),
    ).toBeInTheDocument()
  })
})

describe('Signaler un besoin', () => {
  it('raison sous le bouton, saisie gardée, envoi, mes signalements', async () => {
    const appels = fauxServeur(
      reponsesAtelier('alimentation', {
        'POST /signalements': { corps: {} },
        'GET /signalements': {
          corps: {
            elements: [
              {
                id: 1,
                quand: '2026-10-08T09:00:00+01:00',
                par_id: 3,
                par: 'Ahmed',
                matiere_id: null,
                texte: 'Plus de beige',
                urgence: 'urgente',
                traite_par: 'Karim BENALI',
                traite_le: '2026-10-08T10:00:00+01:00',
                reponse: 'Commandé.',
              },
            ],
            total: 1,
            suivant: null,
          },
        },
      }),
    )
    const u = userEvent.setup()
    monterApp('/atelier/signaler')
    expect(await screen.findByText('Écrire le besoin (2 caractères au moins)')).toBeInTheDocument()
    expect(await screen.findByText(/Réponse de Karim BENALI/)).toBeInTheDocument()
    await u.type(screen.getByRole('textbox', { name: /Quel besoin/ }), 'Il manque du rouge')
    expect(JSON.parse(sessionStorage.getItem('gestion-mp-pro:saisie:signaler') ?? '{}').texte).toBe(
      'Il manque du rouge',
    )
    await u.click(screen.getByRole('radio', { name: 'Urgent' }))
    await u.click(screen.getByRole('button', { name: 'Signaler aux achats' }))
    await waitFor(() =>
      expect(appels.find((a) => a.methode === 'POST')?.corps).toEqual({
        matiere_id: null,
        texte: 'Il manque du rouge',
        urgence: 'urgente',
      }),
    )
    expect(appels.some((a) => a.chemin === '/signalements?mes=true')).toBe(true)
  })
})
