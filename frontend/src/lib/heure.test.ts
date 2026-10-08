/** Essais de l'heure de l'usine : le décalage du serveur lu dans `X-Heure-Serveur`. */
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ajouterJours,
  aujourdhui,
  decalageDeLUsine,
  decouper,
  heureServeur,
  instantDe,
  instantServeur,
  jourDansN,
  joursDepuis,
  moisCourant,
  murDe,
  recalerHorloge,
  reinitialiserHorloge,
} from './heure'

afterEach(() => {
  vi.useRealTimers()
  reinitialiserHorloge()
})

describe('Recalage sur le serveur', () => {
  it('prend le jour et l’heure du serveur, pas ceux du poste', () => {
    // Le poste se croit le 31/12/2030 à 23 h ; le serveur dit 08/10/2026 13:20:46.
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2030-12-31T23:00:00Z'))
    expect(recalerHorloge('2026-10-08T13:20:46')).toBe(true)
    expect(aujourdhui()).toBe('2026-10-08')
    expect(heureServeur()).toBe('13:20:46')
    expect(moisCourant()).toBe('2026-10')
  })

  it('suit le temps qui passe après le recalage', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2030-01-01T00:00:00Z'))
    recalerHorloge('2026-10-08T23:59:30+01:00')
    expect(aujourdhui()).toBe('2026-10-08')
    vi.advanceTimersByTime(45_000)
    expect(aujourdhui()).toBe('2026-10-09')
    expect(heureServeur()).toBe('00:00:15')
  })

  it('un poste en avance d’une heure (Chrome et le Maroc, octobre 2026) ne change pas le jour', () => {
    vi.useFakeTimers()
    // Le serveur : 08/10 à 23:30 (+00). Le navigateur compte une heure de plus : il croirait le 09/10.
    vi.setSystemTime(new Date('2026-10-09T00:30:00+01:00'))
    recalerHorloge('2026-10-08T23:30:00+00:00')
    expect(aujourdhui()).toBe('2026-10-08')
    expect(jourDansN(-1)).toBe('2026-10-07')
  })

  it('lit le décalage de l’usine et l’instant du serveur quand l’en-tête les porte', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-08T12:00:00Z'))
    recalerHorloge('2026-10-08T13:20:46+01:00')
    expect(decalageDeLUsine()).toBe(60)
    // Le poste retarde de 20 min 46 s sur le serveur.
    expect(instantServeur() - Date.now()).toBe(20 * 60_000 + 46_000)
  })

  it('accepte « Z », « +0100 », les fractions de seconde', () => {
    expect(recalerHorloge('2026-10-08T12:20:46.123Z')).toBe(true)
    expect(decalageDeLUsine()).toBe(0)
    expect(recalerHorloge('2026-10-08T13:20:46+0100')).toBe(true)
    expect(decalageDeLUsine()).toBe(60)
    expect(recalerHorloge('2026-10-08 13:20:46')).toBe(true)
  })

  it('ignore un en-tête absent ou illisible, et garde le dernier recalage', () => {
    recalerHorloge('2026-10-08T13:20:46')
    expect(recalerHorloge(null)).toBe(false)
    expect(recalerHorloge('')).toBe(false)
    expect(recalerHorloge('demain')).toBe(false)
    expect(recalerHorloge('2026-10-08')).toBe(false)
    expect(recalerHorloge('2026-13-40T10:00:00')).toBe(false)
    expect(aujourdhui()).toBe('2026-10-08')
  })

  it('sans en-tête reçu, l’heure du poste fait foi', () => {
    vi.useFakeTimers()
    const maintenant = new Date(2026, 9, 8, 10, 15, 0)
    vi.setSystemTime(maintenant)
    expect(aujourdhui()).toBe('2026-10-08')
    expect(heureServeur()).toBe('10:15:00')
  })
})

describe('Calendrier', () => {
  it('ajoute des jours sans dépendre des changements d’heure', () => {
    expect(ajouterJours('2026-10-08', 1)).toBe('2026-10-09')
    expect(ajouterJours('2026-03-01', -1)).toBe('2026-02-28')
    expect(ajouterJours('2024-02-28', 1)).toBe('2024-02-29')
    expect(ajouterJours('2026-12-31', 1)).toBe('2027-01-01')
    expect(ajouterJours('2026-10-25', 7)).toBe('2026-11-01')
  })

  it('compte les jours depuis une date', () => {
    recalerHorloge('2026-10-08T08:00:00')
    expect(joursDepuis('2026-10-08')).toBe(0)
    expect(joursDepuis('2026-10-07')).toBe(1)
    expect(joursDepuis('2026-10-09')).toBe(-1)
    expect(joursDepuis('2026-09-08')).toBe(30)
    expect(joursDepuis('n’importe quoi')).toBeNull()
  })

  it('découpe dates et instants', () => {
    expect(decouper('2026-10-08')).toMatchObject({ avecHeure: false, decalage: null })
    expect(decouper('2026-10-08T13:20:46-03:30')).toMatchObject({ avecHeure: true, decalage: -210 })
    expect(decouper('2026-02-29')).toBeNull()
  })

  it('présente un instant à l’heure de l’usine', () => {
    expect(murDe('2026-10-08T13:20:46+01:00')?.mur).toMatchObject({ heure: 13, minute: 20 })
    recalerHorloge('2026-10-08T13:20:46+01:00')
    expect(murDe('2026-10-08T12:20:46Z')?.mur).toMatchObject({ jour: 8, heure: 13, minute: 20 })
    expect(murDe('2026-10-08T23:30:00Z')?.mur).toMatchObject({ jour: 9, heure: 0, minute: 30 })
  })

  it('l’instant d’un horodatage sans décalage est pris à l’heure de l’usine', () => {
    recalerHorloge('2026-10-08T13:20:46+01:00')
    expect(instantDe('2026-10-08T13:20:46')).toBe(Date.parse('2026-10-08T12:20:46Z'))
    expect(instantDe('2026-10-08T12:20:46Z')).toBe(Date.parse('2026-10-08T12:20:46Z'))
  })
})
