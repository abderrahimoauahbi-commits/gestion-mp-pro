/**
 * Fiche dossier › « Factures du dossier » (lot PLUSIEURS-FACTURES, décision du 12/10/2026) : une
 * ligne par facture, « Ajouter une facture » dans une fenêtre qui reprend le choix des factures
 * en attente (POST `/dossiers/{id}/factures` avec la version lue), « Retirer » confirmé (DELETE) ou
 * grisé avec la raison du serveur.
 */
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { monterApp, prechargerPages, stockageMemoire } from '../../essais/monter'
import { donnees, serveurImportations, type Donnees } from './essaiImportations'
import type { FactureDossier } from './types'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

function ouvrir(d: Donnees, autres = {}) {
  const appels = serveurImportations('achats', d, autres)
  monterApp(`/dossiers/${d.fiche.id}`)
  return appels
}

/** Le dossier d'essai avec une seconde facture, d'un autre fournisseur et d'une autre devise. */
function avecDeuxFactures(d: Donnees): FactureDossier {
  const [premiere] = d.fiche.factures
  if (!premiere) throw new Error('données')
  const seconde: FactureDossier = {
    ...premiere,
    id: 77,
    numero: 'IZM-2026-501',
    fournisseur_id: 9,
    fournisseur: 'Izmir Iplik',
    montant: 1200,
    devise: 'EUR',
    receptions: [{ id: 41, numero: 'REC-2026-0041' }],
    lignes: 1,
    ecart: {
      facture: 'IZM-2026-501',
      montant: 1200,
      recu: 1000,
      devise: 'EUR',
      ecart: 200,
      part: 0.2,
      tolerance: 0.02,
      hors_tolerance: true,
    },
    retrait: null,
  }
  d.fiche.factures = [premiere, seconde]
  return seconde
}

const bloc = async () => screen.findByRole('table', { name: 'Factures du dossier' })

describe('Fiche dossier › factures du dossier', () => {
  it('une ligne par facture : numéro, fournisseur, montant dans sa devise, réceptions, rapprochement', async () => {
    const d = donnees()
    const seconde = avecDeuxFactures(d)
    ouvrir(d)
    const table = await bloc()
    const lignes = within(table).getAllByRole('row').slice(1)
    expect(lignes).toHaveLength(2)
    expect(screen.getByText('Factures du dossier (2)')).toBeInTheDocument()
    const ligne = within(table).getByText(seconde.numero).closest('tr')
    if (!ligne) throw new Error('ligne')
    expect(ligne.textContent).toContain('Izmir Iplik')
    expect(ligne.textContent).toMatch(/1\u00a0200,00\u00a0EUR/)
    expect(within(ligne).getByRole('link', { name: 'REC-2026-0041' })).toHaveAttribute(
      'href',
      '/receptions/41',
    )
    expect(ligne.textContent).toMatch(/écart 20,0\u00a0%/)
  })

  it('« Ajouter une facture » : la fenêtre des factures en attente, puis la route 253 avec la version', async () => {
    const d = donnees()
    const [libre] = d.attente.factures
    if (!libre) throw new Error('données')
    const avis =
      `Facture ${libre.numero} : reprise de 1 marchandise au cours du bon BC-2026-0007 (10 MAD pour 1 USD) — ` +
      'le cours payé saisi avant sa sortie ne revient pas (le cours payé à la banque se ressaisit dans ' +
      'l’onglet Marchandises). Dernier cours payé saisi : USD à 10,05.'
    const appels = ouvrir(d, {
      [`POST /dossiers/${d.fiche.id}/factures`]: { corps: { ...d.fiche, avis: [avis] } },
    })
    await bloc()
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter une facture' }))
    const fenetre = await screen.findByRole('dialog', {
      name: `Ajouter une facture au dossier ${d.fiche.numero}`,
    })
    const ligne = (await within(fenetre).findByText(libre.numero)).closest('tr')
    if (!ligne) throw new Error('ligne')
    await userEvent.click(within(ligne).getByRole('button', { name: 'Ajouter au dossier' }))
    await waitFor(() =>
      expect(appels.find((a) => a.methode === 'POST' && a.chemin.endsWith('/factures'))?.corps).toEqual({
        version: d.fiche.version,
        facture_id: libre.facture_id,
        local_confirme: false,
      }),
    )
    expect(
      await screen.findByText(new RegExp(`Facture ${libre.numero} ajoutée au dossier`)),
    ).toBeInTheDocument()
    expect(await screen.findByText(avis)).toBeInTheDocument()
  })

  it('« Ajouter une facture » est grisé avec la raison du serveur', async () => {
    const d = donnees()
    d.fiche.actions.ajouter_facture = 'Ce dossier est clos : le rouvrir pour y toucher (c’est tracé).'
    ouvrir(d)
    await bloc()
    const bouton = screen.getByRole('button', { name: 'Ajouter une facture' })
    expect(bouton).toBeDisabled()
    expect(bouton.dataset.raison).toBe(`Sera refusé : ${d.fiche.actions.ajouter_facture}`)
  })

  it('« Retirer » est grisé avec sa raison quand un frais vise sa marchandise', async () => {
    const d = donnees()
    const seconde = avecDeuxFactures(d)
    seconde.retrait = `1 frais porte(nt) sur une marchandise de la facture ${seconde.numero} : les affecter à tout le dossier (onglet Frais, « Porte sur »), ou les retirer, avant de retirer la facture — sinon ils sortiraient avec elle.`
    ouvrir(d)
    const table = await bloc()
    const ligne = within(table).getByText(seconde.numero).closest('tr')
    if (!ligne) throw new Error('ligne')
    const bouton = within(ligne).getByRole('button', { name: 'Retirer' })
    expect(bouton).toBeDisabled()
    expect(bouton.dataset.raison).toBe(`Sera refusé : ${seconde.retrait}`)
  })

  it('« Retirer » se confirme puis appelle la route 254 avec la version du dossier', async () => {
    const d = donnees()
    const seconde = avecDeuxFactures(d)
    const appels = ouvrir(d, {
      [`DELETE /dossiers/${d.fiche.id}/factures/${seconde.id}`]: { corps: d.fiche },
    })
    const table = await bloc()
    const ligne = within(table).getByText(seconde.numero).closest('tr')
    if (!ligne) throw new Error('ligne')
    await userEvent.click(within(ligne).getByRole('button', { name: 'Retirer' }))
    expect(
      await screen.findByText(/Sa marchandise \(1 ligne\(s\)\) en sort et attendra de nouveau/),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Oui, retirer la facture' }))
    await waitFor(() =>
      expect(appels.find((a) => a.methode === 'DELETE')?.chemin).toBe(
        `/dossiers/${d.fiche.id}/factures/${seconde.id}?version=${d.fiche.version}`,
      ),
    )
  })

  it('l’en-tête cite toutes les factures (le bloc les détaille)', async () => {
    const d = donnees()
    const seconde = avecDeuxFactures(d)
    ouvrir(d)
    const table = await bloc()
    const ailleurs = screen.getAllByText(seconde.numero).filter((x) => !table.contains(x))
    expect(ailleurs).toHaveLength(1)
  })

  it('un dossier saisi à la main n’a pas le bloc des factures', async () => {
    const d = donnees()
    Object.assign(d.fiche, { factures: [], a_la_main: true, receptions: [], pieces: [] })
    ouvrir(d)
    expect(await screen.findByText('Saisi à la main (avant la mise en service)')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Factures du dossier' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter une facture' })).not.toBeInTheDocument()
  })
})
