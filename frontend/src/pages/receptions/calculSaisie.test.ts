/**
 * La saisie d'un camion sans écran : écart de pesée (BL, sinon reste si l'on pèse au moins ce
 * reste), excédent tous lots ensemble (anom. 4.6), bobines, blocages annoncés, corps envoyé en
 * **une** requête avec une facture par devise (anom. 4.5).
 */
import { describe, expect, it } from 'vitest'

import { ficheEssai } from '../commandes/donneesEssai'
import {
  apporteParLigne,
  attenduDe,
  blocagesSaisie,
  bobines,
  corps,
  depuisFiche,
  devisesDuCamion,
  ecartDe,
  enExcedent,
  estSaisie,
  ligneDuBon,
  ligneHorsCommande,
  nonLivree,
  noteNonLivrees,
  RIEN_N_EST_PESE,
  TOLERANCES_DEFAUT as TOL,
  totaux,
  type LigneSaisie,
} from './calculSaisie'
import { lireTolerances } from './tolerances'
import { receptionEssai } from './donneesEssai'
import type { Magasin } from './types'

const bon = ficheEssai()
const ligneBon = bon.lignes[0]!
const base = (autres: Partial<LigneSaisie> = {}): LigneSaisie => ({
  ...ligneDuBon(bon, ligneBon, undefined, 1),
  ...autres,
})
const MAGASINS = [
  { id: 1, code: 'Magasin principal', type: 'stock_courant', actif: true },
  { id: 2, code: 'Quarantaine', type: 'quarantaine', actif: true },
] as Magasin[]

