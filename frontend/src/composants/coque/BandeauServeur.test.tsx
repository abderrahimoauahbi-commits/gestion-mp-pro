/** Le bandeau du serveur : l'alerte du serveur (direction, administrateur) en rouge ; la base d'essai pour tous. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { BandeauServeur, phrasesServeur } from './BandeauServeur'

describe('BandeauServeur', () => {
  it('dit l’alerte du serveur en rouge, et la base d’essai', () => {
    expect(phrasesServeur('La dernière sauvegarde date de 30 h.')).toEqual([
      { ton: 'critique', texte: 'La dernière sauvegarde date de 30 h.' },
    ])
    expect(phrasesServeur(null, true)[0]?.ton).toBe('info')
    expect(phrasesServeur('  ', false)).toEqual([])
  })

  it('rien sans alerte ; la base d’essai se dit', () => {
    const { container, rerender } = render(<BandeauServeur alerte={null} />)
    expect(container).toBeEmptyDOMElement()
    rerender(<BandeauServeur alerte={null} baseEssai />)
    expect(screen.getByRole('status')).toHaveTextContent('Base d’essai')
  })
})
