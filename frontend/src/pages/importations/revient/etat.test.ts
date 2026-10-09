/** L'état de l'analyse lu dans l'adresse, les paramètres du serveur, les listes liées. */
import { describe, expect, it } from 'vitest'

import { optionsDesCriteres, premierMot, titragesDe } from './criteres'
import { CLASSIFICATION, MATIERES } from './donneesEssai'
import {
  lireCombinaisons,
  lireEtat,
  lireMatieres,
  libelleCombinaison,
  nombreCriteres,
  parametresServeur,
} from './etat'

const etatDe = (texte: string) => lireEtat(new URLSearchParams(texte))

describe('lireEtat', () => {
  it('rend les défauts : vue regroupée, axe titrage, rien de filtré', () => {
    const e = etatDe('onglet=revient')
    expect(e).toMatchObject({ vue: 'groupe', axe: 'titrage', q: '', statut: '', qualite: null })
    expect(e.matieres).toEqual([])
    expect(e.combinaisons).toEqual([])
    expect(nombreCriteres(e)).toBe(0)
  })

  it('lit chaque paramètre et écarte les valeurs inconnues', () => {
    const e = etatDe(
      'vue=lots&axe=fournisseur&q=rouge&statut=clos&du=2026-01-01&au=2026-02-30x&qualite=3&matieres=2,5,2,x&type=FRI',
    )
    expect(e).toMatchObject({ vue: 'lots', axe: 'fournisseur', q: 'rouge', statut: 'clos', du: '2026-01-01' })
    expect(e.au).toBe('')
    expect(e.qualite).toBe(3)
    expect(e.matieres).toEqual([2, 5])
    expect(e.criteres.type_fil).toBe('FRI')
    expect(etatDe('vue=autre&axe=rien&statut=Clos')).toMatchObject({
      vue: 'groupe',
      axe: 'titrage',
      statut: '',
    })
  })

  it('lit les combinaisons en JSON ; un texte illisible n’en donne aucune', () => {
    expect(lireCombinaisons('[{"composition":"PES","titrage":"1500","inconnu":"x"},{},3]')).toEqual([
      { composition: 'PES', titrage: '1500' },
    ])
    expect(lireCombinaisons('{pas du json')).toEqual([])
    expect(lireCombinaisons('{"composition":"PES"}')).toEqual([])
    expect(lireMatieres('')).toEqual([])
    expect(libelleCombinaison({ titrage: '1500', composition: 'PES' })).toBe('PES · 1500')
  })

  it('compte les critères (« Effacer les filtres » dès deux)', () => {
    const e = etatDe(
      'q=a&statut=ouvert&du=2026-01-01&qualite=1&matieres=1,2&composition=PES&combinaisons=[{"couleur":"NOIR"}]',
    )
    expect(nombreCriteres(e)).toBe(8)
  })
})

describe('parametresServeur', () => {
  it('envoie les critères un à un sans combinaison retenue', () => {
    const p = parametresServeur(etatDe('composition=PES&titrage=1500&matieres=2,5&qualite=3'), 'bursa')
    expect(p).toMatchObject({ axe: 'titrage', q: 'bursa', composition: 'PES', titrage: '1500', qualite: 3 })
    expect(p.matieres).toEqual([2, 5])
    expect(p.selection).toBeUndefined()
  })

  it('envoie `selection` dès qu’une combinaison est retenue, les critères en cours en dernier', () => {
    const p = parametresServeur(
      etatDe('combinaisons=[{"composition":"PES","titrage":"1500"}]&couleur=NOIR&vue=lots&axe=couleur'),
      '',
    )
    expect(JSON.parse(String(p.selection))).toEqual([
      { composition: 'PES', titrage: '1500' },
      { couleur: 'NOIR' },
    ])
    expect(p.couleur).toBeUndefined()
    expect(p.axe).toBe('reference')
  })
})

describe('listes liées', () => {
  const titrages = titragesDe(CLASSIFICATION)
  const vides = { composition: '', type_fil: '', titrage: '', couleur: '', fournisseur: '' }

  it('chaque liste ne propose que les valeurs des matières qui passent les autres critères', () => {
    const toutes = optionsDesCriteres(MATIERES, titrages, vides)
    expect(toutes.titrage.map((o) => [o.valeur, o.nombre])).toEqual([
      ['1500', 2],
      ['1800', 1],
    ])
    const pes = optionsDesCriteres(MATIERES, titrages, { ...vides, composition: 'PES' })
    expect(pes.couleur.map((o) => o.valeur)).toEqual(['BLEU', 'ROUGE'])
    expect(pes.fournisseur.map((o) => o.valeur)).toEqual(['Filature Bursa'])
    expect(pes.composition.map((o) => o.valeur)).toEqual(['PES', 'PP'])
  })

  it('le titrage d’une ligne regroupée est son premier mot', () => {
    expect(premierMot('1500 den')).toBe('1500')
  })
})
