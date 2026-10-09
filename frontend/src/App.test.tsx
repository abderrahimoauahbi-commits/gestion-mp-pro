/**
 * L'application entière dans un routeur de mémoire, contre un faux serveur conforme au contrat
 * (API-PRO routes 1–22, 49–56) : session et connexion, arrivée par rôle et par appareil, garde des
 * écrans, `/lot/:id`, adresse inconnue, garde de saisie sur « Précédent ».
 */
import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import {
  contexteDe,
  fauxServeur,
  moiDe,
  monterApp,
  poste,
  prechargerPages,
  reponsesConnecte,
} from './essais/monter'
import { SESSION_PERDUE } from './lib/api'
import type { Role } from './lib/types'

beforeAll(prechargerPages)
afterEach(() => vi.unstubAllGlobals())

const NON_CONNECTE = {
  statut: 401,
  corps: { detail: 'Connectez-vous pour continuer.', code: 'non_connecte' },
}

describe('Arrivée et garde des écrans', () => {
  it.each<[Role, string]>([
    ['direction', '/cockpit'],
    ['achats', '/accueil'],
    ['alimentation', '/accueil'],
    ['administrateur', '/administration'],
  ])('« %s » arrive sur %s au bureau', async (role, arrivee) => {
    fauxServeur(reponsesConnecte(role))
    const app = monterApp('/')
    await waitFor(() => expect(app.adresse()).toBe(arrivee))
    expect(await screen.findByRole('navigation', { name: 'Menu principal' })).toBeInTheDocument()
  })

  it('l’alimentation arrive sur l’atelier au téléphone, hors coque', async () => {
    poste(true)
    fauxServeur(reponsesConnecte('alimentation'))
    const app = monterApp('/')
    await waitFor(() => expect(app.adresse()).toBe('/atelier'))
    expect(await screen.findByRole('heading', { name: 'Atelier' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Menu principal' })).toBeNull()
  })

  it('un écran réservé ramène à l’accueil avec le bandeau', async () => {
    fauxServeur(reponsesConnecte('achats'))
    const app = monterApp('/cockpit')
    await waitFor(() => expect(app.adresse()).toBe('/accueil'))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'L’écran demandé (/cockpit) est réservé à un autre rôle : vous êtes revenu à votre accueil.',
    )
  })

  it('un onglet réservé est refusé comme un écran', async () => {
    fauxServeur(reponsesConnecte('alimentation'))
    const app = monterApp('/operations?onglet=ajustement')
    await waitFor(() => expect(app.adresse()).toBe('/accueil'))
    expect(await screen.findByRole('alert')).toHaveTextContent('(/operations?onglet=ajustement) est réservé')
  })

  it('une adresse inconnue ramène à l’accueil et le dit', async () => {
    fauxServeur(reponsesConnecte('direction'))
    const app = monterApp('/nulle-part')
    await waitFor(() => expect(app.adresse()).toBe('/cockpit'))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'L’adresse demandée (/nulle-part) n’existe pas',
    )
  })

  it.each<[Role, boolean, string]>([
    ['alimentation', true, '/atelier/lots/884'],
    ['alimentation', false, '/lots/884'],
    ['achats', true, '/lots/884'],
    ['direction', true, '/lots/884'],
  ])('/lot/884 (QR) : %s, téléphone %s → %s', async (role, telephone, cible) => {
    poste(telephone)
    fauxServeur(reponsesConnecte(role))
    const app = monterApp('/lot/884')
    await waitFor(() => expect(app.adresse()).toBe(cible))
  })

  it('/guide mène au Mode d’emploi', async () => {
    fauxServeur(reponsesConnecte('achats'))
    const app = monterApp('/guide')
    await waitFor(() => expect(app.adresse()).toBe('/aide'))
    expect(await screen.findByRole('heading', { level: 1, name: 'Mode d’emploi' })).toBeInTheDocument()
  })
})

describe('Session', () => {
  it('sans session, l’adresse demandée passe par la connexion', async () => {
    fauxServeur({ ...reponsesConnecte('achats'), 'GET /contexte': NON_CONNECTE })
    const app = monterApp('/commandes?onglet=brouillon')
    await waitFor(() => expect(app.adresse()).toBe('/connexion?retour=%2Fcommandes%3Fonglet%3Dbrouillon'))
  })

  it('après la connexion, l’adresse demandée est rouverte', async () => {
    let connecte = false
    fauxServeur({
      ...reponsesConnecte('achats'),
      'GET /contexte': () => (connecte ? { corps: contexteDe('achats') } : NON_CONNECTE),
      'GET /visages': { corps: [{ id: 2, nom: 'Karim BENALI', role: 'achats', longueur_code: null }] },
      'POST /connexion': () => {
        connecte = true
        return { corps: moiDe('achats') }
      },
    })
    const app = monterApp('/commandes?onglet=brouillon')
    await userEvent.click(await screen.findByRole('button', { name: /Karim BENALI/ }))
    await userEvent.type(screen.getByLabelText('Code de Karim BENALI'), 'codeachats{Enter}')
    await waitFor(() => expect(app.adresse()).toBe('/commandes?onglet=brouillon'))
  })

  it('une session perdue en cours de travail revient à la connexion avec le motif', async () => {
    fauxServeur({
      ...reponsesConnecte('direction'),
      'GET /visages': { corps: [] },
    })
    const app = monterApp('/cockpit')
    await screen.findByRole('navigation', { name: 'Menu principal' })
    act(() => {
      window.dispatchEvent(
        new CustomEvent(SESSION_PERDUE, { detail: { motif: 'Ce compte n’est plus actif.' } }),
      )
    })
    await waitFor(() => expect(app.adresse()).toBe('/connexion?retour=%2Fcockpit'))
    expect(await screen.findByText('Ce compte n’est plus actif : voyez la direction.')).toBeInTheDocument()
  })

  it('« Se déconnecter » se confirme, ferme la session et revient à la connexion', async () => {
    const appels = fauxServeur({ ...reponsesConnecte('achats'), 'POST /deconnexion': { statut: 204 } })
    const app = monterApp('/accueil')
    await userEvent.click(await screen.findByRole('button', { name: /Mon compte : Karim BENALI/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Se déconnecter' }))
    expect(appels.some((a) => a.chemin === '/deconnexion')).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Oui, me déconnecter' }))
    await waitFor(() => expect(app.adresse()).toBe('/connexion'))
    expect(appels.some((a) => a.methode === 'POST' && a.chemin === '/deconnexion')).toBe(true)
  })
})

describe('Garde de saisie', () => {
  it('« Précédent » est retenu tant qu’une saisie n’est pas enregistrée', async () => {
    fauxServeur(reponsesConnecte('achats'))
    const app = monterApp('/aide')
    await screen.findByRole('heading', { level: 1, name: 'Mode d’emploi' })
    await act(() => app.routeur.navigate('/compte'))
    await userEvent.type(await screen.findByLabelText('Code actuel'), '12')
    await act(() => app.routeur.navigate(-1))
    const question = await screen.findByRole('alertdialog')
    expect(question).toHaveTextContent('Des modifications ne sont pas enregistrées. Les abandonner ?')
    await userEvent.click(screen.getByRole('button', { name: 'Non, continuer la saisie' }))
    expect(app.adresse()).toBe('/compte')
    await act(() => app.routeur.navigate(-1))
    await userEvent.click(await screen.findByRole('button', { name: 'Oui, abandonner' }))
    await waitFor(() => expect(app.adresse()).toBe('/aide'))
  })

  it('un lien du menu est retenu, puis suivi après « Oui, abandonner »', async () => {
    fauxServeur(reponsesConnecte('achats'))
    const app = monterApp('/compte')
    await userEvent.type(await screen.findByLabelText('Code actuel'), '12')
    await userEvent.click(screen.getByRole('link', { name: 'Mode d’emploi' }))
    expect(app.adresse()).toBe('/compte')
    await userEvent.click(await screen.findByRole('button', { name: 'Oui, abandonner' }))
    await waitFor(() => expect(app.adresse()).toBe('/aide'))
  })
})
