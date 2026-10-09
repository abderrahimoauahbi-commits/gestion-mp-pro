/** La session : motif lisible d'une session perdue (H-09), adresse de connexion qui rouvre la page demandée. */
import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { motifLisible, useSession, versConnexion } from './session'

describe('session', () => {
  it('dit pourquoi on revient à la connexion', () => {
    expect(motifLisible('Connectez-vous pour continuer.')).toBe('Votre session a expiré : reconnectez-vous.')
    expect(motifLisible('')).toBe('Votre session a expiré : reconnectez-vous.')
    expect(motifLisible('Ce compte n’est plus actif.')).toBe(
      'Ce compte n’est plus actif : voyez la direction.',
    )
    expect(motifLisible('Votre code a été changé : reconnectez-vous.')).toBe(
      'Votre code a été changé : reconnectez-vous.',
    )
  })

  it('garde l’adresse demandée pour après la connexion', () => {
    expect(versConnexion('/commandes?onglet=prix')).toBe('/connexion?retour=%2Fcommandes%3Fonglet%3Dprix')
    expect(versConnexion('/')).toBe('/connexion')
  })

  it('useSession hors d’une session est une faute', () => {
    expect(() => renderHook(() => useSession())).toThrow('useSession hors de la session.')
  })
})
