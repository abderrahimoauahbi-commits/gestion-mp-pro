/** L'ouverture d'un inventaire sans écran : libellé, conflit, lots figés, manque, corps. */
import { describe, expect, it } from 'vitest'

import { lotEssai, matiereEssai } from './donneesEssai'
import {
  conflitOuvert,
  corpsOuverture,
  libelleAuto,
  lotsFiges,
  manqueOuverture,
  matieresRetenues,
  messageConflit,
  questionOuverture,
  type SaisieOuverture,
} from './ouverture'

const S: SaisieOuverture = {
  libelle: '',
  date: '2026-10-08',
  magasin: 1,
  tolerance: 2,
  perimetre: 'tout',
  roles: [],
  compositions: [],
  classes: [],
  matieres: [],
  ecartees: [],
}

describe('ouvrir un inventaire', () => {
  it('le libellé suit le périmètre et le magasin (an. 16)', () => {
    expect(libelleAuto(S, 'PRINCIPAL', '')).toBe('Inventaire de tout le stock PRINCIPAL')
    expect(libelleAuto({ ...S, perimetre: 'famille' }, null, 'Poil, classe A')).toBe(
      'Inventaire par famille (Poil, classe A)',
    )
    expect(libelleAuto({ ...S, perimetre: 'matieres', matieres: [1, 2] }, 'QUAR', '')).toBe(
      'Inventaire de 2 matière(s) — QUAR',
    )
    expect(libelleAuto({ ...S, perimetre: 'tournant' }, 'QUAR', '')).toBe('Inventaire tournant — QUAR')
  })

  it('un inventaire par magasin ; un inventaire de tous les magasins exclut tout autre', () => {
    const ici = { id: 1, numero: 'INV-2026-0001', date: '2026-10-08', magasin: 'PRINCIPAL', matieres: [1] }
    const tous = { ...ici, numero: 'INV-2026-0002', magasin: null }
    expect(conflitOuvert([ici], 'QUAR')).toBeNull()
    expect(conflitOuvert([ici], 'PRINCIPAL')).toBe(ici)
    expect(conflitOuvert([ici], null)).toBe(ici)
    expect(conflitOuvert([tous], 'QUAR')).toBe(tous)
    expect(messageConflit(ici, null)).toBe(
      'L’inventaire INV-2026-0001 est déjà ouvert sur « PRINCIPAL » : un inventaire de tous les magasins attend qu’il soit validé ou abandonné. Le valider ou l’abandonner d’abord.',
    )
  })

  it('les lots figés : soldes > 0 du magasin et des matières retenues', () => {
    const lots = [
      lotEssai(),
      lotEssai({
        lot_id: 12,
        matiere_id: 2,
        magasins: [
          { magasin_id: 1, magasin: 'PRINCIPAL', type: 'stock_courant', quantite: 10, fond_de_lot: false },
          { magasin_id: 2, magasin: 'QUAR', type: 'quarantaine', quantite: 5, fond_de_lot: false },
        ],
      }),
    ]
    expect(lotsFiges(lots, null, null)).toBe(3)
    expect(lotsFiges(lots, 1, null)).toBe(2)
    expect(lotsFiges(lots, 1, new Set([2]))).toBe(1)
    const famille = matieresRetenues(
      { ...S, perimetre: 'famille', roles: [1] },
      [matiereEssai(), matiereEssai({ id: 2, role_id: 3 })],
      [],
    )
    expect([...(famille ?? [])]).toEqual([1])
    expect(questionOuverture(2, 'PRINCIPAL')).toBe(
      'Figer 2 lot(s) du magasin PRINCIPAL et suspendre leurs mouvements ?',
    )
    expect(questionOuverture(null, null)).toBe(
      'Figer les lots des matières retenues de tous les magasins et suspendre leurs mouvements ?',
    )
  })

  it('ce qui manque : la tolérance bornée 0…100 %, un critère, une matière', () => {
    expect(manqueOuverture(S)).toEqual([])
    expect(manqueOuverture({ ...S, tolerance: 150 })).toEqual(['la tolérance (0 à 100 %)'])
    expect(manqueOuverture({ ...S, perimetre: 'famille' })).toEqual(['au moins un critère coché'])
    expect(manqueOuverture({ ...S, perimetre: 'matieres' })).toEqual(['au moins une matière'])
    expect(manqueOuverture({ ...S, date: '2026-10-09' }, undefined, '2026-10-08')).toEqual(['la date'])
  })

  it('le corps : tolérance en fraction, critères du périmètre, matières dues retenues', () => {
    expect(
      corpsOuverture({ ...S, perimetre: 'tournant', ecartees: [2] }, 'Inventaire tournant', [1, 2, 3]),
    ).toEqual({
      date: '2026-10-08',
      magasin_id: 1,
      libelle: 'Inventaire tournant',
      tolerance: 0.02,
      criteres: { matieres: [1, 3], roles: [], compositions: [], classes_abc: [] },
    })
    expect(
      corpsOuverture({ ...S, perimetre: 'famille', classes: ['A'], libelle: ' Fin de mois ' }, 'x', [])
        .libelle,
    ).toBe('Fin de mois')
  })
})