describe('Saisie d’une réception', () => {
  it('une ligne du bon : reste à livrer, prix confirmé du bon, magasin par défaut', () => {
    const l = base()
    expect(l).toMatchObject({
      commande_ligne_id: ligneBon.id,
      attendu: 522,
      commandee: 1500,
      dejaRecu: 978,
      prix: 27.5,
      prixConfirme: true,
      magasin_id: 1,
      devise: 'MAD',
    })
    expect(estSaisie(l)).toBe(false)
    expect(estSaisie({ ...l, lot_interne: true })).toBe(true)
  })

  it('l’écart se compare au BL ; sans BL, au reste seulement si l’on pèse au moins ce reste', () => {
    expect(attenduDe(base({ quantite_bl: 500, quantite_pesee: 480 }), TOL)).toBe(500)
    expect(ecartDe(base({ quantite_bl: 500, quantite_pesee: 480 }), TOL)).toMatchObject({
      kg: -20,
      hors: true,
    })
    expect(attenduDe(base({ quantite_pesee: 300 }), TOL)).toBe(0)
    expect(attenduDe(base({ quantite_pesee: 520 }), TOL)).toBe(522)
  })

  it('l’excédent se compte tous lots d’une ligne de bon ensemble (deux lots de 300 kg sur 522 restants)', () => {
    const a = base({ cle: 'a', quantite_pesee: 300 })
    const b = base({ cle: 'b', quantite_pesee: 300 })
    expect(apporteParLigne([a, b]).get(ligneBon.id)).toBe(600)
    expect(enExcedent(a, [a], TOL)).toBe(false)
    expect(enExcedent(a, [a, b], TOL)).toBe(false) // 600 ≤ 522 + 150
    const c = base({ cle: 'c', quantite_pesee: 100 })
    expect(enExcedent(a, [a, b, c], TOL)).toBe(true) // 700 > 672
    expect(enExcedent(a, [a, b, { ...c, qualite: 'refuse' }], TOL)).toBe(false)
  })

  it('bobines : palettes × bobines par palette + en plus, poids moyen face au catalogue', () => {
    const l = base({
      quantite_pesee: 505,
      nb_palettes: 1,
      bobines_en_plus: 4,
      bobinesPalette: 96,
      poidsBobine: 5,
    })
    expect(bobines(l)).toEqual({ total: 100, moyen: 5.05, ecart: expect.closeTo(0.01) })
  })

  it('ce qui sera refusé à la validation : pesée nulle, lot, magasin, quarantaine absente, excédent', () => {
    const l = base({ quantite_bl: 500, quantite_pesee: 0, magasin_id: null })
    expect(blocagesSaisie([l], MAGASINS, TOL)).toEqual([
      expect.stringContaining('la pesée est à zéro'),
      expect.stringContaining('le numéro de lot manque'),
      expect.stringContaining('choisir le magasin'),
    ])
    expect(
      blocagesSaisie(
        [base({ quantite_pesee: 10, lot_interne: true, qualite: 'reserve' })],
        [MAGASINS[0]!],
        TOL,
      ),
    ).toEqual([expect.stringContaining('Quarantaine')])
    expect(blocagesSaisie([base({ qualite: 'refuse' })], MAGASINS, TOL)).toEqual([])
  })

  it('une ligne de bon laissée vide n’est pas livrée : aucun blocage, une note ; toutes vides, rien n’est pesé', () => {
    const vide = base({ magasin_id: null, observations: 'pas dans ce camion' })
    const pesee = base({ quantite_pesee: 480, lot_numero: 'FS-1' })
    expect(nonLivree(vide)).toBe(true)
    expect(blocagesSaisie([pesee, vide, base()], MAGASINS, TOL)).toEqual([])
    expect(noteNonLivrees([pesee, vide, base()])).toBe(
      '2 lignes vides : non livrées par ce camion, elles resteront dues sur le bon.',
    )
    expect(noteNonLivrees([pesee, vide])).toBe(
      '1 ligne vide : non livrée par ce camion, elle restera due sur le bon.',
    )
    expect(noteNonLivrees([pesee])).toBe('')
    expect(blocagesSaisie([vide, base()], MAGASINS, TOL)).toEqual([RIEN_N_EST_PESE])
    expect(RIEN_N_EST_PESE).toBe(
      "Rien n'est pesé : saisir ce que le camion a apporté (les lignes laissées vides restent dues sur le bon).",
    )
  })

  it('à moitié remplie, refusée ou hors bon : la ligne n’est pas « non livrée », les blocages restent', () => {
    for (const autres of [
      { quantite_bl: 500 },
      { quantite_pesee: 480 },
      { nb_palettes: 2 },
      { lot_interne: true },
    ])
      expect(nonLivree(base(autres))).toBe(false)
    expect(nonLivree(base({ qualite: 'refuse' }))).toBe(false)
    const hors = { ...base(), commande_ligne_id: null, commande: '' }
    expect(nonLivree(hors)).toBe(false)
    expect(blocagesSaisie([hors], MAGASINS, TOL)).toEqual([
      expect.stringContaining('la pesée est à zéro'),
      expect.stringContaining('le numéro de lot manque'),
    ])
    expect(blocagesSaisie([base({ quantite_pesee: 480 })], MAGASINS, TOL)).toEqual([
      expect.stringContaining('le numéro de lot manque'),
    ])
  })

  it('un camion en deux devises : une seule requête, une facture par devise (sans numéro : absente)', () => {
    const a = base({ quantite_pesee: 480, lot_numero: ' FS-9 ' })
    const h = ligneHorsCommande(
      {
        id: 2,
        reference: 'PP',
        designation: '',
        devise: 'EUR',
        prix_kg: 2.8,
        kg_par_ml: 0,
        poids_bobine: 0,
        bobines_palette: 0,
      } as never,
      'EUR',
      1,
    )
    expect(devisesDuCamion([a, h])).toEqual(['EUR', 'MAD'])
    const c = corps(
      { fournisseurId: 3, date: '2026-10-08', numeroBl: 'BL-1', controlePar: '', observations: '' },
      [a, h],
      {
        MAD: { numero: 'FS-1', date: '2026-10-08', montant: 100, echeance: '' },
        EUR: { numero: '', date: '', montant: null, echeance: '' },
      },
    )
    expect(c.factures).toEqual({ MAD: { numero: 'FS-1', date: '2026-10-08', montant: 100, echeance: null } })
    expect(c.lignes).toHaveLength(2)
    expect(c.lignes[0]).toMatchObject({ lot_numero: 'FS-9', prix: null, devise: '', magasin_id: 1 })
    expect(c.lignes[1]).toMatchObject({ commande_ligne_id: null, devise: 'EUR', prix: 2.8 })
    expect(totaux([a, { ...h, quantite_pesee: 20, qualite: 'refuse' }], TOL)).toMatchObject({ pese: 480 })
  })

  it('un brouillon à corriger repart de ses lignes ; la case « Lot interne » remplace le texte', () => {
    const r = receptionEssai()
    const l = depuisFiche(r.lignes[1]!, r.devise)
    expect(l).toMatchObject({ qualite: 'reserve', devise: 'MAD', quantite_pesee: 505 })
    expect(lireTolerances([{ cle: 'toler_ecart_pesee', valeur: '0.03' } as never])).toEqual({
      ...TOL,
      pesee: 0.03,
    })
  })
})
