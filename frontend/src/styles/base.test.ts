/// <reference types="node" />
/**
 * Règles de la feuille commune que jsdom ne peut pas mesurer (la recette navigateur les mesure) :
 * on les lit dans la feuille.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

const base = readFileSync(join(process.cwd(), 'src/styles/base.css'), 'utf8')

describe('Feuille commune', () => {
  it('un texte masqué est posé en haut à gauche : il n’allonge jamais la page qui défile', () => {
    const regle = /\.masque-accessible\s*\{([^}]*)\}/.exec(base)?.[1] ?? ''
    expect(regle).toMatch(/position:\s*absolute/)
    expect(regle).toMatch(/top:\s*0/)
    expect(regle).toMatch(/left:\s*0/)
  })
})
