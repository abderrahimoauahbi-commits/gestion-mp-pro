/** Essais de l'export : adresse du classeur avec la vue ; CSV de ce qui est affiché, formules neutralisées. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ExportExcel, texteCsv } from './ExportExcel'

describe('ExportExcel', () => {
  it('vise /api/export/… avec les paramètres non vides', () => {
    render(
      <ExportExcel
        route="/export/mouvements"
        parametres={{ onglet: 'mouvements', q: 'rouge', type: '', magasin: 3 }}
      />,
    )
    const lien = screen.getByRole('link', { name: 'Exporter en Excel' })
    expect(lien).toHaveAttribute('href', '/api/export/mouvements?onglet=mouvements&q=rouge&magasin=3')
    expect(lien).toHaveAttribute('download')
  })

  it('le CSV garde l’ordre des colonnes exportées, la virgule décimale, et neutralise les formules', () => {
    type L = { ref: string; kg: number; note: string }
    const csv = texteCsv<L>(
      [
        { cle: 'ref', titre: 'Référence' },
        { cle: 'kg', titre: 'Reste (kg)' },
        { cle: 'note', titre: 'Observations', exporte: false },
      ],
      [{ ref: '=SOMME(A1)', kg: 1234.5, note: 'x' }],
    )
    expect(csv).toBe("\ufeffRéférence;Reste (kg)\r\n'=SOMME(A1);1234,5")
  })
})
