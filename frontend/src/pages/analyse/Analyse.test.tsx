/**
 * La page Analyse dans l'application entière, sur des réponses relevées au vrai serveur (base
 * d'essai du lot F8) : onglet par défaut selon le rôle et ancienne adresse, compteurs des onglets
 * (`a_corriger` pour les contrôles, H-07), détail d'un contrôle à adresse stable et écart en
 * fraction formaté une seule fois (P8-3), huit matières au plus sur une courbe (P8-6), filtres de
 * l'échéancier envoyés au serveur (P8-21), mois du bilan.
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fauxServeur,
  monterApp,
  prechargerPages,
  reponsesConnecte,
  stockageMemoire,
} from '../../essais/monter'
import type { Role } from '../../lib/types'
import { moisPrecedent, raisonMois } from './BilanDuMois'
import { celluleLisible } from './controles/cellules'
import { trierControles } from './controles/Controles'
import consommation from './essais/consommation.json'
import controleC30 from './essais/controle_C30.json'
import controles from './essais/controles.json'
import echeancier from './essais/echeancier.json'
import historique from './essais/historique.json'
import matrice from './essais/matrice.json'
import opportunites from './essais/opportunites.json'
import performance from './essais/performance.json'
import soldes from './essais/soldes.json'
import valorisation from './essais/valorisation.json'
import { cases } from './prix/Matrice'
import { mouvement } from './prix/commun'
import { finsDeMois } from './Valorisation'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

function servir(role: Role) {
  return fauxServeur(
    reponsesConnecte(role, {
      'GET /valorisation': { corps: valorisation },
      'GET /controles': { corps: controles },
      'GET /controles/soldes': { corps: soldes },
      'GET /controles/C30': { corps: controleC30 },
      'GET /prix/matrice': { corps: matrice },
      'GET /prix/historique': { corps: historique },
      'GET /opportunites': { corps: opportunites },
      'GET /fournisseurs/performance': { corps: performance },
      'GET /echeancier': { corps: echeancier },
      'GET /ordres/consommation': { corps: consommation },
    }),
  )
}

describe('Analyse', () => {
  it('direction : la Valorisation par défaut, ses indicateurs et les compteurs des onglets', async () => {
    servir('direction')
    monterApp('/analyse')
    expect(await screen.findByRole('table', { name: 'Valorisation par matière' })).toBeInTheDocument()
    expect(screen.getByText('Valeur du stock détenu')).toBeInTheDocument()
    const controlesOnglet = screen.getByRole('tab', { name: /Contrôles/ })
    expect(controlesOnglet).toHaveTextContent(String(controles.synthese.a_corriger))
    expect(screen.getByRole('tab', { name: /Matrice/ })).toHaveTextContent(String(matrice.lignes.length))
  })

  it('achats : la Matrice par défaut ; ?onglet=prix (Gestion MP) mène à la Matrice', async () => {
    servir('achats')
    const { adresse } = monterApp('/analyse?onglet=prix')
    expect(await screen.findByRole('table', { name: 'Matrice des prix' })).toBeInTheDocument()
    await waitFor(() => expect(adresse()).toBe('/analyse?onglet=matrice'))
  })

  it('un contrôle non conforme s’ouvre à son adresse ; l’écart (fraction) se lit en %', async () => {
    servir('direction')
    const { adresse } = monterApp('/analyse?onglet=controles')
    const tableau = await screen.findByRole('table', { name: 'Contrôles de cohérence' })
    await userEvent.click(within(tableau).getByText('C30'))
    await waitFor(() => expect(adresse()).toBe('/analyse?onglet=controles&controle=C30'))
    const fenetre = await screen.findByRole('dialog')
    const ligne = controleC30.elements[0] as { ecart: number }
    const attendu = celluleLisible(ligne.ecart, '%').replace(/\s/g, ' ')
    await waitFor(() => expect(fenetre.textContent?.replace(/\s/g, ' ')).toContain(attendu))
    expect(celluleLisible(-0.1238, '%').replace(/\s/g, ' ')).toBe('−12,4 %')
  })

  it('huit matières au plus sur une même courbe : la neuvième case est grisée, avec sa raison', async () => {
    servir('direction')
    monterApp('/analyse?onglet=matrice')
    await screen.findByRole('table', { name: 'Matrice des prix' })
    const cases = screen.getAllByRole('checkbox', { name: /^Comparer / })
    for (const c of cases.slice(0, 8)) await userEvent.click(c)
    expect(cases[8]).toBeDisabled()
    expect(cases[8]?.closest('label')).toHaveAttribute('title', '8 matières au plus sur une même courbe')
    expect(screen.getByRole('button', { name: 'Comparer les 8 matières cochées' })).toBeEnabled()
  })

  it('l’échéancier envoie ses filtres au serveur (nature, recherche)', async () => {
    const appels = servir('direction')
    monterApp('/analyse?onglet=echeancier')
    await screen.findByText('Ce qu’il faudra payer')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Nature' }), 'frais')
    await waitFor(() =>
      expect(appels.some((a) => a.chemin.startsWith('/echeancier?nature=frais'))).toBe(true),
    )
  })

  it('le fournisseur s’ouvre en fenêtre à adresse stable (&fournisseur=ID, P8-1)', async () => {
    servir('direction')
    const id = performance.lignes[0]?.fournisseur_id ?? 0
    monterApp(`/analyse?onglet=fournisseurs&fournisseur=${id}`)
    const fenetre = await screen.findByRole('dialog')
    expect(
      within(fenetre).getByText(`${performance.lignes[0]?.fournisseur} — ses réceptions`),
    ).toBeInTheDocument()
  })
})

describe('règles de l’Analyse', () => {
  it('mois du bilan : précédent par défaut, jamais un mois à venir', () => {
    expect(moisPrecedent('2026-01')).toBe('2025-12')
    expect(moisPrecedent('2026-10')).toBe('2026-09')
    expect(raisonMois('2026-11', '2026-10')).toBe('Le bilan d’un mois à venir n’existe pas encore.')
    expect(raisonMois('2026-13', '2026-10')).toMatch(/AAAA-MM/)
    expect(raisonMois('2026-10', '2026-10')).toBe('')
  })

  it('les douze fins de mois de la valorisation', () => {
    expect(finsDeMois('2026-10-09').slice(0, 3)).toEqual(['2026-09-30', '2026-08-31', '2026-07-31'])
    expect(finsDeMois('2026-03-15')[0]).toBe('2026-02-28')
  })

  it('chaque prix face au dernier prix antérieur ; la forte hausse suit le réglage', () => {
    const c = cases([null, 2, null, 2.2])
    expect(c[3]?.avant).toBe(2)
    expect(mouvement(c[3]?.variation, { stable: 0.005, forte: 0.05 })).toBe('forte')
    expect(mouvement(c[3]?.variation, { stable: 0.005, forte: 0.2 })).toBe('hausse')
    expect(mouvement(null, { stable: 0.005, forte: 0.05 })).toBe('initial')
  })

  it('contrôles : non conformes d’abord, puis par gravité', () => {
    const tries = trierControles(controles.controles)
    const premierConforme = tries.findIndex((c) => c.conforme)
    expect(tries.slice(0, premierConforme).every((c) => !c.conforme)).toBe(true)
    expect(tries[0]?.gravite).toBe('bloquant')
  })
})
