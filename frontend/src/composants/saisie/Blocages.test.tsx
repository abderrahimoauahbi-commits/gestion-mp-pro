/** Essais de Blocages : la liste des refus annoncés, rien sans blocage. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Blocages } from './Blocages'

describe('Blocages', () => {
  it('annonce chaque refus ; rien quand il n’y en a pas', () => {
    const { rerender, container } = render(
      <Blocages
        blocages={[
          'Date antérieure au dernier ordre validé (07/10/2026).',
          'Le magasin Quarantaine n’accepte pas de sortie.',
        ]}
      />,
    )
    const note = screen.getByRole('note', { name: 'Sera refusé :' })
    expect(note.querySelectorAll('li')).toHaveLength(2)
    rerender(<Blocages blocages={[]} />)
    expect(container).toBeEmptyDOMElement()
  })
})
