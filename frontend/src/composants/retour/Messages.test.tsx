/** Essais des messages : succès qui s'efface, erreur qui reste, refus dit tel quel. */
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ErreurApi } from '../../lib/api'
import { dire, direErreur, DUREE_MESSAGE, Messages } from './Messages'

describe('Messages', () => {
  it('un succès s’efface seul ; une erreur reste jusqu’à ce qu’on la ferme', async () => {
    vi.useFakeTimers()
    render(<Messages />)
    act(() => {
      dire('Réception validée : REC-2026-0042.')
      direErreur(new ErreurApi('Cette commande a été modifiée entre-temps par Karim.', 409))
    })
    expect(screen.getByText('Réception validée : REC-2026-0042.')).toBeInTheDocument()
    act(() => {
      vi.advanceTimersByTime(DUREE_MESSAGE + 10)
    })
    expect(screen.queryByText('Réception validée : REC-2026-0042.')).toBeNull()
    expect(screen.getByText('Cette commande a été modifiée entre-temps par Karim.')).toBeInTheDocument()
    vi.useRealTimers()
    await userEvent.click(screen.getByRole('button', { name: 'Fermer le message' }))
    expect(screen.queryByText(/modifiée entre-temps/)).toBeNull()
  })

  it('garde les quatre derniers messages', () => {
    render(<Messages />)
    act(() => {
      for (let i = 1; i <= 6; i++) dire(`message ${i}`, 'info')
    })
    expect(screen.queryByText('message 2')).toBeNull()
    expect(screen.getByText('message 3')).toBeInTheDocument()
    expect(screen.getByText('message 6')).toBeInTheDocument()
  })
})
