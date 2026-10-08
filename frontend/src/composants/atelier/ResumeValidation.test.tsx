/** Essais du résumé de validation : date, magasin, métier rappelés au-dessus du bouton. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ResumeValidation } from './ResumeValidation'

describe('ResumeValidation', () => {
  it('rappelle ce qui compte au-dessus du geste', () => {
    render(
      <ResumeValidation
        lignes={[
          ['Date', 'hier 07/10'],
          ['Magasin', 'Principal'],
          ['Métier', 'M3'],
        ]}
      >
        <button type="button">Valider la sortie</button>
      </ResumeValidation>,
    )
    const resume = screen.getByRole('region', { name: 'Résumé avant validation' })
    expect(resume).toHaveTextContent('Datehier 07/10')
    expect(resume).toHaveTextContent('MétierM3')
    expect(screen.getByRole('button', { name: 'Valider la sortie' })).toBeInTheDocument()
  })
})
