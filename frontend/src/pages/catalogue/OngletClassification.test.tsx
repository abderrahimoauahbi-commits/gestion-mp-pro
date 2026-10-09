/**
 * L'onglet Classification : désactiver une valeur se confirme sur la ligne et dit l'avertissement
 * du serveur (matières qui la gardent) ; supprimer est grisé tant qu'une matière la porte ; un
 * rôle se modifie à sa version.
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
import { classificationEssai, reponsesCatalogue, roleEssai, valeurEssai } from './donneesEssai'
import { blocagesRole } from './Roles'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

describe('Classification', () => {
  it('désactiver « PP » : confirmé sur la ligne, avertissement du serveur dit', async () => {
    const appels = fauxServeur({
      ...reponsesConnecte('achats'),
      ...reponsesCatalogue(),
      'PUT /classification/compositions/1': {
        corps: valeurEssai(1, 'PP', {
          actif: false,
          avertissement:
            '« PP » reste porté par 3 matière(s) : elle ne se choisit plus, ces matières la gardent.',
        }),
      },
    })
    monterApp('/catalogue?onglet=classification')
    const tableau = await screen.findByRole('table', { name: 'Compositions' })
    const ligne = within(tableau).getByText('PP').closest('tr')
    if (!ligne) throw new Error('ligne absente')
    expect(within(ligne).getByRole('button', { name: 'Supprimer' }).dataset.raison).toContain(
      'Portée par 3 matière(s)',
    )
    await userEvent.click(within(ligne).getByRole('button', { name: 'Désactiver' }))
    await userEvent.click(within(ligne).getByRole('button', { name: 'Oui, désactiver' }))
    expect(await screen.findByText(/reste porté par 3 matière\(s\)/)).toBeInTheDocument()
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toMatchObject({
      code: 'PP',
      actif: false,
      version: 1,
    })
  })

  it('un rôle : supprimer grisé par la règle du serveur ; modifier envoie sa version', async () => {
    expect(blocagesRole(roleEssai(1, 'Poil'))).toEqual(['Rôle du calcul : il ne se supprime pas'])
    expect(blocagesRole({ ...roleEssai(9, 'Velours'), de_base: false, nb_matieres: 2 })).toEqual([
      'Porté par 2 matière(s) et 0 qualité(s) : les changer d’abord',
    ])
    const c = classificationEssai()
    const appels = fauxServeur({
      ...reponsesConnecte('direction'),
      ...reponsesCatalogue({
        'GET /classification': {
          corps: {
            ...c,
            roles: [...c.roles, { ...roleEssai(9, 'Velours', false, 8), de_base: false, version: 2 }],
          },
        },
      }),
      'PUT /classification/roles/9': { corps: { ...roleEssai(9, 'Velours ras', false, 8), version: 3 } },
    })
    monterApp('/catalogue?onglet=classification&liste=roles')
    await userEvent.click(await screen.findByText('Velours'))
    const dialogue = await screen.findByRole('dialog')
    const nom = within(dialogue).getByRole('textbox', { name: 'Nom du rôle' })
    await userEvent.type(nom, ' ras')
    await userEvent.click(within(dialogue).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'PUT')).toBe(true))
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toEqual({
      code: 'Velours ras',
      ordre: 8,
      version: 2,
    })
  })
})
