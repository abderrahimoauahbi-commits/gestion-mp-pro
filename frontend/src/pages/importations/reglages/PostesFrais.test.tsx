/**
 * Réglages › Postes de frais : la direction écrit, les achats lisent ; la fenêtre s'ouvre et se
 * ferme par l'adresse ; « Enregistrer » dit pourquoi il est grisé ; un changement de clé est dit
 * d'avance, envoie la nature lue et le toast dit les dossiers ouverts recalculés et clos figés ;
 * un poste système ne se supprime pas (raison) ; le code se contrôle à la frappe.
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
} from '../../../essais/monter'
import type { Role } from '../../../lib/types'
import type { PosteFiche } from '../types'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

function poste(id: number, code: string, libelle: string, autres: Partial<PosteFiche> = {}): PosteFiche {
  return {
    id,
    code,
    libelle,
    recuperable: false,
    nature: 'autre',
    entre_valeur_douane: false,
    cle: 'valeur',
    ordre: id,
    systeme: false,
    frais_ouverts: 0,
    frais_clos: 0,
    dossiers_ouverts: 0,
    dossiers_clos: 0,
    utilise: false,
    version: 1,
    parts_figees: null,
    ...autres,
  }
}

const POSTES: PosteFiche[] = [
  poste(4, 'PORT', 'Port Med', {
    ordre: 3,
    frais_ouverts: 3,
    frais_clos: 2,
    dossiers_ouverts: 2,
    dossiers_clos: 1,
    utilise: true,
    version: 4,
  }),
  poste(1, 'DD', 'Droits de douane', { ordre: 0, nature: 'droits', systeme: true }),
  poste(3, 'TVA', 'TVA à l’importation', { ordre: 2, nature: 'tva', recuperable: true, systeme: true }),
  poste(9, 'MANUT', 'Manutention', { ordre: 3 }),
]

function serveur(role: Role, autres = {}) {
  return fauxServeur({ ...reponsesConnecte(role), 'GET /postes-frais': { corps: POSTES }, ...autres })
}

describe('Postes de frais', () => {
  it('la direction a « Nouveau poste » ; liste triée par ordre puis code, badge « calculs »', async () => {
    serveur('direction')
    monterApp('/reglages?onglet=postes')
    const tableau = await screen.findByRole('table', { name: 'Postes de frais' })
    expect(screen.getByRole('button', { name: 'Nouveau poste' })).toBeInTheDocument()
    const codes = within(tableau)
      .getAllByRole('row')
      .slice(1)
      .map((r) => r.querySelectorAll('td')[1]?.textContent)
    expect(codes).toEqual(['DDcalculs', 'TVAcalculs', 'MANUT', 'PORT'])
    expect(within(tableau).getAllByText('calculs')[0]).toHaveAttribute(
      'title',
      'Lu par les calculs du dossier (TVA attendue) : il ne se supprime pas et garde sa nature',
    )
    expect(within(tableau).getByText('récupérable, hors coût')).toBeInTheDocument()
  })

  it('la recherche affine à la frappe sur le code et le libellé', async () => {
    serveur('direction')
    monterApp('/reglages?onglet=postes')
    await screen.findByRole('table', { name: 'Postes de frais' })
    await userEvent.type(screen.getByRole('searchbox'), 'manu')
    expect(screen.queryByText('Port Med')).not.toBeInTheDocument()
    expect(screen.getByText('Manutention')).toBeInTheDocument()
    await userEvent.type(screen.getByRole('searchbox'), 'zzz')
    expect(screen.getByText('Aucun poste ne correspond.')).toBeInTheDocument()
  })

  it('les achats lisent : pas de « Nouveau poste », fenêtre sans geste d’écriture', async () => {
    serveur('achats')
    const app = monterApp('/reglages?onglet=postes')
    await userEvent.click(await screen.findByText('Port Med'))
    const fenetre = await screen.findByRole('dialog', { name: 'Poste PORT — Port Med' })
    expect(app.adresse()).toBe('/reglages?onglet=postes&poste=4')
    expect(screen.queryByRole('button', { name: 'Nouveau poste' })).not.toBeInTheDocument()
    expect(within(fenetre).queryByRole('button', { name: 'Enregistrer' })).not.toBeInTheDocument()
    expect(within(fenetre).queryByRole('button', { name: 'Supprimer' })).not.toBeInTheDocument()
    expect(within(fenetre).queryByRole('textbox')).not.toBeInTheDocument()
    expect(within(fenetre).getByText('à la valeur')).toBeInTheDocument()
    expect(within(fenetre).getAllByRole('button', { name: 'Fermer' })).toHaveLength(2)
  })

  it('l’adresse ouvre la fenêtre ; « Fermer » retire le paramètre et garde l’onglet', async () => {
    serveur('direction')
    const app = monterApp('/reglages?onglet=postes&poste=4')
    const fenetre = await screen.findByRole('dialog', { name: 'Poste PORT — Port Med' })
    const enregistrer = within(fenetre).getByRole('button', { name: 'Enregistrer' })
    expect(enregistrer).toBeDisabled()
    expect(enregistrer.dataset.raison).toContain('Rien n’a changé')
    const [, fermer] = within(fenetre).getAllByRole('button', { name: 'Fermer' })
    if (!fermer) throw new Error('« Fermer » absent du pied')
    await userEvent.click(fermer)
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(app.adresse()).toBe('/reglages?onglet=postes')
  })

  it('changer la clé : message d’avance, PUT avec la nature lue, toast des dossiers figés', async () => {
    const appels = serveur('direction', {
      'PUT /postes-frais/4': { corps: { ...POSTES[0], cle: 'poids', version: 5, parts_figees: 1 } },
    })
    monterApp('/reglages?onglet=postes&poste=4')
    const fenetre = await screen.findByRole('dialog', { name: 'Poste PORT — Port Med' })
    await userEvent.click(within(fenetre).getByRole('radio', { name: 'au poids' }))
    expect(
      within(fenetre).getByText(
        'Les 2 dossier(s) ouvert(s) seront recalculés au poids. Les 1 dossier(s) clos gardent leur coût : leurs frais de ce poste seront éclatés sur leurs marchandises, à la valeur (c’est tracé).',
      ),
    ).toBeInTheDocument()
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(appels.some((a) => a.methode === 'PUT')).toBe(true))
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toEqual({
      libelle: 'Port Med',
      recuperable: false,
      cle: 'poids',
      ordre: 3,
      nature: 'autre',
      entre_valeur_douane: false,
      version: 4,
    })
    expect(
      await screen.findByText(
        /2 dossier\(s\) ouvert\(s\) recalculé\(s\) ; 1 dossier\(s\) clos gardent leur coût/,
      ),
    ).toBeInTheDocument()
  })

  it('un poste système : suppression grisée avec sa raison, nature figée dite', async () => {
    serveur('direction')
    monterApp('/reglages?onglet=postes&poste=1')
    const fenetre = await screen.findByRole('dialog', { name: 'Poste DD — Droits de douane' })
    const supprimer = within(fenetre).getByRole('button', { name: 'Supprimer' })
    expect(supprimer).toBeDisabled()
    expect(supprimer.dataset.raison).toContain('Ce poste sert aux calculs du dossier : il ne se supprime pas')
    expect(
      within(fenetre).getByText('Nature figée : les calculs du dossier lisent ce poste ainsi.'),
    ).toBeTruthy()
    expect(within(fenetre).queryByRole('switch')).not.toBeInTheDocument()
  })

  it('un poste libre se supprime après « Oui, supprimer » ; la fenêtre se ferme', async () => {
    const appels = serveur('direction', { 'DELETE /postes-frais/9': { statut: 204 } })
    const app = monterApp('/reglages?onglet=postes&poste=9')
    const fenetre = await screen.findByRole('dialog', { name: 'Poste MANUT — Manutention' })
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Supprimer' }))
    expect(within(fenetre).getByText('Supprimer ce poste ?')).toBeInTheDocument()
    await userEvent.click(within(fenetre).getByRole('button', { name: 'Oui, supprimer' }))
    await waitFor(() => expect(app.adresse()).toBe('/reglages?onglet=postes'))
    expect(appels.find((a) => a.methode === 'DELETE')?.chemin).toBe('/postes-frais/9?version=1')
    expect(await screen.findByText('Poste MANUT supprimé.')).toBeInTheDocument()
  })

  it('nouveau poste : code contrôlé à la frappe, puis POST en capitales', async () => {
    const appels = serveur('direction', {
      'POST /postes-frais': { statut: 201, corps: poste(12, 'TRANSIT', 'x') },
    })
    monterApp('/reglages?onglet=postes')
    await userEvent.click(await screen.findByRole('button', { name: 'Nouveau poste' }))
    const fenetre = await screen.findByRole('dialog', { name: 'Nouveau poste de frais' })
    const creer = within(fenetre).getByRole('button', { name: 'Créer le poste' })
    expect(creer.dataset.raison).toContain('À renseigner : Code, Libellé')
    await userEvent.type(within(fenetre).getByRole('textbox', { name: /Code/ }), 'tr-1')
    expect(within(fenetre).getAllByText(/Le code d’un poste : lettres, chiffres ou « _ »/)[0]).toBeVisible()
    await userEvent.clear(within(fenetre).getByRole('textbox', { name: /Code/ }))
    await userEvent.type(within(fenetre).getByRole('textbox', { name: /Code/ }), 'transit')
    await userEvent.type(within(fenetre).getByRole('textbox', { name: /Libellé/ }), 'Transitaire')
    await userEvent.click(creer)
    await waitFor(() =>
      expect(appels.some((a) => a.methode === 'POST' && a.chemin === '/postes-frais')).toBe(true),
    )
    expect(appels.find((a) => a.chemin === '/postes-frais' && a.methode === 'POST')?.corps).toEqual({
      code: 'TRANSIT',
      libelle: 'Transitaire',
      recuperable: false,
      cle: 'valeur',
      ordre: null,
      nature: 'autre',
      entre_valeur_douane: false,
    })
  })
})
