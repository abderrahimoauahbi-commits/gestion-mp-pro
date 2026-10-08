/** Essais de Pastille : nombre à la française, rien à zéro. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Pastille } from './Pastille'

describe('Pastille', () => {
  it('dit son nombre et ce qu’il compte ; rien à zéro', () => {
    const { rerender, container } = render(<Pastille nombre={1234} titre="ruptures et critiques" />)
    expect(screen.getByLabelText('1 234 — ruptures et critiques')).toHaveClass('pastille', 'critique')
    rerender(<Pastille nombre={0} titre="ruptures et critiques" />)
    expect(container).toBeEmptyDOMElement()
  })
})
