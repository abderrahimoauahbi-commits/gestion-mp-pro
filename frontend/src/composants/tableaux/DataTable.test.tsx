/**
 * Essais du DataTable : tri numérique puis naturel, recherche multi-mots sans accents sur champs
 * cachés (focus gardé), filtres liés, « Effacer les filtres », export avec la vue, totaux sans
 * mélange d'unités, ligne cliquable, listes vides.
 */
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { kg as enKg } from '../../lib/format'
import type { Colonne } from './colonnes'
import { DataTable, type DataTableProps } from './DataTable'
import { useEtatTableAdresse } from './etatAdresse'
import type { Filtre } from './filtrage'

interface Lot {
  id: number
  numero: string
  matiere: string
  fournisseur: string
  couleur: string
  reste: number | null
  unite: 'kg' | 'ml'
  code: string
}

const LOTS: Lot[] = [
  {
    id: 1,
    numero: 'LOT-10',
    matiere: 'IMP FRISÉ ROUGE',
    fournisseur: 'HASIRCI',
    couleur: 'Rouge',
    reste: 120.5,
    unite: 'kg',
    code: 'C5N',
  },
  {
    id: 2,
    numero: 'LOT-9',
    matiere: 'IMP FRISÉ BEIGE',
    fournisseur: 'HASIRCI',
    couleur: 'Beige',
    reste: 9,
    unite: 'kg',
    code: 'B12',
  },
  {
    id: 3,
    numero: 'LOT-100',
    matiere: 'Cuir naturel',
    fournisseur: 'TANNERIE FÈS',
    couleur: 'Camel',
    reste: 1.9,
    unite: 'ml',
    code: 'CU1',
  },
  {
    id: 4,
    numero: 'LOT-2',
    matiere: 'Coton écru',
    fournisseur: 'FILATURE DU NORD',
    couleur: 'Écru',
    reste: null,
    unite: 'kg',
    code: 'CO8',
  },
]

const COLONNES: Colonne<Lot>[] = [
  { cle: 'numero', titre: 'Lot' },
  { cle: 'matiere', titre: 'Matière', recherche: (l) => [l.code] },
  { cle: 'fournisseur', titre: 'Fournisseur' },
  {
    cle: 'reste',
    titre: 'Reste',
    droite: true,
    unite: (l) => l.unite,
    total: true,
    rendu: (l) => (l.reste == null ? '—' : `${l.reste} ${l.unite}`),
  },
]

const FILTRES: Filtre<Lot>[] = [
  { cle: 'fournisseur', libelle: 'Fournisseur', valeur: (l) => l.fournisseur },
  { cle: 'couleur', libelle: 'Couleur', valeur: (l) => l.couleur },
]

function monter(props: Partial<DataTableProps<Lot>> = {}) {
  return render(
    <MemoryRouter>
      <DataTable
        lignes={LOTS}
        colonnes={COLONNES}
        cle={(l) => l.id}
        filtres={FILTRES}
        libelle="Lots"
        {...props}
      />
    </MemoryRouter>,
  )
}

const premiereColonne = () =>
  within(screen.getByRole('table', { name: 'Lots' }))
    .getAllByRole('row')
    .slice(1, -1)
    .map((r) => r.querySelector('td')?.textContent)

describe('DataTable — tri', () => {
  it('naturel sur le texte : LOT-2, LOT-9, LOT-10, LOT-100 ; puis décroissant ; puis sans tri', async () => {
    monter()
    const entete = screen.getByRole('columnheader', { name: 'Lot' })
    await userEvent.click(entete)
    expect(premiereColonne()).toEqual(['LOT-2', 'LOT-9', 'LOT-10', 'LOT-100'])
    expect(entete).toHaveAttribute('aria-sort', 'ascending')
    await userEvent.click(entete)
    expect(premiereColonne()).toEqual(['LOT-100', 'LOT-10', 'LOT-9', 'LOT-2'])
    await userEvent.click(entete)
    expect(premiereColonne()).toEqual(['LOT-10', 'LOT-9', 'LOT-100', 'LOT-2'])
    expect(entete).not.toHaveAttribute('aria-sort')
  })

  it('numérique sur les nombres (9 avant 120,5), les vides toujours à la fin ; au clavier', async () => {
    monter()
    const entete = screen.getByRole('columnheader', { name: 'Reste' })
    entete.focus()
    await userEvent.keyboard('{Enter}')
    expect(premiereColonne()).toEqual(['LOT-100', 'LOT-9', 'LOT-10', 'LOT-2'])
    await userEvent.keyboard('{Enter}')
    expect(premiereColonne()).toEqual(['LOT-10', 'LOT-9', 'LOT-100', 'LOT-2'])
  })
})

