/** Essais du Selecteur : recherche multi-mots sans accents sur champs cachés, clavier, Échap. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { Fenetre } from '../mise-en-page/Fenetre'
import { Champ } from './Champ'
import { filtrerOptions, Selecteur, type OptionSelecteur } from './Selecteur'

const MATIERES: OptionSelecteur[] = [
  { id: 1, titre: 'IMP FRISÉ ROUGE 2900', sous: 'HASIRCI', groupe: 'Polypropylène', recherche: 'C5N red' },
  { id: 2, titre: 'IMP FRISÉ BEIGE 2900', sous: 'HASIRCI', groupe: 'Polypropylène' },
  { id: 3, titre: 'Coton écru 8/2', sous: 'FILATURE DU NORD', groupe: 'Coton' },
]

function Essai({ surChange = () => {} }: { surChange?: (id: number | null) => void }) {
  const [v, setV] = useState<number | null>(null)
  return (
    <Champ libelle="Matière">
      <Selecteur
        valeur={v}
        options={MATIERES}
        onChange={(id) => {
          setV(id)
          surChange(id)
        }}
      />
    </Champ>
  )
}

describe('Selecteur', () => {
  it('filtre à la frappe : plusieurs mots, sans accents, champs cachés compris', () => {
    expect(filtrerOptions(MATIERES, 'frise rouge').map((o) => o.id)).toEqual([1])
    expect(filtrerOptions(MATIERES, 'red hasi').map((o) => o.id)).toEqual([1])
    expect(filtrerOptions(MATIERES, 'ecru').map((o) => o.id)).toEqual([3])
    expect(filtrerOptions(MATIERES, '').length).toBe(3)
  })

  it('au clavier : ↓ ↓ Entrée choisit, la valeur s’affiche', async () => {
    const vu = vi.fn()
    render(<Essai surChange={vu} />)
    const champ = screen.getByRole('combobox', { name: 'Matière' })
    await userEvent.click(champ)
    expect(champ).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getAllByRole('option')).toHaveLength(3)
    await userEvent.keyboard('{ArrowDown}{ArrowDown}')
    expect(screen.getAllByRole('option')[2]).toHaveAttribute('aria-selected', 'true')
    await userEvent.keyboard('{ArrowDown}{Enter}')
    expect(vu).toHaveBeenCalledWith(3)
    expect(champ).toHaveValue('Coton écru 8/2')
    expect(champ).toHaveAttribute('aria-expanded', 'false')
  })

  it('Entrée choisit le résultat unique ; « Rien ne correspond. » sinon', async () => {
    const vu = vi.fn()
    render(<Essai surChange={vu} />)
    await userEvent.type(screen.getByRole('combobox'), 'zzz')
    expect(screen.getByText('Rien ne correspond.')).toBeInTheDocument()
    await userEvent.clear(screen.getByRole('combobox'))
    await userEvent.type(screen.getByRole('combobox'), 'beige{Enter}')
    expect(vu).toHaveBeenCalledWith(2)
  })

  it('Échap ferme la liste sans fermer la fenêtre ; un second Échap la ferme', async () => {
    const fermer = vi.fn()
    render(
      <Fenetre titre="Ligne" onFermer={fermer}>
        <Essai />
      </Fenetre>,
    )
    const champ = screen.getByRole('combobox')
    expect(champ).toHaveFocus()
    expect(champ).toHaveAttribute('aria-expanded', 'true')
    await userEvent.keyboard('{Escape}')
    expect(champ).toHaveAttribute('aria-expanded', 'false')
    expect(fermer).not.toHaveBeenCalled()
    await userEvent.keyboard('{Escape}')
    expect(fermer).toHaveBeenCalledTimes(1)
  })

  it('la souris choisit ; « — Aucun — » efface ; les groupes ont leur titre', async () => {
    const vu = vi.fn()
    render(<Essai surChange={vu} />)
    await userEvent.click(screen.getByRole('combobox'))
    expect(screen.getByText('Coton')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('option', { name: /BEIGE/ }))
    expect(vu).toHaveBeenLastCalledWith(2)
    await userEvent.click(screen.getByRole('combobox'))
    await userEvent.click(screen.getByRole('option', { name: '— Aucun —' }))
    expect(vu).toHaveBeenLastCalledWith(null)
  })
})
