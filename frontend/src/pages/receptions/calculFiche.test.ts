/** La fiche d'une réception sans écran : blocages regroupés, échéance dite, question de validation, facture. */
import { describe, expect, it } from 'vitest'

import { ajouterJours, aujourdhui } from '../../lib/heure'
import { date } from '../../lib/format'

import {
  corpsFacture,
  echeanceLisible,
  questionValidation,
  resumerBlocages,
  versFormeFacture,
} from './calculFiche'
import { RIEN_N_EST_PESE } from './calculSaisie'
import { receptionEssai } from './donneesEssai'
import type { LigneReception } from './types'

describe('Fiche d’une réception', () => {
  it('au-delà de deux lignes sans pesée ou sans lot, une phrase pour chacune', () => {
    const pesee = (n: number) => `« R${n} » : la pesée est à zéro. La saisir.`
    const lot = (n: number) => `« R${n} » : le numéro de lot manque.`
    expect(resumerBlocages([pesee(1), pesee(2), pesee(3), lot(1), 'Autre refus.'])).toEqual([
      'Autre refus.',
      '3 lignes sans pesée : la saisir, ou marquer la ligne « refusé ».',
      lot(1),
    ])
  })

  it('échéance : dépassée, aujourd’hui, à venir (au jour de l’usine)', () => {
    const avant = ajouterJours(aujourdhui(), -3)
    const apres = ajouterJours(aujourdhui(), 12)
    expect(echeanceLisible(avant)).toBe(`échéance ${date(avant)}, dépassée de 3 j`)
    expect(echeanceLisible(aujourdhui())).toBe('échéance aujourd’hui')
    expect(echeanceLisible(apres)).toBe(`échéance ${date(apres)} (dans 12 j)`)
  })

  it('la question de la validation dit ce qui entre, en quarantaine, refusé ; ou la trace du refus', () => {
    const r = receptionEssai()
    expect(questionValidation(r)).toBe(
      '1 ligne(s) en stock disponible, 1 en quarantaine — 1 483 kg. 1 écart(s) de pesée hors tolérance. Ensuite, elle ne se modifie plus.',
    )
    const refusee = receptionEssai({ lignes: r.lignes.map((l) => ({ ...l, qualite: 'refuse' })) })
    expect(questionValidation(refusee)).toMatch(/^Toutes les lignes sont refusées/)
  })

  it('la question de la validation annonce les lignes non livrées retirées, dues sur le bon', () => {
    const r = receptionEssai()
    const [l1, l2] = r.lignes as [LigneReception, LigneReception]
    const vide = (id: number): LigneReception => ({
      ...l2,
      id,
      lot_numero: '',
      lot_interne: false,
      lot_id: null,
      quantite_bl: 0,
      quantite_pesee: 0,
      nb_palettes: 0,
      bobines_en_plus: 0,
      nb_bobines: 0,
      qualite: 'conforme',
      hors_tolerance: false,
    })
    const vides = Array.from({ length: 23 }, (_, i) => vide(10 + i))
    expect(questionValidation({ ...r, lignes: [l1, ...vides], pese: 978 })).toBe(
      '1 ligne(s) en stock disponible — 978 kg. 1 écart(s) de pesée hors tolérance. 23 lignes non livrées par ce camion seront retirées : elles restent dues sur le bon BC-2026-0002. Ensuite, elle ne se modifie plus.',
    )
    expect(questionValidation({ ...r, lignes: [l1, vide(9)], pese: 978 })).toContain(
      ' 1 ligne non livrée par ce camion sera retirée : elle reste due sur le bon BC-2026-0002.',
    )
    expect(questionValidation({ ...r, lignes: [{ ...l1, qualite: 'refuse' }, vide(9)] })).toMatch(
      /^Toutes les lignes sont refusées.* 1 ligne non livrée par ce camion sera retirée/,
    )
    expect(questionValidation({ ...r, lignes: vides })).toBe(RIEN_N_EST_PESE)
    expect(questionValidation(r)).not.toContain('non livrée')
  })

  it('facture : seuls les champs changés partent ; un numéro vidé détache', () => {
    const r = receptionEssai()
    const f = versFormeFacture(r)
    expect(corpsFacture(f, f, 4)).toEqual({ version: 4 })
    expect(corpsFacture({ ...f, numero: ' ', montant: 39000 }, f, 4)).toEqual({
      version: 4,
      numero: null,
      montant: 39000,
    })
  })
})
