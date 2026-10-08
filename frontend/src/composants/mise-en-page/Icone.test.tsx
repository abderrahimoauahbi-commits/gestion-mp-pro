/** Essais des icônes : décoratives, au trait de la couleur du texte. */
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { classes } from './classes'
import { Icone, NOMS_ICONES } from './Icone'

describe('Icone', () => {
  it('est cachée aux lecteurs d’écran et a la taille demandée', () => {
    const { container } = render(<Icone nom="recherche" taille={22} />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('aria-hidden', 'true')
    expect(svg).toHaveAttribute('width', '22')
    expect(svg?.querySelector('path')?.getAttribute('d')).toBeTruthy()
  })

  it('chaque nom a un tracé', () => {
    for (const nom of NOMS_ICONES) {
      const { container, unmount } = render(<Icone nom={nom as 'info'} />)
      expect(container.querySelector('path')?.getAttribute('d')?.length).toBeGreaterThan(5)
      unmount()
    }
  })

  it('classes saute les vides', () => {
    expect(classes('a', false, null, undefined, '', 'b')).toBe('a b')
  })
})
