/** Essais d'Erreur : « Pas de réseau » distinct d'un refus, « Réessayer ». */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ErreurApi, PAS_DE_RESEAU } from '../../lib/api'
import { Erreur, estPasDeReseau } from './Erreur'

describe('Erreur', () => {
  it('dit « Pas de réseau » quand le serveur n’a pas répondu, et relit au clic', async () => {
    const relire = vi.fn()
    render(<Erreur erreur={new ErreurApi(PAS_DE_RESEAU, 0, 'pas_de_reseau')} onReessayer={relire} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Pas de réseau')
    expect(screen.getByRole('alert')).toHaveTextContent('vérifiez le Wi-Fi ou la 4G/5G')
    await userEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(relire).toHaveBeenCalled()
  })

  it('un refus du serveur est dit tel quel ; rien sans erreur', () => {
    const { rerender, container } = render(
      <Erreur erreur={new ErreurApi('Commande introuvable.', 404, 'introuvable')} />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Commande introuvable.')
    expect(estPasDeReseau(new ErreurApi('x', 502, 'serveur_absent'))).toBe(true)
    rerender(<Erreur erreur={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})
