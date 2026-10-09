/**
 * La fiche fournisseur : 409 « modifié entre-temps par X » avec « Recharger la fiche » (P7-14),
 * suppression grisée par tout ce que le serveur a compté (P7-4), délai en attention qui dit
 * pourquoi (P7-24), création qui ouvre la fiche créée.
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
import { fournisseurEssai, reponsesCatalogue } from './donneesEssai'
import {
  codeClassement,
  corpsFournisseur,
  delaiDepasse,
  manquesFournisseur,
  versFormeFournisseur,
} from './formeFournisseur'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

async function ficheChargee() {
  await waitFor(() => expect(screen.getByRole('dialog').textContent).not.toMatch(/Un instant/))
  return screen.getByRole('dialog')
}

describe('Fiche fournisseur', () => {
  it('règles sans écran : manques, délai dépassé, classement, corps entier', () => {
    expect(manquesFournisseur({ ...versFormeFournisseur(null), delai_jours: null, email: 'x' })).toEqual([
      'le nom',
      'le délai d’approvisionnement',
      'un e-mail de la forme nom@domaine.ma',
    ])
    expect(manquesFournisseur({ ...versFormeFournisseur(fournisseurEssai()), delai_jours: 731 })).toEqual([
      'un délai de deux ans au plus',
    ])
    expect(delaiDepasse(fournisseurEssai({ delai_mesure_jours: 73, livraisons_mesurees: 3 }))).toBe(true)
    expect(delaiDepasse(fournisseurEssai({ delai_mesure_jours: 73, livraisons_mesurees: 2 }))).toBe(false)
    expect(codeClassement('À surveiller')).toBe('a_surveiller')
    expect(Object.keys(corpsFournisseur(versFormeFournisseur(fournisseurEssai())))).toHaveLength(17)
  })

  it('409 : le message du serveur et « Recharger la fiche »', async () => {
    fauxServeur({
      ...reponsesConnecte('achats'),
      ...reponsesCatalogue(),
      'PUT /fournisseurs/7': {
        statut: 409,
        corps: {
          detail:
            'Ce fournisseur a été modifié entre-temps par Karim (08/10/2026 11:00) : rouvrez-le pour repartir de sa dernière version.',
          code: 'conflit_version',
        },
      },
    })
    monterApp('/fournisseurs/7')
    const dialogue = await ficheChargee()
    await userEvent.type(within(dialogue).getByRole('textbox', { name: 'Contact' }), ' Demir')
    await userEvent.click(within(dialogue).getByRole('button', { name: 'Enregistrer' }))
    expect(await within(dialogue).findByText(/modifié entre-temps par Karim/)).toBeInTheDocument()
    expect(within(dialogue).getByRole('button', { name: 'Recharger la fiche' })).toBeInTheDocument()
    expect(within(dialogue).getByRole('textbox', { name: 'Contact' })).toHaveValue('Ayse Demir')
  })

  it('supprimer : grisé avec ce qui l’empêche ; délai mesuré au-delà de 120 % signalé', async () => {
    fauxServeur({ ...reponsesConnecte('direction'), ...reponsesCatalogue() })
    monterApp('/fournisseurs/7')
    const dialogue = await ficheChargee()
    expect(within(dialogue).getByRole('button', { name: 'Supprimer' }).dataset.raison).toContain(
      'Il a des matières du catalogue, des commandes : le désactiver plutôt',
    )
    expect(within(dialogue).getByText(/plus de 20 % au-delà du déclaré/)).toBeInTheDocument()
  })

  it('créer ouvre la fiche créée', async () => {
    const appels = fauxServeur({
      ...reponsesConnecte('achats'),
      ...reponsesCatalogue(),
      'POST /fournisseurs': { statut: 201, corps: fournisseurEssai({ id: 9, nom: 'Nouveau' }) },
      'GET /fournisseurs/9': { corps: fournisseurEssai({ id: 9, nom: 'Nouveau' }) },
    })
    const { adresse } = monterApp('/fournisseurs/nouveau?onglet=fiche')
    const dialogue = await ficheChargee()
    const creer = within(dialogue).getByRole('button', { name: 'Créer le fournisseur' })
    expect(creer.dataset.raison).toContain('le nom')
    await userEvent.type(within(dialogue).getByRole('textbox', { name: 'Nom' }), 'Nouveau')
    await userEvent.click(creer)
    await waitFor(() => expect(adresse()).toBe('/fournisseurs/9'))
    expect(appels.find((a) => a.methode === 'POST')?.corps).toMatchObject({
      nom: 'Nouveau',
      delai_jours: 60,
      devise: 'MAD',
    })
  })
})
