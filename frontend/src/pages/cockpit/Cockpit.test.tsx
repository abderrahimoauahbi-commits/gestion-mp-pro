/**
 * Le Cockpit dans l'application entière, sur des réponses relevées au vrai serveur : les six
 * indicateurs sont les valeurs reçues (jamais recalculées), chacun avec sa formule et son lien ;
 * « Ce qui attend une action » dans l'ordre de Gestion MP, son compte à l'onglet ; les matières en
 * alerte toutes listées ; le bilan du mois du mois précédent dans un nouvel onglet.
 */
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { jours, montant, montantCourt, part } from '../../lib/format'
import type { Cockpit, CommandeResume, EtatSauvegardes } from '../accueil/types'
import { DONNEES, servirJournee } from '../accueil/essaisServeur'
import { actionsCockpit, tacheSauvegarde, totalAFaire } from './aFaire'
import { moisProposes } from './BilanDuMois'
import { valeurKpi } from './IndicateursCockpit'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const cockpit: Cockpit = DONNEES.cockpit

describe('Cockpit — indicateurs', () => {
  it('affiche les valeurs reçues, sans les recalculer, avec la formule et le lien du serveur', async () => {
    // Une valeur reçue qui ne tombe pas sur le stock détaillé : l'écran la dit telle quelle.
    const kpi = cockpit.kpi.map((k) =>
      k.cle === 'valeur' ? { ...k, valeur: 123456, formule: 'Formule du serveur' } : k,
    )
    servirJournee('direction', { 'GET /cockpit': { corps: { ...cockpit, kpi } } })
    monterApp('/cockpit')
    const zone = await screen.findByRole('region', { name: 'Indicateurs du Cockpit' })
    const valeur = within(zone).getByRole('link', { name: /Valeur du stock/ })
    expect(valeur).toHaveTextContent('123 456 MAD')
    expect(valeur).not.toHaveTextContent(String(Math.round(cockpit.stock.valeur_mad)))
    expect(valeur).toHaveAttribute('href', '/analyse?onglet=valorisation')
    expect(within(zone).getAllByRole('link')).toHaveLength(6)
    await userEvent.click(within(valeur).getByRole('button', { name: /formule/i }))
    expect(await screen.findByText(/Formule du serveur\. Sur les métiers/)).toBeInTheDocument()
    const controles = cockpit.kpi.find((k) => k.cle === 'controles')!
    expect(within(zone).getByRole('link', { name: /Contrôles/ })).toHaveTextContent(controles.detail)
  })

  it('met chaque unité en forme sans toucher au chiffre', () => {
    const k = cockpit.kpi[0]!
    expect(valeurKpi({ ...k, unite: 'MAD', valeur: 2_450_000 })).toEqual({
      valeur: montantCourt(2_450_000, 'MAD'),
      exact: montant(2_450_000, 'MAD'),
    })
    expect(montantCourt(2_450_000, 'MAD')).toMatch(/^2,5.M.MAD$/)
    expect(valeurKpi({ ...k, unite: 'fraction', valeur: 0.852 }).valeur).toBe(part(0.852, 0))
    expect(valeurKpi({ ...k, unite: 'j', valeur: 50.7 }).valeur).toBe(jours(50.7))
    expect(valeurKpi({ ...k, unite: 'bons', valeur: 2 })).toEqual({ valeur: '2', unite: 'bons' })
  })
})

