/// <reference types="node" />
/**
 * Les cibles tactiles des écrans de l'atelier (REGLES-ECRAN § 4, ECRANS-PRO § 1) : chaque élément
 * qu'on touche, posé par ces pages (lien-bouton, carte, étage, étiquette), fait au moins 44 × 44 px ;
 * les champs 46 px en 16 px (pas de zoom d'iOS). jsdom ne calcule pas la mise en page : la règle se
 * lit dans la feuille ; la recette navigateur mesure les boîtes à 360 et 375 px.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

const css = readFileSync(join(process.cwd(), 'src/pages/atelier/atelier.module.css'), 'utf8')

function declarations(selecteur: string): string {
  const motif = new RegExp(`(^|[},\\s])${selecteur.replace(/[.()]/g, '\\$&')}\\s*\\{([^}]*)\\}`, 'gm')
  return [...css.matchAll(motif)].map((m) => m[2]).join(';')
}

describe('Cibles tactiles des écrans de l’atelier', () => {
  it.each(['.lienBouton', '.carteLien', '.etage', '.lienTexte'])('%s : au moins 44 × 44 px', (s) => {
    const d = declarations(s)
    expect(d, `${s} introuvable`).not.toBe('')
    expect(d).toMatch(/min-height:\s*(var\(--(cible-tactile|champ-atelier)\)|(4[4-9]|[5-9]\d)px)/)
    expect(d).toMatch(/min-width:\s*var\(--cible-tactile\)/)
  })

  it('les champs font 46 px en 16 px (l’étiquette à imprimer : `BoutonImprimer taille="atelier"`)', () => {
    expect(declarations('.pile :is(input, select, textarea)')).toMatch(
      /min-height:\s*var\(--champ-atelier\);\s*font-size:\s*var\(--texte-atelier\)/,
    )
  })
})
