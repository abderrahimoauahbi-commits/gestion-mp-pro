/**
 * Le moteur unique de saisie d'un ordre (bureau F2 et téléphone F3) : ce que le serveur refusera
 * est annoncé avant l'envoi avec ses mots ; « Recalculer » garde les matières ajoutées à la main ;
 * fils et écarts au prévu (une seule règle) ; brouillon rouvert ; corps envoyé en kilos ; ce qui
 * manque est dit. Essais repris des lots F2 (`sorties/ordre.test.ts`) et F3 (`atelier/sortie.test.ts`).
 */
import { describe, expect, it } from 'vitest'

import { donnees } from '../pages/atelier/essaiAtelier'
import proposition from '../pages/sorties/essais/proposition.json'
import {
  blocagesSaisie,
  corpsOrdre,
  depasse,
  ecartLisible,
  filConforme,
  filsDe,
  manqueBrouillon,
  manqueProposer,
  priseDe,
  priseRouverte,
  prisesProposees,
  qualitesDuCorps,
  recalculer,
  tonEcart,
  type ContexteBlocages,
  type Prise,
} from './ordre'
import type { Schema } from './types'

const lignes = proposition.lignes as Schema<'LigneProposee'>[]

const prise = (p: Partial<Prise>): Prise => ({
  cle: 'x',
  matiere_id: 99,
  reference: 'REF À LA MAIN',
  designation: '',
  kg_par_ml: 0,
  poids_bobine: 0,
  bobines_palette: 0,
  lot_id: 900,
  lot: 'L-900',
  kg: 10,
  unite: 'kg',
  ...p,
})

const contexte = (c: Partial<ContexteBlocages> = {}): ContexteBlocages => ({
  jour: '2026-10-09',
  aujourdhui: '2026-10-09',
  cloture: null,
  dernier: null,
  magasin: { code: 'MP', nom: 'Magasin principal' },
  inventaires: [],
  dispo: new Map([[900, 50]]),
  ...c,
})

const beige = {
  matiere_id: 2,
  reference: 'POIL BEIGE 1100',
  designation: 'Poil beige',
  kg_par_ml: 0,
  poids_bobine: 2.5,
  bobines_palette: 40,
}

describe('blocagesSaisie : les mots du serveur, avant l’envoi', () => {
  it('rien à dire quand tout passe', () => {
    expect(blocagesSaisie([prise({})], contexte())).toEqual([])
  })

  it('date future, période close, ordre plus récent déjà validé', () => {
    const b = blocagesSaisie([prise({})], contexte({ jour: '2026-10-10' }))
    expect(b).toEqual(['Date dans le futur (10/10/2026) : un mouvement se saisit le jour où il a lieu.'])
    expect(blocagesSaisie([prise({})], contexte({ jour: '2026-09-30', cloture: '2026-09-30' }))[0]).toBe(
      "La période jusqu'au 30/09/2026 est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir.",
    )
    expect(blocagesSaisie([prise({})], contexte({ jour: '2026-10-01', dernier: '2026-10-07' }))[0]).toBe(
      'Un ordre du 07/10/2026 est déjà validé : les numéros suivent les dates, cet ordre ne peut pas être daté avant. Pour un oubli, le dater du 07/10/2026 et écrire la vraie date dans les observations.',
    )
  })

  it('un inventaire ne bloque que les matières de son périmètre dans son magasin (K2), lu par son nom', () => {
    const inv = { numero: 'INV-2026-0003', date: '2026-10-08', magasin: 'Magasin principal', matieres: [99] }
    expect(blocagesSaisie([prise({})], contexte({ inventaires: [inv] }))[0]).toBe(
      "L'inventaire INV-2026-0003 (Magasin principal, du 08/10/2026) est en cours : les mouvements y sont suspendus jusqu'à sa validation. Garder en brouillon, ou attendre.",
    )
    expect(blocagesSaisie([prise({})], contexte({ inventaires: [{ ...inv, matieres: [1] }] }))).toEqual([])
    expect(blocagesSaisie([prise({})], contexte({ inventaires: [{ ...inv, magasin: 'ATELIER' }] }))).toEqual(
      [],
    )
    // Le contexte nomme le magasin par son nom : le code de l'ordre ne doit pas le faire passer.
    expect(blocagesSaisie([prise({})], contexte({ inventaires: [{ ...inv, magasin: 'MP' }] }))).toEqual([])
    expect(blocagesSaisie([prise({})], contexte({ inventaires: [{ ...inv, magasin: null }] }))[0]).toContain(
      '(tous les magasins,',
    )
  })

  it('un lot qui ne porte pas ce qu’on lui demande à la date, toutes ses lignes additionnées', () => {
    const deux = [prise({ cle: 'a', kg: 30 }), prise({ cle: 'b', kg: 30 })]
    expect(blocagesSaisie(deux, contexte()).map((x) => x.replace(/\u00a0/g, ' '))).toEqual([
      'lot L-900 de REF À LA MAIN : 50 kg seulement dans « MP », 60 kg demandés',
    ])
    expect(blocagesSaisie([prise({})], contexte({ dispo: new Map() }))[0]).toContain('épuisé')
    // Le disponible ne s'est pas encore lu : rien n'est annoncé à tort.
    expect(blocagesSaisie([prise({ kg: 1e6 })], contexte({ dispo: null }))).toEqual([])
  })
})