describe('DataTable — recherche', () => {
  it('plusieurs mots, sans accents, dans n’importe quel ordre, champs cachés compris', async () => {
    monter({ rechercheCachee: (l) => [l.couleur] })
    const champ = screen.getByRole('searchbox', { name: 'Rechercher' })
    await userEvent.type(champ, 'rouge frise')
    expect(premiereColonne()).toEqual(['LOT-10'])
    await userEvent.clear(champ)
    await userEvent.type(champ, 'c5n')
    expect(premiereColonne()).toEqual(['LOT-10'])
    await userEvent.clear(champ)
    await userEvent.type(champ, 'fes camel')
    expect(premiereColonne()).toEqual(['LOT-100'])
    expect(screen.getByText('1 / 4')).toBeInTheDocument()
    await userEvent.clear(champ)
    await userEvent.type(champ, 'zzz')
    expect(screen.getByText('Aucune ligne ne répond à ces critères.')).toBeInTheDocument()
  })

  it('dans l’adresse, la recherche garde le focus pendant la frappe et s’écrit dans ?q=', async () => {
    function Ecran() {
      const etat = useEtatTableAdresse(['fournisseur', 'couleur'])
      const { search } = useLocation()
      return (
        <>
          <DataTable lignes={LOTS} colonnes={COLONNES} cle={(l) => l.id} filtres={FILTRES} {...etat} />
          <output>{search}</output>
        </>
      )
    }
    render(
      <MemoryRouter initialEntries={['/stock?onglet=lots']}>
        <Ecran />
      </MemoryRouter>,
    )
    const champ = screen.getByRole('searchbox')
    await userEvent.type(champ, 'frise rouge')
    expect(champ).toHaveFocus()
    expect(champ).toHaveValue('frise rouge')
    expect(screen.getByRole('status')).toHaveTextContent('?onglet=lots&q=frise+rouge')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Fournisseur' }), 'HASIRCI')
    await userEvent.click(screen.getByRole('button', { name: 'Effacer les filtres' }))
    expect(screen.getByRole('status')).toHaveTextContent('?onglet=lots')
    expect(screen.getByRole('status')).not.toHaveTextContent('q=')
    expect(champ).toHaveValue('')
  })
})

