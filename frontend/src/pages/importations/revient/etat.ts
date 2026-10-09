/**
 * L'état de l'analyse du coût de revient, **tout dans l'adresse** (ECRANS-PRO 5.15, anomalie
 * 5.16) : `?onglet=revient&vue=&axe=&q=&statut=&du=&au=&qualite=&matieres=1,2&combinaisons=<JSON>
 * &composition=&titrage=&type=&couleur=&fournisseur=`. Recharger la page ou copier le lien rend la
 * même vue ; la fiche d'un dossier ouverte depuis l'analyse y ramène.
 *
 * Les critères d'une combinaison se cumulent (PES **et** 1500) ; « + Combinaison » la retient et
 * les combinaisons se réunissent (PES 1500 **plus** PP 1800). Dès qu'une combinaison est retenue,
 * le serveur reçoit `selection` (JSON), les critères en cours y entrant comme dernière
 * combinaison ; sinon les critères partent un à un (comme Gestion MP).
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'

import { avecParametre } from '../../../lib/adresse'

export const VUES = ['groupe', 'lots', 'qualite'] as const
export type VueRevient = (typeof VUES)[number]

export const AXES = [
  { cle: 'reference', libelle: 'Référence' },
  { cle: 'titrage', libelle: 'Titrage' },
  { cle: 'composition', libelle: 'Composition' },
  { cle: 'type_fil', libelle: 'Type de fil' },
  { cle: 'couleur', libelle: 'Couleur' },
  { cle: 'fournisseur', libelle: 'Fournisseur' },
  { cle: 'dossier', libelle: 'Dossier' },
  { cle: 'lot', libelle: 'Lot' },
  { cle: 'role_bom', libelle: 'Rôle' },
] as const
export type Axe = (typeof AXES)[number]['cle']

/** L'axe par défaut de l'écran (le serveur, lui, prend la référence). */
export const AXE_DEFAUT: Axe = 'titrage'

export type Critere = 'composition' | 'type_fil' | 'titrage' | 'couleur' | 'fournisseur'
/** Le nom d'un critère dans l'adresse (`type` pour le type de fil). */
export type CritereAdresse = 'composition' | 'titrage' | 'type' | 'couleur' | 'fournisseur'

/** Les cinq critères combinables : leur nom au serveur, dans l'adresse, et la liste « tous ». */
export const CRITERES: readonly { cle: Critere; adresse: CritereAdresse; tous: string; libelle: string }[] = [
  { cle: 'composition', adresse: 'composition', tous: 'Toutes compositions', libelle: 'Composition' },
  { cle: 'titrage', adresse: 'titrage', tous: 'Tous titrages', libelle: 'Titrage' },
  { cle: 'type_fil', adresse: 'type', tous: 'Tous types de fil', libelle: 'Type de fil' },
  { cle: 'couleur', adresse: 'couleur', tous: 'Toutes couleurs', libelle: 'Couleur' },
  { cle: 'fournisseur', adresse: 'fournisseur', tous: 'Tous fournisseurs', libelle: 'Fournisseur' },
]

export type Combinaison = Partial<Record<Critere, string>>
export type Statut = '' | 'ouvert' | 'clos'

export interface EtatRevient {
  vue: VueRevient
  axe: Axe
  q: string
  statut: Statut
  du: string
  au: string
  qualite: number | null
  matieres: number[]
  combinaisons: Combinaison[]
  criteres: Record<Critere, string>
}

/** Les paramètres d'adresse que l'analyse reconnaît (`onglet` reste celui de la page). */
export type CleAdresse =
  'vue' | 'axe' | 'q' | 'statut' | 'du' | 'au' | 'qualite' | 'matieres' | 'combinaisons' | CritereAdresse

/** Ce qu'« Effacer les filtres » retire : tout sauf la vue et l'axe. */
export const CLES_FILTRES: readonly CleAdresse[] = [
  'q',
  'statut',
  'du',
  'au',
  'qualite',
  'matieres',
  'combinaisons',
  ...CRITERES.map((c) => c.adresse),
]

const DATE = /^\d{4}-\d{2}-\d{2}$/

const estCritere = (v: string): v is Critere => CRITERES.some((c) => c.cle === v)

/** Les combinaisons de l'adresse (JSON) ; un texte illisible n'en donne aucune. */
export function lireCombinaisons(texte: string | null): Combinaison[] {
  if (!texte) return []
  let brut: unknown
  try {
    brut = JSON.parse(texte)
  } catch {
    return []
  }
  if (!Array.isArray(brut)) return []
  const sortie: Combinaison[] = []
  for (const element of brut) {
    if (typeof element !== 'object' || element === null) continue
    const c: Combinaison = {}
    for (const [cle, valeur] of Object.entries(element)) {
      if (estCritere(cle) && typeof valeur === 'string' && valeur.trim()) c[cle] = valeur
    }
    if (Object.keys(c).length) sortie.push(c)
  }
  return sortie
}

/** Les matières choisies (`?matieres=1,2`), sans doublon. */
export function lireMatieres(texte: string | null): number[] {
  const ids = (texte ?? '')
    .split(',')
    .filter((x) => /^\d+$/.test(x))
    .map(Number)
  return [...new Set(ids)]
}

