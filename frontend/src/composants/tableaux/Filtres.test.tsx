/** Essais des filtres : options liées avec leur nombre, critères comptés, effacement dès deux. */
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { optionsLiees, type Filtre } from './filtrage'
import { criteresPoses, Filtres } from './Filtres'

type Ligne = { statut: string; fournisseur: string }
const LIGNES: Ligne[] = [
  { statut: 'envoyee', fournisseur: 'HASIRCI' },
  { statut: 'confirmee', fournisseur: 'HASIRCI' },
  { statut: 'envoyee', fournisseur: 'BELKA' },
]
const NOMS: Record<string, string> = { envoyee: 'Envoyée', confirmee: 'Confirmée' }
const FILTRES: Filtre<Ligne>[] = [
  { cle: 'statut', libelle: 'Statut', valeur: (l) => l.statut, libelleValeur: (v) => NOMS[v] ?? v },
  { cle: 'fournisseur', libelle: 'Fournisseur', valeur: (l) => l.fournisseur },
]

describe('Filtres', () => {
  it('les options suivent les autres filtres ; la valeur choisie reste proposée', () => {
    expect(optionsLiees(LIGNES, FILTRES, { fournisseur: 'BELKA' }, FILTRES[0]!)).toEqual([
      { valeur: 'envoyee', libelle: 'Envoyée', nombre: 1 },
    ])
    expect(
      optionsLiees(LIGNES, FILTRES, { fournisseur: 'BELKA', statut: 'confirmee' }, FILTRES[0]!).map(
        (o) => o.valeur,
      ),
    ).toEqual(['confirmee', 'envoyee'])
    expect(criteresPoses({ statut: 'envoyee', fournisseur: '' }, true)).toBe(2)
  })

  it('rend les listes, compte les critères et efface dès deux', async () => {
    const choisir = vi.fn()
    const effacer = vi.fn()
    const { rerender } = render(
      <Filtres filtres={FILTRES} lignes={LIGNES} choix={{}} onChoix={choisir} onEffacer={effacer} />,
    )
    const statut = screen.getByRole('combobox', { name: 'Statut' })
    expect(
      within(statut)
        .getAllByRole('option')
        .map((o) => o.textContent),
    ).toEqual(['Statut : tous', 'Confirmée (1)', 'Envoyée (2)'])
    await userEvent.selectOptions(statut, 'envoyee')
    expect(choisir).toHaveBeenCalledWith('statut', 'envoyee')
    rerender(
      <Filtres
        filtres={FILTRES}
        lignes={LIGNES}
        choix={{ statut: 'envoyee' }}
        onChoix={choisir}
        onEffacer={effacer}
        recherchePosee
      />,
    )
    expect(screen.getByText('2 critères')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Effacer les filtres' }))
    expect(effacer).toHaveBeenCalled()
  })
})
