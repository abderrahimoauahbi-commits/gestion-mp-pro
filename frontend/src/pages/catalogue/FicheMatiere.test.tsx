/**
 * La fiche matière : référence composée semi-automatique, conflit de version rechargeable (R2),
 * désactiver sans revalider la saisie (P7-21), suppression grisée par les traces, lecture de
 * l'alimentation sans rien de l'achat.
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
import { matiereEssai, reponsesCatalogue } from './donneesEssai'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

/** La fenêtre, une fois la fiche lue (et non son « chargement »). */
async function ficheChargee() {
  await waitFor(() => expect(screen.getByRole('dialog').textContent).not.toMatch(/Un instant/))
  return screen.getByRole('dialog')
}

const CONFLIT = {
  statut: 409,
  corps: {
    detail:
      'Cette matière a été modifiée entre-temps par Nadia (08/10/2026 10:02) : rouvrez-la pour repartir de sa dernière version.',
    code: 'conflit_version',
  },
}

describe('Fiche matière', () => {
  it('compose la référence depuis la classification tant qu’on ne la retouche pas', async () => {
    const appels = fauxServeur({
      ...reponsesConnecte('achats'),
      ...reponsesCatalogue(),
      'GET /matieres/reference': (_c, url) => ({
        corps: {
          reference: `PP${url.searchParams.get('couleur_code') ? ` ${url.searchParams.get('couleur_code')}` : ''}`,
          designation: 'Rouge',
          existe: false,
        },
      }),
    })
    monterApp('/matieres/nouvelle')
    const dialogue = await ficheChargee()
    await userEvent.type(within(dialogue).getByRole('combobox', { name: 'Composition' }), 'PP{Enter}')
    const reference = within(dialogue).getByRole('textbox', { name: 'Référence' })
    await waitFor(() => expect(reference).toHaveValue('PP'))
    await userEvent.type(within(dialogue).getByRole('textbox', { name: 'Code couleur' }), '7001')
    await waitFor(() => expect(reference).toHaveValue('PP 7001'))
    expect(appels.some((a) => a.chemin.startsWith('/matieres/reference?composition_id=1'))).toBe(true)
    await userEvent.type(reference, 'X')
    await userEvent.type(within(dialogue).getByRole('textbox', { name: 'Code couleur' }), '9')
    await new Promise((r) => setTimeout(r, 400))
    expect(reference).toHaveValue('PP 7001X')
    expect(within(dialogue).getByText(/La classification compose/)).toBeInTheDocument()
  })

  it('409 : la saisie reste, le message du serveur et « Recharger la fiche » ; recharger repart de la dernière version', async () => {
    let lectures = 0
    fauxServeur({
      ...reponsesConnecte('direction'),
      ...reponsesCatalogue(),
      'PUT /matieres/12': CONFLIT,
      'GET /matieres/12': () => ({
        corps: matiereEssai({
          designation: lectures++ ? 'Rouge vif' : 'Rouge (7001)',
          version: 3 + (lectures > 1 ? 1 : 0),
        }),
      }),
    })
    monterApp('/matieres/12')
    const dialogue = await ficheChargee()
    const designation = within(dialogue).getByRole('textbox', { name: 'Désignation' })
    await userEvent.clear(designation)
    await userEvent.type(designation, 'Rouge sombre')
    await userEvent.click(within(dialogue).getByRole('button', { name: 'Enregistrer' }))
    expect(await within(dialogue).findByText(/modifiée entre-temps par Nadia/)).toBeInTheDocument()
    expect(designation).toHaveValue('Rouge sombre')
    expect(within(dialogue).getByRole('button', { name: 'Enregistrer' })).toHaveAttribute(
      'data-raison',
      'Recharger d’abord la fiche.',
    )
    await userEvent.click(within(dialogue).getByRole('button', { name: 'Recharger la fiche' }))
    await waitFor(() => expect(designation).toHaveValue('Rouge vif'))
    expect(
      await screen.findByText('Fiche rechargée dans sa dernière version : refaire la modification.'),
    ).toBeInTheDocument()
    expect(within(dialogue).queryByText(/modifiée entre-temps/)).toBeNull()
  })

  it('désactiver envoie la fiche enregistrée, état changé seulement ; grisé tant qu’une saisie est en cours', async () => {
    const appels = fauxServeur({
      ...reponsesConnecte('direction'),
      ...reponsesCatalogue(),
      'PUT /matieres/12': { corps: matiereEssai({ actif: false, version: 4 }) },
    })
    monterApp('/matieres/12')
    const dialogue = await ficheChargee()
    const designation = within(dialogue).getByRole('textbox', { name: 'Désignation' })
    await userEvent.type(designation, ' bis')
    expect(within(dialogue).getByRole('button', { name: 'Désactiver' })).toHaveAttribute(
      'data-raison',
      'Enregistrer d’abord les changements',
    )
    await userEvent.clear(designation)
    await userEvent.type(designation, 'Rouge (7001)')
    await userEvent.click(within(dialogue).getByRole('button', { name: 'Désactiver' }))
    await userEvent.click(within(dialogue).getByRole('button', { name: 'Oui, désactiver' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'PUT')).toBe(true))
    const corps = appels.find((a) => a.methode === 'PUT')?.corps
    expect(corps).toMatchObject({
      actif: false,
      version: 3,
      designation: 'Rouge (7001)',
      priorite_equiv: 10,
      prix: 2.5,
    })
    expect(await screen.findByText('Matière désactivée.')).toBeInTheDocument()
  })

  it('supprimer est grisé par les traces que le serveur a comptées', async () => {
    fauxServeur({ ...reponsesConnecte('direction'), ...reponsesCatalogue() })
    monterApp('/matieres/12')
    const dialogue = await ficheChargee()
    expect(within(dialogue).getByRole('button', { name: 'Supprimer' }).dataset.raison).toContain(
      'figure dans des mouvements de stock, des recettes : la désactiver plutôt',
    )
  })

  it('alimentation : lecture sans prix, devise, minimum ni pièces jointes', async () => {
    fauxServeur({
      ...reponsesConnecte('alimentation'),
      ...reponsesCatalogue({
        'GET /matieres/12': {
          corps: matiereEssai({
            prix: null,
            prix_kg: null,
            devise: null,
            unite_prix: null,
            minimum_commande: null,
          }),
        },
      }),
    })
    monterApp('/matieres/12')
    const dialogue = await ficheChargee()
    expect(within(dialogue).getByText('Mersin Iplik')).toBeInTheDocument()
    expect(within(dialogue).queryByRole('tab', { name: /Achat|Pièces/ })).toBeNull()
    expect(dialogue.textContent).not.toMatch(/\b(USD|MAD)\b|[Pp]rix|[Mm]inimum de commande/)
    expect(within(dialogue).queryByRole('button', { name: 'Enregistrer' })).toBeNull()
  })
})
