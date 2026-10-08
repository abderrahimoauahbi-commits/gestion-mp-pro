/** Essais de la fenêtre : garde de saisie (`sale`), pile et Échap, focus, page dessous figée. */
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { Fenetre, QUESTION_ABANDON, useFermerFenetre } from './Fenetre'
import { profondeur, saisieEnCours } from './pile'

function BoutonAnnuler() {
  const fermer = useFermerFenetre()
  return (
    <button type="button" onClick={fermer}>
      Annuler
    </button>
  )
}

describe('Fenetre — garde de saisie', () => {
  it('sans saisie, Échap ferme tout de suite', async () => {
    const fermer = vi.fn()
    render(
      <Fenetre titre="Fiche" onFermer={fermer}>
        <p>corps</p>
      </Fenetre>,
    )
    expect(screen.getByRole('dialog', { name: 'Fiche' })).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(fermer).toHaveBeenCalledTimes(1)
  })

  it('avec `sale`, ×, Échap, le voile et « Annuler » demandent d’abord', async () => {
    const fermer = vi.fn()
    const { container } = render(
      <Fenetre titre="Saisie" onFermer={fermer} sale>
        <input aria-label="Quantité" />
        <BoutonAnnuler />
      </Fenetre>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Fermer' }))
    expect(screen.getByRole('alert')).toHaveTextContent(QUESTION_ABANDON)
    expect(fermer).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Non, continuer la saisie' }))
    expect(screen.queryByRole('alert')).toBeNull()

    await userEvent.keyboard('{Escape}')
    expect(screen.getByRole('alert')).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('alert')).toBeNull()

    const voile = container.firstElementChild
    if (!voile) throw new Error('voile absent')
    fireEvent.mouseDown(voile)
    expect(screen.getByRole('alert')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Non, continuer la saisie' }))

    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(screen.getByRole('alert')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Oui, abandonner' }))
    expect(fermer).toHaveBeenCalledTimes(1)
  })

  it('une saisie en cours retient la fermeture de l’onglet du navigateur', () => {
    const { rerender, unmount } = render(
      <Fenetre titre="Saisie" onFermer={() => {}} sale>
        x
      </Fenetre>,
    )
    expect(saisieEnCours()).toBe(true)
    const evenement = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(evenement)
    expect(evenement.defaultPrevented).toBe(true)
    rerender(
      <Fenetre titre="Saisie" onFermer={() => {}}>
        x
      </Fenetre>,
    )
    expect(saisieEnCours()).toBe(false)
    unmount()
  })
})

function Pile() {
  const [deux, setDeux] = useState(true)
  const [une, setUne] = useState(true)
  return une ? (
    <Fenetre titre="Commande" onFermer={() => setUne(false)}>
      <input aria-label="Référence" />
      {deux ? (
        <Fenetre titre="Réception" onFermer={() => setDeux(false)}>
          <input aria-label="Lot" />
        </Fenetre>
      ) : null}
    </Fenetre>
  ) : (
    <p>liste</p>
  )
}

describe('Fenetre — pile', () => {
  it('Échap ne ferme que la fenêtre du dessus, puis la suivante', async () => {
    render(<Pile />)
    expect(profondeur()).toBe(2)
    expect(document.body.style.overflow).toBe('hidden')
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog', { name: 'Réception' })).toBeNull()
    expect(screen.getByRole('dialog', { name: 'Commande' })).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(screen.getByText('liste')).toBeInTheDocument()
    expect(profondeur()).toBe(0)
    expect(document.body.style.overflow).toBe('')
  })

  it('le focus entre dans la fenêtre, y tourne, et revient d’où il venait', async () => {
    function Essai() {
      const [ouverte, setOuverte] = useState(false)
      return (
        <>
          <button type="button" onClick={() => setOuverte(true)}>
            Ouvrir
          </button>
          {ouverte ? (
            <Fenetre
              titre="Fiche"
              onFermer={() => setOuverte(false)}
              pied={<button type="button">Enregistrer</button>}
            >
              <input aria-label="Nom" />
            </Fenetre>
          ) : null}
        </>
      )
    }
    render(<Essai />)
    await userEvent.click(screen.getByRole('button', { name: 'Ouvrir' }))
    expect(screen.getByRole('textbox', { name: 'Nom' })).toHaveFocus()
    screen.getByRole('button', { name: 'Enregistrer' }).focus()
    await userEvent.tab()
    expect(screen.getByRole('button', { name: 'Fermer' })).toHaveFocus()
    await userEvent.keyboard('{Escape}')
    expect(screen.getByRole('button', { name: 'Ouvrir' })).toHaveFocus()
  })

  it('useFermerFenetre hors d’une fenêtre est une erreur de construction', () => {
    const erreur = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<BoutonAnnuler />)).toThrow('useFermerFenetre hors d’une Fenetre.')
    erreur.mockRestore()
  })
})
