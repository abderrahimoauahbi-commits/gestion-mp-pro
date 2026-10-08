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
