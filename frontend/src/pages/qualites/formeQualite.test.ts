/** La saisie d'une qualité : une requête pour la fiche et la recette (P7-8), poids nuls tus (P7-5). */
import { describe, expect, it } from 'vitest'

import { resumeEssai } from '../catalogue/donneesEssai'
import { qualiteEssai } from './donneesEssai'
import {
  corpsQualite,
  depuisMatiere,
  memeQualite,
  poidsEnvoyes,
  recetteChangee,
  versFormeQualite,
} from './formeQualite'

describe('formeQualite', () => {
  it('la recette ne part que si elle change ; les poids nuls ne partent pas', () => {
    const f = versFormeQualite(qualiteEssai())
    const nom = { ...f, nom: 'Atlas', poids: { ...f.poids, 7: 0 } }
    expect(poidsEnvoyes(nom)).toEqual([
      { role_id: 1, poids: 1.2 },
      { role_id: 5, poids: 2 },
    ])
    expect(corpsQualite(nom, f, 5)).toMatchObject({ nom: 'Atlas', recette: null, version: 5, motif: '' })
    const parts = {
      ...f,
      lignes: f.lignes.map((l) => ({ ...l, pourcentage: l.matiere_id === 12 ? 60 : l.pourcentage })),
    }
    expect(recetteChangee(parts, f)).toBe(true)
    expect(corpsQualite(parts, f, 5).recette).toEqual([
      { matiere_id: 12, pourcentage: 60 },
      { matiere_id: 13, pourcentage: 100 },
    ])
  })

  it('une matière disparue du catalogue sera retirée : la recette part', () => {
    const q = qualiteEssai({
      recette: [{ ...qualiteEssai().recette[0]!, matiere_id: null, reference: 'DISPARUE' }],
    })
    const f = versFormeQualite(q)
    expect(f.lignes[0]?.disparue).toBe(true)
    expect(corpsQualite(f, f, 5).recette).toEqual([])
    expect(memeQualite(f, f)).toBe(true)
  })

  it('une matière ajoutée reprend son rôle, son prix au kilo, sa devise et sa densité', () => {
    expect(depuisMatiere(resumeEssai({ id: 14 }), 40)).toMatchObject({
      matiere_id: 14,
      role_id: 1,
      pourcentage: 40,
      prix_kg: 2.5,
      devise: 'USD',
    })
  })
})
