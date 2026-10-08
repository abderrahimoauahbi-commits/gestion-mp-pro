/** Essais de la règle unique d'affichage (ARCHITECTURE § 9.3), ligne par ligne de la table. */
import { describe, expect, it } from 'vitest'

import {
  arrondi,
  cours,
  date,
  horodatage,
  horodatageRelatif,
  ilYa,
  jourRelatif,
  jours,
  kg,
  kgEntier,
  kgEtMetres,
  kgTelephone,
  m2,
  metres,
  mois,
  moisCourt,
  montant,
  montantCourt,
  montantPrecis,
  montants,
  nombre,
  nombreSigne,
  part,
  partSignee,
  poidsBobine,
  pourcent,
  prix,
  prixUnite,
  VIDE,
} from './format'
import { recalerHorloge } from './heure'

/** Dans les textes attendus, « ~ » note l'espace insécable (U+00A0). */
const n = (texte: string) => texte.replace(/~/g, '\u00a0')

describe('Arrondi : ARRONDI d’Excel, demi loin de zéro, sur la valeur brute', () => {
  it.each([
    [2.5, 0, 3],
    [-2.5, 0, -3],
    [0.5, 0, 1],
    [1.5, 0, 2],
    [2.675, 2, 2.68],
    [1.005, 2, 1.01],
    [-1.005, 2, -1.01],
    [1.45, 1, 1.5],
    [8.345, 2, 8.35],
    [1234.5, 0, 1235],
    [0.0005, 3, 0.001],
    [1e-7, 2, 0],
    [123456.785, 2, 123456.79],
  ])('arrondi(%s, %s) = %s', (valeur, d, attendu) => {
    expect(arrondi(valeur, d)).toBe(attendu)
  })

  it('ne rend jamais −0', () => {
    expect(Object.is(arrondi(-0.0004, 3), 0)).toBe(true)
    expect(Object.is(arrondi(-0.4, 0), 0)).toBe(true)
  })

  it('arrondit une seule fois : 1,449 → 1 à zéro décimale (pas 1,45 → 1,5 → 2)', () => {
    expect(nombre(1.449, 0)).toBe('1')
    expect(nombre(1.449, 1)).toBe('1,4')
  })
})

describe('Milliers, décimales, signe', () => {
  it('sépare les milliers par une espace insécable', () => {
    expect(nombre(17398184)).toBe('17 398 184')
    expect(nombre(1234)).toBe(n('1~234'))
    expect(nombre(999)).toBe('999')
    expect(nombre(1234567.891, 2)).toBe(n('1~234~567,89'))
  })

  it('écrit la virgule décimale et le nombre exact de décimales', () => {
    expect(nombre(12, 2)).toBe('12,00')
    expect(nombre(0.1 + 0.2, 2)).toBe('0,30')
  })

  it('écrit le moins typographique « − »', () => {
    expect(nombre(-1234.5, 1)).toBe(n('−1~234,5'))
    expect(nombre(-3)).toBe('−3')
  })

  it.each([
    [-0.04, 1, '0,0'],
    [-0.4, 0, '0'],
    [-0.0049, 2, '0,00'],
    [-0, 0, '0'],
  ])('jamais « -0 » : nombre(%s, %s) = %s', (v, d, attendu) => {
    expect(nombre(v, d)).toBe(attendu)
    expect(nombre(v, d)).not.toMatch(/[-−]/)
  })

  it('jamais « −0,0 % »', () => {
    expect(pourcent(-0.04)).toBe(n('0,0~%'))
    expect(part(-0.0001)).toBe(n('0,0~%'))
    expect(partSignee(-0.0001)).toBe(n('0,0~%'))
  })

  it('garde jusqu’à decimalesMax décimales sans zéros inutiles', () => {
    expect(nombre(2.5, 0, 4)).toBe('2,5')
    expect(nombre(2.49524, 0, 4)).toBe('2,4952')
    expect(nombre(3, 0, 4)).toBe('3')
    expect(nombre(2.4, 2, 4)).toBe('2,40')
  })

  it('dit le signe d’un écart', () => {
    expect(nombreSigne(12.46, 1)).toBe('+12,5')
    expect(nombreSigne(-3, 1)).toBe('−3,0')
    expect(nombreSigne(-0.01, 1)).toBe('0,0')
    expect(partSignee(0.042)).toBe(n('+4,2~%'))
  })
})

