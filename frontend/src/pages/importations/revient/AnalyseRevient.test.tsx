/** Analyse › Coût de revient : l'état dans l'adresse, les paramètres du serveur, les liens, les vues. */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fauxServeur,
  monterApp,
  prechargerPages,
  reponsesConnecte,
  stockageMemoire,
  type Appel,
  type Reponse,
} from '../../../essais/monter'
import {
  analyseEssai,
  CLASSIFICATION,
  coutQualiteEssai,
  ligneEssai,
  MATIERES,
  qualiteEssai,
} from './donneesEssai'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

function serveur(autres: Record<string, Reponse> = {}) {
  return fauxServeur({
    ...reponsesConnecte('achats'),
    'GET /matieres': { corps: MATIERES },
    'GET /classification': { corps: CLASSIFICATION },
    'GET /qualites': { corps: [qualiteEssai()] },
    'GET /analyse/revient': (_c, url) => ({
      corps:
        url.searchParams.get('detail') === 'true'
          ? analyseEssai({ axe: 'reference', libelle_axe: 'Référence', detail_lignes: [ligneEssai()] })
          : analyseEssai(),
    }),
    'GET /analyse/revient/qualites/3': { corps: coutQualiteEssai() },
    ...autres,
  })
}

/** Les paramètres de chaque appel à une route. */
const appelsA = (appels: Appel[], chemin: string) =>
  appels
    .filter((a) => a.methode === 'GET' && a.chemin.split('?')[0] === chemin)
    .map((a) => new URL(a.chemin, 'http://localhost').searchParams)

const dernier = (appels: Appel[], chemin = '/analyse/revient') => appelsA(appels, chemin).at(-1)
const parametre = (adresse: string, cle: string) => new URL(adresse, 'http://localhost').searchParams.get(cle)

describe('Coût de revient : l’état vient de l’adresse', () => {
  it('lit vue, axe, statut, période, qualité, matières, combinaisons et recherche, et les envoie', async () => {
    const appels = serveur()
    const combinaisons = encodeURIComponent('[{"composition":"PES","titrage":"1500"}]')
    monterApp(
      `/analyse?onglet=revient&axe=couleur&statut=clos&du=2026-01-01&au=2026-06-30&qualite=3&matieres=2,5&combinaisons=${combinaisons}&couleur=NOIR&q=bursa`,
    )
    expect(await screen.findByText('Ce que la matière importée a coûté, rendue usine')).toBeInTheDocument()
    await waitFor(() => expect(dernier(appels)).toBeDefined())
    const p = dernier(appels)
    expect(p?.get('axe')).toBe('couleur')
    expect(p?.get('statut')).toBe('clos')
    expect(p?.get('du')).toBe('2026-01-01')
    expect(p?.get('au')).toBe('2026-06-30')
    expect(p?.get('qualite')).toBe('3')
    expect(p?.getAll('matieres')).toEqual(['2', '5'])
    expect(p?.get('q')).toBe('bursa')
    expect(p?.get('couleur')).toBeNull()
    expect(JSON.parse(p?.get('selection') ?? '')).toEqual([
      { composition: 'PES', titrage: '1500' },
      { couleur: 'NOIR' },
    ])
    expect(screen.getByRole('radio', { name: 'Dossiers clos' })).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByRole('searchbox', { name: 'Rechercher' })).toHaveValue('bursa')
    expect(screen.getByText('PES · 1500')).toBeInTheDocument()
    expect(screen.getByText('+ en cours : NOIR')).toBeInTheDocument()
    expect(await screen.findByText('IMP PP NOIR-1800')).toBeInTheDocument()
    expect(await screen.findByRole('combobox', { name: 'Regrouper par' })).toHaveValue('Par couleur')
    const exporter = screen.getByRole('link', { name: /Exporter en Excel/ })
    expect(exporter.getAttribute('href')).toMatch(/^\/api\/export\/revient\?/)
    expect(parametre(exporter.getAttribute('href') ?? '', 'selection')).toBe(p?.get('selection'))
  })

  it('la vue qualité appelle la route 207 avec du et au, pas l’analyse', async () => {
    const appels = serveur()
    monterApp('/analyse?onglet=revient&vue=qualite&qualite=3&du=2026-01-01&au=2026-03-31')
    expect(await screen.findByText('Coût matière de la qualité')).toBeInTheDocument()
    const p = dernier(appels, '/analyse/revient/qualites/3')
    expect(p?.get('du')).toBe('2026-01-01')
    expect(p?.get('au')).toBe('2026-03-31')
    expect(appelsA(appels, '/analyse/revient')).toHaveLength(0)
    expect(screen.getByText('Coût matière / m²')).toBeInTheDocument()
    expect(screen.getByText('Rôle Trame')).toBeInTheDocument()
    expect(screen.getByText('aucun fil importé : rôle hors du coût calculé')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Exporter en Excel/ })).not.toBeInTheDocument()
  })

  it('sans qualité, la vue qualité dit quoi faire et ne lit rien', async () => {
    const appels = serveur()
    monterApp('/analyse?onglet=revient&vue=qualite')
    expect(await screen.findByText(/Choisir une qualité : on croise sa recette/)).toBeInTheDocument()
    expect(appels.some((a) => a.chemin.startsWith('/analyse/revient'))).toBe(false)
  })
})

