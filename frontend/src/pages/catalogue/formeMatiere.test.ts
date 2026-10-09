/** La saisie d'une fiche matière sans écran : corps envoyé, manques, unité déduite, défauts. */
import { describe, expect, it } from 'vitest'

import { classificationEssai, matiereEssai } from './donneesEssai'
import {
  avecClasse,
  manqueLisible,
  manques,
  memeFiche,
  uniteDeduite,
  versCorps,
  versForme,
} from './formeMatiere'

const c = classificationEssai()

describe('formeMatiere', () => {
  it('une création part du 1er rôle, de MAD, d’un prix au kilo, en service, et reprend les filtres posés', () => {
    const f = versForme(null, c, { composition_id: 1, fournisseur_id: 7, devise: 'USD' })
    expect(f).toMatchObject({
      role_id: 1,
      devise: 'USD',
      unite_prix: 'kg',
      actif: true,
      composition_id: 1,
      fournisseur_id: 7,
    })
  })

  it('le corps est la fiche entière ; une unité vide part en kilo, contenance 1', () => {
    const corps = versCorps(versForme(matiereEssai(), c), matiereEssai())
    expect(corps).toMatchObject({ unite_achat: 'kg', contenance_achat: 1, priorite_equiv: 10, couleur_id: 4 })
    expect(Object.keys(corps)).toHaveLength(24)
  })

  it('la priorité n’est plus saisie : elle repart telle quelle, et tombe sans groupe (A-26)', () => {
    const f = { ...versForme(matiereEssai(), c), groupe_equiv: '' }
    expect(versCorps(f, matiereEssai()).priorite_equiv).toBeNull()
  })

  it('une fiche existante et sa forme relue sont la même fiche ; le suffixe ne compte pas', () => {
    const f = versForme(matiereEssai(), c)
    expect(memeFiche(f, { ...f, suffixe: 'Hs' })).toBe(true)
    expect(memeFiche(f, { ...f, designation: 'autre' })).toBe(false)
  })

  it('manques : référence, fournisseur en service, densité au mètre, contenance déclarée, bornes', () => {
    const vide = versForme(null, c)
    expect(manques(vide, c).map((m) => m.quoi)).toEqual(['la référence', 'le fournisseur'])
    const cuir = { ...versForme(matiereEssai(), c), role_id: 5 }
    expect(manques(cuir, c)).toContainEqual({ quoi: 'la densité (kg par mètre)', volet: 'classification' })
    const auMetre = { ...versForme(matiereEssai(), c), unite_prix: 'ml' as const }
    expect(manques(auMetre, c)).toContainEqual({ quoi: 'la densité (kg par mètre)', volet: 'achat' })
    const fut = { ...versForme(matiereEssai(), c), unite_achat: 'Fût', contenance_achat: null }
    expect(manques(fut, c).map((m) => m.quoi)).toContain('la contenance d’une unité d’achat (Fût)')
    const trop = { ...versForme(matiereEssai(), c), couv_min_mois: 61 }
    expect(manqueLisible(manques(trop, c))).toEqual([
      'la couverture minimum entre 0 et 60 mois (onglet Conditionnement et stock)',
    ])
  })

  it('une matière désactivée n’exige pas de fournisseur', () => {
    const f = { ...versForme(matiereEssai(), c), actif: false, fournisseur_id: null }
    expect(manques(f, c)).toEqual([])
  })

  it('unité déduite : palette, bobine, sinon kilo (règle du serveur)', () => {
    expect(uniteDeduite({ poids_bobine: 2.5, bobines_palette: 96 })).toEqual({
      unite: 'Palette',
      contenance: 240,
    })
    expect(uniteDeduite({ poids_bobine: 2.5, bobines_palette: null })).toEqual({
      unite: 'Bobine',
      contenance: 2.5,
    })
    expect(uniteDeduite({ poids_bobine: null, bobines_palette: 96 })).toEqual({ unite: 'kg', contenance: 1 })
  })

  it('avecClasse pose une seule valeur de la classification', () => {
    expect(avecClasse('couleur_id', 5)).toEqual({ couleur_id: 5 })
  })
})
