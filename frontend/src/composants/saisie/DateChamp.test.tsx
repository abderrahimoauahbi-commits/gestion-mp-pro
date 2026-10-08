/** Essais de DateChamp : aujourd'hui du serveur en borne haute, période close en borne basse. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { recalerHorloge } from '../../lib/heure'
import { DateChamp, messageDate } from './DateChamp'

describe('DateChamp', () => {
  it('la borne haute est aujourd’hui à l’heure du serveur ; une date future est dite', () => {
    recalerHorloge('2026-10-08T10:00:00+01:00')
    render(<DateChamp valeur="2026-10-09" onChange={() => {}} libelle="Reçu le" />)
    const champ = screen.getByLabelText('Reçu le')
    expect(champ).toHaveAttribute('max', '2026-10-08')
    expect(champ).toHaveAttribute('aria-invalid', 'true')
    expect(champ).toHaveAccessibleDescription(
      "Au plus tard aujourd'hui (08/10/2026) : pas de date dans le futur.",
    )
  })

  it('la borne basse dit sa raison ; futurPermis lève la borne haute', () => {
    recalerHorloge('2026-10-08T10:00:00+01:00')
    expect(
      messageDate('2026-09-15', '2026-10-01', '2026-10-08', 'la période est close jusqu’au 30/09/2026'),
    ).toBe('Au plus tôt le 01/10/2026 : la période est close jusqu’au 30/09/2026.')
    render(<DateChamp valeur="2026-12-01" onChange={() => {}} futurPermis libelle="Livraison prévue" />)
    expect(screen.getByLabelText('Livraison prévue')).not.toHaveAttribute('max')
    expect(screen.getByLabelText('Livraison prévue')).not.toHaveAttribute('aria-invalid')
  })
})
