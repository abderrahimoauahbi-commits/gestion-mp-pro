/** La saisie d'une opération sans écran : quarantaine, suspension, dépassement, encart, corps. */
import { describe, expect, it } from 'vitest'

import { lotEssai, MAGASINS, matiereEssai } from '../inventaire/donneesEssai'
import { manqueEncart, ligneDeLEncart, ENCART_VIERGE, NOUVEAU_LOT, sensImpose } from './encart'
import { ligneSaisieEssai, MOTIFS, operationEssai } from './donneesEssai'
import { destinations, placesDeLots, placesProposees } from './places'
import {
  corpsOperation,
  depassements,
  incompatibilite,
  manqueOperation,
  saisieDe,
  suspensions,
} from './saisie'
import { motifsPermis } from './useOperation'

const motif = (libelle: string) => MOTIFS.motifs.find((m) => m.libelle === libelle)

describe('quarantaine (an. 2, (d))', () => {
  const lots = [
    lotEssai(),
    lotEssai({
      lot_id: 12,
      lot: 'L24-102',
      magasins: [{ magasin_id: 2, magasin: 'QUAR', type: 'quarantaine', quantite: 95 }],
    }),
  ]
  const places = placesDeLots(lots)

  it('un lot en quarantaine ne se propose qu’avec « Libération de quarantaine »', () => {
    expect(placesProposees(places, 'transfert', undefined, null).map((p) => p.lot)).toEqual(['L24-100'])
    expect(
      placesProposees(places, 'transfert', motif('Mise en quarantaine'), null).map((p) => p.lot),
    ).toEqual(['L24-100'])
    expect(
      placesProposees(places, 'transfert', motif('Libération de quarantaine'), null).map((p) => p.lot),
    ).toEqual(['L24-102'])
  })

  it('mise en quarantaine : vers un magasin de quarantaine seulement ; libération : hors quarantaine', () => {
    expect(destinations(MAGASINS, 1, motif('Mise en quarantaine')).map((g) => g.code)).toEqual(['QUAR'])
    expect(destinations(MAGASINS, 2, motif('Libération de quarantaine')).map((g) => g.code)).toEqual([
      'PRINCIPAL',
    ])
  })

  it('changer de motif revérifie les lignes déjà posées', () => {
    const enQuarantaine = ligneSaisieEssai({ quarantaine: true })
    expect(incompatibilite(enQuarantaine, 'transfert', motif('Rangement'))).toBe(
      '« IMP FRISÉ ROUGE », lot L24-100 : un lot en quarantaine ne sort qu’avec le motif « Libération de quarantaine »',
    )
    expect(incompatibilite(enQuarantaine, 'transfert', motif('Libération de quarantaine'))).toBe('')
    expect(incompatibilite(ligneSaisieEssai(), 'transfert', motif('Libération de quarantaine'))).toMatch(
      /part d’un magasin de quarantaine/,
    )
  })

  it('la libération n’est pas proposée à l’alimentation', () => {
    expect(motifsPermis(MOTIFS, 'transfert', 'alimentation').map((m) => m.libelle)).toEqual([
      'Rangement',
      'Mise en quarantaine',
    ])
    expect(motifsPermis(MOTIFS, 'transfert', 'achats')).toHaveLength(3)
    expect(motifsPermis(MOTIFS, 'transfert', 'direction')).toHaveLength(3)
  })

  it('une mise en quarantaine se justifie (3 caractères) ; un ajustement aussi (5)', () => {
    const s = {
      type: 'transfert' as const,
      date: '2026-10-08',
      motif_id: 14,
      commentaire: 'ab',
      ordre_id: null,
      lignes: [ligneSaisieEssai()],
    }
    expect(manqueOperation(s, motif('Mise en quarantaine'))).toEqual([
      'les observations (ce qui est douteux)',
    ])
    expect(manqueOperation({ ...s, commentaire: 'abc' }, motif('Mise en quarantaine'))).toEqual([])
    expect(
      manqueOperation({ ...s, type: 'ajustement', motif_id: null, commentaire: 'casse' }, undefined),
    ).toEqual(['le motif'])
  })
})

