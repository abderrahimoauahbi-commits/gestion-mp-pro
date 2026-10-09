/**
 * Le plan d'achat et la préparation dans l'application entière : indicateurs lus au serveur,
 * deux onglets, « Préparer » ouvre la préparation à adresse stable ; préparation en kilos **et**
 * en palettes ; « Créer » envoie kilos, unité et contenance, puis ouvre le bon ; l'alimentation
 * n'a pas accès à l'écran.
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
} from '../../essais/monter'
import { ficheEssai } from '../commandes/donneesEssai'
import { planEssai, preparationEssai } from './donneesEssai'
import { apresCreation } from './apresCreation'
import { libelleCreer } from './PiedPreparation'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const DEVISES = {
  corps: [
    { code: 'USD', nom: 'Dollar', cours: 10, cours_le: null, cours_repris: false, actif: true, version: 1 },
  ],
}

function serveur(role: 'direction' | 'achats' = 'achats') {
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /plan-achat': { corps: planEssai() },
    'GET /plan-achat/fournisseurs/2': { corps: preparationEssai() },
    'GET /devises': DEVISES,
    'GET /matieres': { corps: [] },
    'POST /commandes': { statut: 201, corps: [ficheEssai({ id: 41, numero: null, statut: 'brouillon' })] },
    'GET /commandes': { corps: [] },
    'GET /commandes/41': { corps: ficheEssai({ id: 41, numero: null, statut: 'brouillon' }) },
  })
}

describe('Plan d’achat', () => {
  it('les indicateurs du serveur, avec leur périmètre ; les deux onglets et leur compte', async () => {
    serveur()
    monterApp('/plan-achat')
    const tableau = await screen.findByRole('table', { name: 'Fournisseurs à solliciter' })
    expect(screen.getAllByText(/sur toutes les matières/).length).toBeGreaterThan(0)
    expect(screen.getByRole('tab', { name: /Par fournisseur/ })).toHaveTextContent('Par fournisseur2')
    expect(within(tableau).getByText('Polyfil Industries')).toBeInTheDocument()
    expect(within(tableau).queryByText(/🚨|📋|📝/)).toBeNull()
  })

  it('« Préparer » ouvre la préparation à son adresse ; kilos et palettes liés ; créer ouvre le bon', async () => {
    const appels = serveur()
    const { adresse } = monterApp('/plan-achat')
    const tableau = await screen.findByRole('table', { name: 'Fournisseurs à solliciter' })
    const ligne = within(tableau).getByText('Polyfil Industries').closest('tr')
    if (!ligne) throw new Error('ligne absente')
    await userEvent.click(within(ligne).getByRole('button', { name: 'Préparer' }))
    await waitFor(() => expect(adresse()).toBe('/plan-achat/preparer/2'))
    const fenetre = await screen.findByRole('dialog', { name: /Préparer une commande — Polyfil Industries/ })
    const unites = within(fenetre).getAllByRole('textbox', { name: /Quantité de .* en Palette/ })[0]
    if (!unites) throw new Error('quantité absente')
    fireEvent.focus(unites)
    fireEvent.change(unites, { target: { value: '10' } })
    fireEvent.blur(unites)
    expect(within(fenetre).getByRole('textbox', { name: 'Kilos de PES TWS 1800 Noir 9005' })).toHaveValue(
      '2 560',
    )
    await userEvent.click(within(fenetre).getByRole('button', { name: /Créer le bon en brouillon/ }))
    await waitFor(() => expect(adresse()).toBe('/commandes/41'))
    const corps = appels.find((a) => a.methode === 'POST' && a.chemin === '/commandes')?.corps
    expect(corps).toMatchObject({ fournisseur_id: 2, prix_catalogue_a_confirmer: false })
    expect(corps).toMatchObject({ lignes: [{ quantite: 2560, unite_achat: 'Palette', contenance: 256 }] })
  })

  it('rien de coché : « Créer » est grisé et dit pourquoi', async () => {
    serveur()
    monterApp('/plan-achat/preparer/2')
    const fenetre = await screen.findByRole('dialog', { name: /Préparer une commande — Polyfil/ })
    for (const c of await within(fenetre).findAllByRole('checkbox')) await userEvent.click(c)
    const creer = within(fenetre).getByRole('button', { name: /Créer le bon/ })
    expect(creer).toBeDisabled()
    expect(creer.dataset.raison).toContain('cochez au moins une ligne')
  })

  it('libellés de création : un bon, ou un par devise ; message et adresse après création', () => {
    expect(libelleCreer(['USD'], 1234)).toBe('Créer le bon en brouillon · 1 234,0 kg')
    expect(libelleCreer(['EUR', 'USD'], 10)).toMatch(/^Créer 2 bons \(un par devise : EUR, USD\)/)
    expect(apresCreation([ficheEssai({ id: 7 })]).adresse).toBe('/commandes/7')
    expect(apresCreation([ficheEssai({ id: 7 }), ficheEssai({ id: 8, devise: 'EUR' })]).adresse).toBe(
      '/commandes?onglet=brouillon',
    )
  })

  it('l’alimentation n’a pas accès au plan d’achat', async () => {
    serveur()
    fauxServeur({ ...reponsesConnecte('alimentation'), 'GET /plan-achat': { corps: planEssai() } })
    const { adresse } = monterApp('/plan-achat')
    await waitFor(() => expect(adresse()).not.toBe('/plan-achat'))
  })
})
