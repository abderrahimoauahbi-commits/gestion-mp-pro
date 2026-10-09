/** Le Mode d'emploi : sept onglets dans l'adresse, liens filtrés par rôle, contenu tiré d'aide.json. */
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterApp, prechargerPages, reponsesConnecte } from '../../essais/monter'
import { versProcedure } from './Volets'
import { MODE_EMPLOI } from '../../lib/aide'

beforeAll(prechargerPages)
afterEach(() => vi.unstubAllGlobals())

describe('Mode d’emploi', () => {
  it('sept onglets ; l’onglet est dans l’adresse', async () => {
    fauxServeur(reponsesConnecte('direction'))
    const app = monterApp('/aide')
    const onglets = await screen.findAllByRole('tab')
    expect(onglets.map((o) => o.textContent)).toEqual([
      'Les règles',
      'Qui fait quoi',
      'Pas à pas',
      'Les calculs',
      'L’analyse',
      'Écrans de l’ERP Fil',
      'Le téléphone',
    ])
    expect(screen.getByText('Les mouvements de stock sont la seule écriture de stock.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: /Les calculs/ }))
    expect(app.adresse()).toBe('/aide?onglet=calculs')
    expect(screen.getAllByRole('row')).toHaveLength(22)
  })

  it('l’alimentation : l’analyse réservée, sans lien ; le Cockpit sans lien dans « Qui fait quoi »', async () => {
    fauxServeur(reponsesConnecte('alimentation'))
    monterApp('/aide?onglet=analyse')
    expect(
      await screen.findByText('L’analyse est réservée aux achats et à la direction.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Valorisation' })).toBeNull()
    await userEvent.click(screen.getByRole('tab', { name: /Qui fait quoi/ }))
    const carte = screen.getByRole('heading', { name: /^Direction/ }).closest('section')
    expect(carte && within(carte).queryByRole('link', { name: 'Cockpit' })).toBeNull()
    expect(carte && within(carte).getAllByText(/réservé : Direction/).length).toBeGreaterThan(0)
  })

  it('le point hebdomadaire mène au Cockpit pour la direction, à Ma journée pour les achats, nulle part pour l’alimentation', () => {
    const point = MODE_EMPLOI.pas.procedures.find((p) => p.titre === 'Le point hebdomadaire')
    expect(point && versProcedure(point, 'direction')).toBe('/cockpit')
    expect(point && versProcedure(point, 'achats')).toBe('/accueil')
    expect(point && versProcedure(point, 'alimentation')).toBeNull()
  })
})
