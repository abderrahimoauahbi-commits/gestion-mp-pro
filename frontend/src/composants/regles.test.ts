/**
 * Les règles du système de composants, vérifiées sur les sources (ECRANS-PRO § 1 et § 3) :
 * - un fichier d'essai par composant ;
 * - aucune couleur écrite hors de `styles/jetons.css` (stylelint le vérifie pour les feuilles de
 *   style ; ici, les sources TypeScript : seule `lib/teintes.ts` en garde, hors de ce dossier) ;
 * - aucune boîte du navigateur (`window.confirm`, `alert`, `prompt`) ;
 * - pas de vocabulaire retiré (REGLES-ECRAN § 5) dans les libellés.
 */
import { describe, expect, it } from 'vitest'

/** Toutes les sources du dossier, lues telles quelles (Vite : `?raw`). */
const TEXTES = import.meta.glob<string>('./**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true })
const TOUS = Object.keys(TEXTES)
const lire = (f: string) => TEXTES[f] ?? ''
const basename = (f: string) => f.split('/').pop() ?? f
const SOURCES = TOUS.filter((f) => !/\.test\.tsx?$/.test(f))
const COMPOSANTS = SOURCES.filter((f) => /\/[A-Z][A-Za-z]+\.tsx$/.test(f) && !f.includes('/demonstration/'))

describe('Système de composants', () => {
  it('chaque composant a son fichier d’essai', () => {
    const sansEssai = COMPOSANTS.filter((f) => !TOUS.includes(f.replace(/\.tsx$/, '.test.tsx')))
    expect(sansEssai.map((f) => basename(f))).toEqual([])
    expect(COMPOSANTS.length).toBeGreaterThanOrEqual(60)
  })

  it('aucune couleur écrite dans les sources : seulement des jetons', () => {
    const fautifs = SOURCES.filter((f) =>
      /#[0-9a-fA-F]{3,8}\b(?![\w-])|\brgba?\(|\bhsla?\(/.test(
        lire(f).replace(/\/\/.*$|\/\*[\s\S]*?\*\//gm, ''),
      ),
    )
    expect(fautifs.map((f) => basename(f))).toEqual([])
  })

  it('aucune boîte du navigateur', () => {
    const fautifs = SOURCES.filter((f) => /\b(window\.)?(confirm|alert|prompt)\s*\(/.test(lire(f)))
    expect(fautifs.map((f) => basename(f))).toEqual([])
  })

  it('pas de vocabulaire retiré dans les libellés', () => {
    const interdits = [
      /['"`>]Réf\./,
      /BC en cours/,
      /Reste attendu/,
      /Saisi par/,
      /\bGuide\b/,
      /\bDH\b/,
      /Brouillon n°/,
      /Mes ordres/,
    ]
    const fautes = SOURCES.flatMap((f) => {
      const texte = lire(f).replace(/\/\/.*$|\/\*[\s\S]*?\*\//gm, '')
      return interdits.filter((m) => m.test(texte)).map((m) => `${basename(f)} : ${m.source}`)
    })
    expect(fautes).toEqual([])
  })
})
