/** Essais du badge : la table complète des statuts, un libellé et un ton chacun, jamais doublé. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { STATUTS, type Famille } from '../../lib/statuts'
import { Badge } from './Badge'

const TONS = ['ok', 'attention', 'urgent', 'critique', 'rupture', 'neutre', 'accent']

describe('Badge', () => {
  it('rend chaque statut de chaque famille avec son libellé et son ton, sans libellé doublé', () => {
    let vus = 0
    for (const famille of Object.keys(STATUTS) as Famille[]) {
      const table: Record<string, { libelle: string; ton: string }> = STATUTS[famille]
      for (const [valeur, { libelle, ton }] of Object.entries(table)) {
        const { container, unmount } = render(<Badge famille={famille} valeur={valeur} />)
        const badge = container.querySelector('span')
        expect(badge, `${famille}.${valeur}`).toHaveTextContent(libelle)
        expect(badge?.textContent).toBe(libelle)
        expect(badge).toHaveClass('badge', ton)
        expect(TONS).toContain(ton)
        // « Brouillon / Brouillon », « Quarantaine quarantaine » : jamais deux fois le même mot.
        const mots = libelle
          .toLowerCase()
          .split(/[\s/]+/)
          .filter((m) => m.length > 3)
        expect(new Set(mots).size, libelle).toBe(mots.length)
        expect(libelle).not.toMatch(/\p{Extended_Pictographic}/u)
        unmount()
        vus++
      }
    }
    expect(vus).toBeGreaterThanOrEqual(90)
  })

  it('une valeur inconnue s’affiche telle quelle en neutre ; vide → « — »', () => {
    const { rerender } = render(<Badge famille="commande" valeur="inventee" />)
    expect(screen.getByText('inventee')).toHaveClass('neutre')
    rerender(<Badge famille="commande" valeur={null} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('une étiquette libre prend son ton', () => {
    render(
      <Badge ton="attention" titre="Montant estimé aux prix du catalogue">
        estimé
      </Badge>,
    )
    expect(screen.getByText('estimé')).toHaveClass('attention')
    expect(screen.getByText('estimé')).toHaveAttribute('title', 'Montant estimé aux prix du catalogue')
  })
})
