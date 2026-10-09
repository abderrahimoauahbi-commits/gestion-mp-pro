/**
 * Les Sorties dans l'application entière, sur des réponses relevées au vrai serveur : la liste par
 * onglet (« Brouillon » au lieu de « sans n° », « À sortir » sur les brouillons), la fiche d'un
 * brouillon bloqué (« Valider la sortie » grisé avec la raison du serveur), la saisie d'un ordre et
 * le retour des machines qui annoncent leurs blocages avant tout envoi (critère F2).
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
import magasins from '../stock/essais/magasins.json'
import motifs from '../stock/essais/motifs.json'
import bloque from './essais/ordre-bloque.json'
import brouillon from './essais/ordre-brouillon.json'
import valide from './essais/ordre-valide.json'
import lotsMagasin from './essais/lots-magasin.json'
import lotsSortis from './essais/lots-sortis.json'
import metiers from './essais/metiers.json'
import ordres from './essais/ordres.json'
import proposition from './essais/proposition.json'
import qualites from './essais/qualites.json'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

function servir(role: Role) {
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /ordres': { corps: ordres },
    'GET /ordres/7': { corps: valide },
    'GET /ordres/5': { corps: brouillon },
    'GET /ordres/6': { corps: bloque },
    'GET /ordres/7/lots-sortis': { corps: lotsSortis },
    'GET /magasins': { corps: magasins },
    'GET /metiers': { corps: metiers },
    'GET /qualites': { corps: qualites },
    'GET /motifs': { corps: motifs },
    'GET /lots': { corps: lotsMagasin },
    'POST /ordres/proposition': { corps: proposition },
    'GET /historique/ordre/7': { corps: [] },
  })
}

const ecritures = (appels: ReturnType<typeof servir>) =>
  appels.filter((a) => a.methode !== 'GET' && a.chemin !== '/ordres/proposition')

describe('Sorties vers les machines', () => {
  it('la liste par onglet : validés numérotés, brouillons « Brouillon » et « À sortir »', async () => {
    servir('achats')
    monterApp('/sorties')
    const tableau = await screen.findByRole('table', { name: 'Ordres de fabrication' })
    expect(await within(tableau).findByText('OF-2026-0005')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Nouvelle sortie' })).toBeNull()
    await userEvent.click(screen.getByRole('tab', { name: /Brouillons/ }))
    expect(await within(tableau).findAllByText('Brouillon')).not.toHaveLength(0)
    expect(within(tableau).getByText('À sortir (kg)')).toBeInTheDocument()
    expect(within(tableau).getByText('sera refusé')).toBeInTheDocument()
  })

  it('un brouillon bloqué : « Valider la sortie » grisé avec la raison du serveur', async () => {
    servir('alimentation')
    monterApp('/ordres/6?onglet=brouillon')
    const fiche = await screen.findByRole('dialog')
    expect(await within(fiche).findByText(bloque.blocages[0] as string)).toBeInTheDocument()
    const valider = within(fiche).getByRole('button', { name: 'Valider la sortie' })
    expect(valider).toBeDisabled()
    expect(valider.getAttribute('data-raison')).toContain(bloque.blocages[0])
  })

  it('un ordre validé : retour et annulation pour l’alimentation, lecture pour les achats', async () => {
    servir('achats')
    monterApp('/ordres/7')
    const fiche = await screen.findByRole('dialog')
    expect(await within(fiche).findByText(/OF-2026-0005/)).toBeInTheDocument()
    expect(within(fiche).queryByRole('button', { name: 'Faire un retour' })).toBeNull()
    expect(within(fiche).getByRole('button', { name: 'Traçabilité de l’ordre' })).toBeInTheDocument()
  })
})

describe('Saisie d’ordre : blocages annoncés avant l’envoi', () => {
  it('daté avant le dernier ordre validé, le refus est dit et rien ne part', async () => {
    const appels = servir('alimentation')
    monterApp('/ordres/nouveau')
    const saisie = await screen.findByRole('dialog', { name: /Nouvel ordre — Brouillon/ })
    await userEvent.click(within(saisie).getByRole('button', { name: 'Ordre hors recette' }))
    // Une matière ajoutée à la main, puis une date d'avant le dernier ordre validé.
    const ajout = within(saisie).getByRole('combobox', { name: 'Ajouter une matière' })
    await userEvent.click(ajout)
    await userEvent.click(await within(saisie).findByText(/PP FRZ-2900 Rouge · lot L-R-102/))
    await userEvent.type(within(saisie).getByRole('textbox', { name: 'Quantité du lot L-R-102' }), '5')
    fireEvent.change(within(saisie).getByLabelText(/^Date/), { target: { value: '2026-09-01' } })
    expect(await within(saisie).findAllByText(/Un ordre du 09\/10\/2026 est déjà validé/)).not.toHaveLength(0)
    const valider = within(saisie).getByRole('button', { name: 'Valider la sortie' })
    expect(valider).toBeDisabled()
    expect(valider.getAttribute('data-raison')).toMatch(/^Sera refusé : Un ordre du 09\/10\/2026/)
    expect(ecritures(appels)).toEqual([])
  })

  it('plus que le lot n’en porte : annoncé, « Valider la sortie » grisé', async () => {
    const appels = servir('direction')
    monterApp('/ordres/nouveau')
    const saisie = await screen.findByRole('dialog', { name: /Nouvel ordre — Brouillon/ })
    await userEvent.click(within(saisie).getByRole('button', { name: 'Ordre hors recette' }))
    await userEvent.click(within(saisie).getByRole('combobox', { name: 'Ajouter une matière' }))
    await userEvent.click(await within(saisie).findByText(/PP FRZ-2900 Rouge · lot L-R-102/))
    await userEvent.type(within(saisie).getByRole('textbox', { name: 'Quantité du lot L-R-102' }), '99999')
    expect(
      await within(saisie).findAllByText(/lot L-R-102 de PP FRZ-2900 Rouge : .* seulement dans/),
    ).not.toHaveLength(0)
    expect(within(saisie).getByRole('button', { name: 'Valider la sortie' })).toBeDisabled()
    expect(ecritures(appels)).toEqual([])
  })

  it('« Garder en brouillon » grisé tant qu’aucune ligne n’est saisie, avec la raison', async () => {
    servir('direction')
    monterApp('/ordres/nouveau')
    const saisie = await screen.findByRole('dialog', { name: /Nouvel ordre — Brouillon/ })
    const garder = within(saisie).getByRole('button', { name: 'Garder en brouillon' })
    expect(garder.getAttribute('data-raison')).toMatch(/au moins une ligne/)
    expect(
      within(saisie)
        .getByRole('button', { name: 'Proposer les matières à sortir' })
        .getAttribute('data-raison'),
    ).toMatch(/la qualité de chaque ligne/)
  })
})

describe('Retour des machines : blocages annoncés avant l’envoi', () => {
  it('plus que ce qui est parti : dit, et « Remettre en stock » grisé', async () => {
    const appels = servir('alimentation')
    monterApp('/ordres/7/retour')
    const retour = await screen.findByRole('dialog', { name: /Retour des machines — OF-2026-0005/ })
    const premier = lotsSortis[0]
    const champ = await within(retour).findByRole('textbox', {
      name: `Ce qui revient du lot ${premier?.lot}`,
    })
    await userEvent.type(champ, '999')
    expect(await within(retour).findAllByText(/1 lot\(s\) dépassent ce qui est parti/)).not.toHaveLength(0)
    const remettre = within(retour).getByRole('button', { name: /Remettre .* en stock/ })
    expect(remettre).toBeDisabled()
    expect(ecritures(appels)).toEqual([])
    await waitFor(() => expect(within(retour).getAllByText('plus que ce qui est parti')).not.toHaveLength(0))
  })
})
