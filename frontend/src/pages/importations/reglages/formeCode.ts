/**
 * Les règles d'écran d'un code douanier (ECRANS-PRO 5.21–5.22), sans affichage : la forme saisie
 * (taux en fraction, 0,1 = 10 %, saisi en %), le code et le taux contrôlés à la frappe comme le
 * serveur, ce qui empêche la suppression, le corps envoyé.
 */
import { nombre } from '../../../lib/format'
import type { Schema } from '../../../lib/types'
import type { CodeDouanier } from '../types'

/** Un code douanier comme le serveur l'accepte : des chiffres, éventuellement séparés de points. */
export const FORMAT_CODE = /^\d[\d.]{1,19}$/
export const LONGUEUR_CODE = 20
export const LONGUEUR_LIBELLE = 160
export const MESSAGE_CODE =
  'Un code douanier s’écrit en chiffres, éventuellement séparés de points (ex. 5402.47.00.00).'
export const MESSAGE_TAUX = 'Un taux de droits va de 0 à 100 %.'

export interface FormeCode {
  code: string
  libelle: string
  /** En fraction (0,1 = 10 %), `null` tant qu'il n'est pas saisi. */
  taux: number | null
  actif: boolean
}

/** Un taux sans les restes du passage en % (12,3 / 100 = 0,12300000000000001). */
export const arrondirTaux = (t: number) => Math.round(t * 1e8) / 1e8

export function versFormeCode(c: CodeDouanier | null): FormeCode {
  return {
    code: c?.code ?? '',
    libelle: c?.libelle ?? '',
    taux: c ? arrondirTaux(c.taux_droits) : null,
    actif: c?.actif ?? true,
  }
}

export const egalCode = (a: FormeCode, b: FormeCode) =>
  a.code === b.code &&
  a.libelle === b.libelle &&
  a.actif === b.actif &&
  (a.taux == null ? b.taux == null : b.taux != null && arrondirTaux(a.taux) === arrondirTaux(b.taux))

/** Le code tel que le serveur le range (les espaces ne comptent pas). */
export const codePropre = (code: string) => code.replace(/\s+/g, '')

/** Le message sous le code tapé s'il n'est pas accepté, sinon ''. */
export function erreurCodeDouanier(code: string): string {
  const c = codePropre(code)
  return c && !FORMAT_CODE.test(c) ? MESSAGE_CODE : ''
}

/** Vrai si le taux saisi sort de 0 à 100 %. */
export const tauxHorsBornes = (t: number | null) => t != null && (t < 0 || t > 1)

/** Ce qui reste à renseigner pour enregistrer. */
export function manquesCode(f: FormeCode): string[] {
  const manque: string[] = []
  if (!codePropre(f.code)) manque.push('Code')
  if (f.taux == null || tauxHorsBornes(f.taux)) manque.push('Taux de 0 à 100 %')
  return manque
}

/** Ce qui empêche la suppression (le serveur refusera). */
export function blocagesCode(c: CodeDouanier): string[] {
  return c.nb_matieres
    ? [`${nombre(c.nb_matieres)} matière(s) portent ce code : le leur retirer, ou le désactiver`]
    : []
}

/** Le corps d'une création (route 39) ; la modification (route 40) y ajoute la version. */
export function corpsCode(f: FormeCode): Schema<'CodeDouanierCreation'> {
  return {
    code: codePropre(f.code),
    libelle: f.libelle.trim(),
    taux_droits: arrondirTaux(f.taux ?? 0),
    actif: f.actif,
  }
}

/** Les matières qui portent ce code, au catalogue. */
export const lienMatieres = (code: string) => `/catalogue?onglet=matieres&q=${encodeURIComponent(code)}`
