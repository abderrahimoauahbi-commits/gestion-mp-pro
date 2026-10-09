/**
 * Le moteur de saisie d'un ordre : ce que le serveur refusera est annoncé avant l'envoi, avec ses
 * mots (critère F2 « saisie d'ordre : blocages annoncés ») ; « Recalculer » garde les matières
 * ajoutées à la main ; ce qui manque pour garder en brouillon ou demander la proposition est dit.
 */
import { describe, expect, it } from 'vitest'

import type { LigneProposee } from './donnees'
import { dernierOrdre, nomMetier } from './donnees'
import proposition from './essais/proposition.json'
import { blocagesRetour } from './RetourMachines'
import sortis from './essais/lots-sortis.json'
import {
  blocagesSaisie,
  filsDe,
  manqueBrouillon,
  manqueProposer,
  prisesProposees,
  recalculer,
  type ContexteBlocages,
  type Prise,
} from './ordre'
import type { LotSorti } from './donnees'

const lignes = proposition.lignes as LigneProposee[]

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
  magasin: 'Magasin principal',
  inventaires: [],
  dispo: new Map([[900, 50]]),
  ...c,
})

describe('blocagesSaisie', () => {
  it('rien à dire quand tout passe', () => {
    expect(blocagesSaisie([prise({})], contexte())).toEqual([])
  })

  it('date future, période close, ordre plus récent déjà validé : les mots du serveur', () => {
    const b = blocagesSaisie([prise({})], contexte({ jour: '2026-10-10' }))
    expect(b).toEqual(['Date dans le futur (10/10/2026) : un mouvement se saisit le jour où il a lieu.'])
    expect(blocagesSaisie([prise({})], contexte({ jour: '2026-09-30', cloture: '2026-09-30' }))[0]).toBe(
      "La période jusqu'au 30/09/2026 est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir.",
    )
    expect(blocagesSaisie([prise({})], contexte({ jour: '2026-10-01', dernier: '2026-10-07' }))[0]).toBe(
      'Un ordre du 07/10/2026 est déjà validé : les numéros suivent les dates, cet ordre ne peut pas être daté avant. Pour un oubli, le dater du 07/10/2026 et écrire la vraie date dans le commentaire.',
    )
  })

  it('un inventaire ne bloque que les matières de son périmètre dans son magasin (K2)', () => {
    const inv = { numero: 'INV-2026-0003', date: '2026-10-08', magasin: 'Magasin principal', matieres: [99] }
    expect(blocagesSaisie([prise({})], contexte({ inventaires: [inv] }))[0]).toBe(
      "L'inventaire INV-2026-0003 (Magasin principal, du 08/10/2026) est en cours : les mouvements y sont suspendus jusqu'à sa validation. Garder en brouillon, ou attendre.",
    )
    expect(blocagesSaisie([prise({})], contexte({ inventaires: [{ ...inv, matieres: [1] }] }))).toEqual([])
    expect(blocagesSaisie([prise({})], contexte({ inventaires: [{ ...inv, magasin: 'ATELIER' }] }))).toEqual(
      [],
    )
    expect(blocagesSaisie([prise({})], contexte({ inventaires: [{ ...inv, magasin: null }] }))[0]).toContain(
      '(tous les magasins,',
    )
  })

  it('un lot qui ne porte pas ce qu’on lui demande à la date, toutes ses lignes additionnées', () => {
    const deux = [prise({ cle: 'a', kg: 30 }), prise({ cle: 'b', kg: 30 })]
    expect(blocagesSaisie(deux, contexte()).map((x) => x.replace(/\u00a0/g, ' '))).toEqual([
      'lot L-900 de REF À LA MAIN : 50,0 kg seulement dans « Magasin principal », 60,0 kg demandés',
    ])
    expect(blocagesSaisie([prise({})], contexte({ dispo: new Map() }))[0]).toContain('épuisé')
    // Le disponible ne s'est pas encore lu : rien n'est annoncé à tort.
    expect(blocagesSaisie([prise({ kg: 1e6 })], contexte({ dispo: null }))).toEqual([])
  })
})

describe('proposition et prises', () => {
  it('les lots proposés au gramme près, puis « Recalculer » garde les matières ajoutées à la main', () => {
    const proposees = prisesProposees(lignes)
    expect(proposees.length).toBe(lignes.reduce((n, l) => n + l.lots.length, 0))
    const avant = [...proposees, prise({})]
    const apres = recalculer(avant, lignes, lignes)
    expect(apres.filter((x) => x.matiere_id === 99)).toHaveLength(1)
    expect(apres.length).toBe(avant.length)
  })

  it('les fils : un par matière, le sorti et l’écart au prévu', () => {
    const fils = filsDe(lignes, prisesProposees(lignes))
    for (const f of fils) {
      expect(f.besoin).toBeDefined()
      expect(Math.abs(f.ecart ?? 1)).toBeLessThan(0.01)
    }
    const main = filsDe([], [prise({ kg: 4 })])
    expect(main[0]).toMatchObject({ reference: 'REF À LA MAIN', sorti: 4, ecart: null })
  })

  it('ce qui manque est dit (P2-11)', () => {
    expect(manqueBrouillon([])).toEqual(['au moins une ligne de plus d’un gramme'])
    expect(manqueBrouillon([prise({ unite: 'bobine' })])[0]).toContain('poids de bobine inconnu')
    expect(
      manqueProposer({ jour: '', magasin: null, fabrications: [{ qualite_id: null, m2: null }] }),
    ).toEqual(['le magasin', 'la date', 'la qualité de chaque ligne', 'les m² à tisser de chaque qualité'])
  })
})

describe('retour des machines : blocages annoncés', () => {
  const lots = sortis as LotSorti[]
  const premier = lots[0] as LotSorti

  it('plus que ce qui est parti, lot inventorié, date future', () => {
    const trop = { [premier.lot_id]: { kg: premier.sorti_net + 1, unite: 'kg' as const } }
    expect(blocagesRetour(lots, trop, '2026-10-09', null)[0]).toMatch(
      /^1 lot\(s\) dépassent ce qui est parti : /,
    )
    const inventorie = [{ ...premier, blocage: "l'inventaire INV-1 est en cours sur « MAG »" }]
    const un = { [premier.lot_id]: { kg: 1, unite: 'kg' as const } }
    expect(blocagesRetour(inventorie, un, '2026-10-09', null)).toEqual([
      `lot ${premier.lot} de ${premier.reference} : l'inventaire INV-1 est en cours sur « MAG »`,
    ])
    expect(blocagesRetour(lots, {}, '2026-10-09', null)).toEqual([])
  })
})

describe('outils', () => {
  it('le dernier ordre validé ou annulé, hors brouillons et hors l’ordre lui-même', () => {
    const o = (id: number, date: string, statut: string) => ({ id, date, statut }) as never
    expect(
      dernierOrdre([
        o(1, '2026-10-01', 'valide'),
        o(2, '2026-10-05', 'annule'),
        o(3, '2026-10-09', 'brouillon'),
      ]),
    ).toBe('2026-10-05')
    expect(dernierOrdre([o(1, '2026-10-01', 'valide'), o(2, '2026-10-05', 'valide')], 2)).toBe('2026-10-01')
  })

  it('« CODE · Nom » d’un métier', () => {
    expect(nomMetier({ code: 'M1', nom: 'Métier un' })).toBe('M1 · Métier un')
    expect(nomMetier({ code: 'M1', nom: '' })).toBe('M1')
  })
})
