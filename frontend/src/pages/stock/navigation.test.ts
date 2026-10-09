/**
 * Les adresses du Stock : fiches à adresse stable par-dessus l'onglet d'où l'on vient, recherche
 * gardée par onglet, chemin du suivi de traçabilité dans l'adresse (A5, P2-17, P2-18).
 */
import { describe, expect, it } from 'vitest'

import { adresseAncienne } from './Stock'
import { adresseListe, adresseSuivi, ongletSous, ouvertDe, parametresOnglet } from './navigation'
import { ecrireEtape, libelleRevenir, lireDepuis, nomSuivi, titreSuivi } from './Tracabilite'

const p = (texte: string) => new URLSearchParams(texte)

describe('navigation du Stock', () => {
  it('lit ce que l’adresse ouvre par-dessus la liste', () => {
    expect(ouvertDe('/stock/matieres/12', p(''))).toEqual({ genre: 'matiere', id: 12 })
    expect(ouvertDe('/lots/7', p('onglet=lots'))).toEqual({ genre: 'lot', id: 7 })
    expect(ouvertDe('/tracabilite', p('ordre=5'))).toEqual({ genre: 'suivi', suivi: { ordre: 5 } })
    expect(ouvertDe('/tracabilite', p(''))).toBeNull()
    expect(ouvertDe('/stock', p('onglet=lots'))).toBeNull()
  })

  it('garde sous une fiche l’onglet d’où l’on vient', () => {
    expect(ongletSous({ genre: 'lot', id: 7 }, p('onglet=mouvements'))).toBe('mouvements')
    expect(ongletSous({ genre: 'lot', id: 7 }, p(''))).toBe('lots')
    expect(ongletSous({ genre: 'matiere', id: 1 }, p('onglet=lots'))).toBe('matieres')
    const suivi = { genre: 'suivi', suivi: { lot: 3 } } as const
    expect(ongletSous(suivi, p(`retour=${encodeURIComponent('/stock?onglet=a-valider&q=x')}`))).toBe(
      'a-valider',
    )
    expect(ongletSous(suivi, p(`retour=${encodeURIComponent('/lots/3?onglet=lots')}`))).toBe('lots')
    expect(ongletSous(suivi, p(`retour=${encodeURIComponent('/ordres/9')}`))).toBe('ordres')
    expect(ongletSous(null, p('volet=tracabilite'))).toBe('ordres')
    expect(ongletSous(null, p('onglet=tracabilite'))).toBe('ordres')
  })

  it('chaque onglet garde sa recherche', () => {
    const vers = parametresOnglet('q=rouge&statut=RUPTURE', 'matieres', 'lots')
    expect(vers).toBe('?statut=RUPTURE&q_matieres=rouge&onglet=lots')
    expect(parametresOnglet(vers.slice(1), 'lots', 'matieres')).toBe('?statut=RUPTURE&q=rouge')
  })

  it('fermer une fiche rend la liste, l’onglet écrit seulement s’il n’est pas le premier', () => {
    expect(adresseListe('onglet=matieres&q=a', 'matieres')).toBe('/stock?q=a')
    expect(adresseListe('onglet=lots&matiere=2', 'lots')).toBe('/stock?matiere=2&onglet=lots')
  })

  it('les anciennes adresses de Gestion MP mènent aux nouvelles', () => {
    expect(adresseAncienne(p('lot_id=4'))).toBe('/tracabilite?lot=4')
    expect(adresseAncienne(p('onglet=lots&article=3'))).toBe('/stock?onglet=lots&matiere=3')
    expect(adresseAncienne(p('volet=mouvements'))).toBe('/stock?onglet=mouvements')
    expect(adresseAncienne(p('onglet=tracabilite'))).toBe('/stock?onglet=ordres')
    expect(adresseAncienne(p('onglet=lots'))).toBeNull()
  })
})

describe('chemin du suivi de traçabilité', () => {
  it('écrit et relit le chemin parcouru, noms compris', () => {
    const depuis = [
      ecrireEtape({ suivi: { ordre: 5 }, nom: 'ordre OF-2026-0005' }),
      ecrireEtape({ suivi: { lot: 3 }, nom: 'lot L:R,1' }),
    ]
    const adresse = adresseSuivi({ matiere: 1 }, '/ordres/5', depuis)
    const lu = lireDepuis(new URLSearchParams(adresse.split('?')[1]).get('depuis'))
    expect(lu).toEqual([
      { suivi: { ordre: 5 }, nom: 'ordre OF-2026-0005' },
      { suivi: { lot: 3 }, nom: 'lot L:R,1' },
    ])
  })

  it('« ← Revenir au lot », « à l’ordre », « à la matière » (P2-17)', () => {
    expect(libelleRevenir({ suivi: { lot: 3 }, nom: 'lot L-1' })).toBe('← Revenir au lot L-1')
    expect(libelleRevenir({ suivi: { ordre: 5 }, nom: 'ordre OF-1' })).toBe('← Revenir à l’ordre OF-1')
    expect(libelleRevenir({ suivi: { matiere: 1 }, nom: 'matière REF' })).toBe('← Revenir à la matière REF')
  })

  it('titres et noms d’après la réponse du serveur', () => {
    const t = { lot: 'L-1', ordre: 'OF-1', matiere: 'REF' } as Parameters<typeof nomSuivi>[1]
    expect(titreSuivi({ lot: 3 }, t)).toBe('Traçabilité du lot L-1')
    expect(titreSuivi({ ordre: 5 }, t)).toBe('Ordre de fabrication OF-1')
    expect(titreSuivi({ matiere: 1 }, t)).toBe('Parcours de la matière REF')
    expect(nomSuivi({ lot: 3 }, undefined)).toBe('lot 3')
  })
})
