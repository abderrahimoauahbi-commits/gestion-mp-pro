/** L'aide, une seule source : l'écriture des textes, le texte unique « Sur les métiers », les formules. */
import { describe, expect, it } from 'vitest'

import aide from '../aide.json'
import { developper, formule, MODE_EMPLOI, morceaux, SUR_LES_METIERS } from './aide'

describe('aide.json', () => {
  it('découpe gras, italique et liens', () => {
    expect(
      morceaux('Le **brouillon** puis *la validation* : [Classification](/catalogue?onglet=classification).'),
    ).toEqual([
      { genre: 'texte', texte: 'Le ' },
      { genre: 'gras', texte: 'brouillon' },
      { genre: 'texte', texte: ' puis ' },
      { genre: 'italique', texte: 'la validation' },
      { genre: 'texte', texte: ' : ' },
      { genre: 'lien', texte: 'Classification', vers: '/catalogue?onglet=classification' },
      { genre: 'texte', texte: '.' },
    ])
  })

  it('reprend mot pour mot le texte unique « Sur les métiers »', () => {
    expect(SUR_LES_METIERS).toBe(
      'Sur les métiers : le fil monté, pas encore tissé. C’est du stock : il compte dans le stock, sa valeur, le disponible et le stock projeté. Monter n’écrit aucun mouvement : le fil a déjà été sorti par un ordre.',
    )
    expect(developper('A {{sur_les_metiers}} B')).toBe(`A ${SUR_LES_METIERS} B`)
    expect(formule('stock_detenu')).toContain(SUR_LES_METIERS)
  })

  it('aucun renvoi {{…}} inconnu, aucun « hors stock » ni « en machine » pour le fil monté', () => {
    const tout = JSON.stringify(aide)
    const renvois = [...tout.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1])
    expect(renvois.every((r) => r === 'sur_les_metiers')).toBe(true)
    expect(tout).not.toMatch(/hors stock|En machine|valorisé à part/)
  })

  it('le Mode d’emploi a ses sept volets ; les calculs citent des formules existantes', () => {
    expect(MODE_EMPLOI.regles.elements).toHaveLength(14)
    expect(MODE_EMPLOI.roles.cartes.map((c) => c.role)).toEqual([
      'direction',
      'achats',
      'alimentation',
      'administrateur',
    ])
    expect(MODE_EMPLOI.pas.procedures).toHaveLength(9)
    expect(MODE_EMPLOI.calculs.lignes).toHaveLength(21)
    for (const cle of MODE_EMPLOI.calculs.lignes) expect(Object.keys(aide.formule)).toContain(cle)
    expect(MODE_EMPLOI.analyse.lignes).toHaveLength(9)
    expect(MODE_EMPLOI.ecrans.lignes).toHaveLength(25)
    expect(MODE_EMPLOI.telephone.etapes.length).toBeGreaterThanOrEqual(4)
  })

  it('les clés des écrans et des formules sont triées (moins de conflits entre lots)', () => {
    for (const bloc of [aide.ecran, aide.formule]) {
      const cles = Object.keys(bloc)
      expect(cles).toEqual([...cles].sort())
    }
  })
})