describe('Cockpit — À faire et à valider', () => {
  it('ce qui attend une action, dans l’ordre de Gestion MP, et son compte sur l’onglet', async () => {
    servirJournee('direction')
    monterApp('/cockpit')
    const liste = await screen.findByRole('list', { name: 'Ce qui attend une action' })
    const cles = within(liste)
      .getAllByRole('listitem')
      .map((li) => li.getAttribute('data-tache'))
    expect(cles).toEqual([
      'rouges',
      'approuver',
      'retards',
      'prix',
      'receptions',
      'ordres',
      'operations',
      'inventaires',
      'besoins',
      'reclamations',
      'controles',
      'sauvegarde',
    ])
    expect(screen.getByRole('tab', { name: /À faire et à valider/ })).toHaveTextContent('18')
    expect(within(liste).getByRole('link', { name: 'Traiter' })).toHaveAttribute(
      'href',
      '/cockpit?signalement=1',
    )
    expect(screen.getByText(/3 en rupture ou critiques/)).toBeInTheDocument()
    const examiner = screen.getByRole('table', { name: 'Commandes à approuver' })
    expect(within(examiner).getByText('LOMAT')).toBeInTheDocument()
  })

  it('le compte est la somme des comptes affichés, plus une sauvegarde en défaut', () => {
    const commandes: CommandeResume[] = DONNEES.commandes
    const actions = actionsCockpit({
      role: 'direction',
      cockpit,
      commandes,
      retards: DONNEES.retards,
      inventaires: [],
      besoins: [],
      reclamations: [],
    })
    expect(actions.map((a) => a.cle)).toEqual(['rouges', 'approuver', 'retards', 'prix', 'controles'])
    const somme = cockpit.alerte_rouge + 1 + 1 + 1 + cockpit.controles.a_corriger
    expect(totalAFaire(actions, false)).toBe(somme)
    expect(totalAFaire(actions, true)).toBe(somme + 1)
  })

  it('sauvegarde : à jour sous 26 h, à vérifier au-delà ou sans sauvegarde, illisible en erreur', () => {
    const etat: EtatSauvegardes = {
      base: 'b',
      derniere: '2026-10-08T03:00:00Z',
      age_h: 7,
      alerte: null,
      politique: '',
      dossier: '',
      copie: null,
      nb: 3,
      autres: 0,
      outils: true,
      fichiers: [],
    }
    expect(tacheSauvegarde('direction', etat, null)?.tache.titre).toBe('Sauvegarde à jour')
    expect(tacheSauvegarde('direction', { ...etat, age_h: 30 }, null)?.enAlerte).toBe(true)
    expect(tacheSauvegarde('direction', { ...etat, derniere: null, age_h: null }, null)?.tache.detail).toBe(
      'Aucune sauvegarde n’a encore été faite.'.replace('’', "'"),
    )
    expect(tacheSauvegarde('direction', undefined, new Error('x'))?.tache.titre).toBe(
      'Sauvegardes : état illisible',
    )
  })
})

describe('Cockpit — onglets', () => {
  it('Matières en alerte : toutes, la plus pressée d’abord, ligne → fiche, « Préparer la commande »', async () => {
    servirJournee('direction')
    monterApp('/cockpit?onglet=alertes')
    const table = await screen.findByRole('table', { name: 'Matières en alerte' })
    const lignes = within(table).getAllByRole('row').slice(1)
    expect(lignes).toHaveLength(cockpit.nb_alertes)
    expect(lignes[0]).toHaveTextContent('COTON CHAINE 12/6')
    expect(within(lignes[0]!).getByRole('link', { name: 'Préparer la commande' })).toHaveAttribute(
      'href',
      '/plan-achat/preparer/3',
    )
  })

  it('Évolution : une photo par jour, les vues dans l’adresse', async () => {
    servirJournee('direction')
    const app = monterApp('/cockpit?onglet=evolution')
    await screen.findByRole('table', { name: 'Les photos des indicateurs' })
    await userEvent.click(screen.getByRole('button', { name: 'Alertes' }))
    expect(app.adresse()).toBe('/cockpit?onglet=evolution&vue=alertes')
  })

  it('Bilan du mois : le mois précédent, ouvert dans un nouvel onglet', async () => {
    servirJournee('direction')
    monterApp('/cockpit')
    const bilan = await screen.findByRole('link', { name: /Bilan du mois/ })
    expect(bilan).toHaveAttribute('href', '/api/documents/bilan?mois=2026-09')
    expect(bilan).toHaveAttribute('target', '_blank')
    expect(moisProposes('2026-01', 3)).toEqual(['2026-01', '2025-12', '2025-11'])
  })
})
