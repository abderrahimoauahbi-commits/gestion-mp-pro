/**
 * Le catalogue par tableur : l'aperçu **est** l'application — « Appliquer » renvoie le même
 * fichier avec l'empreinte du plan montré ; un tableur en erreur n'écrit rien ; un refus relit
 * l'aperçu.
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
import { reponsesCatalogue } from './donneesEssai'
import { notePied } from './Tableur'
import { champsModifies, voletInitial } from './TableurApercu'
import type { ApercuImport } from './types'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

function apercu(autres: Partial<ApercuImport> = {}): ApercuImport {
  return {
    lignes: [
      {
        ligne: 2,
        reference: 'PP 1',
        etat: 'modifiee',
        erreurs: [],
        changements: [
          { champ: 'prix', libelle: 'Prix', avant: '2,95', apres: '9,99' },
          { champ: 'stock_min', libelle: 'Stock minimum', avant: '500', apres: '750' },
        ],
      },
      { ligne: 3, reference: 'NOUVELLE', etat: 'nouvelle', erreurs: [], changements: [] },
      { ligne: 4, reference: 'PP 2', etat: 'inchangee', erreurs: [], changements: [] },
    ],
    creees: 1,
    modifiees: 1,
    inchangees: 1,
    erreurs: 0,
    appliquable: true,
    empreinte_apercu: 'abc123',
    ...autres,
  }
}

/** Les appels d'envoi de fichier : `fauxServeur` ne lit pas un FormData, on le garde ici. */
function suivreEnvois() {
  const envois: FormData[] = []
  const vrai = globalThis.fetch
  vi.stubGlobal('fetch', (entree: string, init: RequestInit = {}) => {
    if (init.body instanceof FormData) envois.push(init.body)
    return vrai(entree, init)
  })
  return envois
}

async function choisir(fichier: File) {
  const dialogue = await screen.findByRole('dialog')
  const champ = dialogue.querySelector<HTMLInputElement>('input[type=file]')
  if (!champ) throw new Error('pas de champ de fichier')
  fireEvent.change(champ, { target: { files: [fichier] } })
  return dialogue
}

describe('Tableur', () => {
  it('le pied dit ce qui sera écrit ; le volet ouvert d’office ; un champ par ligne', () => {
    expect(notePied(null)).toContain('Rien n’est écrit')
    expect(notePied(apercu())).toBe('2 matières seront écrites.')
    expect(notePied(apercu({ creees: 0, modifiees: 0 }))).toBe(
      'Rien à écrire : le tableur dit la même chose que le catalogue.',
    )
    expect(notePied(apercu({ erreurs: 1 }))).toContain('un tableur en erreur n’écrit rien')
    expect(voletInitial(apercu({ erreurs: 2 }))).toBe('erreurs')
    expect(voletInitial(apercu())).toBe('modifiees')
    expect(champsModifies(apercu().lignes).map((l) => `${l.champ} ${l.avant}→${l.apres}`)).toEqual([
      'Prix 2,95→9,99',
      'Stock minimum 500→750',
    ])
  })

  it('« Appliquer » renvoie le même fichier et l’empreinte de l’aperçu', async () => {
    fauxServeur({
      ...reponsesConnecte('achats'),
      ...reponsesCatalogue(),
      'POST /matieres/tableur/apercu': { corps: apercu() },
      'POST /matieres/tableur/appliquer': { corps: apercu() },
    })
    const envois = suivreEnvois()
    const { adresse } = monterApp('/catalogue/tableur')
    const fichier = new File(['x'], 'corrige.xlsx')
    const dialogue = await choisir(fichier)
    expect(await within(dialogue).findByText('9,99')).toBeInTheDocument()
    await userEvent.click(within(dialogue).getByRole('button', { name: 'Appliquer' }))
    expect(within(dialogue).getByText('Écrire 2 matières au catalogue ?')).toBeInTheDocument()
    await userEvent.click(within(dialogue).getByRole('button', { name: 'Oui, appliquer' }))
    await waitFor(() => expect(adresse()).toBe('/catalogue'))
    expect(envois).toHaveLength(2)
    const [lu, ecrit] = [envois[0]?.get('fichier'), envois[1]?.get('fichier')]
    if (!(lu instanceof File) || !(ecrit instanceof File)) throw new Error('fichiers absents')
    expect([ecrit.name, ecrit.size]).toEqual([lu.name, lu.size])
    expect(envois[1]?.get('empreinte_apercu')).toBe('abc123')
    expect(await screen.findByText(/Tableur appliqué/)).toBeInTheDocument()
  })

  it('un tableur en erreur grise « Appliquer » et montre les erreurs', async () => {
    fauxServeur({
      ...reponsesConnecte('direction'),
      ...reponsesCatalogue(),
      'POST /matieres/tableur/apercu': {
        corps: apercu({
          erreurs: 1,
          lignes: [
            {
              ligne: 5,
              reference: 'X',
              etat: 'erreur',
              erreurs: ['Densité : pas un nombre (« a »)', 'Rôle « Velours » inconnu'],
              changements: [],
            },
          ],
        }),
      },
    })
    monterApp('/catalogue/tableur')
    const dialogue = await choisir(new File(['x'], 'faux.xlsx'))
    expect(
      await within(dialogue).findByText('Densité : pas un nombre (« a ») ; Rôle « Velours » inconnu'),
    ).toBeInTheDocument()
    expect(within(dialogue).getByRole('button', { name: 'Appliquer' }).dataset.raison).toContain(
      'Des lignes sont en erreur',
    )
  })

  it('un refus à l’application relit l’aperçu', async () => {
    let apercus = 0
    fauxServeur({
      ...reponsesConnecte('direction'),
      ...reponsesCatalogue(),
      'POST /matieres/tableur/apercu': () => ({
        corps: apercu(apercus++ ? { erreurs: 1, modifiees: 0 } : {}),
      }),
      'POST /matieres/tableur/appliquer': {
        statut: 409,
        corps: { detail: 'Le catalogue a changé depuis l’aperçu.', code: 'conflit_version' },
      },
    })
    suivreEnvois()
    monterApp('/catalogue/tableur')
    const dialogue = await choisir(new File(['x'], 'corrige.xlsx'))
    await within(dialogue).findByText('9,99')
    await userEvent.click(within(dialogue).getByRole('button', { name: 'Appliquer' }))
    await userEvent.click(within(dialogue).getByRole('button', { name: 'Oui, appliquer' }))
    expect(await screen.findByText('Le catalogue a changé depuis l’aperçu.')).toBeInTheDocument()
    await waitFor(() => expect(apercus).toBe(2))
  })
})
