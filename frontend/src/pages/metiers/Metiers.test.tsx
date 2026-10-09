/**
 * Métiers à tisser au bureau, dans l'application entière : indicateurs (formule de chacun), liste
 * « Sur les métiers (kg) » sans valeur pour l'alimentation, création réservée à la direction (an.
 * 15), fiche en fenêtre à adresse stable avec onglets dans l'adresse (an. 29), enregistrement en
 * une requête — `PUT /metiers/{id}` (réglage et fils) pour la direction, `PUT …/montage` pour
 * l'alimentation — avec l'effet à confirmer et le texte unique ((a)) ; achats en lecture.
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { donnees, MONETAIRE, reponsesAtelier } from '../atelier/essaiAtelier'
import type { MetierFiche } from '../atelier/types'
import { aVoir } from './colonnes'
import { corpsMontage, etagesTouches, raisonEnregistrer, versForme } from './formeMetier'
import { ficheDe, sousTitre } from './Metiers'
import { manqueCreation } from './NouveauMetier'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const M1 = (): MetierFiche => {
  const m = donnees().METIERS.find((x) => x.id === 1)
  if (!m) throw new Error('fixture')
  return m
}

describe('Forme d’un métier', () => {
  it('étages touchés, montage envoyé avec sa version, raisons qui suivent l’état', () => {
    const m = M1()
    const avant = versForme(m)
    const apres = { ...avant, fils: avant.fils.map((f) => ({ ...f, metres: 2 })) }
    expect(etagesTouches(avant, apres)).toEqual([1])
    expect(corpsMontage(m, avant, apres, 12.3)).toEqual({
      etages: [
        {
          etage: 1,
          version: m.etages_detail[0]?.version,
          fils: [{ matiere_id: 1, metres: 2, pourcentage: 100, commentaire: '' }],
        },
      ],
      confirme_effet_kg: 12.3,
    })
    expect(corpsMontage(m, avant, avant, 0)).toBeNull()
    expect(raisonEnregistrer(avant, avant, true)).toBe('Aucune modification')
    expect(raisonEnregistrer({ ...avant, code: '' }, avant, true)).toBe('Saisir le code')
    expect(raisonEnregistrer({ ...avant, etages: 41 }, avant, true)).toBe('Les étages vont de 1 à 40')
    expect(raisonEnregistrer({ ...avant, etages: 0 }, avant, false)).toBe(
      'Fils hors machine : les déplacer ou les retirer',
    )
    expect(
      raisonEnregistrer({ ...apres, fils: apres.fils.map((f) => ({ ...f, metres: 5 })) }, avant, false),
    ).toBe('Étage 1 trop large')
    expect(
      raisonEnregistrer({ ...apres, fils: apres.fils.map((f) => ({ ...f, metres: 0 })) }, avant, false),
    ).toBe('Saisir les mètres de POIL ROUGE 2900')
    expect(manqueCreation(versForme(null))).toEqual(['le code'])
    expect(ficheDe('/metiers/nouveau')).toBe('nouveau')
    expect(ficheDe('/metiers/4')).toBe(4)
    expect(sousTitre('achats')).toMatch(/Lecture seule/)
    expect(aVoir({ ...m, densite_a_saisir: true, etages_trop_larges: [2, 3] }).map((x) => x.texte)).toEqual([
      'densité à saisir',
      'étages 2, 3 trop larges',
    ])
  })
})

describe('Métiers à tisser', () => {
  it('alimentation : liste et indicateurs sans valeur ; la création lui est refusée avec la raison', async () => {
    fauxServeur(reponsesAtelier('alimentation'))
    const app = monterApp('/metiers')
    const table = await screen.findByRole('table', { name: 'Métiers à tisser' })
    expect(within(table).getByText('M1 · Van de Wiele n° 1')).toBeInTheDocument()
    expect(within(table).queryByText(/Ancien métier/)).toBeNull()
    expect(screen.getByText('Sur les métiers (kg)')).toBeInTheDocument()
    expect(document.querySelector('main')?.textContent).not.toMatch(MONETAIRE)
    expect(screen.queryByRole('button', { name: 'Nouveau métier' })).toBeNull()
    await app.routeur.navigate('/metiers/nouveau')
    await waitFor(() => expect(app.adresse()).toBe('/metiers'))
    expect(
      await screen.findByText('La création d’un métier est réservée à la direction.'),
    ).toBeInTheDocument()
  })

  it('alimentation : monte un fil au bureau par PUT …/montage, effet annoncé puis confirmé', async () => {
    const m = M1()
    const appels = fauxServeur(
      reponsesAtelier('alimentation', {
        'PUT /metiers/1/montage': {
          corps: { metier: m, effet_kg: 0, avant_kg: 0, apres_kg: 0, alertes: [], message: '' },
        },
      }),
    )
    const u = userEvent.setup()
    monterApp('/metiers/1')
    const dialogue = await screen.findByRole('dialog', { name: /Métier M1/ })
    const metres = await within(dialogue).findByRole('textbox', { name: 'Mètres de POIL ROUGE 2900' })
    expect(
      within(dialogue).getByText('Vous montez les fils ; la direction règle le métier.'),
    ).toBeInTheDocument()
    await u.clear(metres)
    await u.type(metres, '2')
    await u.click(within(dialogue).getByRole('button', { name: 'Enregistrer' }))
    const question = within(dialogue).getByRole('group', { name: 'Confirmation' })
    expect(question.textContent).toMatch(
      /^Monter n’écrit aucun mouvement : ce fil est déjà sorti par un ordre\./,
    )
    await u.click(within(question).getByRole('button', { name: 'Oui, enregistrer' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'PUT')).toBe(true))
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toMatchObject({
      etages: [{ etage: 1, fils: [{ matiere_id: 1, metres: 2 }] }],
      confirme_effet_kg: 399.232,
    })
  })

  it('direction : réglage et fils dans une seule requête ; onglets dans l’adresse', async () => {
    const m = M1()
    const appels = fauxServeur(
      reponsesAtelier('direction', { 'PUT /metiers/1': { corps: { ...m, montage: null } } }),
    )
    const u = userEvent.setup()
    const app = monterApp('/metiers/1')
    const dialogue = await screen.findByRole('dialog', { name: /Métier M1/ })
    await u.click(within(dialogue).getByRole('tab', { name: /Réglages/ }))
    await waitFor(() => expect(app.adresse()).toBe('/metiers/1?onglet=reglages'))
    const densite = within(dialogue).getByRole('textbox', { name: 'Densité (bobines par mètre)' })
    await u.clear(densite)
    await u.type(densite, '160')
    await u.click(within(dialogue).getByRole('button', { name: 'Enregistrer' }))
    await u.click(within(dialogue).getByRole('button', { name: 'Oui, enregistrer' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'PUT')).toBe(true))
    expect(appels.find((a) => a.methode === 'PUT')).toMatchObject({
      chemin: '/metiers/1',
      corps: { code: 'M1', bobines_par_metre: 160, version: m.version, montage: null },
    })
    expect(within(dialogue).getByRole('button', { name: 'Supprimer' })).toBeDisabled()
  })

  it('achats : la fiche est en lecture, sans « Enregistrer »', async () => {
    fauxServeur(reponsesAtelier('achats'))
    monterApp('/metiers/1?onglet=fils')
    const dialogue = await screen.findByRole('dialog', { name: /Métier M1/ })
    expect(
      await within(dialogue).findByText(
        'Lecture seule : l’alimentation monte les fils, la direction règle le métier.',
      ),
    ).toBeInTheDocument()
    expect(within(dialogue).queryByRole('button', { name: 'Enregistrer' })).toBeNull()
    expect(within(dialogue).getByRole('textbox', { name: 'Mètres de POIL ROUGE 2900' })).toBeDisabled()
  })
})
