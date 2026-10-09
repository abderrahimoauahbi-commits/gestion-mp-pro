/** « Signaler un besoin » : le bouton dit ce qui manque, l'envoi suit le contrat (POST /signalements). */
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, expectTypeOf, it, vi } from 'vitest'

import { fauxServeur, monterDansSession } from '../../essais/monter'
import type { Schema } from '../../lib/types'
import { manqueSignalement, SignalerBesoin, versChoix } from './SignalerBesoin'

afterEach(() => vi.unstubAllGlobals())

describe('SignalerBesoin', () => {
  it('dit ce qui manque', () => {
    expect(manqueSignalement(' a ')).toEqual(['le besoin (2 caractères au moins)'])
    expect(manqueSignalement('ok')).toEqual([])
    expect(
      versChoix({
        id: 1,
        reference: 'R',
        designation: '',
        composition: null,
        type_fil: 'Frisé',
        titrage: null,
        couleur: null,
        fournisseur: null,
      }).type,
    ).toBe('Frisé')
  })

  it('lit la matière selon le contrat publié de GET /matieres (et non une forme provisoire)', () => {
    type Lue = Parameters<typeof versChoix>[0]
    expectTypeOf<Lue['designation']>().toEqualTypeOf<Schema<'MatiereResume'>['designation']>()
    expectTypeOf<Lue['type_fil']>().toEqualTypeOf<Schema<'MatiereResume'>['type_fil']>()
  })

  it('envoie le besoin, l’urgence, sans matière', async () => {
    const appels = fauxServeur({ 'GET /matieres': { corps: [] }, 'POST /signalements': { corps: { id: 9 } } })
    const fermer = vi.fn()
    monterDansSession(<SignalerBesoin onFermer={fermer} />, 'alimentation')
    const bouton = screen.getByRole('button', { name: 'Signaler aux achats' })
    expect(bouton).toBeDisabled()
    expect(bouton).toHaveAttribute('data-raison', 'À renseigner : le besoin (2 caractères au moins).')
    await userEvent.type(screen.getByLabelText(/Quel besoin/), 'Plus que deux palettes de beige')
    await userEvent.click(screen.getByRole('radio', { name: 'Urgent' }))
    await userEvent.click(bouton)
    await waitFor(() => expect(fermer).toHaveBeenCalled())
    expect(appels.find((a) => a.methode === 'POST')?.corps).toEqual({
      matiere_id: null,
      texte: 'Plus que deux palettes de beige',
      urgence: 'urgente',
    })
  })
})