/** L'état de l'analyse lu dans l'adresse ; une valeur inconnue rend le défaut. */
export function lireEtat(params: URLSearchParams): EtatRevient {
  const vue = VUES.find((v) => v === params.get('vue')) ?? 'groupe'
  const axe = AXES.find((a) => a.cle === params.get('axe'))?.cle ?? AXE_DEFAUT
  const statut = params.get('statut')
  const qualite = params.get('qualite') ?? ''
  const date = (cle: string) => {
    const v = params.get(cle) ?? ''
    return DATE.test(v) ? v : ''
  }
  const lu = (cle: CritereAdresse) => params.get(cle) ?? ''
  const criteres: Record<Critere, string> = {
    composition: lu('composition'),
    type_fil: lu('type'),
    titrage: lu('titrage'),
    couleur: lu('couleur'),
    fournisseur: lu('fournisseur'),
  }
  return {
    vue,
    axe,
    q: params.get('q') ?? '',
    statut: statut === 'ouvert' || statut === 'clos' ? statut : '',
    du: date('du'),
    au: date('au'),
    qualite: /^\d+$/.test(qualite) ? Number(qualite) : null,
    matieres: lireMatieres(params.get('matieres')),
    combinaisons: lireCombinaisons(params.get('combinaisons')),
    criteres,
  }
}

/** La combinaison en cours : les critères posés. */
export function enCours(criteres: Record<Critere, string>): Combinaison {
  const c: Combinaison = {}
  for (const { cle } of CRITERES) if (criteres[cle]) c[cle] = criteres[cle]
  return c
}

/** « PES · 1500 » : une combinaison lue d'un coup d'œil. */
export function libelleCombinaison(c: Combinaison): string {
  return CRITERES.map(({ cle }) => c[cle])
    .filter(Boolean)
    .join(' · ')
}

/** Le nombre de critères posés (« N critère(s) » ; « Effacer les filtres » dès deux). */
export function nombreCriteres(e: EtatRevient): number {
  return (
    Object.values(e.criteres).filter(Boolean).length +
    e.combinaisons.length +
    e.matieres.length +
    [e.qualite != null, e.du, e.au, e.q.trim(), e.statut].filter(Boolean).length
  )
}

export type ParametresRevient = Record<string, string | number | boolean | number[] | undefined>

/** Les filtres envoyés au serveur (routes 206 et 208) ; `q` : la recherche déjà différée. */
export function parametresServeur(e: EtatRevient, q: string): ParametresRevient {
  const courante = enCours(e.criteres)
  const criteres: ParametresRevient = {}
  if (e.combinaisons.length) {
    const toutes = Object.keys(courante).length ? [...e.combinaisons, courante] : e.combinaisons
    criteres.selection = JSON.stringify(toutes)
  } else {
    for (const { cle } of CRITERES) criteres[cle] = e.criteres[cle] || undefined
  }
  return {
    axe: e.vue === 'lots' ? 'reference' : e.axe,
    q: q.trim() || undefined,
    statut: e.statut || undefined,
    du: e.du || undefined,
    au: e.au || undefined,
    qualite: e.qualite ?? undefined,
    matieres: e.matieres.length ? e.matieres : undefined,
    ...criteres,
  }
}

/** Les valeurs d'adresse d'une liste de matières et de combinaisons (`null` : retirer). */
export const ecrireMatieres = (ids: readonly number[]) => (ids.length ? ids.join(',') : null)
export const ecrireCombinaisons = (c: readonly Combinaison[]) => (c.length ? JSON.stringify(c) : null)

/** Les critères à vider (après « + Combinaison »). */
export function criteresVides(): Partial<Record<CleAdresse, null>> {
  const vides: Partial<Record<CleAdresse, null>> = {}
  for (const { adresse } of CRITERES) vides[adresse] = null
  return vides
}

export type Modifier = (changements: Partial<Record<CleAdresse, string | null>>) => void

/** L'état lu dans l'adresse et l'écriture groupée (une seule écriture, sans remplir l'historique). */
export function useEtatRevient(): { etat: EtatRevient; modifier: Modifier } {
  const [params, setParams] = useSearchParams()
  const etat = useMemo(() => lireEtat(params), [params])
  const modifier = useCallback<Modifier>(
    (changements) =>
      setParams(
        (p) => {
          let suite = new URLSearchParams(p)
          for (const [cle, valeur] of Object.entries(changements)) suite = avecParametre(suite, cle, valeur)
          return suite
        },
        { replace: true },
      ),
    [setParams],
  )
  return { etat, modifier }
}

/** Une valeur qui suit l'autre après un délai (la recherche part au serveur 300 ms après la frappe). */
export function useDiffere<T>(valeur: T, delai = 300): T {
  const [differe, setDiffere] = useState(valeur)
  useEffect(() => {
    const minuterie = setTimeout(() => setDiffere(valeur), delai)
    return () => clearTimeout(minuterie)
  }, [valeur, delai])
  return differe
}
