/**
 * « Qualités et recettes » dans l'application entière : indicateurs sur la base des qualités en
 * service, alimentation sans coût ni prix, fiche enregistrée en une requête avec l'avertissement
 * du serveur, conflit rechargeable, retour à une version avec un motif exigé, onglet de la liste
 * gardé sous la fiche.
 */
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fauxServeur,
  monterApp,
  prechargerPages,
  reponsesConnecte,
  stockageMemoire,
} from '../../essais/monter'
import { qualiteEssai, reponsesQualites } from './donneesEssai'
import { synthese } from './indicateurs'
import { BadgeRecette } from './OngletQualites'
import { ficheDe } from './Qualites'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

const MONETAIRE = /\b(USD|MAD|EUR)\b|[Pp]rix|[Cc]oût|[Mm]ontant/

async function ficheChargee() {
  await waitFor(() => expect(screen.getByRole('dialog').textContent).not.toMatch(/Un instant/))
  return screen.getByRole('dialog')
}

describe('Qualités', () => {
  it('le badge d’une recette dit de créer la matière d’un rôle que nul fil du catalogue ne porte', () => {
    const q = qualiteEssai({
      poids: [
        { role_id: 1, role: 'Poil', lineaire: false, poids: 1.2 },
        { role_id: 6, role: 'Franges', lineaire: true, poids: 0.8 },
        { role_id: 5, role: 'Cuir', lineaire: true, poids: 2 },
      ],
      controle: {
        roles_utilises: 3,
        roles_conformes: 1,
        conforme: false,
        ecarts: [
          { role: 'Franges', somme: 0, sans_matiere: true },
          { role: 'Cuir', somme: 90, sans_matiere: false },
        ],
      },
    })
    render(<BadgeRecette q={q} />)
    expect(screen.getByText('créer la matière Franges · Cuir 90,0 %')).toBeInTheDocument()
  })

  it('synthèse sur les qualités en service ; arrêtées à part', () => {
    const s = synthese([
      qualiteEssai(),
      qualiteEssai({
        id: 3,
        code: 'B',
        actif: false,
        controle: {
          roles_utilises: 1,
          roles_conformes: 0,
          ecarts: [{ role: 'Poil', somme: 90, sans_matiere: false }],
          conforme: false,
        },
      }),
      qualiteEssai({ id: 4, code: 'C', base_mensuelle: 800, cout_m2_mad: 20, recette: [] }),
    ])
    expect(s).toMatchObject({
      fabriquees: 2,
      arretees: 1,
      incompletes: ['C'],
      incompletesArretees: 1,
      planMensuel: 2000,
    })
    expect(s.coutMoyen).toBeCloseTo((38.22 * 1200 + 20 * 800) / 2000)
    expect(ficheDe('/qualites/12')).toBe(12)
    expect(ficheDe('/qualites/nouvelle')).toBe('nouvelle')
  })

  it('alimentation : lit les qualités, la nomenclature et la fiche sans coût ni prix', async () => {
    fauxServeur({ ...reponsesConnecte('alimentation'), ...reponsesQualites() })
    const { routeur } = monterApp('/qualites')
    await screen.findByRole('table', { name: 'Qualités' })
    expect(document.querySelector('main')?.textContent).not.toMatch(MONETAIRE)
    expect(screen.queryByRole('button', { name: 'Nouvelle qualité' })).toBeNull()
    await routeur.navigate('/qualites?onglet=nomenclature')
    await screen.findByRole('table', { name: 'Nomenclature' })
    expect(document.querySelector('main')?.textContent).not.toMatch(MONETAIRE)
    await routeur.navigate('/qualites/2')
    const fiche = await ficheChargee()
    expect(fiche.textContent).not.toMatch(MONETAIRE)
    expect(
      within(fiche).getByText('Lecture seule : seule la direction modifie les qualités et les recettes.'),
    ).toBeInTheDocument()
    expect(within(fiche).getAllByRole('button', { name: 'Fermer' })).toHaveLength(2)
  })

  it('la nomenclature ouvre la qualité et la referme sur la nomenclature', async () => {
    fauxServeur({ ...reponsesConnecte('achats'), ...reponsesQualites() })
    const { adresse } = monterApp('/qualites?onglet=nomenclature')
    const tableau = await screen.findByRole('table', { name: 'Nomenclature' })
    await userEvent.click(within(tableau).getByText('CUIR NAT 40'))
    await waitFor(() => expect(adresse()).toBe('/qualites/2?liste=nomenclature'))
    const fiche = await ficheChargee()
    await userEvent.click(within(fiche).getAllByRole('button', { name: 'Fermer' }).at(-1)!)
    await waitFor(() => expect(adresse()).toBe('/qualites?onglet=nomenclature'))
  })

  it('direction : fiche et recette en une requête, avertissement du serveur dit', async () => {
    const appels = fauxServeur({
      ...reponsesConnecte('direction'),
      ...reponsesQualites(),
      'PUT /qualites/2': {
        corps: qualiteEssai({
          version: 6,
          avertissement: 'Qualité arrêtée : recette enregistrée telle quelle.',
        }),
      },
    })
    monterApp('/qualites/2')
    const fiche = await ficheChargee()
    const part = within(fiche).getByRole('textbox', { name: 'Part de PP FRZ-2900 Dtex-Rouge 7001' })
    await userEvent.clear(part)
    await userEvent.type(part, '90')
    expect(within(fiche).getByText('À corriger avant d’enregistrer : Poil.')).toBeInTheDocument()
    expect(within(fiche).getByText(/il manque 10,00 %/)).toBeInTheDocument()
    await userEvent.clear(part)
    await userEvent.type(part, '100')
    await userEvent.clear(within(fiche).getByRole('textbox', { name: 'Nom' }))
    await userEvent.type(within(fiche).getByRole('textbox', { name: 'Nom' }), 'Atlas')
    await userEvent.click(within(fiche).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(appels.filter((a) => a.methode === 'PUT')).toHaveLength(1))
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toMatchObject({
      nom: 'Atlas',
      version: 5,
      recette: null,
    })
    expect(await screen.findByText(/Qualité enregistrée/)).toBeInTheDocument()
    expect(await screen.findByText('Qualité arrêtée : recette enregistrée telle quelle.')).toBeInTheDocument()
  })

  it('409 : « Recharger la qualité »', async () => {
    fauxServeur({
      ...reponsesConnecte('direction'),
      ...reponsesQualites(),
      'PUT /qualites/2': {
        statut: 409,
        corps: {
          detail:
            'Cette qualité a été modifiée entre-temps par Nadia (08/10/2026 09:00) : rouvrez-la pour repartir de sa dernière version.',
          code: 'conflit_version',
        },
      },
    })
    monterApp('/qualites/2')
    const fiche = await ficheChargee()
    await userEvent.type(within(fiche).getByRole('textbox', { name: 'Nom' }), ' bis')
    await userEvent.click(within(fiche).getByRole('button', { name: 'Enregistrer' }))
    expect(await within(fiche).findByText(/modifiée entre-temps par Nadia/)).toBeInTheDocument()
    expect(within(fiche).getByRole('button', { name: 'Recharger la qualité' })).toBeInTheDocument()
  })

  it('revenir à une version : motif exigé, envoyé avec la version de la qualité', async () => {
    const appels = fauxServeur({
      ...reponsesConnecte('direction'),
      ...reponsesQualites(),
      'POST /qualites/2/versions/2/restaurer': { corps: qualiteEssai({ version: 6 }) },
    })
    monterApp('/qualites/2?onglet=versions')
    await ficheChargee()
    await userEvent.click(await screen.findByRole('button', { name: 'Revenir à cette version' }))
    const oui = screen.getByRole('button', { name: 'Oui, revenir à cette version' })
    expect(oui.dataset.raison).toBe('À renseigner : le motif.')
    await userEvent.type(screen.getByRole('textbox', { name: 'Motif (obligatoire)' }), 'erreur de saisie')
    await userEvent.click(oui)
    await waitFor(() => expect(appels.some((a) => a.methode === 'POST')).toBe(true))
    expect(appels.find((a) => a.methode === 'POST')?.corps).toEqual({ motif: 'erreur de saisie', version: 5 })
    expect(await screen.findByText(/Recette revenue à cette version/)).toBeInTheDocument()
  })
})
