/** Essais de FenetreConfirmation : motif exigé, « J'ai compris », fermeture après réussite. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { FenetreConfirmation } from './FenetreConfirmation'

describe('FenetreConfirmation', () => {
  it('la restauration exige « J’ai compris » : le bouton grisé le dit', async () => {
    const oui = vi.fn()
    const fermer = vi.fn()
    render(
      <FenetreConfirmation
        titre="Restaurer la sauvegarde du 07/10/2026 03:00"
        texte="Toutes les données saisies depuis seront remplacées."
        oui="Restaurer cette sauvegarde"
        variante="danger"
        caseJaiCompris="J’ai compris : les données actuelles seront remplacées."
        onOui={oui}
        onFermer={fermer}
      />,
    )
    const bouton = screen.getByRole('button', { name: 'Restaurer cette sauvegarde' })
    expect(bouton).toBeDisabled()
    expect(bouton).toHaveAttribute('data-raison', 'Cochez « J’ai compris » pour continuer.')
    await userEvent.click(screen.getByRole('checkbox', { name: /J’ai compris/ }))
    await userEvent.click(bouton)
    expect(oui).toHaveBeenCalledWith('')
    expect(fermer).toHaveBeenCalled()
  })

  it('la clôture de période exige un motif ; un motif tapé protège la fenêtre', async () => {
    const oui = vi.fn()
    const fermer = vi.fn()
    render(
      <FenetreConfirmation
        titre="Clore la période jusqu’au 30/09/2026"
        texte="Les mouvements jusqu’à cette date ne pourront plus être modifiés."
        oui="Clore la période"
        motif="exige"
        onOui={oui}
        onFermer={fermer}
      />,
    )
    const bouton = screen.getByRole('button', { name: 'Clore la période' })
    expect(bouton).toHaveAttribute('data-raison', 'À renseigner : le motif.')
    await userEvent.type(screen.getByRole('textbox', { name: /Motif/ }), 'Clôture mensuelle')
    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Les abandonner ?')
    await userEvent.click(screen.getByRole('button', { name: 'Non, continuer la saisie' }))
    await userEvent.click(bouton)
    expect(oui).toHaveBeenCalledWith('Clôture mensuelle')
    expect(fermer).toHaveBeenCalledTimes(1)
  })
})

describe('FenetreConfirmation à étapes', () => {
  it('une lecture d’abord (« Continuer » après « J’ai compris »), puis le mot et le motif, puis l’issue suivie sur place', async () => {
    const oui = vi.fn()
    const fermer = vi.fn()
    const { rerender } = render(
      <FenetreConfirmation
        titre="Restaurer"
        etapes={[{ texte: 'Tout ce qui a été saisi depuis disparaîtra.', caseJaiCompris: 'J’ai compris.' }]}
        texte="Dernière confirmation."
        mot="RESTAURER"
        motif="exige"
        motifMin={3}
        oui="Restaurer maintenant"
        fermerApres={false}
        onOui={oui}
        onFermer={fermer}
      />,
    )
    const dialogue = screen.getByRole('dialog')
    expect(screen.getByText('Tout ce qui a été saisi depuis disparaîtra.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Restaurer maintenant' })).not.toBeInTheDocument()
    const continuer = screen.getByRole('button', { name: 'Continuer' })
    expect(continuer).toHaveAttribute('data-raison', 'Cochez « J’ai compris » pour continuer.')
    await userEvent.click(screen.getByRole('checkbox', { name: 'J’ai compris.' }))
    await userEvent.click(continuer)
    expect(screen.getByText('Dernière confirmation.')).toBeInTheDocument()
    const bouton = screen.getByRole('button', { name: 'Restaurer maintenant' })
    expect(bouton).toHaveAttribute(
      'data-raison',
      'À renseigner : le mot RESTAURER, un motif de 3 caractères au moins.',
    )
    await userEvent.type(screen.getByRole('textbox', { name: /Taper RESTAURER/ }), 'restaurer')
    await userEvent.type(screen.getByRole('textbox', { name: /Motif/ }), 'Essai')
    await userEvent.click(bouton)
    expect(oui).toHaveBeenCalledWith('Essai', 'restaurer')
    expect(fermer).not.toHaveBeenCalled()
    // L'issue suivie dans la même fenêtre : non fermable pendant l'opération, puis « Fermer ».
    const props = {
      titre: 'Restaurer',
      texte: '',
      oui: 'Restaurer maintenant',
      onOui: oui,
      onFermer: fermer,
    }
    rerender(<FenetreConfirmation {...props} issue={{ corps: 'En cours…', fermable: false }} />)
    expect(screen.getByRole('dialog')).toBe(dialogue)
    await userEvent.keyboard('{Escape}')
    expect(fermer).not.toHaveBeenCalled()
    rerender(<FenetreConfirmation {...props} issue={{ corps: 'Faite.', fermable: true }} />)
    // Le « Fermer » du pied (le × de la fenêtre porte le même nom).
    await userEvent.click(screen.getAllByRole('button', { name: 'Fermer' }).at(-1)!)
    expect(fermer).toHaveBeenCalled()
  })
})
