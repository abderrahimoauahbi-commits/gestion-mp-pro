/**
 * Les calculs du montage d'un étage, **comme le serveur** (services/montage.py, lot D2) :
 * largeur occupée = Σ mètres ; bobines = mètres × bobines par mètre (le remplissage des bobines
 * n'y entre pas) ; poids = bobines × poids de bobine retenu (pesé au lot, sinon catalogue — le
 * même au bureau et au téléphone, an. 11) × remplissage des bobines / 100 ; un métier arrêté ne
 * compte rien. L'effet annoncé est envoyé pour
 * confirmation (`confirme_effet_kg`) ; le texte unique « sur les métiers » ((a)) et l'alerte
 * 30 jours sont ceux du serveur.
 */
import { arrondi, nombre } from '../../lib/format'
import type { EtageFiche, MatiereMontage, MetierFiche } from './types'

export interface FilSaisi {
  matiere_id: number
  reference: string
  designation: string
  metres: number
  pourcentage: number
  commentaire: string
}

export interface SaisieEtage {
  version: number
  fils: FilSaisi[]
}

export const TOLERANCE_EFFET = 0.05

/** L'étage tel qu'enregistré : sa version et ses fils. */
export function etageEnregistre(m: MetierFiche, n: number): SaisieEtage {
  const detail: EtageFiche | undefined = m.etages_detail.find((e) => e.etage === n)
  return {
    version: detail?.version ?? 1,
    fils: m.fils
      .filter((f) => f.etage === n)
      .map((f) => ({
        matiere_id: f.matiere_id,
        reference: f.reference,
        designation: f.designation,
        metres: f.metres,
        pourcentage: f.pourcentage,
        commentaire: f.commentaire,
      })),
  }
}

/** Le poids d'une bobine retenu par le montage (celui que le stock comptera). */
export function poidsRetenu(
  m: MetierFiche,
  matieres: readonly MatiereMontage[] | undefined,
  id: number,
): number {
  const lu = matieres?.find((x) => x.matiere_id === id)
  if (lu) return lu.poids_bobine_compte
  return m.fils.find((f) => f.matiere_id === id)?.poids_bobine_utilise ?? 0
}

/** Ce qu'il faut d'un fil pour le peser. */
export type FilPese = Pick<FilSaisi, 'matiere_id' | 'metres' | 'pourcentage'>

/** Ce qu'il faut d'un métier pour peser ses fils. */
export type ReglagePese = Pick<MetierFiche, 'actif' | 'bobines_par_metre'>

export const largeurDe = (fils: readonly FilPese[]) => fils.reduce((t, f) => t + f.metres, 0)

export const bobinesDe = (m: ReglagePese, f: FilPese) => f.metres * m.bobines_par_metre

/** Ce que pèsent ces fils sur ce métier (0 s'il est arrêté). Poids = bobines × poids de
 * bobine retenu × remplissage des bobines / 100. */
export function peser(m: ReglagePese, fils: readonly FilPese[], poids: (id: number) => number): number {
  if (!m.actif) return 0
  return fils.reduce((t, f) => t + bobinesDe(m, f) * poids(f.matiere_id) * (f.pourcentage / 100), 0)
}

/** « +40,0 », « −3,5 » (comme `montage.signe` du serveur). */
export const signe = (v: number) => `${v >= 0 ? '+' : '−'}${nombre(Math.abs(v), 0, 2)}`

/** Le texte unique de l'effet d'un montage sur le stock sur les métiers ((a)). */
export function messageMontage(actif: boolean, avant: number, apres: number): string {
  if (!actif) return 'Métier arrêté : rien n’est compté sur lui.'
  if (Math.abs(apres - avant) < TOLERANCE_EFFET) return 'Le stock sur les métiers ne change pas.'
  return (
    'Monter n’écrit aucun mouvement : ce fil est déjà sorti par un ordre. Le stock sur les métiers passe de ' +
    `${nombre(avant, 0, 2)} à ${nombre(apres, 0, 2)} kg (${signe(apres - avant)} kg) ; il compte dans le stock ` +
    'global, sa valeur, le disponible et le projeté.'
  )
}

/**
 * Les alertes 30 jours : une matière de l'étage dont le poids sur les métiers en service, une
 * fois l'étage monté, dépasse 1,1 × ce qui est parti aux machines en 30 jours + 1 kg.
 */
export function alertesMontage(
  m: { avant: ReglagePese; apres: ReglagePese },
  avant: readonly FilPese[],
  apres: readonly (FilPese & { reference?: string })[],
  matieres: readonly MatiereMontage[] | undefined,
  poids: (id: number) => number,
): string[] {
  const textes: string[] = []
  for (const id of new Set(apres.map((f) => f.matiere_id))) {
    const lu = matieres?.find((x) => x.matiere_id === id)
    if (!lu) continue
    const seul = (fils: readonly FilPese[]) => fils.filter((f) => f.matiere_id === id)
    const total = lu.deja_monte - peser(m.avant, seul(avant), poids) + peser(m.apres, seul(apres), poids)
    if (total > 1.1 * lu.sorti_30_j + 1)
      textes.push(
        `${lu.reference} : ${nombre(total, 0, 2)} kg sur les métiers pour ${nombre(lu.sorti_30_j, 0, 2)} kg partis ` +
          `aux machines en ${lu.jours} jours : vérifier qu’il est bien sorti par un ordre avant de le monter.`,
      )
  }
  return textes
}

/** L'effet à confirmer, au gramme (comme le serveur l'arrondit). */
export const effetDe = (
  m: { avant: ReglagePese; apres: ReglagePese },
  avant: readonly FilPese[],
  apres: readonly FilPese[],
  poids: (id: number) => number,
) => arrondi(peser(m.apres, apres, poids) - peser(m.avant, avant, poids), 3)

/** La raison de griser « Enregistrer l'étage », écrite sous le bouton (an. 9). */
export function raisonEtage(e: { trop: boolean; sansMetres: readonly FilSaisi[]; modifie: boolean }): string {
  if (e.trop) return 'Plus large que la laize'
  if (e.sansMetres.length) return `Saisir les mètres de : ${e.sansMetres.map((f) => f.reference).join(', ')}`
  if (!e.modifie) return 'Aucune modification'
  return ''
}

/** Le corps de `PUT /metiers/{id}/etages/{n}`. */
export function corpsEtage(s: SaisieEtage, effet: number) {
  return {
    version: s.version,
    fils: s.fils.map((f) => ({
      matiere_id: f.matiere_id,
      metres: f.metres,
      pourcentage: f.pourcentage,
      commentaire: f.commentaire,
    })),
    confirme_effet_kg: effet,
  }
}
