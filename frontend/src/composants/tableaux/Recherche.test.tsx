/** Essais de la recherche : focus gardé à la frappe, Échap efface sans fermer la fenêtre. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { Fenetre } from '../mise-en-page/Fenetre'
import { Recherche } from './Recherche'

function Essai() {
  const [q, setQ] = useState('')
  return (
    <>
      <Recherche valeur={q} onChange={setQ} />
      <ul>
        {['IMP FRISÉ ROUGE', 'Coton']
          .filter((x) => x.toLowerCase().includes(q.toLowerCase()))
          .map((x) => (
            <li key={x}>{x}</li>
          ))}
      </ul>
    </>
  )
}

describe('Recherche', () => {
  it('garde le focus pendant que la liste se refait', async () => {
    render(<Essai />)
    const champ = screen.getByRole('searchbox', { name: 'Rechercher' })
    await userEvent.type(champ, 'coton')
    expect(champ).toHaveFocus()
    expect(screen.getAllByRole('listitem')).toHaveLength(1)
  })

  it('Échap efface une recherche posée sans fermer la fenêtre ; vide, il la ferme', async () => {
    const fermer = vi.fn()
    render(
      <Fenetre titre="Choix" onFermer={fermer}>
        <Essai />
      </Fenetre>,
    )
    const champ = screen.getByRole('searchbox')
    await userEvent.type(champ, 'rouge')
    await userEvent.keyboard('{Escape}')
    expect(champ).toHaveValue('')
    expect(fermer).not.toHaveBeenCalled()
    await userEvent.keyboard('{Escape}')
    expect(fermer).toHaveBeenCalled()
  })
})
