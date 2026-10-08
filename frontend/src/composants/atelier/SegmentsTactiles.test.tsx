/** Essais des segments tactiles : mode tactile posé, choix au doigt. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { SegmentsTactiles } from './SegmentsTactiles'

describe('SegmentsTactiles', () => {
  it('pose le mode tactile et choisit', async () => {
    const choisir = vi.fn()
    render(
      <SegmentsTactiles
        libelle="Magasin"
        valeur="principal"
        onChange={choisir}
        options={[
          { valeur: 'principal', libelle: 'Principal' },
          { valeur: 'annexe', libelle: 'Annexe' },
        ]}
      />,
    )
    expect(screen.getByRole('radiogroup', { name: 'Magasin' })).toHaveClass('tactile')
    await userEvent.click(screen.getByRole('radio', { name: 'Annexe' }))
    expect(choisir).toHaveBeenCalledWith('annexe')
  })
})
