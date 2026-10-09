/**
 * Les règles d'écran d'un poste de frais (ECRANS-PRO 5.19–5.20), sans affichage : la forme saisie,
 * le code contrôlé à la frappe comme le serveur, la nature figée, ce qui empêche la suppression,
 * le message avant un changement de clé et le retour du serveur après (anomalie 5.12).
 */
import { nombre } from '../../../lib/format'
import type { Schema } from '../../../lib/types'
import type { PosteFiche } from '../types'

export type Cle = 'valeur' | 'poids'

/** « à la valeur », « au poids ». */
export const CLES: Readonly<Record<Cle, string>> = { valeur: 'à la valeur', poids: 'au poids' }

export const lireCle = (cle: string): Cle => (cle === 'poids' ? 'poids' : 'valeur')

/** Le code d'un poste, comme le serveur l'accepte (`[A-Z0-9_]{1,16}`). */
export const CODE_POSTE = /^[A-Z0-9_]{1,16}$/
export const LONGUEUR_CODE = 16
export const LONGUEUR_LIBELLE = 80
export const MESSAGE_CODE = 'Le code d’un poste : lettres, chiffres ou « _ », sans espace (ex. MANUT).'

/** L'infobulle du badge « calculs » d'un poste système. */
export const AIDE_SYSTEME =
  'Lu par les calculs du dossier (TVA attendue) : il ne se supprime pas et garde sa nature'

export interface FormePoste {
  code: string
  libelle: string
  cle: Cle
  ordre: number | null
  recuperable: boolean
}

export function versFormePoste(p: PosteFiche | null): FormePoste {
  return {
    code: p?.code ?? '',
    libelle: p?.libelle ?? '',
    cle: lireCle(p?.cle ?? 'valeur'),
    ordre: p?.ordre ?? null,
    recuperable: p?.recuperable ?? false,
  }
}

export const egalPoste = (a: FormePoste, b: FormePoste) => JSON.stringify(a) === JSON.stringify(b)

/** Le message sous le code tapé s'il n'est pas accepté, sinon ''. */
export function erreurCodePoste(code: string): string {
  const c = code.trim()
  return c && !CODE_POSTE.test(c) ? MESSAGE_CODE : ''
}

/** Les frais saisis d'un poste (dossiers ouverts et clos). */
export const fraisSaisis = (p: PosteFiche) => p.frais_ouverts + p.frais_clos

/** « récupérable, hors coût » ou « coût ». */
export const nature = (recuperable: boolean) => (recuperable ? 'récupérable, hors coût' : 'coût')

/** Pourquoi la nature (« récupérable ») ne se change pas, ou `null`. */
export function natureFigee(p: PosteFiche | null): string | null {
  if (!p) return null
  if (p.systeme) return 'Nature figée : les calculs du dossier lisent ce poste ainsi.'
  if (p.dossiers_clos)
    return `Nature figée : il porte des frais dans ${nombre(p.dossiers_clos)} dossier(s) clos : créer un autre poste.`
  return null
}

/** Ce qui empêche la suppression (le serveur refusera). */
export function blocagesPoste(p: PosteFiche): string[] {
  if (p.systeme) return ['Ce poste sert aux calculs du dossier : il ne se supprime pas']
  const n = fraisSaisis(p)
  if (n) return [`Ce poste porte ${nombre(n)} frais dans des dossiers : il ne se supprime pas`]
  if (p.utilise) return ['Ce poste porte des frais dans des dossiers : il ne se supprime pas']
  return []
}

/** Avant d'enregistrer un changement de clé : ce que deviennent les dossiers ouverts et clos. */
export function messageChangementCle(p: PosteFiche, nouvelle: Cle): string {
  const ouverts = `Les ${nombre(p.dossiers_ouverts)} dossier(s) ouvert(s) seront recalculés ${CLES[nouvelle]}.`
  if (!p.dossiers_clos) return ouverts
  return `${ouverts} Les ${nombre(p.dossiers_clos)} dossier(s) clos gardent leur coût : leurs frais de ce poste seront éclatés sur leurs marchandises, ${CLES[lireCle(p.cle)]} (c’est tracé).`
}

/** Après l'enregistrement : ce que le serveur a fait (dossiers ouverts recalculés, clos figés). */
export function messageEnregistre(avant: PosteFiche, rendu: PosteFiche): string {
  const debut = `Poste ${rendu.code} enregistré.`
  if (lireCle(rendu.cle) === lireCle(avant.cle)) return debut
  const figes = rendu.parts_figees ?? 0
  const clos = figes
    ? `${nombre(figes)} dossier(s) clos gardent leur coût : leurs frais de ce poste sont figés ${CLES[lireCle(avant.cle)]} (c’est tracé).`
    : 'aucun dossier clos à figer.'
  return `${debut} Ses frais se répartissent désormais ${CLES[lireCle(rendu.cle)]} : ${nombre(rendu.dossiers_ouverts)} dossier(s) ouvert(s) recalculé(s) ; ${clos}`
}

/** Ce qui reste à renseigner pour enregistrer. */
export function manquesPoste(f: FormePoste): string[] {
  const manque: string[] = []
  if (!f.code.trim()) manque.push('Code')
  if (!f.libelle.trim()) manque.push('Libellé')
  return manque
}

/** Le corps d'une création (route 35) : nature ordinaire, hors valeur en douane. */
export function corpsCreation(f: FormePoste): Schema<'PosteCreation'> {
  return {
    code: f.code.trim().toUpperCase(),
    libelle: f.libelle.trim(),
    recuperable: f.recuperable,
    cle: f.cle,
    ordre: f.ordre,
    nature: 'autre',
    entre_valeur_douane: false,
  }
}

/** Le corps d'une modification (route 36) : la nature et l'entrée en valeur en douane lues, inchangées. */
export function corpsModification(f: FormePoste, p: PosteFiche): Schema<'PosteModification'> {
  return {
    libelle: f.libelle.trim(),
    recuperable: f.recuperable,
    cle: f.cle,
    ordre: f.ordre,
    nature: p.nature,
    entre_valeur_douane: p.entre_valeur_douane,
    version: p.version,
  }
}
