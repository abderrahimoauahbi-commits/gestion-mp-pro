/** Essais de la formule : bulle décrite, ouverte au toucher, fermée en quittant. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { Formule } from './Formule'

describe('Formule', () => {
  it('le « ? » décrit la formule, s’ouvre au toucher et se referme en quittant', async () => {
    render(<Formule texte="Disponible + commandé − demande pendant le délai." de="Stock projeté" />)
    const b = screen.getByRole('button', { name: 'Formule : Stock projeté' })
    expect(screen.getByRole('tooltip', { hidden: true })).toHaveTextContent('Disponible + commandé')
    await userEvent.click(b)
    expect(b).toHaveAttribute('aria-expanded', 'true')
    await userEvent.tab()
    expect(b).toHaveAttribute('aria-expanded', 'false')
  })
})
