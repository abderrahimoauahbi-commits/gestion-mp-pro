/** Essais du bandeau des blocages : annoncé en alerte, rien sans blocage. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { BandeauBlocages } from './BandeauBlocages'

describe('BandeauBlocages', () => {
  it('annonce les refus dès l’ouverture ; rien sans blocage', () => {
    const texte =
      'L’inventaire INV-2026-0003 (Principal, du 08/10/2026) compte « PP Rouge » : ses mouvements y sont suspendus jusqu’à sa validation. Garder en brouillon, ou attendre.'
    const { rerender, container } = render(<BandeauBlocages blocages={[texte]} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Sera refusé à la validation :')
    expect(screen.getByRole('alert')).toHaveTextContent(texte)
    rerender(<BandeauBlocages blocages={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})
