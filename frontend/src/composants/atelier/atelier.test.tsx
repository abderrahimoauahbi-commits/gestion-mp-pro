/// <reference types="node" />
/**
 * Règle des cibles tactiles de l'atelier (REGLES-ECRAN § 4, ECRANS-PRO § 1) : chaque élément
 * qu'on touche dans les composants `atelier/` (et le mode tactile des segments et du bouton) a
 * une hauteur et une largeur minimales d'au moins 44 px (`--cible-tactile`), ou le champ de 46 px.
 * jsdom ne calcule pas la mise en page : la règle se lit dans les feuilles de style, et la
 * recette navigateur mesure les boîtes (page de démonstration, 375 × 812).
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

// Vitest ne rend pas le texte des feuilles de style importées (`?raw`) : on les lit sur le disque.
const SRC = join(process.cwd(), 'src')
const lire = (f: string) => readFileSync(join(SRC, 'composants', f), 'utf8')
const jetons = readFileSync(join(SRC, 'styles/jetons.css'), 'utf8')

/** Les déclarations d'une règle CSS (`.sel { … }`), tous blocs confondus. */
function declarations(css: string, selecteur: string): string {
  const motif = new RegExp(
    `(^|[},\\s])${selecteur.replace(/\./g, '\\.')}(\\s*,[^{]*)?\\s*\\{([^}]*)\\}`,
    'gm',
  )
  return [...css.matchAll(motif)].map((m) => m[3]).join(';')
}

const CIBLES: [string, string][] = [
  ['atelier/Compteur.module.css', '.pas'],
  ['atelier/EcranAtelier.module.css', '.retour'],
  ['atelier/BarreBas.module.css', '.case'],
  ['atelier/Tuile.module.css', '.tuile'],
  ['saisie/Segments.module.css', '.tactile .segment'],
  ['saisie/Bouton.module.css', '.atelier'],
]

describe('Cibles tactiles de l’atelier', () => {
  it.each(CIBLES)('%s %s : au moins 44 × 44 px', (fichier, selecteur) => {
    const d = declarations(lire(fichier), selecteur)
    expect(d, `${selecteur} introuvable`).not.toBe('')
    const haut =
      /(min-height|height):\s*var\(--(cible-tactile|champ-atelier)\)|min-height:\s*(4[4-9]|[5-9]\d|\d{3})px/.test(
        d,
      )
    const large = /(min-width|width):\s*var\(--cible-tactile\)/.test(d)
    expect(haut, `${selecteur} : hauteur`).toBe(true)
    expect(large, `${selecteur} : largeur`).toBe(true)
  })

  it('le champ du compteur fait 46 px en 16 px (pas de zoom d’iOS)', () => {
    const d = declarations(lire('atelier/Compteur.module.css'), '.champ')
    expect(d).toMatch(/min-height:\s*var\(--champ-atelier\)/)
    expect(d).toMatch(/font-size:\s*var\(--texte-atelier\)/)
    expect(jetons).toMatch(/--cible-tactile:\s*44px/)
    expect(jetons).toMatch(/--champ-atelier:\s*46px/)
    expect(jetons).toMatch(/--texte-atelier:\s*16px/)
  })
})
