/**
 * Le taux d'un frais (lot TAUX-FRAIS) : le montant proposé suit la base (valeur en douane, plus
 * droits et TPI pour la TVA ; tout le dossier ou une marchandise), jusqu'à ce qu'il soit tapé à la
 * main ; vidé, il revient au calcul. Un frais enregistré rouvert garde son montant ; seul un taux
 * changé le recalcule.
 *
 * Données (`donneesEssai.json`) : deux marchandises de valeur en douane 37 764,51 et 26 075,49 MAD
 * (63 840 au total), des droits de douane de 5 964 MAD (3 528 et 2 436 répartis), un fret de 4 200.
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { donnees, serveurImportations, type Donnees } from './essaiImportations'
import { baseDuTaux, montantAuTaux, noteDuTaux } from './tauxFrais'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const DOUANE = 37764.50704225352 + 26075.49295774648
const DD = 5964

function ouvrir(d: Donnees, autres = {}) {
  const appels = serveurImportations('achats', d, autres)
  monterApp(`/dossiers/${d.fiche.id}?onglet=frais`)
  return appels
}

/** Le texte d'un champ nombre, sans les espaces des milliers. */
const texte = (champ: HTMLElement) => (champ as HTMLInputElement).value.replace(/\s/g, '')

/** La ligne d'ajout, une fois les postes chargés (le premier poste choisi d'office). */
async function ligneAjout() {
  const ajouter = await screen.findByRole('button', { name: 'Ajouter' })
  await waitFor(() => expect(ajouter.dataset.raison).toBe('À renseigner : Montant.'))
  const ajout = screen.getByLabelText('Ajouter un frais')
  const u = userEvent.setup()
  const choisir = async (nom: string, cherche: string) => {
    const liste = within(ajout).getByRole('combobox', { name: nom })
    await u.click(liste)
    await u.clear(liste)
    await u.type(liste, `${cherche}{Enter}`)
  }
  return {
    u,
    ajout,
    taux: within(ajout).getByRole('textbox', { name: 'Taux (%)' }),
    montant: within(ajout).getByRole('textbox', { name: 'Montant (MAD)' }),
    choisir,
  }
}

describe('Frais › taux : la ligne d’ajout', () => {
  it('TVA 20 % sur le dossier : (valeur en douane + droits + TPI) × 20 %, la base dite sous le taux', async () => {
    const d = donnees()
    const appels = ouvrir(d, { [`POST /dossiers/${d.fiche.id}/frais`]: { corps: d.fiche } })
    const l = await ligneAjout()
    await l.choisir('Poste', 'TVA')
    await l.u.type(l.taux, '20')
    const attendu = montantAuTaux(DOUANE + DD, 20)
    expect(attendu).toBe(13960.8)
    expect(texte(l.montant)).toBe('13960,8')
    expect(
      within(l.ajout).getByText(/^20\s%\sde\s69\s804,00\sMAD\s\(valeur en douane \+ droits \+ TPI\)$/),
    ).toBeInTheDocument()
    await l.u.click(screen.getByRole('button', { name: 'Ajouter' }))
    await waitFor(() => expect(appels.some((a) => a.chemin.endsWith('/frais'))).toBe(true))
    expect(appels.find((a) => a.chemin.endsWith('/frais'))?.corps).toMatchObject({
      poste_id: 3,
      taux: 20,
      montant: 13960.8,
      ligne_id: null,
    })
  })

  it('droits 2,5 % sur une seule marchandise : sa valeur en douane × 2,5 %', async () => {
    ouvrir(donnees())
    const l = await ligneAjout()
    await l.choisir('Porte sur', 'ROUGE')
    await l.u.type(l.taux, '2,5')
    expect(texte(l.montant)).toBe('944,11')
    expect(
      within(l.ajout).getByText(/^2,5\s%\sde\s37\s764,51\sMAD\s\(valeur en douane\)$/),
    ).toBeInTheDocument()
  })

  it('un montant tapé à la main ne bouge plus quand le poste change ; vidé, il revient au calcul', async () => {
    ouvrir(donnees())
    const l = await ligneAjout()
    await l.choisir('Poste', 'TVA')
    await l.u.type(l.taux, '20')
    await l.u.clear(l.montant)
    await l.u.type(l.montant, '13961')
    await l.choisir('Poste', 'Fret')
    expect(texte(l.montant)).toBe('13961')
    await l.choisir('Porte sur', 'BLEU')
    expect(texte(l.montant)).toBe('13961')
    await l.u.clear(l.montant)
    await l.u.tab()
    // Fret 20 % de la valeur en douane de la marchandise bleue.
    expect(texte(l.montant)).toBe(String(montantAuTaux(26075.49295774648, 20)).replace('.', ','))
    // Un taux changé ensuite est un geste explicite : il recalcule.
    await l.u.clear(l.montant)
    await l.u.type(l.montant, '100')
    await l.u.clear(l.taux)
    await l.u.type(l.taux, '10')
    expect(texte(l.montant)).toBe('2607,55')
  })
})

