/**
 * Les outils des Sorties : blocages annoncés du retour des machines, dernier ordre, nom d'un métier.
 * Le moteur de saisie d'un ordre (bureau et téléphone) est éprouvé dans `lib/ordre.test.ts`.
 */
import { describe, expect, it } from 'vitest'

import { dernierOrdre, nomMetier, type LotSorti } from './donnees'
import sortis from './essais/lots-sortis.json'
import { blocagesRetour } from './RetourMachines'

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
