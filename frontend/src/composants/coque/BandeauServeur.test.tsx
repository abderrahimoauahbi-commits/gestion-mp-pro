/** Le bandeau du serveur : sauvegarde, schéma, HTTPS pour la direction et l'administrateur ; base d'essai pour tous. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { BandeauServeur, phrasesServeur } from './BandeauServeur'

describe('BandeauServeur', () => {
  it('dit la sauvegarde en défaut en rouge à la direction, pas aux achats', () => {
    const alerte = { sauvegarde_en_defaut: true, sauvegarde_age_h: 30 }
    expect(phrasesServeur(alerte, 'direction')).toEqual([
      {
        ton: 'critique',
        texte: 'La dernière sauvegarde date de 30 h : vérifiez Administration › Sauvegardes.',
      },
    ])
    expect(phrasesServeur(alerte, 'achats')).toEqual([])
    expect(
      phrasesServeur({ sauvegarde_en_defaut: true, sauvegarde_age_h: null }, 'administrateur')[0]?.texte,
    ).toMatch(/^Aucune sauvegarde/)
  })

  it('dit la base d’essai à tous ; rien sans alerte', () => {
    const { container, rerender } = render(<BandeauServeur alerte={null} role="alimentation" />)
    expect(container).toBeEmptyDOMElement()
    rerender(<BandeauServeur alerte={{ schema_en_retard: true }} role="alimentation" baseEssai />)
    expect(screen.getByRole('status')).toHaveTextContent('Base d’essai')
    expect(screen.getByRole('status')).not.toHaveTextContent('migration')
  })
})