describe('Vide : « — »', () => {
  it.each([null, undefined, Number.NaN, Number.POSITIVE_INFINITY])('%s', (v) => {
    expect(nombre(v)).toBe(VIDE)
    expect(kg(v)).toBe(VIDE)
    expect(montant(v, 'MAD')).toBe(VIDE)
    expect(prix(v)).toBe(VIDE)
    expect(pourcent(v)).toBe(VIDE)
    expect(poidsBobine(v)).toBe(VIDE)
    expect(m2(v)).toBe(VIDE)
    expect(cours(v)).toBe(VIDE)
    expect(kgTelephone(v)).toBe(VIDE)
    expect(kgEtMetres(v, 0.014)).toBe(VIDE)
  })

  it('dates vides', () => {
    expect(date(null)).toBe('—')
    expect(horodatage('')).toBe('—')
    expect(jourRelatif(undefined)).toBe('—')
  })
})

describe('Kilos', () => {
  it('au bureau : une décimale', () => {
    expect(kg(1234.5)).toBe(n('1~234,5~kg'))
    expect(kg(1234.56)).toBe(n('1~234,6~kg'))
    expect(kg(2.49)).toBe(n('2,5~kg'))
    expect(kg(0)).toBe(n('0,0~kg'))
  })

  it.each([
    [445.4, '445~kg'],
    [100, '100~kg'],
    [52.44, '52,4~kg'],
    [10, '10,0~kg'],
    [2.494, '2,49~kg'],
    [0.05, '0,05~kg'],
    [99.96, '100~kg'],
    [9.996, '10,0~kg'],
    [-52.44, '\u221252,4~kg'],
  ])('au téléphone : %s → %s', (v, attendu) => {
    expect(kgTelephone(v)).toBe(n(attendu))
  })

  it('commandés au kilo : entiers', () => {
    expect(kgEntier(5029.4)).toBe(n('5~029~kg'))
    expect(kgEntier(5028.5)).toBe(n('5~029~kg'))
  })
})

describe('Mètres indicatifs (cuir, franges, ruban)', () => {
  it('« 14,3 kg ≈ 1 020 ml »', () => {
    expect(kgEtMetres(14.28, 0.014)).toBe(n('14,3~kg ≈~1~020~ml'))
    expect(metres(14.28, 0.014)).toBe(n('≈~1~020~ml'))
  })

  it('rien pour une matière au poids, sans densité, ou un reste d’arrondi', () => {
    expect(kgEtMetres(14.28)).toBe(n('14,3~kg'))
    expect(kgEtMetres(14.28, 0)).toBe(n('14,3~kg'))
    expect(metres(14.28, null)).toBe('')
    expect(metres(0.0001, 0.014)).toBe('')
  })

  it('au téléphone, les kilos suivent la règle du téléphone', () => {
    expect(kgEtMetres(445.4, 0.5, true)).toBe(n('445~kg ≈~891~ml'))
  })
})

describe('Montants : devise toujours dite', () => {
  it('tableaux et indicateurs : sans décimale', () => {
    expect(montant(1234.4, 'MAD')).toBe(n('1~234~MAD'))
    expect(montant(-1234.5, 'USD')).toBe(n('−1~235~USD'))
  })

  it('documents, échéancier, dossiers : deux décimales', () => {
    expect(montantPrecis(7795.2, 'MAD')).toBe(n('7~795,20~MAD'))
  })

  it('indicateur au-delà d’un million : « 17,4 M MAD »', () => {
    expect(montantCourt(17_398_184, 'MAD')).toBe(n('17,4~M~MAD'))
    expect(montantCourt(1_000_000, 'MAD')).toBe(n('1,0~M~MAD'))
    expect(montantCourt(999_999.4, 'MAD')).toBe(n('999~999~MAD'))
    expect(montantCourt(-2_450_000, 'EUR')).toBe(n('−2,5~M~EUR'))
  })

  it('devises jamais additionnées : « 61 888 USD · 53 132 EUR »', () => {
    expect(montants({ EUR: 53132, USD: 61888 })).toBe(n('61~888~USD · 53~132~EUR'))
    expect(montants({ EUR: 0, USD: 10 })).toBe(n('10~USD'))
    expect(montants({})).toBe('—')
    expect(montants(null)).toBe('—')
    expect(montants({ MAD: 12.5 }, true)).toBe(n('12,50~MAD'))
  })
})

