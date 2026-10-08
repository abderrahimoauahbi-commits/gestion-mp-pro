/** Essais de SelecteurMatiere : critères cumulés et liés, recherche, choix. */
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { SelecteurMatiere, type MatiereChoix } from './SelecteurMatiere'

const MATIERES: MatiereChoix[] = [
  {
    id: 1,
    reference: 'PP FRZ-2900 Red',
    composition: 'PP',
    couleur: 'Rouge',
    fournisseur: 'HASIRCI',
    titrage: '2900',
  },
  {
    id: 2,
    reference: 'PP FRZ-2900 Beige',
    composition: 'PP',
    couleur: 'Beige',
    fournisseur: 'HASIRCI',
    titrage: '2900',
  },
  {
    id: 3,
    reference: 'PES 1500 Rouge',
    composition: 'PES',
    couleur: 'Rouge',
    fournisseur: 'BELKA',
    titrage: '1500',
  },
]

describe('SelecteurMatiere', () => {
  it('choisir un fournisseur réduit les autres critères à ses matières (M75)', async () => {
    render(<SelecteurMatiere matieres={MATIERES} valeur={null} onChange={() => {}} />)
    expect(screen.getByText('3 matières')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Fournisseur' }), 'HASIRCI')
    const compo = within(screen.getByRole('combobox', { name: 'Composition' }))
    expect(compo.queryByRole('option', { name: /PES/ })).toBeNull()
    expect(compo.getByRole('option', { name: 'PP (2)' })).toBeInTheDocument()
    expect(screen.getByText('2 matières')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Effacer les critères' }))
    expect(screen.getByText('3 matières')).toBeInTheDocument()
  })

  it('la recherche affine sur les critères cachés et rend la matière choisie', async () => {
    const vu = vi.fn()
    render(
      <SelecteurMatiere matieres={MATIERES} valeur={null} onChange={vu} criteres={{ couleur: 'Rouge' }} />,
    )
    const champ = screen.getByRole('combobox', { name: 'Matière' })
    await userEvent.type(champ, 'pes{Enter}')
    expect(vu).toHaveBeenCalledWith(3, MATIERES[2])
  })
})