describe('DataTable — filtres', () => {
  it('liés : choisir un fournisseur ne propose plus que ses couleurs, avec leur nombre', async () => {
    monter()
    const couleur = screen.getByRole('combobox', { name: 'Couleur' })
    expect(within(couleur).getAllByRole('option')).toHaveLength(5)
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Fournisseur' }), 'HASIRCI')
    expect(
      within(couleur)
        .getAllByRole('option')
        .map((o) => o.textContent),
    ).toEqual(['Couleur : tous', 'Beige (1)', 'Rouge (1)'])
    expect(screen.getByText('1 critère')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Effacer les filtres' })).toBeNull()
    await userEvent.selectOptions(couleur, 'Rouge')
    expect(premiereColonne()).toEqual(['LOT-10'])
    expect(screen.getByText('2 critères')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Effacer les filtres' }))
    expect(premiereColonne()).toHaveLength(4)
    expect(screen.queryByText(/critère/)).toBeNull()
  })
})

describe('DataTable — export et totaux', () => {
  it('l’export emporte l’onglet, la recherche et les filtres', async () => {
    monter({ exporter: { route: '/export/lots', parametres: { onglet: 'lots' } } })
    await userEvent.type(screen.getByRole('searchbox'), 'frisé')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Fournisseur' }), 'HASIRCI')
    const lien = screen.getByRole('link', { name: 'Exporter en Excel' })
    const adresse = new URL(lien.getAttribute('href') ?? '', 'http://x')
    expect(adresse.pathname).toBe('/api/export/lots')
    expect(Object.fromEntries(adresse.searchParams)).toEqual({
      onglet: 'lots',
      q: 'frisé',
      fournisseur: 'HASIRCI',
    })
  })

  it('les totaux ne mélangent jamais les unités : kg et ml côte à côte, sur les lignes affichées', async () => {
    monter()
    const pied = () => screen.getAllByRole('row').at(-1)
    expect(pied()).toHaveTextContent(`Total${enKg(129.5)} · 1,9\u00a0ml`.replace(/\u00a0/g, ' '))
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Fournisseur' }), 'HASIRCI')
    expect(pied()?.textContent).toBe(`Total${enKg(129.5)}`)
  })

  it('deux devises ne s’additionnent pas', () => {
    type Ligne = { id: number; montant: number; devise: string }
    render(
      <MemoryRouter>
        <DataTable<Ligne>
          lignes={[
            { id: 1, montant: 61888, devise: 'USD' },
            { id: 2, montant: 53132, devise: 'EUR' },
            { id: 3, montant: 112, devise: 'USD' },
          ]}
          colonnes={[{ cle: 'montant', titre: 'Montant', droite: true, unite: (l) => l.devise, total: true }]}
          cle={(l) => l.id}
        />
      </MemoryRouter>,
    )
    expect(screen.getAllByRole('row').at(-1)?.textContent).toBe('62\u00a0000\u00a0USD · 53\u00a0132\u00a0EUR')
  })
})

describe('DataTable — lignes et vides', () => {
  it('une ligne cliquable s’ouvre au clic et à Entrée ; une cellule-lien mène à son adresse', async () => {
    const ouvrir = vi.fn()
    monter({
      cliquable: ouvrir,
      colonnes: [{ ...COLONNES[0]!, lien: (l) => `/lots/${l.id}` }, ...COLONNES.slice(1)],
    })
    await userEvent.click(screen.getByText('IMP FRISÉ BEIGE'))
    expect(ouvrir).toHaveBeenCalledWith(LOTS[1])
    const ligne = screen.getByText('Cuir naturel').closest('tr')
    ligne?.focus()
    await userEvent.keyboard('{Enter}')
    expect(ouvrir).toHaveBeenLastCalledWith(LOTS[2])
    expect(screen.getByRole('link', { name: 'LOT-9' })).toHaveAttribute('href', '/lots/2')
  })

  it('une liste vide dit pourquoi ; le compteur dit le total du serveur', () => {
    const { unmount } = monter({ lignes: [], vide: 'Aucun lot dans ce magasin.' })
    expect(screen.getByText('Aucun lot dans ce magasin.')).toBeInTheDocument()
    unmount()
    monter({ serveur: true, total: 12345, chargerPlus: { charges: 4, total: 12345, onCharger: () => {} } })
    expect(screen.getByText('4 / 12 345')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Charger les 500 suivants' })).toBeInTheDocument()
  })
})

describe('DataTable — vide filtré et lignes de groupe', () => {
  it('une recherche qui ne trouve rien dit le texte de la page (videFiltre)', async () => {
    monter({
      videFiltre: 'Aucun lot ne correspond : la recherche porte sur le n°, la matière, le fournisseur.',
    })
    await userEvent.type(screen.getByRole('searchbox'), 'introuvable')
    expect(
      screen.getByText('Aucun lot ne correspond : la recherche porte sur le n°, la matière, le fournisseur.'),
    ).toBeInTheDocument()
  })

  it('une ligne d’en-tête avant chaque suite de lignes de même clé, avec les lignes du groupe', () => {
    monter({
      filtres: [],
      groupe: {
        cle: (l) => l.fournisseur,
        entete: (cle, lignes) => `${cle} : ${lignes.length} lot(s)`,
      },
      triInitial: { cle: 'fournisseur', sens: 1 },
    })
    const table = screen.getByRole('table', { name: 'Lots' })
    const entetes = within(table)
      .getAllByRole('rowheader')
      .map((c) => c.textContent)
    const fournisseurs = [...new Set(LOTS.map((l) => l.fournisseur))].sort()
    expect(entetes).toEqual(
      fournisseurs.map((f) => `${f} : ${LOTS.filter((l) => l.fournisseur === f).length} lot(s)`),
    )
    expect(within(table).getAllByRole('rowheader')[0]).toHaveAttribute('colspan', String(COLONNES.length))
  })
})

describe('DataTable — tableau large (douze mois)', () => {
  it('« serre » et « figee » : cellules resserrées, première colonne figée, débordement dit au cadre', () => {
    monter({ serre: true, figee: true })
    const table = screen.getByRole('table', { name: 'Lots' })
    expect(table).toHaveClass('table', 'serre', 'figee')
    const cadre = table.parentElement
    expect(cadre).toHaveClass('horizontal')
    expect(cadre?.parentElement).toHaveClass('enveloppe')
  })

  it('sans ces options, ni classe ni enveloppe : les autres listes ne changent pas', () => {
    monter()
    const table = screen.getByRole('table', { name: 'Lots' })
    expect(table).not.toHaveClass('serre')
    expect(table).not.toHaveClass('figee')
    expect(table.parentElement).not.toHaveClass('horizontal')
    expect(table.parentElement?.parentElement).not.toHaveClass('enveloppe')
  })
})