describe('Prix unitaire, cours, pourcentage, bobine, m²', () => {
  it('prix : deux décimales, jusqu’à quatre sous 0,1', () => {
    expect(prixUnite(2.8, 'USD', 'kg')).toBe(n('2,80~USD / kg'))
    expect(prixUnite(0.0011, 'USD', 'ml')).toBe(n('0,0011~USD / ml'))
    expect(prix(0.05)).toBe('0,05')
    expect(prix(0.012345)).toBe('0,0123')
    expect(prix(0)).toBe('0,00')
    expect(prix(0.1)).toBe('0,10')
    expect(prix(-0.0011)).toBe('−0,0011')
  })

  it('cours : quatre décimales', () => {
    expect(cours(10.05)).toBe('10,0500')
    expect(cours(9.87654)).toBe('9,8765')
  })

  it('pourcentage : une décimale, espace insécable', () => {
    expect(pourcent(12.5)).toBe(n('12,5~%'))
    expect(part(0.125)).toBe(n('12,5~%'))
    expect(part(0.07)).toBe(n('7,0~%'))
  })

  it('poids de bobine : jusqu’à quatre décimales sans zéros', () => {
    expect(poidsBobine(2.49524)).toBe(n('2,4952~kg / bobine'))
    expect(poidsBobine(2.5)).toBe(n('2,5~kg / bobine'))
  })

  it('m² : entier', () => {
    expect(m2(1200.4)).toBe(n('1~200~m²'))
  })

  it('jours : « 45 j »', () => {
    expect(jours(45)).toBe(n('45~j'))
  })
})

describe('Dates, à l’heure du serveur', () => {
  it('JJ/MM/AAAA ; une date seule ne recule jamais d’un jour', () => {
    expect(date('2026-10-08')).toBe('08/10/2026')
    expect(date('2026-01-01')).toBe('01/01/2026')
  })

  it('horodatage JJ/MM/AAAA HH:MM, lu à l’heure de l’usine', () => {
    expect(horodatage('2026-10-08T14:05:33+01:00')).toBe('08/10/2026 14:05')
    expect(horodatage('2026-10-08T14:05:33')).toBe('08/10/2026 14:05')
    recalerHorloge('2026-10-08T13:20:46+01:00')
    expect(horodatage('2026-10-08T13:05:00Z')).toBe('08/10/2026 14:05')
    expect(horodatage('2026-12-31T23:30:00Z')).toBe('01/01/2027 00:30')
  })

  it('« aujourd’hui », « hier » selon le serveur, pas le poste', () => {
    recalerHorloge('2026-10-08T00:10:00+01:00', Date.now())
    expect(jourRelatif('2026-10-08')).toBe("aujourd'hui")
    expect(jourRelatif('2026-10-07')).toBe('hier')
    expect(jourRelatif('2026-10-06')).toBe('06/10/2026')
    expect(horodatageRelatif('2026-10-07T09:12:00+01:00')).toBe('hier 09:12')
    expect(horodatageRelatif('2026-10-01T09:12:00+01:00')).toBe('01/10/2026 09:12')
  })

  it('« il y a » à l’heure du serveur', () => {
    recalerHorloge('2026-10-08T13:20:00+01:00', Date.now())
    expect(ilYa('2026-10-08T13:19:40+01:00')).toBe("à l'instant")
    expect(ilYa('2026-10-08T12:40:00+01:00')).toBe(n('il y a 40~min'))
    expect(ilYa('2026-10-08T07:20:00Z')).toBe(n('il y a 5~h'))
    expect(ilYa('2026-10-06T13:20:00+01:00')).toBe(n('il y a 2~j'))
    expect(ilYa('2026-09-01T13:20:00+01:00')).toBe('01/09/2026')
  })

  it('mois', () => {
    expect(mois('2026-10')).toBe('octobre 2026')
    expect(moisCourt('2026-09-30')).toBe('sept. 2026')
  })

  it('un texte illisible reste tel quel', () => {
    expect(date('bientôt')).toBe('bientôt')
    expect(date('2026-02-30')).toBe('2026-02-30')
  })
})
