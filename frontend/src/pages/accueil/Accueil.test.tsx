/**
 * Ma journée dans l'application entière, sur des réponses relevées au vrai serveur : l'ordre des
 * tâches et leurs liens (document seul, liste filtrée sinon), les indicateurs reçus, la fenêtre
 * « Besoin signalé » à adresse stable (réponse envoyée, saisie gardée), l'alimentation au bureau
 * sans aucun prix ni conseil d'achat.
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { DONNEES, servirJournee } from './essaisServeur'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const taches = (nom: string) =>
  [...within(screen.getByRole('list', { name: nom })).getAllByRole('listitem')].map(
    (li) => li.getAttribute('data-tache') ?? '',
  )

describe('Ma journée — achats', () => {
  it('« À faire » dans l’ordre exact, chaque tâche vers son document ou sa liste filtrée', async () => {
    servirJournee('achats')
    monterApp('/accueil')
    await screen.findByText(/1 commande\(s\) en retard/)
    expect(taches('À faire')).toEqual([
      'besoin-1',
      'besoin-2',
      'alerte',
      'retards',
      'prix',
      'brouillons',
      'factures',
      'sans-facture',
      'inventaire-1',
      'reclamations',
      'controles',
    ])
    const lien = (texte: RegExp) => screen.getByRole('link', { name: texte }).getAttribute('href')
    expect(lien(/commande\(s\) en retard/)).toBe('/commandes/3')
    expect(lien(/^3 en rupture ou critiques$/)).toBe('/plan-achat')
    expect(lien(/Inventaire INV-2026-0001 en cours/)).toBe('/inventaires/1')
    expect(lien(/facture\(s\) reçue\(s\) sans dossier/)).toBe('/importations?onglet=rattacher')
    expect(lien(/2 réception\(s\) en brouillon/)).toBe('/receptions?onglet=brouillon')
    expect(lien(/1 ordre\(s\) de fabrication en brouillon/)).toBe('/ordres/4')
    expect(lien(/BC-2026-0002 · Cuirs du Sud/)).toBe('/commandes/4')
    expect(screen.getByRole('link', { name: 'Tout valider…' })).toHaveAttribute(
      'href',
      '/stock?onglet=a-valider',
    )
  })

  it('les indicateurs disent les chiffres reçus du serveur', async () => {
    servirJournee('achats', {
      'GET /cockpit': {
        corps: {
          ...DONNEES.cockpit,
          alerte_rouge: 41,
          controles: { ...DONNEES.cockpit.controles, a_corriger: 17 },
        },
      },
    })
    monterApp('/accueil')
    const indicateurs = await screen.findByRole('region', { name: 'Indicateurs de la journée' })
    await within(indicateurs).findByText('41')
    expect(within(indicateurs).getByText('17')).toBeInTheDocument()
    expect(within(indicateurs).getByRole('link', { name: /Commandes en retard/ })).toHaveAttribute(
      'href',
      '/commandes?filtre=retard',
    )
    expect(screen.getByText('41 en rupture ou critiques')).toBeInTheDocument()
  })

  it('« Traiter » ouvre la fenêtre à adresse stable ; « Marquer traité » envoie la réponse', async () => {
    const appels = servirJournee('achats', {
      'POST /signalements/1/traiter': { corps: { ...DONNEES.signalements.elements[1], traite: true } },
    })
    const app = monterApp('/accueil')
    const traiter = await screen.findAllByRole('link', { name: 'Traiter' })
    await userEvent.click(traiter[0]!)
    expect(app.adresse()).toBe('/accueil?signalement=1')
    const fenetre = await screen.findByRole('dialog', { name: /Besoin signalé par Alimentation/ })
    await userEvent.type(
      within(fenetre).getByRole('textbox', { name: /Réponse à l’atelier/ }),
      'Commandé hier',
    )
    // Une réponse tapée ne se perd pas sans la question.
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Annuler' }))
    expect(await screen.findByText(/Les abandonner \?/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Non, continuer la saisie' }))
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Marquer traité' }))
    await waitFor(() => expect(app.adresse()).toBe('/accueil'))
    expect(appels.find((a) => a.methode === 'POST')).toEqual({
      methode: 'POST',
      chemin: '/signalements/1/traiter',
      corps: { reponse: 'Commandé hier' },
    })
  })
})

describe('Ma journée — alimentation au bureau', () => {
  it('les gestes du jour et ses brouillons, sans prix, montant ni conseil d’achat', async () => {
    const appels = servirJournee('alimentation')
    monterApp('/accueil')
    await screen.findByRole('link', { name: /1 ordre\(s\) de fabrication en brouillon/ })
    expect(screen.getByRole('link', { name: /Envoyer aux machines/ })).toHaveAttribute(
      'href',
      '/ordres/nouveau',
    )
    expect(screen.getByRole('link', { name: /Déplacer un lot/ })).toHaveAttribute(
      'href',
      '/operations/nouvelle?type=transfert',
    )
    expect(taches('À valider')).toEqual(['valider-ordre', 'valider-operation'])
    const texte = document.querySelector('main')?.textContent ?? ''
    expect(texte).not.toMatch(/\b(MAD|EUR|USD)\b|prix|montant|commander|plan d’achat/i)
    // Aucune lecture de pilotage ni d'achat.
    expect(appels.map((a) => a.chemin.split('?')[0])).not.toContain('/cockpit')
    expect(appels.map((a) => a.chemin.split('?')[0])).not.toContain('/commandes')
  })
})