describe('proposition, prises et fils', () => {
  it('les lots proposés au gramme près, puis « Recalculer » garde les matières ajoutées à la main', () => {
    const proposees = prisesProposees(lignes)
    expect(proposees.length).toBe(lignes.reduce((n, l) => n + l.lots.length, 0))
    const avant = [...proposees, prise({})]
    const apres = recalculer(avant, lignes, lignes)
    expect(apres.filter((x) => x.matiere_id === 99)).toHaveLength(1)
    expect(apres.length).toBe(avant.length)
  })

  it('les fils : un par matière, le sorti et l’écart au prévu ; un fil ajouté à la main, hors recette', () => {
    const fils = filsDe(lignes, prisesProposees(lignes))
    for (const f of fils) {
      expect(f.besoin).toBeDefined()
      expect(Math.abs(f.ecart ?? 1)).toBeLessThan(0.01)
    }
    const main = filsDe(lignes, [prise({ kg: 4 })])
    expect(main.at(-1)).toMatchObject({ reference: 'REF À LA MAIN', sorti: 4, ecart: null })
    expect(main.at(-1)?.besoin).toBeUndefined()
  })

  it('vue « tout est conforme » et une seule règle d’écart (P2-25)', () => {
    const d = donnees()
    const prises = prisesProposees(d.PROPOSITION.lignes)
    const fils = filsDe(d.PROPOSITION.lignes, prises)
    expect(fils.every((f) => filConforme(f, () => 1000))).toBe(true)
    const plus = prises.map((p, i) => (i === 0 ? { ...p, kg: (p.kg ?? 0) + 5 } : p))
    const f0 = filsDe(d.PROPOSITION.lignes, plus)[0]
    if (!f0?.besoin) throw new Error('fixture')
    expect(filConforme(f0, () => 1000)).toBe(false)
    expect(ecartLisible(f0.ecart, f0.besoin.prevu)).toMatchObject({ conforme: false, ton: 'attention' })
    expect(ecartLisible(0.04, 40)).toMatchObject({ conforme: true })
    // À 5 % près c'est juste, comme le badge des Sorties ; au-delà : excès attention, manque critique.
    expect(ecartLisible(-1, 40)).toMatchObject({ conforme: false, ton: 'ok' })
    expect(ecartLisible(-5, 40)).toMatchObject({ ton: 'critique' })
    expect(ecartLisible(3, 0)).toBeNull()
    expect([tonEcart(0.05), tonEcart(0.06), tonEcart(-0.06), tonEcart(null)]).toEqual([
      'ok',
      'attention',
      'critique',
      undefined,
    ])
  })

  it('un brouillon rouvert : compté en bobines si le compte tombe juste, sinon au gramme', () => {
    const l = donnees().ORDRE_VALIDE.lignes[0]
    if (!l) throw new Error('fixture')
    expect(priseRouverte({ ...l, bobines: 12, quantite: 30 })).toMatchObject({ unite: 'bobine', kg: 30 })
    expect(priseRouverte({ ...l, bobines: null, quantite: 30.1234 })).toMatchObject({
      unite: 'kg',
      kg: 30.123,
    })
  })

  it('dépassement au-delà du disponible (inconnu : pas jugé)', () => {
    const p = priseDe(beige, { lot_id: 3, lot: 'L-2603' }, 10)
    expect(depasse(p, 9.99)).toBe(true)
    expect(depasse(p, 10)).toBe(false)
    expect(depasse(p, -1)).toBe(false)
  })
})

describe('le corps envoyé et ce qui manque', () => {
  const demande = {
    jour: '2026-10-08',
    metier: 4,
    commentaire: '  équipe B ',
    horsRecette: false,
    fabrications: [
      { qualite_id: 1, m2: 100 },
      { qualite_id: null, m2: null },
    ],
  }

  it('les lignes d’au moins un gramme, en kilos ; hors recette : aucune qualité', () => {
    const p = { ...priseDe(beige, { lot_id: 3, lot: 'L-2603' }, 50), unite: 'bobine' as const }
    const vide = priseDe(beige, { lot_id: 7, lot: 'L-2607' }, 0)
    expect(corpsOrdre(demande, 2, [p, vide])).toEqual({
      date: '2026-10-08',
      magasin_id: 2,
      metier_id: 4,
      commentaire: 'équipe B',
      qualites: [{ qualite_id: 1, m2: 100 }],
      lignes: [{ lot_id: 3, matiere_id: 2, quantite: 50, unite: 'kg' }],
    })
    expect(qualitesDuCorps({ ...demande, horsRecette: true })).toEqual([])
  })

  it('ce qui manque est dit (P2-11), dans l’ordre où on remplit', () => {
    expect(manqueBrouillon([])).toEqual(['au moins une ligne de plus d’un gramme'])
    expect(manqueBrouillon([prise({ unite: 'bobine' })])[0]).toContain('poids de bobine inconnu')
    expect(
      manqueProposer({ jour: '', magasin: null, fabrications: [{ qualite_id: null, m2: null }] }),
    ).toEqual(['le magasin', 'la date', 'la qualité de chaque ligne', 'les m² à tisser de chaque qualité'])
    expect(manqueProposer({ jour: '2026-10-08', magasin: 1, horsRecette: true, fabrications: [] })).toEqual(
      [],
    )
    expect(manqueProposer({ jour: '2026-10-08', magasin: 1, fabrications: [] })).toEqual([
      'la qualité de chaque ligne',
    ])
  })
})
