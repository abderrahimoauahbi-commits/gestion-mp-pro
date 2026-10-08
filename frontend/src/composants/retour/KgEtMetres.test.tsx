/** Essais de KgEtMetres : mètres indicatifs, décimales du téléphone. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { KgEtMetres } from './KgEtMetres'

describe('KgEtMetres', () => {
  it('« 14,3 kg ≈ 1 021 ml » pour un cuir ; kilos seuls sinon ; décimales du téléphone', () => {
    const { rerender, container } = render(<KgEtMetres kg={14.3} kgParMl={0.014} />)
    expect(container.textContent).toBe('14,3\u00a0kg ≈\u00a01\u00a0021\u00a0ml')
    rerender(<KgEtMetres kg={445.4} telephone />)
    expect(screen.getByText('445 kg')).toBeInTheDocument()
    rerender(<KgEtMetres kg={null} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
