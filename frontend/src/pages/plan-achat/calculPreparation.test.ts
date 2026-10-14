/**
 * La préparation sans écran : départ du serveur, unités (jamais « ml »), kilos et unités liés,
 * palettes et place dans le conteneur, écart à la suggestion, corps envoyé (kilos, unité, contenance).
 */
import { describe, expect, it } from 'vitest'

import {
  arrondirAuConditionnement,
  avertissement,
  changerUnite,
  corps,
  depuisMatiere,
  depuisServeur,
  devisesDe,
  ecart,
  expliquerEcart,
  palettesDe,
  placeRestante,
  retenues,
  revenirALaSuggestion,
  totaux,
  unitesDe,
} from './calculPreparation'
import { lignePreparationEssai } from './donneesEssai'
import { cleTier, cleUrgence, libelleTier, libelleUnite, quantiteEnUnite, texteUrgence } from './libelles'
import { groupeEssai } from './donneesEssai'
import type { Matiere } from './types'

const matiere = (autres: Partial<Matiere> = {}): Matiere =>
  ({
    id: 9,
    reference: 'PP FRZ Rouge',
    designation: 'Rouge',
    role: 'Poil',
    devise: 'EUR',
    prix_kg: 2.9,
    poids_bobine: 2.5,
    bobines_palette: 96,
    unite_achat: 'Fût',
    contenance_achat: 200,
    minimum_commande: 500,
    contenance_palette: 240,
    kg_par_ml: 0,
    ...autres,
  }) as Matiere

