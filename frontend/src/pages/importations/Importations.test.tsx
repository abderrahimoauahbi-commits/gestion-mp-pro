/**
 * Importations (liste, attente, nouveau dossier) : indicateurs sur tous les dossiers, frais non
 * répartis à part avec chaque dossier ouvrable, onglets et filtres dans l'adresse, pied « Total des
 * N dossiers affichés », ouverture d'un dossier depuis sa facture (fournisseur marocain confirmé),
 * second camion bloqué sur un dossier clos, saisie à la main qui exige sa date et garde la fenêtre.
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { donnees, serveurImportations } from './essaiImportations'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

describe('Importations › listes', () => {
  it('indicateurs sur tous les dossiers ; frais non répartis à part, chaque dossier en lien', async () => {
    const d = donnees()
    const [ouvert] = d.dossiers.filter((x) => x.statut === 'ouvert')
    if (!ouvert) throw new Error('données')
    ouvert.charges_non_reparties_mad = 1234
    serveurImportations('achats', d)
    monterApp('/importations')
    expect(await screen.findByText('Dossiers', { selector: 'span' })).toBeInTheDocument()
    expect(screen.getByLabelText('Tous les dossiers, ouverts et clos (hors annulés)')).toBeInTheDocument()
    const [resume] = await screen.findAllByText(/non répartis$/, { selector: 'summary' })
    await userEvent.click(resume!)
    const liste = screen.getByRole('list', { name: 'Dossiers aux frais non répartis' })
    expect(within(liste).getByRole('link', { name: ouvert.numero })).toHaveAttribute(
      'href',
      `/dossiers/${ouvert.id}`,
    )
    // La ligne de la liste dit aussi ses non répartis, en rouge, à part du coût.
    expect(await screen.findByText(/\+ 1 234,00 MAD non répartis/)).toBeInTheDocument()
  })

  it('onglets, recherche et filtre dans l’adresse ; pied « Total des N dossiers affichés »', async () => {
    const d = donnees()
    const clos = d.dossiers.find((x) => x.statut === 'clos')
    if (!clos) throw new Error('données')
    d.dossiers.push({ ...clos, id: 99, numero: '09/25', libelle: 'Autre camion' })
    serveurImportations('achats', d)
    const app = monterApp('/importations')
    await userEvent.click(await screen.findByRole('tab', { name: /Dossiers clos/ }))
    expect(app.adresse()).toBe('/importations?onglet=clos')
    expect(await screen.findByText('Total des 2 dossiers affichés')).toBeInTheDocument()
    await userEvent.type(screen.getByPlaceholderText(/Numéro, libellé, facture/), 'autre')
    await waitFor(() => expect(app.adresse()).toBe('/importations?onglet=clos&q=autre'))
    expect(screen.queryByText(/Total des/)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Annulés' }))
    await waitFor(() => expect(app.adresse()).toContain('etat=annules'))
    expect(await screen.findByText('Aucun dossier ne correspond à la recherche.')).toBeInTheDocument()
  })

  it('une ligne ouvre la fiche à son adresse ; la fermer rend la liste avec ses filtres', async () => {
    const d = donnees()
    serveurImportations('direction', d)
    const app = monterApp('/importations?q=FA')
    await userEvent.click(await screen.findByText(d.fiche.numero, { selector: 'strong' }))
    await waitFor(() => expect(app.adresse()).toBe(`/dossiers/${d.fiche.id}`))
    // La fenêtre peut être rendue deux fois (fiche relue) : attendre la version stable.
    const fermer = await waitFor(() => {
      const boutons = within(screen.getByRole('dialog')).getAllByRole('button', { name: 'Fermer' })
      expect(boutons[1]).toBeInTheDocument()
      return boutons[1]!
    })
    await userEvent.click(fermer)
    await waitFor(() => expect(app.adresse()).toBe('/importations?q=FA'))
  })
})

describe('Importations › en attente et nouveau dossier', () => {
  it('la bascule et la case des marocains vont dans l’adresse ; « Ouvrir son dossier » ouvre la fiche', async () => {
    const d = donnees()
    const appels = serveurImportations('achats', d, {
      'POST /dossiers': { statut: 201, corps: d.fiche },
    })
    const app = monterApp('/importations?onglet=rattacher')
    await userEvent.click(await screen.findByRole('button', { name: /Réceptions sans facture/ }))
    expect(app.adresse()).toBe('/importations?onglet=rattacher&vue=receptions')
    await userEvent.click(screen.getByRole('button', { name: /Factures reçues/ }))
    await userEvent.click(screen.getByRole('switch'))
    await waitFor(() => expect(app.adresse()).toContain('locaux=1'))
    const [premier] = await screen.findAllByRole('button', { name: 'Ouvrir son dossier' })
    await userEvent.click(premier!)
    await waitFor(() => expect(app.adresse()).toBe(`/dossiers/${d.fiche.id}`))
    const post = appels.find((a) => a.methode === 'POST')
    expect(post?.corps).toEqual({ facture_id: d.attente.factures[0]?.facture_id, local_confirme: false })
  })

  it('un fournisseur marocain se confirme sur la ligne et part avec local_confirme', async () => {
    const d = donnees()
    const f = d.attente.factures[0]
    if (!f) throw new Error('données')
    f.local = true
    const appels = serveurImportations('achats', d, { 'POST /dossiers': { statut: 201, corps: d.fiche } })
    monterApp('/dossiers/nouveau')
    const [bouton] = await screen.findAllByRole('button', { name: 'Ouvrir son dossier' })
    await userEvent.click(bouton!)
    expect(
      screen.getByText(/est un fournisseur marocain : ni douane, ni fret international/),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Oui, l’ouvrir' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'POST')).toBe(true))
    expect(appels.find((a) => a.methode === 'POST')?.corps).toMatchObject({ local_confirme: true })
  })

  it('le second camion d’un dossier clos est bloqué avec sa raison', async () => {
    const d = donnees()
    const clos = d.dossiers.find((x) => x.statut === 'clos')
    const f = d.attente.factures[0]
    if (!clos || !f) throw new Error('données')
    f.dossier_id = clos.id
    f.dossier = clos.numero
    serveurImportations('achats', d)
    monterApp('/importations?onglet=rattacher')
    const bouton = await screen.findByRole('button', { name: `Ajouter au dossier ${clos.numero}` })
    expect(bouton).toBeDisabled()
    expect(bouton.dataset.raison).toContain('est clos : le rouvrir d’abord')
  })

  it('à la main : la date d’arrivée manque, la saisie garde la fenêtre et survit aux onglets', async () => {
    const d = donnees()
    serveurImportations('achats', d)
    const app = monterApp('/dossiers/nouveau?onglet=main')
    const ouvrir = await screen.findByRole('button', { name: 'Ouvrir le dossier à saisir à la main' })
    expect(ouvrir.dataset.raison).toBe('À renseigner : la date d’arrivée.')
    await userEvent.type(screen.getByRole('textbox', { name: 'Libellé' }), 'Ancien conteneur')
    await userEvent.click(screen.getByRole('tab', { name: /Depuis la facture/ }))
    await userEvent.click(screen.getByRole('tab', { name: /mise en service|À la main/ }))
    expect(screen.getByRole('textbox', { name: 'Libellé' })).toHaveValue('Ancien conteneur')
    await userEvent.keyboard('{Escape}')
    expect(
      screen.getByText('Des modifications ne sont pas enregistrées. Les abandonner ?'),
    ).toBeInTheDocument()
    expect(app.adresse()).toBe('/dossiers/nouveau?onglet=main')
  })
})
