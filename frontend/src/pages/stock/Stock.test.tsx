/**
 * La page du Stock dans l'application entière, sur des réponses relevées au vrai serveur (base
 * d'essai du lot F2) : par rôle (l'alimentation sans prix ni conseil d'achat, H-03), la fiche
 * matière et son addition qui tombe juste, « Tout valider » qui ne compte et n'envoie que ce qui
 * sera validé (P2-12, H-23), les étiquettes grisées avec leur raison (P2-11).
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
import type { Role } from '../../lib/types'
import brouillons from './essais/brouillons.json'
import consommation from './essais/consommation.json'
import fiche from './essais/fiche-matiere.json'
import lots from './essais/lots.json'
import magasins from './essais/magasins.json'
import matieres from './essais/matieres.json'
import motifs from './essais/motifs.json'
import mouvements from './essais/mouvements.json'
import stock from './essais/stock.json'
import stockAlimentation from './essais/stock-alimentation.json'
import tracabiliteOrdre from './essais/tracabilite-ordre.json'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const MONETAIRE = /\b(USD|MAD|EUR)\b|[Pp]rix|[Cc]oût|[Mm]ontant|Budget|À commander|Classe ABC/

function servir(role: Role, autres = {}) {
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /stock': { corps: role === 'alimentation' ? stockAlimentation : stock },
    'GET /stock/1': { corps: fiche },
    'GET /magasins': { corps: magasins },
    'GET /matieres': { corps: matieres },
    'GET /lots': { corps: lots },
    'GET /brouillons': { corps: brouillons },
    'GET /motifs': { corps: motifs },
    'GET /ordres/consommation': { corps: consommation },
    'GET /historique/matiere/1': { corps: [] },
    ...autres,
  })
}

/** Le nombre d'une cellule (« 1 737,9 » → 1737.9). */
const lire = (texte: string) =>
  Number(
    texte
      .replace(/[\s\u00a0\u202f]/g, '')
      .replace('−', '-')
      .replace(',', '.'),
  )

describe('Stock › Par matière', () => {
  it('direction : chaque matière, son statut, ses kilos, le budget à commander', async () => {
    servir('direction')
    monterApp('/stock')
    const tableau = await screen.findByRole('table', { name: 'Stock par matière' })
    expect(within(tableau).getByText('PP FRZ-2900 Rouge')).toBeInTheDocument()
    expect(screen.getByText('Budget à commander')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Exporter en Excel/ })).toHaveAttribute(
      'href',
      '/api/export/pilotage',
    )
  })

  it('alimentation : ni prix, ni montant, ni conseil d’achat, ni classe ABC (H-03)', async () => {
    servir('alimentation')
    monterApp('/stock')
    await screen.findByRole('table', { name: 'Stock par matière' })
    expect(document.querySelector('main')?.textContent).not.toMatch(MONETAIRE)
    await userEvent.click(screen.getByRole('button', { name: 'Classement et risque' }))
    expect(document.querySelector('main')?.textContent).not.toMatch(MONETAIRE)
  })

  it('« Ruptures » et « Critiques » posent leur filtre', async () => {
    servir('achats')
    monterApp('/stock')
    await screen.findByRole('table', { name: 'Stock par matière' })
    expect(screen.getByRole('link', { name: /Ruptures/ })).toHaveAttribute('href', '/stock?statut=RUPTURE')
  })
})

describe('Fiche matière', () => {
  it('s’ouvre à son adresse ; « Où se trouve la matière » s’additionne juste', async () => {
    servir('direction')
    const { adresse } = monterApp('/stock?q=rouge')
    await userEvent.click(await screen.findByText('PP FRZ-2900 Rouge'))
    await waitFor(() => expect(adresse()).toBe('/stock/matieres/1?q=rouge&onglet=matieres'))
    const carte = await screen.findByRole('table', { name: 'Où se trouve la matière' })
    const valeur = (libelle: RegExp, rang = 0) =>
      lire(within(carte).getAllByText(libelle)[rang]?.closest('tr')?.lastElementChild?.textContent ?? '')
    const disponible = valeur(/^Disponible$/)
    expect(
      disponible + valeur(/Commandé, attendu dans le délai/) - valeur(/Demande pendant le délai/),
    ).toBeCloseTo(valeur(/Stock projeté à la livraison/), 6)
    // Les indicateurs disent les mêmes chiffres que la carte.
    const texte = (libelle: RegExp) =>
      within(carte).getAllByText(libelle)[0]?.closest('tr')?.lastElementChild?.textContent ?? '?'
    const indicateurs = screen.getByRole('region', { name: 'Indicateurs de la matière' }).textContent ?? ''
    expect(indicateurs).toContain(texte(/Demande pendant le délai/))
    expect(indicateurs).toContain(texte(/Stock projeté à la livraison/))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Fermer' }))
    await waitFor(() => expect(adresse()).toBe('/stock?q=rouge'))
  })
})

