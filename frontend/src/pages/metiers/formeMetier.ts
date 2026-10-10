/**
 * La forme d'un métier au bureau (`/metiers/:id`, `/metiers/nouveau`) : son réglage et ses fils
 * montés, ce qui a changé, ce qui grise « Enregistrer » (raison qui suit l'état, an. 9), et les
 * corps envoyés : `PUT /metiers/{id}/montage` (alimentation) ou `PUT /metiers/{id}` (direction :
 * réglage **et** fils en une transaction, an. 14), avec l'effet annoncé à confirmer.
 */
import { nombre } from '../../lib/format'
import { largeurDe } from '../atelier/calculMontage'
import type { FilMonteFiche, MetierFiche } from '../atelier/types'

export interface FilForme {
  cle: string
  matiere_id: number
  reference: string
  designation: string
  etage: number
  metres: number | null
  pourcentage: number | null
  commentaire: string
}

export interface FormeMetier {
  code: string
  nom: string
  laize: number | null
  bobines_par_metre: number | null
  etages: number | null
  actif: boolean
  commentaire: string
  fils: FilForme[]
}

export const versFil = (f: FilMonteFiche): FilForme => ({
  cle: `f${f.id}`,
  matiere_id: f.matiere_id,
  reference: f.reference,
  designation: f.designation,
  etage: f.etage,
  metres: f.metres,
  pourcentage: f.pourcentage,
  commentaire: f.commentaire,
})

/** La forme d'un métier lu, ou celle d'un nouveau métier (laize 4,2 m, 6 étages, en service). */
export function versForme(m: MetierFiche | null): FormeMetier {
  return {
    code: m?.code ?? '',
    nom: m?.nom ?? '',
    laize: m?.laize ?? 4.2,
    bobines_par_metre: m?.bobines_par_metre ?? 0,
    etages: m?.etages ?? 6,
    actif: m?.actif ?? true,
    commentaire: m?.commentaire ?? '',
    fils: (m?.fils ?? []).map(versFil),
  }
}

const sansCle = (fils: readonly FilForme[]) =>
  JSON.stringify(
    fils.map(({ cle: _cle, ...f }) => f).sort((a, b) => a.etage - b.etage || a.matiere_id - b.matiere_id),
  )

export const filsChanges = (a: FormeMetier, b: FormeMetier) => sansCle(a.fils) !== sansCle(b.fils)

export function reglageChange(a: FormeMetier, b: FormeMetier): boolean {
  const { fils: _a, ...ra } = a
  const { fils: _b, ...rb } = b
  return JSON.stringify(ra) !== JSON.stringify(rb)
}

export const egal = (a: FormeMetier, b: FormeMetier) => !filsChanges(a, b) && !reglageChange(a, b)

/** Les étages dont les fils ont changé (ils partent au serveur avec leur version). */
export function etagesTouches(avant: FormeMetier, apres: FormeMetier): number[] {
  const n = new Set([...avant.fils, ...apres.fils].map((f) => f.etage))
  return [...n]
    .filter(
      (e) =>
        sansCle(avant.fils.filter((f) => f.etage === e)) !== sansCle(apres.fils.filter((f) => f.etage === e)),
    )
    .sort((a, b) => a - b)
}

/** La largeur occupée de chaque étage (Σ mètres montés ; le remplissage des bobines n'y entre pas). */
export function largeurs(f: FormeMetier): Map<number, number> {
  const m = new Map<number, number>()
  for (const fil of f.fils)
    m.set(
      fil.etage,
      (m.get(fil.etage) ?? 0) +
        largeurDe([{ matiere_id: 0, metres: fil.metres ?? 0, pourcentage: fil.pourcentage ?? 0 }]),
    )
  return m
}

/** Ce qui grise « Enregistrer », dans l'ordre où on le lève ; vide si tout est prêt. */
export function raisonEnregistrer(f: FormeMetier, initiale: FormeMetier, direction: boolean): string {
  if (egal(f, initiale)) return 'Aucune modification'
  if (direction && !f.code.trim()) return 'Saisir le code'
  if (direction && !(f.etages != null && Number.isInteger(f.etages) && f.etages >= 1 && f.etages <= 40))
    return 'Les étages vont de 1 à 40'
  const max = f.etages ?? 0
  if (f.fils.some((x) => x.etage > max)) return 'Fils hors machine : les déplacer ou les retirer'
  const laize = f.laize ?? 0
  const trop = [...largeurs(f)].filter(([, l]) => laize > 0 && l > laize + 1e-6).map(([e]) => e)
  if (trop.length) return `Étage ${trop.join(', ')} trop large`
  const sans = f.fils.filter((x) => !((x.metres ?? 0) > 0))
  if (sans.length) return `Saisir les mètres de ${sans.map((x) => x.reference).join(', ')}`
  return ''
}

/** Le montage envoyé : les étages touchés, chacun avec sa version, et l'effet à confirmer. */
export function corpsMontage(m: MetierFiche, avant: FormeMetier, apres: FormeMetier, effet: number) {
  const touches = etagesTouches(avant, apres)
  if (!touches.length) return null
  return {
    etages: touches.map((e) => ({
      etage: e,
      version: m.etages_detail.find((x) => x.etage === e)?.version ?? 1,
      fils: apres.fils
        .filter((f) => f.etage === e)
        .map((f) => ({
          matiere_id: f.matiere_id,
          metres: f.metres ?? 0,
          pourcentage: f.pourcentage ?? 0,
          commentaire: f.commentaire,
        })),
    })),
    confirme_effet_kg: effet,
  }
}

/** Le réglage envoyé par la direction (`PUT /metiers/{id}`, `POST /metiers`). */
export function corpsReglage(f: FormeMetier) {
  return {
    code: f.code.trim(),
    nom: f.nom.trim(),
    laize: f.laize ?? 0,
    bobines_par_metre: f.bobines_par_metre ?? 0,
    etages: f.etages ?? 1,
    actif: f.actif,
    commentaire: f.commentaire.trim(),
  }
}

/** Le pied de la fiche : « Étage(s) trop large(s) : 2, 4. » / « Modifications non enregistrées. » / « Aucune modification. » */
export function etatPied(f: FormeMetier, initiale: FormeMetier): string {
  const laize = f.laize ?? 0
  const trop = [...largeurs(f)].filter(([, l]) => laize > 0 && l > laize + 1e-6).map(([e]) => nombre(e))
  if (trop.length) return `Étage(s) trop large(s) : ${trop.join(', ')}.`
  return egal(f, initiale) ? 'Aucune modification.' : 'Modifications non enregistrées.'
}
