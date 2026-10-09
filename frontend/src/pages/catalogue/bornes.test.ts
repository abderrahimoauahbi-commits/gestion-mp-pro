/// <reference types="node" />
/**
 * Une seule déclaration des bornes (R5, P7-19, P7-20) : celles que l'écran contrôle à la frappe
 * sont relues dans les sources du serveur ; une borne qui change au serveur fait échouer l'essai.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import { BORNES_MATIERE, COMMENTAIRE_MAX, DELAI_MAX, LONGUEURS, NOTES_MAX } from './bornes'

const SERVEUR = join(process.cwd(), '..', 'backend', 'gestion_mp_pro')
const lire = (f: string) => readFileSync(join(SERVEUR, f), 'utf8')

describe('bornes de la fiche matière et du fournisseur', () => {
  it('reprend les bornes des nombres de services/matieres.py', () => {
    const source = lire('services/matieres.py')
    const bloc = source.slice(source.indexOf('BORNES: dict'), source.indexOf('"""Bornes des nombres'))
    for (const [champ, [bas, haut]] of Object.entries(BORNES_MATIERE)) {
      const m = new RegExp(`"${champ}": \\(([^,]+), ([^)]+)\\)`).exec(bloc)
      expect(m, champ).not.toBeNull()
      expect(Number(m?.[1]), champ).toBe(bas)
      expect(Number(m?.[2]), champ).toBe(haut)
    }
  })

  it('reprend les longueurs de modeles/longueurs.py', () => {
    const source = lire('modeles/longueurs.py')
    for (const [nom, valeur] of Object.entries(LONGUEURS)) {
      expect(new RegExp(`^${nom} = (\\d+)$`, 'm').exec(source)?.[1], nom).toBe(String(valeur))
    }
  })

  it('reprend les délais des fournisseurs et la longueur des observations', () => {
    expect(lire('api/fournisseurs/schemas.py')).toContain(`DELAI_MAX = ${DELAI_MAX}`)
    expect(lire('api/fournisseurs/schemas.py')).toContain(`NOTES_MAX = ${NOTES_MAX}`)
    expect(lire('api/classification/schemas.py')).toContain(`COMMENTAIRE_MAX = ${COMMENTAIRE_MAX}`)
  })
})
