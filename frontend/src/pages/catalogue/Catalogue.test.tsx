/**
 * La page du catalogue dans l'application entière : liste des matières par rôle (l'alimentation
 * sans aucun prix), filtres et état dans l'adresse, anciennes adresses, fiche à adresse stable.
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
import { adresseNouvelle, ouvertDe } from './Catalogue'
import { reponsesCatalogue } from './donneesEssai'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const MONETAIRE = /\b(USD|MAD|EUR)\b|[Pp]rix|[Cc]oût|[Mm]ontant/

describe('Catalogue', () => {
  it('lit l’adresse : fiche ouverte, tableur, anciennes adresses de Gestion MP', () => {
    expect(ouvertDe('/matieres/12')).toEqual({ genre: 'matiere', id: 12 })
    expect(ouvertDe('/matieres/nouvelle')).toEqual({ genre: 'matiere', id: null })
    expect(ouvertDe('/fournisseurs/nouveau')).toEqual({ genre: 'fournisseur', id: null })
    expect(ouvertDe('/catalogue/tableur')).toEqual({ genre: 'tableur' })
    expect(adresseNouvelle(new URLSearchParams('matiere=12'))).toBe('/matieres/12')
    expect(adresseNouvelle(new URLSearchParams('onglet=fournisseurs&fournisseur=3'))).toBe('/fournisseurs/3')
    expect(adresseNouvelle(new URLSearchParams('fournisseur_filtre=3'))).toBe('/catalogue?fournisseur=3')
    expect(adresseNouvelle(new URLSearchParams('onglet=matieres&fournisseur=3'))).toBeNull()
  })

  it('direction : les matières actives, leur prix, les gestes ; compteurs des onglets', async () => {
    fauxServeur({ ...reponsesConnecte('direction'), ...reponsesCatalogue() })
    monterApp('/catalogue')
    const tableau = await screen.findByRole('table', { name: 'Matières du catalogue' })
    expect(within(tableau).getByText('PP FRZ-2900 Dtex-Rouge 7001')).toBeInTheDocument()
    expect(within(tableau).queryByText('CUIR NAT 40')).toBeNull()
    expect(within(tableau).getByText('2,50 USD / kg')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Nouvelle matière' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Classification/ })).toHaveTextContent('Classification4') // valeurs actives seulement (P7-27)
  })

  it('alimentation : aucun prix ni geste d’écriture, ni onglet réservé', async () => {
    fauxServeur({ ...reponsesConnecte('alimentation'), ...reponsesCatalogue() })
    monterApp('/catalogue')
    await screen.findByRole('table', { name: 'Matières du catalogue' })
    expect(document.querySelector('main')?.textContent).not.toMatch(MONETAIRE)
    expect(screen.queryByRole('button', { name: 'Nouvelle matière' })).toBeNull()
    expect(screen.queryByRole('tab', { name: /Fournisseurs/ })).toBeNull()
  })

  it('l’état « Désactivées » est un critère ; « Effacer les filtres » remet tout, état compris (P7-31)', async () => {
    fauxServeur({ ...reponsesConnecte('achats'), ...reponsesCatalogue() })
    const { adresse } = monterApp('/catalogue?role=5')
    const tableau = await screen.findByRole('table', { name: 'Matières du catalogue' })
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'État' }), 'desactivees')
    await waitFor(() => expect(within(tableau).getByText('CUIR NAT 40')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: 'Effacer les filtres' }))
    await waitFor(() => expect(adresse()).toBe('/catalogue'))
    expect(within(tableau).queryByText('CUIR NAT 40')).toBeNull()
  })

  it('une ligne ouvre la fiche à son adresse ; fermer rend la liste avec ses filtres', async () => {
    fauxServeur({ ...reponsesConnecte('direction'), ...reponsesCatalogue() })
    const { adresse } = monterApp('/catalogue?q=rouge')
    await userEvent.click(await screen.findByText('PP FRZ-2900 Dtex-Rouge 7001'))
    await waitFor(() => expect(adresse()).toBe('/matieres/12?q=rouge'))
    expect(await screen.findByText(/modifiée le .* par Nadia/)).toBeInTheDocument()
    const fiche = screen.getByRole('dialog')
    await userEvent.click(within(fiche).getAllByRole('button', { name: 'Fermer' }).at(-1)!)
    await waitFor(() => expect(adresse()).toBe('/catalogue?q=rouge'))
  })

  it('l’ancienne adresse ?matiere=12 ouvre la fiche', async () => {
    fauxServeur({ ...reponsesConnecte('direction'), ...reponsesCatalogue() })
    const { adresse } = monterApp('/catalogue?matiere=12')
    await waitFor(() => expect(adresse()).toBe('/matieres/12'))
  })
})
