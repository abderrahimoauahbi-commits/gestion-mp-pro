/** Essais des segments : groupe radio nommé par le Champ, flèches. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { Champ } from './Champ'
import { Segments } from './Segments'

describe('Segments', () => {
  it('nommé par le Champ ; clic et flèches changent le choix', async () => {
    function Essai() {
      const [u, setU] = useState<'kg' | 'bobine' | 'palette'>('kg')
      return (
        <Champ libelle="Unité" groupe>
          <Segments
            valeur={u}
            onChange={setU}
            options={[
              { valeur: 'kg', libelle: 'kg' },
              { valeur: 'bobine', libelle: 'Bobines' },
              { valeur: 'palette', libelle: 'Palettes' },
            ]}
          />
        </Champ>
      )
    }
    render(<Essai />)
    expect(screen.getByRole('radiogroup', { name: 'Unité' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('radio', { name: 'Bobines' }))
    expect(screen.getByRole('radio', { name: 'Bobines' })).toBeChecked()
    await userEvent.keyboard('{ArrowRight}')
    expect(screen.getByRole('radio', { name: 'Palettes' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Palettes' })).toHaveFocus()
    await userEvent.keyboard('{ArrowRight}')
    expect(screen.getByRole('radio', { name: 'kg' })).toBeChecked()
  })
})
