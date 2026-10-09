/** Essais de l'interrupteur : rôle switch, bascule au clic et au clavier. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { Interrupteur } from './Interrupteur'

describe('Interrupteur', () => {
  it('bascule au clic et à la barre d’espace', async () => {
    function Essai() {
      const [v, setV] = useState(false)
      return <Interrupteur valeur={v} onChange={setV} libelle="Prix du catalogue, à confirmer" />
    }
    render(<Essai />)
    const s = screen.getByRole('switch', { name: 'Prix du catalogue, à confirmer' })
    expect(s).toHaveAttribute('aria-checked', 'false')
    await userEvent.click(s)
    expect(s).toHaveAttribute('aria-checked', 'true')
    s.focus()
    await userEvent.keyboard(' ')
    expect(s).toHaveAttribute('aria-checked', 'false')
  })
})

describe('Interrupteur grisé', () => {
  it('ne se grise qu’avec sa raison (manque, blocages, grise), dite en infobulle et en description', async () => {
    const change = vi.fn()
    render(
      <Interrupteur
        valeur
        onChange={change}
        libelle="récupérable"
        grise="Nature figée : les calculs du dossier lisent ce poste ainsi."
      />,
    )
    const s = screen.getByRole('switch', { name: 'récupérable' })
    expect(s).toBeDisabled()
    expect(s).toHaveAttribute('data-raison', 'Nature figée : les calculs du dossier lisent ce poste ainsi.')
    expect(s).toHaveAccessibleDescription('Nature figée : les calculs du dossier lisent ce poste ainsi.')
    await userEvent.click(s)
    expect(change).not.toHaveBeenCalled()
  })

  it('les blocages du serveur et ce qui manque se disent comme pour un bouton', () => {
    render(
      <Interrupteur
        valeur={false}
        onChange={() => {}}
        libelle="actif"
        manque={['la recette']}
        blocages={['Refusé']}
      />,
    )
    expect(screen.getByRole('switch', { name: 'actif' })).toHaveAttribute(
      'data-raison',
      'À renseigner : la recette. Sera refusé : Refusé.',
    )
  })
})
