/** Essais du QR : identifiant tiré de l'adresse de l'étiquette ; sans caméra, la voie du numéro est dite. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { detecteurDisponible, lotDuQR, ScanQR } from './ScanQR'

describe('ScanQR', () => {
  it('lit l’identifiant du lot dans l’adresse de l’étiquette', () => {
    expect(lotDuQR('https://mp.usine.local/lot/123')).toBe(123)
    expect(lotDuQR('/atelier/lots/45?x=1')).toBe(45)
    expect(lotDuQR('LOT-2026-0007')).toBeNull()
  })

  it('sans lecteur de QR dans le navigateur, le dit', () => {
    expect(detecteurDisponible()).toBeNull()
    render(<ScanQR onLot={() => {}} />)
    expect(screen.getByText(/tapez le numéro du lot/)).toBeInTheDocument()
  })
})
