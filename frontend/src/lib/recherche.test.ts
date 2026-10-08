/** Essais de la recherche à la frappe : sans accents, multi-mots, littérale. */
import { describe, expect, it } from 'vitest'

import { correspond, filtrer, motsDe, parametreRecherche, sansAccents } from './recherche'

describe('Recherche sans accents, multi-mots', () => {
  it('« frise rouge » trouve « IMP FRISÉ ROUGE »', () => {
    expect(correspond('IMP FRISÉ ROUGE', 'frise rouge')).toBe(true)
    expect(correspond('IMP FRISÉ ROUGE', 'FRISÉ')).toBe(true)
    expect(correspond('IMP FRISÉ ROUGE', 'rouge frisé imp')).toBe(true)
  })

  it('chaque mot doit être quelque part', () => {
    expect(correspond('IMP FRISÉ ROUGE', 'frise bleu')).toBe(false)
  })

  it('« rouge 2900 hasi » trouve la ligne de HASIRCI', () => {
    expect(correspond('PP FRZ-2900 Dtex-Red Rouge HASIRCI', 'rouge 2900 hasi')).toBe(true)
  })

  it('les accents de la recherche comme du texte ne comptent pas', () => {
    expect(correspond('Crème écru', 'creme ECRU')).toBe(true)
    expect(correspond('Creme ecru', 'crème')).toBe(true)
    expect(sansAccents('Ça, Œuvre ÀÉÎÕÜ')).toBe('ca, œuvre aeiou')
  })

  it('une recherche vide trouve tout', () => {
    expect(correspond('n’importe quoi', '')).toBe(true)
    expect(correspond('n’importe quoi', '   ')).toBe(true)
    expect(motsDe('  ')).toEqual([])
  })

  it('les blancs, dont l’espace insécable, séparent les mots', () => {
    expect(correspond('Stock 1 234 kg', '1 234')).toBe(true)
    expect(motsDe(' frise  rouge\t')).toEqual(['frise', 'rouge'])
  })
})

describe('« % » et « _ » sont littéraux', () => {
  it('« % » ne remplace rien', () => {
    expect(correspond('Coton 100%', '100%')).toBe(true)
    expect(correspond('Coton 100 pour cent', '100%')).toBe(false)
    expect(correspond('IMP FRISÉ ROUGE', '%')).toBe(false)
    expect(correspond('IMP FRISÉ ROUGE', 'fr%se')).toBe(false)
  })

  it('« _ » ne remplace pas un caractère', () => {
    expect(correspond('LOT_12', 'lot_12')).toBe(true)
    expect(correspond('LOT-12', 'lot_12')).toBe(false)
    expect(correspond('IMP FRISÉ ROUGE', 'fris_')).toBe(false)
  })

  it('les autres caractères spéciaux aussi (pas d’expression régulière)', () => {
    expect(correspond('PP FRZ-2900 (a+b)', '(a+b)')).toBe(true)
    expect(correspond('PP FRZ', '.*')).toBe(false)
  })
})

describe('filtrer', () => {
  const matieres = [
    { ref: 'IMP FRISÉ ROUGE', fournisseur: 'HASIRCI', cache: 'polyester' },
    { ref: 'PP FRZ-2900 Dtex', fournisseur: 'BELKA', cache: null },
    { ref: 'Cuir naturel', fournisseur: 'Tannerie', cache: 'franges' },
  ]
  const champs = (m: (typeof matieres)[number]) => [m.ref, m.fournisseur, m.cache]

  it('cherche aussi dans les champs cachés', () => {
    expect(filtrer(matieres, 'polyester rouge', champs).map((m) => m.ref)).toEqual(['IMP FRISÉ ROUGE'])
    expect(filtrer(matieres, 'franges', champs)).toHaveLength(1)
  })

  it('une recherche vide rend toute la liste (une copie)', () => {
    const r = filtrer(matieres, '', champs)
    expect(r).toEqual(matieres)
    expect(r).not.toBe(matieres)
  })

  it('le paramètre ?q= est nettoyé, ou absent', () => {
    expect(parametreRecherche('  frise   rouge ')).toBe('frise rouge')
    expect(parametreRecherche('   ')).toBeUndefined()
  })
})