describe('blocages annoncés dès la saisie', () => {
  it('suspension par un inventaire ouvert, seulement pour les matières de son périmètre (an. 20)', () => {
    const ouvert = { id: 1, numero: 'INV-2026-0001', date: '2026-10-08', magasin: 'QUAR', matieres: [1] }
    expect(suspensions([ligneSaisieEssai()], [ouvert], MAGASINS)).toEqual([
      'l’inventaire INV-2026-0001 compte « IMP FRISÉ ROUGE » (QUAR)',
    ])
    expect(suspensions([ligneSaisieEssai({ matiere_id: 2 })], [ouvert], MAGASINS)).toEqual([])
  })

  it('une quantité qui dépasse le lot est un blocage (an. 6)', () => {
    const s = {
      type: 'transfert' as const,
      date: '',
      motif_id: null,
      commentaire: '',
      ordre_id: null,
      lignes: [ligneSaisieEssai({ quantite: 500 })],
    }
    expect(depassements(s)).toEqual(['« IMP FRISÉ ROUGE », lot L24-100 : plus que les 420,0 kg du lot'])
    expect(depassements({ ...s, type: 'ajustement', lignes: [ligneSaisieEssai({ quantite: 500 })] })).toEqual(
      [],
    )
  })
})

describe('l’encart de ligne', () => {
  it('matière retrouvée : sens « + » imposé, lot à créer avec la case « Lot interne » (an. 3, (c))', () => {
    const e = {
      ...ENCART_VIERGE,
      matiere: 1,
      place: NOUVEAU_LOT,
      lot_interne: true,
      magasin: 1,
      kg: 12,
      sens: '+' as const,
    }
    expect(sensImpose('ajustement', e, undefined)).toBe(true)
    expect(manqueEncart('ajustement', e, undefined)).toEqual([])
    const l = ligneDeLEncart(
      'ajustement',
      e,
      matiereEssai(),
      undefined,
      { magasin: () => 'PRINCIPAL', lot: () => '' },
      'n1',
    )
    expect(l).toMatchObject({ lot_id: null, lot_interne: true, lot_numero: '', quantite: 12 })
    expect(
      corpsOperation({
        type: 'ajustement',
        date: '2026-10-08',
        motif_id: 9,
        commentaire: ' retrouvée ',
        ordre_id: null,
        lignes: [l],
      }).lignes[0],
    ).toEqual({
      matiere_id: 1,
      lot_id: null,
      lot_numero: '',
      lot_interne: true,
      magasin_id: 1,
      magasin_destination_id: null,
      quantite: 12,
      unite: 'kg',
      prix: 0,
      devise: 'MAD',
    })
  })

  it('un retour des machines ne rend pas plus que ce qui est parti pour l’ordre', () => {
    const e = { ...ENCART_VIERGE, matiere: 1, place: '11', magasin: 1, kg: 31 }
    expect(manqueEncart('retour_machine', e, undefined, 30)).toEqual([
      'une quantité qui ne dépasse pas les 30,0 kg partis pour l’ordre',
    ])
    expect(manqueEncart('retour_machine', { ...e, kg: 30 }, undefined, 30)).toEqual([])
  })

  it('dit ce qui manque, dont le dépassement du lot', () => {
    const place = placesDeLots([lotEssai()])[0]
    const e = { ...ENCART_VIERGE, matiere: 1, place: place?.cle ?? null, kg: 500 }
    expect(manqueEncart('transfert', e, place)).toEqual([
      'le magasin de destination',
      'une quantité qui ne dépasse pas les 420,0 kg du lot',
    ])
    expect(manqueEncart('ouverture', { ...ENCART_VIERGE, matiere: 1 }, undefined)).toEqual([
      'le numéro de lot (ou cocher « Lot interne »)',
      'le magasin',
      'la quantité',
      'le prix au kilo',
    ])
  })
})

describe('relire une opération', () => {
  it('le brouillon local reprend les lignes et marque la quarantaine', () => {
    const s = saisieDe(
      operationEssai({ lignes: [{ ...operationEssai().lignes[0]!, magasin_id: 2 }] }),
      MAGASINS,
    )
    expect(s.lignes[0]).toMatchObject({ cle: 'l1', quarantaine: true, lot_id: 11 })
  })
})
