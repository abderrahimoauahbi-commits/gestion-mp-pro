/// <reference types="node" />
/**
 * Les Paramètres disent à la frappe ce que le serveur refuserait, **avec sa phrase** : les ordres
 * des seuils sont relus dans `services/registre_reglages.py` (une seule déclaration) ; les 57
 * réglages relevés au vrai serveur sont tous contrôlés (bornes, nombre, texte).
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import parametres from '../essais/parametres.json'
import {
  corps,
  desordres,
  FAMILLES_AILLEURS,
  ORDRES_LARGES,
  ORDRES_STRICTS,
  poser,
  refus,
  refusDuChamp,
  texteInitial,
  type Reglage,
} from './logique'
import { familles } from './Parametres'

const SERVEUR = join(process.cwd(), '..', 'backend', 'gestion_mp_pro')
const registre = readFileSync(join(SERVEUR, 'services', 'registre_reglages.py'), 'utf8')
const REGLAGES = parametres as Reglage[]
const r = (cle: string) => REGLAGES.find((x) => x.cle === cle) as Reglage

/** Les triplets (plus petit, plus grand, phrase) d'un bloc d'ordres du registre du serveur. */
function ordresDuServeur(nom: string): [string, string, string][] {
  const bloc = registre.slice(
    registre.indexOf(`${nom}: tuple`),
    registre.indexOf('"""', registre.indexOf(`${nom}: tuple`)),
  )
  const triplets: [string, string, string][] = []
  const motif = /\("(\w+)", "(\w+)",\s*((?:"[^"]*"\s*)+)\)/g
  for (const m of bloc.matchAll(motif)) {
    const phrase = [...(m[3] ?? '').matchAll(/"([^"]*)"/g)].map((x) => x[1]).join('')
    triplets.push([m[1] ?? '', m[2] ?? '', phrase])
  }
  return triplets
}

const apostrophes = (t: string) => t.replace(/’/g, "'")

describe('paramètres : les refus du serveur, à la frappe', () => {
  it('les ordres des seuils sont ceux du serveur, mot pour mot', () => {
    const stricts = ordresDuServeur('ORDRES_STRICTS')
    const larges = ordresDuServeur('ORDRES_LARGES')
    expect(stricts).toHaveLength(ORDRES_STRICTS.length)
    expect(larges).toHaveLength(ORDRES_LARGES.length)
    expect(ORDRES_STRICTS.map(([a, b, m]) => [a, b, apostrophes(m)])).toEqual(stricts)
    expect(ORDRES_LARGES.map(([a, b, m]) => [a, b, apostrophes(m)])).toEqual(larges)
  })

  it('57 réglages ; neuf familles dans l’onglet, la période close et la technique ailleurs', () => {
    expect(REGLAGES).toHaveLength(57)
    expect(familles(REGLAGES)).toHaveLength(9)
    expect(
      REGLAGES.filter((x) => FAMILLES_AILLEURS.has(x.famille))
        .map((x) => x.cle)
        .sort(),
    ).toEqual(['adresse_publique', 'courriel_destinataires', 'date_cloture'])
  })

  it('chaque réglage numérique refuse un texte et une valeur hors bornes ; sa valeur en base passe', () => {
    for (const x of REGLAGES.filter((y) => !y.texte)) {
      expect(refusDuChamp(x, texteInitial(x)), x.cle).toBe('')
      expect(refusDuChamp(x, 'abc'), x.cle).toBe(`« ${x.libelle} » attend un nombre.`)
      if (x.haut != null)
        expect(refusDuChamp(x, String(x.haut * x.echelle * 2 + 1)), x.cle).toMatch(/doit rester entre/)
    }
  })

  it('un taux se saisit en % et part en fraction ; la version globale part avec', () => {
    const b = poser({}, r('taux_perte'), '3,5')
    expect(corps(REGLAGES, b)).toEqual({
      valeurs: { taux_perte: 0.035 },
      version_globale: r('taux_perte').version_globale,
    })
    expect(refusDuChamp(r('taux_perte'), '60')).toMatch(/entre 0 et 50 %/)
  })

  it('revenir à la valeur en base retire la saisie du brouillon', () => {
    const b = poser({}, r('seuil_alerte'), '100')
    expect(Object.keys(b)).toEqual(['seuil_alerte'])
    expect(poser(b, r('seuil_alerte'), texteInitial(r('seuil_alerte')))).toEqual({})
  })

  it('les ordres : critique sous attention (strict), Tier 2 au plus Tier 1 (égalité permise)', () => {
    const critique = Number(texteInitial(r('seuil_alerte')))
    expect(desordres(REGLAGES, { seuil_critique: String(critique) })).toEqual([ORDRES_STRICTS[0]?.[2]])
    const tier1 = Number(texteInitial(r('seuil_tier1')))
    expect(desordres(REGLAGES, { seuil_tier2: String(tier1) })).toEqual([])
    expect(refus(REGLAGES, { seuil_tier2: String(tier1 + 1) })).toEqual([ORDRES_LARGES[0]?.[2]])
  })

  it('les adresses : http(s) pour les téléphones, courriels lisibles pour le lundi', () => {
    expect(refusDuChamp(r('adresse_publique'), 'mac-usine:8050')).toMatch(/http:\/\/ ou https:\/\//)
    expect(refusDuChamp(r('adresse_publique'), 'http://mac-usine:8050')).toBe('')
    expect(refusDuChamp(r('courriel_destinataires'), 'direction@usine.ma, achats')).toMatch(
      /illisible : achats/,
    )
  })
})
