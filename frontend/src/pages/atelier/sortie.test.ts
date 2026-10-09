/**
 * Les règles de la sortie vers les machines (ECRANS-PRO partie 3, « Logique de l'envoi ») :
 * conversions kg ↔ bobines ↔ palettes avec l'arrondi dit, bobines entières d'un brouillon rouvert,
 * fils regroupés et écarts, vue repliée, lignes envoyées, raisons écrites sous les boutons.
 */
import { describe, expect, it } from 'vitest'

import { donnees } from './essaiAtelier'
import {
  changerUnite,
  depasse,
  ecartLisible,
  filConforme,
  kgDe,
  lignesDuCorps,
  manqueDemande,
  priseDe,
  priseRouverte,
  qualitesDuCorps,
  regrouper,
  type Prise,
} from './sortie'

const beige = {
  matiere_id: 2,
  reference: 'POIL BEIGE 1100',
  designation: 'Poil beige',
  kg_par_ml: 0,
  poids_bobine: 2.5,
  bobines_palette: 40,
}

describe('Sortie vers les machines', () => {
  it('kg → bobines → palettes : bobine entière, arrondi dit, kilos au gramme', () => {
    const p = priseDe(beige, { lot_id: 3, lot: 'L-2603' }, 48.96)
    const b = changerUnite(p, 'bobine')
    expect(b).toMatchObject({ unite: 'bobine', quantite: 20 })
    expect(kgDe(b)).toBe(50)
    expect(b.arrondi).toMatch(/^arrondi : 50,0\skg au lieu de 49,0\skg$/)
    expect(changerUnite(b, 'bobine')).toBe(b)
    const pal = changerUnite(b, 'palette')
    expect(pal).toMatchObject({ unite: 'palette', quantite: 0.5, arrondi: undefined })
    expect(kgDe(pal)).toBe(50)
    expect(kgDe(changerUnite(pal, 'kg'))).toBe(50)
  })

  it('poids de bobine inconnu : la prise en bobines ne pèse rien (et le dit)', () => {
    const p = priseDe({ ...beige, poids_bobine: 0, bobines_palette: 0 }, { lot_id: 5, lot: 'L-2605' }, 10)
    expect(kgDe(changerUnite(p, 'bobine'))).toBe(0)
  })

  it('un brouillon rouvert : en bobines si le compte tombe juste, sinon au gramme', () => {
    const l = donnees().ORDRE_VALIDE.lignes[0]
    if (!l) throw new Error('fixture')
    expect(priseRouverte({ ...l, bobines: 12, quantite: 30 })).toMatchObject({
      unite: 'bobine',
      quantite: 12,
    })
    expect(priseRouverte({ ...l, bobines: null, quantite: 30.1234 })).toMatchObject({
      unite: 'kg',
      quantite: 30.123,
    })
  })

  it('fils regroupés, écart au prévu, vue « tout est conforme »', () => {
    const d = donnees()
    const prises = d.PROPOSITION.lignes.flatMap((l) => l.lots.map((lot) => priseDe(l, lot, lot.propose)))
    const fils = regrouper(d.PROPOSITION.lignes, prises)
    expect(fils).toHaveLength(d.PROPOSITION.lignes.length)
    expect(fils.every((f) => filConforme(f, () => 1000))).toBe(true)
    const plus = prises.map((p, i) => (i === 0 ? { ...p, quantite: p.quantite + 5 } : p))
    const f0 = regrouper(d.PROPOSITION.lignes, plus)[0]
    if (!f0?.besoin) throw new Error('fixture')
    expect(filConforme(f0, () => 1000)).toBe(false)
    expect(ecartLisible(f0.ecart, f0.besoin.prevu)).toMatchObject({ conforme: false, ton: 'attention' })
    expect(ecartLisible(0.04, 40)).toMatchObject({ conforme: true })
    expect(ecartLisible(-1, 40)).toMatchObject({ ton: 'neutre' })
    expect(ecartLisible(-5, 40)).toMatchObject({ ton: 'critique' })
    expect(ecartLisible(3, 0)).toBeNull()
  })

  it('un fil ajouté à la main se garde à part, hors recette', () => {
    const d = donnees()
    const lot = d.LOTS.find((l) => l.matiere_id === 5)
    if (!lot) throw new Error('fixture')
    const main: Prise = { ...priseDe(lot, lot, 10) }
    const fils = regrouper(d.PROPOSITION.lignes, [main])
    expect(fils.at(-1)).toMatchObject({ matiere_id: 5, ecart: null, sorti: 10 })
    expect(fils.at(-1)?.besoin).toBeUndefined()
  })

  it('dépassement au-delà du disponible (inconnu : pas jugé)', () => {
    const p = priseDe(beige, { lot_id: 3, lot: 'L-2603' }, 10)
    expect(depasse(p, 9.99)).toBe(true)
    expect(depasse(p, 10)).toBe(false)
    expect(depasse(p, -1)).toBe(false)
  })

  it('les lignes envoyées : quantités > 0, unité gardée ; hors recette : aucune qualité', () => {
    const p = changerUnite(priseDe(beige, { lot_id: 3, lot: 'L-2603' }, 48.96), 'bobine')
    const vide = priseDe(beige, { lot_id: 7, lot: 'L-2607' }, 0)
    expect(lignesDuCorps([p, vide])).toEqual([{ lot_id: 3, matiere_id: 2, quantite: 20, unite: 'bobine' }])
    expect(qualitesDuCorps(true, [{ qualite: 1, m2: 100 }])).toEqual([])
    expect(
      qualitesDuCorps(false, [
        { qualite: 1, m2: 100 },
        { qualite: null, m2: 0 },
      ]),
    ).toEqual([{ qualite_id: 1, m2: 100 }])
  })

  it('la raison sous « Voir les fils et les lots », dans l’ordre où on remplit', () => {
    const base = {
      magasin: 1,
      jour: '2026-10-08',
      horsRecette: false,
      fabrications: [{ qualite: 1, m2: 100 }],
    }
    expect(manqueDemande({ ...base, magasin: null })).toBe('Choisir le magasin d’où sort la matière')
    expect(manqueDemande({ ...base, jour: '' })).toBe('Choisir la date')
    expect(manqueDemande({ ...base, fabrications: [] })).toBe('Ajouter une qualité à fabriquer')
    expect(manqueDemande({ ...base, fabrications: [{ qualite: null, m2: 0 }] })).toBe(
      'Choisir la qualité à fabriquer',
    )
    expect(manqueDemande({ ...base, fabrications: [{ qualite: 1, m2: 0 }] })).toBe(
      'Saisir les mètres carrés à fabriquer',
    )
    expect(manqueDemande({ ...base, horsRecette: true, fabrications: [] })).toBe('')
    expect(manqueDemande(base)).toBe('')
  })
})