describe('Coût de revient : les gestes écrivent l’adresse', () => {
  it('bascule de vue : « Lot par lot » écrit vue=lots et demande le détail par référence', async () => {
    const appels = serveur()
    const app = monterApp('/analyse?onglet=revient')
    await userEvent.click(await screen.findByRole('button', { name: 'Lot par lot' }))
    await waitFor(() => expect(parametre(app.adresse(), 'vue')).toBe('lots'))
    expect(parametre(app.adresse(), 'onglet')).toBe('revient')
    await waitFor(() => expect(dernier(appels)?.get('detail')).toBe('true'))
    expect(dernier(appels)?.get('axe')).toBe('reference')
    expect(await screen.findByText('L-BUR-18')).toBeInTheDocument()
  })

  it('les listes liées posent un critère ; « + Combinaison » le retient et envoie `selection`', async () => {
    const appels = serveur()
    const app = monterApp('/analyse?onglet=revient')
    const combinaison = await screen.findByRole('button', { name: '+ Combinaison' })
    expect(combinaison).toHaveAttribute('data-raison', 'À renseigner : Choisissez au moins un critère.')
    const composition = await screen.findByRole('combobox', { name: 'Composition' })
    await waitFor(() =>
      expect(within(composition).getByRole('option', { name: 'PES (2)' })).toBeInTheDocument(),
    )
    await userEvent.selectOptions(composition, 'PES')
    await waitFor(() => expect(parametre(app.adresse(), 'composition')).toBe('PES'))
    const couleurs = within(screen.getByRole('combobox', { name: 'Couleur' })).getAllByRole('option')
    expect(couleurs.map((o) => o.textContent)).toEqual(['Toutes couleurs', 'BLEU (1)', 'ROUGE (1)'])
    await waitFor(() => expect(combinaison).not.toHaveAttribute('data-raison'))
    await userEvent.click(combinaison)
    await waitFor(() => expect(parametre(app.adresse(), 'combinaisons')).toBe('[{"composition":"PES"}]'))
    expect(parametre(app.adresse(), 'composition')).toBeNull()
    await waitFor(() => expect(dernier(appels)?.get('selection')).toBe('[{"composition":"PES"}]'))
    expect(screen.getByRole('button', { name: 'Retirer cette combinaison : PES' })).toBeInTheDocument()
  })

  it('« Effacer les filtres » dès deux critères, avec leur nombre, et garde la vue', async () => {
    serveur()
    const app = monterApp('/analyse?onglet=revient&vue=lots&statut=clos&composition=PES&matieres=2')
    expect(await screen.findByText('3 critères')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Effacer les filtres' }))
    await waitFor(() => expect(app.adresse()).toBe('/analyse?onglet=revient&vue=lots'))
    expect(screen.queryByRole('button', { name: 'Effacer les filtres' })).not.toBeInTheDocument()
  })

  it('ajoute et retire une matière (puces)', async () => {
    serveur()
    const app = monterApp('/analyse?onglet=revient')
    const choix = await screen.findByRole('combobox', { name: 'Ajouter une matière' })
    await userEvent.click(choix)
    await userEvent.type(choix, 'noir')
    await userEvent.keyboard('{Enter}')
    await waitFor(() => expect(parametre(app.adresse(), 'matieres')).toBe('5'))
    await userEvent.click(
      await screen.findByRole('button', { name: 'Retirer cette matière : IMP PP NOIR-1800' }),
    )
    await waitFor(() => expect(parametre(app.adresse(), 'matieres')).toBeNull())
  })

  it('la recherche s’écrit tout de suite dans l’adresse et part au serveur après la frappe', async () => {
    const appels = serveur()
    const app = monterApp('/analyse?onglet=revient')
    await userEvent.type(await screen.findByRole('searchbox', { name: 'Rechercher' }), 'rouge')
    await waitFor(() => expect(parametre(app.adresse(), 'q')).toBe('rouge'))
    await waitFor(() => expect(dernier(appels)?.get('q')).toBe('rouge'))
    expect(
      appelsA(appels, '/analyse/revient').filter((p) => p.get('q')?.startsWith('r')).length,
    ).toBeLessThan(5)
  })

  it('un clic sur une ligne (axe titrage) pose le titrage et passe l’axe à la référence', async () => {
    const appels = serveur()
    const app = monterApp('/analyse?onglet=revient')
    await userEvent.click(await screen.findByText('1800 den'))
    await waitFor(() => expect(parametre(app.adresse(), 'titrage')).toBe('1800'))
    expect(parametre(app.adresse(), 'axe')).toBe('reference')
    await waitFor(() => expect(dernier(appels)?.get('titrage')).toBe('1800'))
  })
})

describe('Coût de revient : les dossiers', () => {
  it('« + N non répartis » liste chaque dossier en lien, à part du coût', async () => {
    serveur({
      'GET /analyse/revient': {
        corps: analyseEssai({
          frais_non_repartis_mad: 1500,
          dossiers_non_repartis: [
            { dossier: '02/26', montant: 1200 },
            { dossier: '03/26', montant: 300 },
          ],
        }),
      },
    })
    monterApp('/analyse?onglet=revient')
    const resume = await screen.findByText(/non répartis/, { selector: 'summary' })
    expect(resume.textContent).toMatch(/^\+ 1.500.MAD non répartis$/)
    await userEvent.click(resume)
    const liste = screen.getByRole('list', { name: 'Dossiers aux frais non répartis' })
    const liens = within(liste).getAllByRole('link')
    expect(liens.map((l) => [l.textContent, l.getAttribute('href')])).toEqual([
      ['02/26', '/dossiers/12'],
      ['03/26', '/dossiers/13'],
    ])
    // Jamais additionnés au coût : le coût hors TVA reste celui du serveur.
    const kpis = screen.getByRole('region', { name: 'Indicateurs du coût de revient' })
    expect(within(kpis).getAllByText(/^61.572.MAD$/).length).toBeGreaterThan(0)
    expect(screen.queryByText(/63.072/)).not.toBeInTheDocument()
  })

  it('le n° d’un dossier mène à sa fiche en emportant l’adresse de l’analyse', async () => {
    serveur()
    const adresse = '/analyse?onglet=revient&statut=clos'
    const app = monterApp(adresse)
    const lien = await screen.findByRole('link', { name: '03/26' })
    expect(lien).toHaveAttribute('href', '/dossiers/13')
    await userEvent.click(lien)
    await waitFor(() => expect(app.adresse()).toBe('/dossiers/13'))
    expect(app.routeur.state.location.state).toEqual({ retour: adresse })
  })

  it('en vue « Lot par lot », le dossier est un lien et un dossier ouvert le dit', async () => {
    serveur()
    monterApp('/analyse?onglet=revient&vue=lots')
    const ligne = (await screen.findByText('L-BUR-18')).closest('tr')
    expect(ligne).not.toBeNull()
    const lien = within(ligne as HTMLElement).getByRole('link', { name: '01/26' })
    expect(lien).toHaveAttribute('href', '/dossiers/11')
    expect(within(ligne as HTMLElement).getByText('Ouvert')).toBeInTheDocument()
    expect(within(ligne as HTMLElement).getByRole('link', { name: 'IMP PES ROUGE-1500' })).toHaveAttribute(
      'href',
      '/matieres/2',
    )
  })
})
