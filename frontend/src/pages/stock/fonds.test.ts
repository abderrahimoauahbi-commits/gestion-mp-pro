/**
 * Les fonds de lot à l'écran (lot FOND-DE-LOT) : la marque écrite comme le serveur (« fond de lot
 * (< 100 g) »), les poids en grammes sous le kilo, le compte des fonds d'une liste, qui met au
 * rebut quoi, et les fonds laissés en stock par une proposition.
 */
import { describe, expect, it } from 'vitest'

import {
  fondsDe,
  marqueFond,
  poidsFond,
  questionCourte,
  questionRebut,
  rebutPermis,
  soldesFonds,
} from './fonds'
import { fondsLaisses } from './fondsProposes'
import type { LotSolde, SoldeMagasin } from './types'

const solde = (
  quantite: number,
  fond: boolean,
  type = 'stock_courant',
  magasin = 'Morocco',
): SoldeMagasin => ({
  magasin_id: type === 'quarantaine' ? 2 : 1,
  magasin,
  type,
  quantite,
  fond_de_lot: fond,
})

const lot = (magasins: SoldeMagasin[]): LotSolde => ({
  lot_id: 1,
  lot: 'HT-280502-0427',
  interne: false,
  matiere_id: 1,
  reference: 'POIL ROUGE 2900',
  designation: '',
  role: 'Poil',
  kg_par_ml: 0,
  fournisseur: '',
  entre_le: '2028-05-02',
  poids_bobine: 2,
  bobines_palette: 0,
  quantite: magasins.reduce((t, g) => t + g.quantite, 0),
  disponible: 0,
  quarantaine: 0,
  magasins,
  bobines: null,
  statut: 'disponible',
  historique: { entre: 0, sorti: 0, dernier_mouvement: null, ordres: [] },
  fond_de_lot: magasins.some((g) => g.fond_de_lot),
  fond_de_lot_kg: magasins.filter((g) => g.fond_de_lot).reduce((t, g) => t + g.quantite, 0),
  version: 1,
})

describe('fonds de lot', () => {
  it('la marque et les poids s’écrivent comme le serveur', () => {
    expect(marqueFond(0.1)).toBe('fond de lot (< 100 g)')
    expect(marqueFond(2)).toBe('fond de lot (< 2 kg)')
    expect(marqueFond(0)).toBe('')
    expect(poidsFond(0.056)).toBe('56 g')
    expect(poidsFond(3.151)).toBe('3,15 kg')
  })

  it('compte un fond par lot et par magasin, et ce qu’ils pèsent', () => {
    const lots = [
      lot([solde(0.056, true), solde(300, false, 'stock_courant', 'Polyfashions')]),
      lot([solde(0.05, true, 'quarantaine', 'Quarantaine')]),
      lot([solde(5, false)]),
    ]
    expect(fondsDe(lots)).toEqual({ nombre: 2, kg: 0.106 })
    expect(soldesFonds(lots[0] as LotSolde).map((g) => g.magasin)).toEqual(['Morocco'])
  })

  it('qui met au rebut : un fond pour tous, la quarantaine pas depuis l’atelier, au-dessus la direction avec motif', () => {
    expect(rebutPermis('achats', solde(0.056, true))).toMatchObject({ permis: true, motifExige: false })
    expect(rebutPermis('alimentation', solde(0.056, true))).toMatchObject({ permis: true })
    expect(rebutPermis('alimentation', solde(0.05, true, 'quarantaine'))).toMatchObject({ permis: false })
    expect(rebutPermis('alimentation', solde(0.05, true, 'quarantaine')).raison).toMatch(/quarantaine/)
    expect(rebutPermis('achats', solde(3.151, false))).toMatchObject({ permis: false })
    expect(rebutPermis('achats', solde(3.151, false)).raison).toMatch(/pas un fond de lot/)
    expect(rebutPermis('direction', solde(3.151, false))).toMatchObject({ permis: true, motifExige: true })
    expect(questionCourte({ lot: 'HT-1' }, solde(0.056, true))).toBe(
      'Rebut : 56 g du lot HT-1 dans « Morocco » ?',
    )
    expect(questionRebut({ lot: 'HT-1', reference: 'POIL' }, solde(0.056, true))).toMatch(
      /Mettre au rebut 56 g du lot HT-1 \(POIL\) dans « Morocco »/,
    )
  })

  it('les fonds laissés en stock par une proposition sont nommés avec leur poids et leur fil', () => {
    const base = {
      matiere_id: 1,
      designation: '',
      role: 'Poil',
      prevu: 10,
      kg_par_ml: 0,
      poids_bobine: 2,
      bobines_palette: 0,
      par_qualite: [],
      lots: [],
      manque: 0,
    }
    const dispo = (lot: string, disponible: number, fond_de_lot: boolean) => ({
      lot_id: 1,
      lot,
      entre_le: '2028-05-02',
      disponible,
      poids_bobine: 2,
      propose: 0,
      fond_de_lot,
    })
    const besoins = [
      {
        ...base,
        reference: 'POIL ROUGE',
        disponibles: [dispo('HT-1', 0.056, true), dispo('HT-2', 400, false)],
      },
      { ...base, reference: 'TRAME', disponibles: [dispo('T-9', 0.01, true)] },
    ]
    expect(fondsLaisses(besoins)).toEqual(['HT-1 (56 g, POIL ROUGE)', 'T-9 (10 g, TRAME)'])
  })
})
