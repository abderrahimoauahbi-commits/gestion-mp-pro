/**
 * Les règles d'un déplacement à l'atelier ((d)) : départ hors quarantaine le plus garni d'abord,
 * arrivée autre que le départ (la quarantaine dite comme telle), motifs sans libération, motif
 * imposé vers la quarantaine, raisons de griser « Déplacer ».
 */
import { describe, expect, it } from 'vitest'

import {
  arrivees,
  departs,
  deplacementVide,
  lireDeplacement,
  motifQuarantaine,
  motifsAtelier,
  raisonDeplacer,
} from './deplacement'
import { donnees } from './essaiAtelier'

describe('Déplacer un lot', () => {
  it('départs, arrivées, motifs de l’atelier', () => {
    const d = donnees()
    const lot = {
      ...d.LOT,
      magasins: [
        ...d.LOT.magasins,
        { magasin_id: 2, magasin: 'Quarantaine', type: 'quarantaine', quantite: 5 },
      ],
    }
    expect(departs(lot).map((m) => m.magasin_id)).toEqual([1])
    const a = arrivees(d.MAGASINS, 1)
    expect(a.map((x) => x.id)).not.toContain(1)
    expect(a.find((x) => x.id === 2)?.titre).toBe('Quarantaine (quarantaine : matière douteuse)')
    const motifs = motifsAtelier(d.MOTIFS.motifs).map((m) => m.libelle)
    expect(motifs).toEqual(['Rangement', "Approvisionnement de l'atelier"])
    expect(motifs).not.toContain('Libération de quarantaine')
    expect(motifQuarantaine(d.MOTIFS.motifs)?.libelle).toBe('Mise en quarantaine')
  })

  it('la quantité proposée est tout ce qui est dans le départ, relue après chaque déplacement', () => {
    const d = donnees()
    const lu = lireDeplacement(d.LOT, deplacementVide(), d.MAGASINS)
    expect(lu.depuis).toBe(1)
    expect(lu.kg).toBe(d.LOT.magasins[0]?.quantite)
    expect(lireDeplacement(d.LOT, { ...deplacementVide(), kg: 3 }, d.MAGASINS).kg).toBe(3)
  })

  it('les raisons de griser « Déplacer »', () => {
    const base = { blocages: [], vers: 2, kg: 10, dispo: 20, quarantaine: false, commentaire: '' }
    expect(raisonDeplacer({ ...base, blocages: ['inv'] })).toBe(
      'Un inventaire est en cours (voir le bandeau)',
    )
    expect(raisonDeplacer({ ...base, vers: null })).toBe('Choisir le magasin d’arrivée')
    expect(raisonDeplacer({ ...base, kg: 0 })).toBe('Saisir la quantité')
    expect(raisonDeplacer({ ...base, kg: 21 })).toBe('Plus que ce qui est là')
    expect(raisonDeplacer({ ...base, quarantaine: true, commentaire: 'ab' })).toBe(
      'Écrire ce qui est douteux, dans les observations',
    )
    expect(raisonDeplacer({ ...base, quarantaine: true, commentaire: 'tachées' })).toBe('')
  })
})
