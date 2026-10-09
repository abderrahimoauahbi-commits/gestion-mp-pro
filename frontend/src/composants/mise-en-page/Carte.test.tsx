/** Essais de Carte : titre, actions à droite (sous le titre au téléphone), ton. */
import { render, screen } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import { Carte } from './Carte'

const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'Carte.module.css'), 'utf8')

describe('Carte', () => {
  it('rend le titre en h2, le sous-titre et les actions', () => {
    render(
      <Carte titre="Lots" sous="du magasin principal" actions={<button type="button">Exporter</button>}>
        corps
      </Carte>,
    )
    expect(screen.getByRole('heading', { level: 2, name: 'Lots' })).toBeInTheDocument()
    expect(screen.getByText('du magasin principal')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Exporter' })).toBeInTheDocument()
  })

  it('sans titre ni actions, pas d’en-tête ; le ton pose son filet', () => {
    const { container } = render(<Carte ton="critique">corps</Carte>)
    expect(container.querySelector('header')).toBeNull()
    expect(container.querySelector('section')).toHaveClass('ton-critique')
  })

  it('au téléphone, les actions passent sous le titre (en-tête en colonne)', () => {
    const telephone = /@media \(width <= 700px\) \{([\s\S]*?)\n\}/.exec(css)?.[1] ?? ''
    expect(telephone).toMatch(/\.entete \{[^}]*flex-direction: column;/)
  })
})
