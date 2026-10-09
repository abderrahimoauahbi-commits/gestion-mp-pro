/** Le comptage sans écran : tolérance, lignes lues ou recalculées, recomptage à quatre yeux, Valider. */
import { describe, expect, it } from 'vitest'

import {
  changer,
  corpsComptages,
  etatLigne,
  horsTolerance,
  questionValider,
  raisonsDeValider,
  sansLesEnvoyes,
  totaux,
  type Brouillons,
} from './calculComptage'
import { ficheEssai, ligneEssai } from './donneesEssai'

const KARIM = { nom: 'Karim BENALI', ouvreur: 'MAZARI' }

describe('hors tolérance (règles du serveur)', () => {
  it('écart relatif au-delà de la tolérance, seuil de 0,001 kg, théorique nul', () => {
    expect(horsTolerance(420, 400, 0.02)).toBe(true)
    expect(horsTolerance(420, 415, 0.02)).toBe(false)
    expect(horsTolerance(420, 420.0005, 0)).toBe(false)
    expect(horsTolerance(0, 3, 0.5)).toBe(true)
    expect(horsTolerance(420, null, 0.02)).toBe(false)
  })
})

describe('la ligne à l’écran', () => {
  it('une ligne enregistrée se lit au serveur (an. 15)', () => {
    const l = ligneEssai({ compte: 400, retenu: 400, ecart: -20, hors_tolerance: true, a_recompter: true })
    const e = etatLigne(l, undefined, 0.02, KARIM)
    expect(e).toMatchObject({ modifiee: false, retenu: 400, hors: true, recompter: true, manque: true })
  })

  it('une ligne modifiée se recalcule : le recompté est retenu', () => {
    const l = ligneEssai({ compte: 400, compte_par: 'MAZARI' })
    const e = etatLigne(
      l,
      { compte: 400, palettes: null, bobines: null, second_compte: 418, justification: '' },
      0.02,
      KARIM,
    )
    expect(e.retenu).toBe(418)
    expect(e.hors).toBe(false)
    expect(e.recompter).toBe(false)
    expect(e.valeur).toBeCloseTo(-60)
  })

  it('justification exigée au-delà de la tolérance (3 caractères au moins)', () => {
    const l = ligneEssai()
    const b = { compte: 380, palettes: null, bobines: null, second_compte: null, justification: 'ab' }
    expect(etatLigne(l, b, 0.02, KARIM).manque).toBe(true)
    expect(etatLigne(l, { ...b, justification: 'abc' }, 0.02, KARIM).manque).toBe(false)
  })

  it('un recomptage par la même personne est signalé, jamais refusé', () => {
    const l = ligneEssai({ compte: 400, compte_par: 'Karim BENALI' })
    const b = { compte: 400, palettes: null, bobines: null, second_compte: 405, justification: 'casse' }
    expect(etatLigne(l, b, 0.02, KARIM).quatreYeux).toMatch(/^même personne que le premier comptage/)
    const parAutre = ligneEssai({ compte: 400, compte_par: 'Ahmed' })
    expect(etatLigne(parAutre, b, 0.02, KARIM).quatreYeux).toBe('')
    expect(etatLigne(parAutre, b, 0.02, { nom: 'MAZARI', ouvreur: 'MAZARI' }).quatreYeux).toMatch(
      /^même personne que l'ouvreur/,
    )
  })

  it('premier comptage et recomptage tapés ensemble : la même personne', () => {
    const l = ligneEssai()
    const b = { compte: 400, palettes: null, bobines: null, second_compte: 405, justification: '' }
    expect(etatLigne(l, b, 0.02, KARIM).quatreYeux).toMatch(/premier comptage/)
  })
})

describe('les saisies', () => {
  it('palettes et bobines donnent le poids, au poids de bobine du lot', () => {
    const l = ligneEssai()
    let b: Brouillons = changer({}, l, { palettes: 2 })
    b = changer(b, l, { bobines: 3 })
    expect(b[1]?.compte).toBe(127.5)
  })

  it('saisir le compté efface palettes et bobines ; revenir au serveur n’est plus à enregistrer', () => {
    const l = ligneEssai()
    const b = changer(changer({}, l, { bobines: 4 }), l, { compte: 12 })
    expect(b[1]).toMatchObject({ compte: 12, palettes: null, bobines: null })
    expect(changer(b, l, { compte: null })).toEqual({})
  })

  it('les saisies tapées pendant un envoi ne sont pas oubliées', () => {
    const l = ligneEssai()
    const envoyes = changer({}, l, { compte: 400 })
    const pendant = changer(envoyes, ligneEssai({ id: 2 }), { compte: 10 })
    expect(Object.keys(sansLesEnvoyes(pendant, envoyes))).toEqual(['2'])
  })

  it('le corps n’envoie que les lignes modifiées, avec la version', () => {
    const fiche = ficheEssai()
    const b = changer({}, fiche.lignes[0]!, { compte: 400, justification: ' casse  ' })
    expect(corpsComptages(fiche, b)).toEqual({
      version: 3,
      lignes: [
        {
          ligne_id: 1,
          compte: 400,
          palettes: null,
          bobines: null,
          second_compte: null,
          justification: 'casse',
        },
      ],
    })
  })
})

describe('Valider', () => {
  it('grisé par les écarts sans justification, avec la raison', () => {
    const fiche = ficheEssai()
    const b = changer({}, fiche.lignes[0]!, { compte: 380 })
    const t = totaux(fiche.lignes.map((l) => etatLigne(l, b[l.id], 0.02, KARIM)))
    expect(raisonsDeValider(fiche, t)).toEqual([
      '1 écart(s) hors tolérance sans justification : écrire d’abord ce qui a été constaté (lignes en rouge)',
    ])
  })

  it('sans saisie locale, les blocages du serveur tels quels', () => {
    const fiche = ficheEssai()
    const t = totaux(fiche.lignes.map((l) => etatLigne(l, undefined, 0.02, KARIM)))
    expect(raisonsDeValider(fiche, t)).toEqual(fiche.blocages)
  })

  it('la question dit les non comptés et les recomptages par la même personne', () => {
    const fiche = ficheEssai()
    const b = changer({}, fiche.lignes[0]!, { compte: 400, second_compte: 402, justification: 'casse' })
    const t = totaux(fiche.lignes.map((l) => etatLigne(l, b[l.id], 0.02, KARIM)))
    expect(questionValider(t)).toBe(
      'Valider ? 1 lot(s) comptés, 1 écart(s) ajusté(s) (−18,0 kg), 1 non comptés restent au théorique, 1 recomptage(s) faits par la même personne. Seule une annulation (contre-passation, avec un motif) la défait.',
    )
  })
})