describe('Frais › taux : un frais enregistré rouvert', () => {
  function avecTaux() {
    const d = donnees()
    const [dd] = d.fiche.frais
    if (!dd) throw new Error('données')
    Object.assign(dd, { taux: 2.5, montant: 1596.01 })
    const appels = ouvrir(d, { [`PUT /dossiers/${d.fiche.id}/frais/${dd.id}`]: { corps: d.fiche } })
    return { d, dd, appels }
  }

  it('le montant enregistré s’affiche tel quel, sans recalcul ni envoi', async () => {
    const { dd, appels } = avecTaux()
    const montant = await screen.findByLabelText(`Montant du frais ${dd.libelle}`)
    expect(texte(montant)).toBe('1596,01')
    expect(texte(screen.getByLabelText(`Taux du frais ${dd.libelle}`))).toBe('2,5')
    expect(montantAuTaux(DOUANE, 2.5)).toBe(1596)
    expect(appels.some((a) => a.methode === 'PUT')).toBe(false)
  })

  it('changer son taux recalcule le montant et enregistre les deux', async () => {
    const { d, dd, appels } = avecTaux()
    const u = userEvent.setup()
    const taux = await screen.findByLabelText(`Taux du frais ${dd.libelle}`)
    await u.clear(taux)
    await u.type(taux, '3')
    await u.tab()
    await waitFor(() => expect(appels.some((a) => a.methode === 'PUT')).toBe(true))
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toMatchObject({
      version: dd.version,
      poste_id: dd.poste_id,
      taux: 3,
      montant: montantAuTaux(DOUANE, 3),
      ligne_id: null,
    })
    expect(montantAuTaux(DOUANE, 3)).toBe(1915.2)
    expect(d.fiche.frais).toHaveLength(2)
  })

  it('en lecture (dossier clos), la colonne Taux dit « 20 % »', async () => {
    const d = donnees()
    Object.assign(d.fiche, { statut: 'clos', clos_le: '2026-10-09T11:07:00+01:00' })
    const [dd] = d.fiche.frais
    if (!dd) throw new Error('données')
    dd.taux = 20
    ouvrir(d)
    const table = await screen.findByRole('table', { name: /Frais du dossier/ })
    const ligne = within(table).getByText(dd.libelle, { selector: 'span' }).closest('tr')
    if (!ligne) throw new Error('ligne')
    expect(within(ligne).getByText(/^20\s%$/)).toBeInTheDocument()
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((x) => x.textContent?.trim()),
    ).toContain('Taux')
  })
})

describe('Frais › taux : la base', () => {
  it('TVA d’une marchandise : sa valeur en douane et ses parts de droits et de TPI', () => {
    const d = donnees()
    const tva = d.postes.find((p) => p.code === 'TVA')
    const base = baseDuTaux(d.fiche, d.postes, tva, 2)
    expect(base.montant).toBeCloseTo(37764.50704225352 + 3528, 6)
    expect(noteDuTaux(20, base)).toMatch(/^20\s%\sde\s41\s292,51\sMAD \(valeur en douane \+ droits \+ TPI\)$/)
    const fret = d.postes.find((p) => p.code === 'FRET')
    expect(baseDuTaux(d.fiche, d.postes, fret, null).montant).toBeCloseTo(DOUANE, 6)
  })
})
