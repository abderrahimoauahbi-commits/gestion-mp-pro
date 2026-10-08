/** Essais du Kpi : la formule est obligatoire et présente ; lien, ton, valeur exacte. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { Kpi } from './Kpi'

describe('Kpi', () => {
  it('montre sa formule dans la bulle « ? »', async () => {
    render(
      <Kpi
        titre="Valeur du stock"
        valeur="17,4 M"
        unite="MAD"
        exact="17 398 184,20 MAD"
        formule="Σ reste des lots × coût moyen pondéré, magasins et métiers."
      />,
    )
    const bulle = screen.getByRole('button', { name: 'Formule : Valeur du stock' })
    expect(bulle).toHaveAccessibleDescription('Σ reste des lots × coût moyen pondéré, magasins et métiers.')
    await userEvent.click(bulle)
    expect(bulle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('17,4 M')).toHaveAttribute('title', '17 398 184,20 MAD')
  })

  it('la formule est exigée par le type, et une formule vide est signalée', () => {
    const erreur = vi.spyOn(console, 'error').mockImplementation(() => {})
    // @ts-expect-error — un Kpi sans formule ne se construit pas.
    render(<Kpi titre="Ruptures" valeur={3} />)
    render(<Kpi titre="Ruptures" valeur={3} formule="  " />)
    expect(erreur).toHaveBeenCalledWith(
      'Indicateur « Ruptures » sans formule : elle est obligatoire (aide.json).',
    )
  })

  it('avec un lien, ouvre son écran ; le ton pose son filet', () => {
    render(
      <MemoryRouter>
        <Kpi
          titre="Ruptures"
          valeur={3}
          formule="Matières au statut RUPTURE."
          lien="/stock?statut=RUPTURE"
          ton="rupture"
          detail="3 matières à zéro"
        />
      </MemoryRouter>,
    )
    const lien = screen.getByRole('link', { name: /Ruptures/ })
    expect(lien).toHaveAttribute('href', '/stock?statut=RUPTURE')
    expect(lien).toHaveClass('rupture')
    expect(screen.getByText('3 matières à zéro')).toBeInTheDocument()
  })
})