describe('Stock › À valider', () => {
  const avec = {
    ...brouillons,
    lignes: [
      ...brouillons.lignes,
      {
        ...brouillons.lignes[1],
        genre: 'operation',
        type: 'transfert',
        id: 41,
        version: 3,
        libelle: 'Transfert entre magasins',
      },
      {
        ...brouillons.lignes[1],
        genre: 'operation',
        type: 'ajustement',
        id: 42,
        peut_valider: false,
        raison: 'Réservé aux achats.',
      },
    ],
  }
  const attendus = avec.lignes.filter((x) => x.peut_valider && !x.blocages.length)

  it('« Tout valider (N) » : N et l’envoi ne comptent que ce qui sera validé', async () => {
    const appels = servir('direction', {
      'GET /brouillons': { corps: { ...avec, nombre: 4, bloques: 1, validables: attendus.length } },
      'POST /brouillons/valider': {
        corps: { valides: [{ ...attendus[0], numero: 'OF-2026-0006' }], refuses: [], ignores: [] },
      },
    })
    monterApp('/stock?onglet=a-valider')
    const bouton = await screen.findByRole('button', { name: `Tout valider (${attendus.length})` })
    await userEvent.click(bouton)
    await userEvent.click(screen.getByRole('button', { name: 'Oui, tout valider' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'POST')).toBe(true))
    const envoi = appels.find((a) => a.methode === 'POST' && a.chemin === '/brouillons/valider')
    expect(envoi?.corps).toEqual({
      documents: attendus.map((x) => ({ genre: x.genre, id: x.id, version: x.version })),
    })
    expect(await screen.findAllByText(/1 brouillon\(s\) validé\(s\) : OF-2026-0006/)).not.toHaveLength(0)
  })

  it('rien à valider : le bouton est grisé et dit pourquoi', async () => {
    servir('achats', {
      'GET /brouillons': { corps: { ...brouillons, lignes: [brouillons.lignes[0]], validables: 0 } },
    })
    monterApp('/stock?onglet=a-valider')
    const bouton = await screen.findByRole('button', { name: 'Tout valider (0)' })
    expect(bouton).toBeDisabled()
    expect(bouton.getAttribute('data-raison')).toMatch(/Aucun brouillon/)
  })
})

describe('Stock › Lots', () => {
  it('« Étiquettes (0) » grisé avec sa raison ; cocher un lot ouvre ses étiquettes', async () => {
    servir('alimentation')
    monterApp('/stock?onglet=lots')
    const zero = await screen.findByRole('button', { name: 'Étiquettes (0)' })
    expect(zero.getAttribute('data-raison')).toMatch(/cocher au moins un lot/)
    fireEvent.click(screen.getByRole('checkbox', { name: `Étiquette du lot ${lots[0]?.lot}` }))
    const lien = await screen.findByRole('link', { name: /Étiquettes \(1\)/ })
    expect(lien.getAttribute('href')).toBe(`/api/documents/etiquettes?lots=${lots[0]?.lot_id}`)
  })
})

describe('Suivi de traçabilité', () => {
  it('d’un ordre : prévu et sorti par matière ; suivre une matière allonge le chemin ; × rend la fiche d’où l’on vient', async () => {
    servir('direction', {
      'GET /tracabilite': (_c: unknown, url: URL) => ({
        corps: url.searchParams.get('ordre')
          ? tracabiliteOrdre
          : { ...tracabiliteOrdre, ordre: '', matiere: 'PP FRZ-2900 Rouge' },
      }),
      'GET /ordres/7': { corps: { blocages: [] } },
    })
    const { adresse } = monterApp(
      `/tracabilite?ordre=7&retour=${encodeURIComponent('/stock?onglet=ordres&q=atlas')}`,
    )
    const fenetre = await screen.findByRole('dialog', { name: /Ordre de fabrication OF-2026-0005/ })
    const table = await within(fenetre).findByRole('table', {
      name: 'Prévu par la recette et sorti net, par matière',
    })
    await userEvent.click(within(table).getByRole('button', { name: 'PP FRZ-2900 Rouge' }))
    await waitFor(() => expect(adresse()).toMatch(/^\/tracabilite\?matiere=1&depuis=ordre%3A7/))
    const suite = await screen.findByRole('dialog', { name: /Parcours de la matière/ })
    // Les ids des étapes (RESTES3) : le n° du document mène à sa fiche, l'ordre se suit par son id.
    const documents = await within(suite).findAllByRole('link', { name: 'OF-2026-0005' })
    expect(documents[0]).toHaveAttribute('href', '/ordres/7')
    expect(within(suite).getAllByRole('button', { name: 'OF-2026-0005' }).length).toBeGreaterThan(0)
    expect(
      within(suite).getByRole('button', { name: '← Revenir à l’ordre OF-2026-0005' }),
    ).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    await waitFor(() => expect(adresse()).toBe('/stock?onglet=ordres&q=atlas'))
  })
})

describe('Stock › Mouvements de stock', () => {
  it('alimentation : ni prix ni valeur ; la recherche et les filtres partent au serveur', async () => {
    const appels = servir('alimentation', {
      'GET /mouvements': {
        corps: {
          ...mouvements,
          elements: mouvements.elements.map((m) => ({ ...m, prix: null, valeur_mad: null, cout_mad: null })),
        },
      },
    })
    monterApp('/stock?onglet=mouvements&type=SORTIE')
    await screen.findByRole('table', { name: 'Mouvements de stock' })
    expect(document.querySelector('main')?.textContent).not.toMatch(MONETAIRE)
    expect(appels.some((a) => a.chemin.startsWith('/mouvements?') && a.chemin.includes('type=SORTIE'))).toBe(
      true,
    )
  })
})
