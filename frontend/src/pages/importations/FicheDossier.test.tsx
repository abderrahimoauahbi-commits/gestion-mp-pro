/**
 * La fiche d'un dossier : clôture confirmée dans une `FenetreConfirmation` qui énumère les alertes du
 * serveur (et les relit sur un refus `confirmation_requise`), boutons grisés avec la raison du
 * serveur, frais réglé intouchable, montant vidé rétabli avec son message, ligne d'ajout,
 * annulation au motif exigé, réouverture, volets présents selon le dossier.
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { donnees, serveurImportations, type Donnees } from './essaiImportations'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const fenetre = () => screen.getByRole('dialog')

function ouvrir(d: Donnees, volet = '', autres = {}) {
  const appels = serveurImportations('achats', d, autres)
  const app = monterApp(`/dossiers/${d.fiche.id}${volet ? `?onglet=${volet}` : ''}`)
  return { appels, app }
}

describe('Fiche dossier › clôture', () => {
  it('la confirmation énumère les alertes du serveur et envoie alertes_lues', async () => {
    const d = donnees()
    const close = { ...d.fiche, statut: 'clos', clos_le: '2026-10-09T11:07:00+01:00' }
    const { appels } = ouvrir(d, '', { [`POST /dossiers/${d.fiche.id}/cloturer`]: { corps: close } })
    await userEvent.click(await screen.findByRole('button', { name: 'Clôturer le dossier' }))
    const alertes = await screen.findByRole('list', { name: 'Alertes du dossier' })
    expect(
      within(alertes)
        .getAllByRole('listitem')
        .map((li) => li.textContent),
    ).toEqual(d.fiche.alertes)
    await userEvent.click(screen.getByRole('button', { name: 'Oui, clôturer' }))
    await waitFor(() => expect(screen.getByText('Dossier clôturé : son coût est figé.')).toBeInTheDocument())
    const post = appels.find((a) => a.chemin.endsWith('/cloturer'))
    expect(post?.corps).toEqual({ version: d.fiche.version, alertes_lues: true })
  })

  it('un refus confirmation_requise relit la fiche et garde la fenêtre ouverte', async () => {
    const d = donnees()
    const { appels } = ouvrir(d, '', {
      [`POST /dossiers/${d.fiche.id}/cloturer`]: {
        statut: 422,
        corps: {
          detail: 'Clore ce dossier se confirme après lecture de ses alertes : TVA ≠ attendue.',
          code: 'confirmation_requise',
        },
      },
    })
    await userEvent.click(await screen.findByRole('button', { name: 'Clôturer le dossier' }))
    const lectures = () =>
      appels.filter((a) => a.methode === 'GET' && a.chemin === `/dossiers/${d.fiche.id}`).length
    const avant = lectures()
    await userEvent.click(screen.getByRole('button', { name: 'Oui, clôturer' }))
    expect(await screen.findByText(/se confirme après lecture de ses alertes/)).toBeInTheDocument()
    await waitFor(() => expect(lectures()).toBeGreaterThan(avant))
    expect(screen.getByRole('button', { name: 'Oui, clôturer' })).toBeInTheDocument()
  })

  it('« Clôturer » est grisé avec la raison du serveur', async () => {
    const d = donnees()
    d.fiche.actions.cloturer = 'Un dossier sans marchandise n’a rien à clore.'
    ouvrir(d)
    const bouton = await screen.findByRole('button', { name: 'Clôturer le dossier' })
    expect(bouton).toBeDisabled()
    expect(bouton.dataset.raison).toBe('Sera refusé : Un dossier sans marchandise n’a rien à clore.')
  })

  it('un dossier clos se rouvre avec un motif facultatif ; les volets de saisie disparaissent', async () => {
    const d = donnees()
    Object.assign(d.fiche, { statut: 'clos', clos_le: '2026-10-09T11:07:00+01:00' })
    d.fiche.actions.rouvrir = null
    const { appels } = ouvrir(d, 'frais', {
      [`POST /dossiers/${d.fiche.id}/rouvrir`]: { corps: { ...d.fiche, statut: 'ouvert' } },
    })
    expect(await screen.findByText(/Clos le 09\/10\/2026/)).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Ajouter un frais' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Montant du frais/)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Rouvrir pour corriger' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Motif (facultatif)' }), 'transit en retard')
    await userEvent.click(screen.getByRole('button', { name: 'Oui, rouvrir' }))
    await waitFor(() =>
      expect(appels.find((a) => a.chemin.endsWith('/rouvrir'))?.corps).toEqual({
        version: d.fiche.version,
        motif: 'transit en retard',
      }),
    )
  })
})

describe('Fiche dossier › frais', () => {
  it('un frais réglé garde poste, montant, marchandise et ne se retire pas (raison dite)', async () => {
    const d = donnees()
    const [f] = d.fiche.frais
    if (!f) throw new Error('données')
    f.payee_le = '2026-10-01'
    f.blocage = 'Frais réglé le 01/10/2026 : annuler d’abord le règlement (Analyse › Échéancier)'
    ouvrir(d, 'frais')
    expect(await screen.findByText('réglé le 01/10/2026')).toBeInTheDocument()
    expect(screen.queryByLabelText(`Montant du frais ${f.libelle}`)).not.toBeInTheDocument()
    const ligne = screen.getByText(f.libelle, { selector: 'span' }).closest('tr')
    if (!ligne) throw new Error('ligne')
    const retirer = within(ligne).getByRole('button', { name: 'Retirer' })
    expect(retirer).toBeDisabled()
    expect(retirer.dataset.raison).toContain('annuler d’abord le règlement')
  })

  it('un montant vidé revient, avec son message, sans rien envoyer', async () => {
    const d = donnees()
    const [, f] = d.fiche.frais
    if (!f) throw new Error('données')
    const { appels } = ouvrir(d, 'frais')
    const champ = await screen.findByLabelText(`Montant du frais ${f.libelle}`)
    await userEvent.clear(champ)
    await userEvent.tab()
    expect(
      await screen.findByText('Un frais a un montant : pour l’enlever, « Retirer ».'),
    ).toBeInTheDocument()
    expect(appels.some((a) => a.methode === 'PUT')).toBe(false)
    expect((champ as HTMLInputElement).value.replace(/\s/g, '')).toBe('4200')
  })

  it('la ligne d’ajout dit ce qui manque, envoie le frais, et rend la fenêtre « sale » entre-temps', async () => {
    const d = donnees()
    const { appels } = ouvrir(d, 'frais', { [`POST /dossiers/${d.fiche.id}/frais`]: { corps: d.fiche } })
    const ajouter = await screen.findByRole('button', { name: 'Ajouter' })
    expect(ajouter.dataset.raison).toBe('À renseigner : Montant.')
    const ajout = screen.getByLabelText('Ajouter un frais')
    await userEvent.type(within(ajout).getByPlaceholderText('avoir : négatif'), '-150')
    expect(screen.getByRole('tab', { name: /Frais/ }).textContent).toContain('•')
    await userEvent.click(ajouter)
    await waitFor(() => expect(appels.some((a) => a.chemin.endsWith('/frais'))).toBe(true))
    expect(appels.find((a) => a.chemin.endsWith('/frais'))?.corps).toMatchObject({
      version: d.fiche.version,
      poste_id: d.postes[0]?.id,
      montant: -150,
      ligne_id: null,
    })
  })
})

describe('Fiche dossier › annulation et volets', () => {
  it('« Annuler le dossier » exige un motif et dit ce que deviennent facture et frais', async () => {
    const d = donnees()
    const { appels } = ouvrir(d, '', {
      [`POST /dossiers/${d.fiche.id}/annuler`]: { corps: { ...d.fiche, statut: 'annule' } },
    })
    await userEvent.click(await screen.findByRole('button', { name: 'Modifier l’en-tête' }))
    await userEvent.click(within(fenetre()).getByRole('button', { name: 'Annuler le dossier' }))
    expect(
      screen.getByText(/Il garde son numéro\. La facture .* attendra de nouveau son dossier\. 2 frais/),
    ).toBeInTheDocument()
    const oui = screen.getByRole('button', { name: 'Oui, annuler le dossier' })
    expect(oui.dataset.raison).toBe('À renseigner : le motif.')
    await userEvent.type(screen.getByRole('textbox', { name: 'Motif (obligatoire)' }), 'erreur de facture')
    await userEvent.click(oui)
    await waitFor(() =>
      expect(appels.find((a) => a.chemin.endsWith('/annuler'))?.corps).toEqual({
        version: d.fiche.version,
        motif: 'erreur de facture',
      }),
    )
  })

  it('volets : pas de second camion sans facture qui attend ; la saisie à la main pour un dossier à la main vide', async () => {
    const d = donnees()
    ouvrir(d, 'facture')
    expect(await screen.findByRole('tab', { name: /famille/i })).toHaveAttribute('aria-selected', 'true')
    expect(screen.queryByRole('tab', { name: /Second camion/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /Saisie à la main/ })).not.toBeInTheDocument()
  })

  it('un dossier à la main encore vide s’ouvre sur sa saisie', async () => {
    const d = donnees()
    Object.assign(d.fiche, { a_la_main: true, facture: null, lignes: [], familles: [] })
    ouvrir(d)
    expect(await screen.findByRole('tab', { name: /Saisie à la main/ })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByRole('button', { name: 'Ajouter au dossier' }).dataset.raison).toContain(
      'À renseigner : Matière, Poids, Valeur',
    )
  })
})