describe('Préparation d’une commande', () => {
  it('part de la ligne du serveur : unité, contenance et kilos de `depart`, cochée', () => {
    const l = depuisServeur(
      lignePreparationEssai({ depart: { unite: 'Palette', contenance: 256, quantite: 5632, unites: 22 } }),
    )
    expect(l).toMatchObject({
      unite: 'Palette',
      contenance: 256,
      quantite: 5632,
      suggestion: 5632,
      retenue: true,
      ajoutee: false,
    })
  })

  it('les unités d’une matière ajoutée : kilo, bobine, palette, unité d’achat — jamais « ml »', () => {
    expect(unitesDe(matiere()).map((u) => u.unite)).toEqual(['kg', 'Bobine', 'Palette', 'Fût'])
    expect(unitesDe(matiere({ unite_achat: 'ml', contenance_achat: 1 })).map((u) => u.unite)).not.toContain(
      'ml',
    )
    const l = depuisMatiere(matiere())
    expect(l).toMatchObject({ unite: 'Fût', contenance: 200, quantite: 200, ajoutee: true, statut: '' })
    expect(depuisMatiere(matiere({ poids_bobine: 0, unite_achat: 'kg' }))).toMatchObject({
      unite: 'kg',
      quantite: 500,
    })
  })

  it('kilos et palettes liés ; changer d’unité garde les kilos ; arrondir monte à l’unité entière', () => {
    const l = { ...depuisMatiere(matiere()), unite: 'Palette', contenance: 240, quantite: 500 }
    expect(changerUnite(l, 'Bobine')).toMatchObject({ unite: 'Bobine', contenance: 2.5, quantite: 500 })
    expect(avertissement(l)).toBe('palette entamée')
    expect(arrondirAuConditionnement([l])[0]?.quantite).toBe(720)
    expect(avertissement({ ...l, quantite: 240, minimum: 300 })).toBe('sous le minimum (300 kg)')
  })

  it('totaux : kilos, palettes, montants par devise jamais additionnés, MAD au cours', () => {
    const a = { ...depuisMatiere(matiere()), quantite: 480 }
    const b = { ...depuisMatiere(matiere({ id: 10, devise: 'USD', prix_kg: 2 })), quantite: 240 }
    const t = totaux(
      [a, b, { ...b, matiere_id: 11, retenue: false }],
      [{ code: 'EUR', cours: 10.8 } as never, { code: 'USD', cours: 10 } as never],
    )
    expect(t.kilos).toBe(720)
    expect(t.palettes).toBe(3)
    expect(t.parDevise).toEqual({ EUR: 1392, USD: 480 })
    expect(t.mad).toBeCloseTo(1392 * 10.8 + 4800)
    expect(devisesDe([a, b])).toEqual(['EUR', 'USD'])
    expect(placeRestante(3, 20)).toEqual({ conteneurs: 0.15, libres: 17, nombre: 1 })
  })

  it('conteneur de 18 : il reste 3, on en ajoute 3, il est plein (pas « il reste 18 »)', () => {
    // 15 palettes : il reste 3.
    expect(placeRestante(15, 18)).toMatchObject({ libres: 3, nombre: 1 })
    // 18 palettes, à une poussière de kilos près (kg ↔ palettes) : plein, un seul conteneur.
    expect(placeRestante(18.0000004, 18)).toMatchObject({ libres: 0, nombre: 1 })
    expect(placeRestante(17.9999996, 18)).toMatchObject({ libres: 0, nombre: 1 })
    expect(placeRestante(36, 18)).toMatchObject({ libres: 0, nombre: 2 })
    // Une vraie palette de plus ouvre bien un conteneur.
    expect(placeRestante(19, 18)).toMatchObject({ libres: 17, nombre: 2 })
  })

  it('une ligne saisie en palettes compte le nombre tapé, sans repasser par les kilos', () => {
    const l = depuisServeur(lignePreparationEssai())
    // Contenance de la palette affichée (761,6) un peu au-dessus de celle de la matière : 3 palettes
    // tapées font 2 284,8 kg, soit 3,0000004 palettes « de matière » — le compte reste 3.
    const saisie = {
      ...l,
      unite: 'Palette',
      contenance: 761.6,
      contenance_palette: 761.599712,
      quantite: 2284.8,
    }
    expect(palettesDe(saisie)).toBe(3)
    expect(palettesDe({ ...saisie, unite: 'kg', contenance: 1 })).toBeCloseTo(3.0000011, 6)
  })

  it('l’infobulle du badge dit pourquoi : rupture sous la suggestion, surstock au-dessus', () => {
    const l = { ...depuisServeur(lignePreparationEssai()), suggestion: 1000 }
    expect(expliquerEcart(ecart({ ...l, quantite: 850 }))).toMatch(/15 % sous la suggestion.*rupture/)
    expect(expliquerEcart(ecart({ ...l, quantite: 1200 }))).toMatch(/20 % au-dessus.*trésorerie/)
    expect(expliquerEcart(ecart({ ...l, quantite: 1050 }))).toMatch(/^À 5 % de la suggestion/)
    expect(expliquerEcart(ecart({ ...l, quantite: 1000 }))).toBe('')
  })

  it('écart à la suggestion : ok ≤ 10 %, attention au-dessus, critique en dessous', () => {
    const l = { ...depuisServeur(lignePreparationEssai()), suggestion: 1000 }
    expect(ecart({ ...l, quantite: 1002 })).toEqual({ genre: 'suggestion' })
    expect(ecart({ ...l, quantite: 1050 })).toMatchObject({ ton: 'ok' })
    expect(ecart({ ...l, quantite: 1200 })).toMatchObject({ ton: 'attention' })
    expect(ecart({ ...l, quantite: 800 })).toMatchObject({ ton: 'critique' })
    expect(ecart({ ...l, retenue: false })).toEqual({ genre: 'non_commandee' })
  })

  it('revenir à la suggestion retire les lignes ajoutées ; le corps ne porte que les lignes retenues', () => {
    const depart = [depuisServeur(lignePreparationEssai())]
    expect(
      revenirALaSuggestion([...depart, depuisMatiere(matiere())].filter((l) => !l.ajoutee)),
    ).toHaveLength(1)
    const lignes = [...depart, { ...depuisMatiere(matiere()), retenue: false }]
    expect(retenues(lignes)).toHaveLength(1)
    const c = corps(
      { fournisseurId: 2, livraison: '', observations: '  Deliver in one shipment ', prixCatalogue: false },
      lignes,
    )
    expect(c).toMatchObject({
      fournisseur_id: 2,
      date_livraison_prevue: null,
      prix_catalogue_a_confirmer: false,
      observations: 'Deliver in one shipment',
    })
    expect(c.lignes).toEqual([
      {
        matiere_id: depart[0]?.matiere_id,
        quantite: depart[0]?.quantite,
        unite_achat: depart[0]?.unite,
        contenance: depart[0]?.contenance,
      },
    ])
  })
})

describe('Libellés du moteur sans émoticône', () => {
  it('tiers, urgences, unités', () => {
    expect(cleTier('🔥 TIER 1')).toBe('TIER_1')
    expect(libelleTier('⚪ TIER 4')).toBe('Tier 4')
    expect(cleUrgence('🚨 BC URGENT')).toBe('urgent')
    expect(cleUrgence('📋 BC groupé')).toBe('a_grouper')
    expect(cleUrgence('—')).toBeNull()
    expect(
      texteUrgence(groupeEssai({ urgence: '🚨 BC URGENT', ruptures: 2, critiques: 1, urgents: 0 })),
    ).toBe('Urgent · 2 rupt. · 1 crit.')
    expect(libelleUnite('Palette', 862.4)).toBe('Palette (862,4 kg)')
    expect(libelleUnite('kg', 1)).toBe('kg')
    expect(quantiteEnUnite(22, 'Palette')).toBe('22 palettes')
  })
})
