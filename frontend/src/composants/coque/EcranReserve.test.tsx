/** Le bandeau d'une adresse refusée ou inconnue, fermable. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { EcranReserve, texteRefus } from './EcranReserve'

describe('EcranReserve', () => {
  it('dit l’écran réservé et l’adresse inconnue', () => {
    expect(texteRefus({ refuse: '/cockpit' })).toBe(
      'L’écran demandé (/cockpit) est réservé à un autre rôle : vous êtes revenu à votre accueil.',
    )
    expect(texteRefus({ inconnue: '/x' })).toBe(
      'L’adresse demandée (/x) n’existe pas : vous êtes revenu à votre accueil.',
    )
    expect(texteRefus(null)).toBeNull()
  })

  it('se ferme ; rien sans refus', async () => {
    const { rerender, container } = render(<EcranReserve etat={{ refuse: '/cockpit' }} />)
    await userEvent.click(screen.getByRole('button', { name: 'Fermer ce message' }))
    expect(screen.queryByRole('alert')).toBeNull()
    rerender(<EcranReserve etat={{ autre: 1 }} />)
    expect(container).toBeEmptyDOMElement()
  })
})
