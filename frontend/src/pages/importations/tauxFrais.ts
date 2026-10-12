/**
 * Le taux d'un frais (lot TAUX-FRAIS) : 20 % de TVA, 2,5 % de droits… L'écran en tire un montant
 * proposé, que l'utilisateur garde ou corrige (la douane arrondit). Le serveur garde le taux pour
 * mémoire et le montant **tel quel** : rien ne le recalcule ensuite, pas même la réouverture du
 * dossier. Seul un changement explicite du taux recalcule.
 *
 * La base, en MAD, se lit dans la fiche déjà servie :
 * - « Porte sur » tout le dossier → toutes les marchandises ; une marchandise → elle seule ;
 * - TVA à l'importation (poste de nature `tva`) : valeur en douane + droits de douane + TPI déjà
 *   saisis (postes de nature `droits` et `tpi` ; pour une marchandise, ses parts réparties) ;
 * - tout autre poste : la valeur en douane (`valeur_douane_mad` : marchandise au cours payé + sa
 *   part de fret et d'assurance).
 */
import { arrondi, INSECABLE, montantPrecis, nombre } from '../../lib/format'
import type { DossierFiche, PosteFiche } from './types'

/** La base d'un taux : son montant en MAD et ce qu'elle additionne. */
export interface BaseDuTaux {
  montant: number
  libelle: string
}

/** Les natures de poste qui entrent dans la base de la TVA à l'importation. */
const NATURES_DE_LA_TVA = ['droits', 'tpi']

/** Le plus grand taux permis (le serveur refuse au-delà, et 0). */
export const TAUX_MAX = 100

/** La base du taux d'un frais de ce poste, sur tout le dossier (`ligneId` vide) ou une marchandise. */
export function baseDuTaux(
  d: DossierFiche,
  postes: readonly PosteFiche[],
  poste: PosteFiche | undefined,
  ligneId: number | null,
): BaseDuTaux {
  const lignes = ligneId == null ? d.lignes : d.lignes.filter((l) => l.id === ligneId)
  const douane = lignes.reduce((s, l) => s + l.valeur_douane_mad, 0)
  if (poste?.nature !== 'tva') return { montant: douane, libelle: 'valeur en douane' }
  const taxes = postes.filter((p) => NATURES_DE_LA_TVA.includes(p.nature))
  const ids = new Set(taxes.map((p) => p.id))
  const codes = new Set(taxes.map((p) => p.code))
  const saisies =
    ligneId == null
      ? d.frais.filter((f) => ids.has(f.poste_id)).reduce((s, f) => s + f.montant, 0)
      : lignes.reduce(
          (s, l) =>
            s +
            Object.entries(l.frais_par_poste)
              .filter(([code]) => codes.has(code))
              .reduce((t, [, m]) => t + m, 0),
          0,
        )
  return { montant: douane + saisies, libelle: 'valeur en douane + droits + TPI' }
}

/** Un taux permis : plus de 0, au plus 100. */
export const tauxPermis = (taux: number | null): taux is number =>
  taux != null && taux > 0 && taux <= TAUX_MAX

/** Le montant au taux : arrondi(base × taux / 100) au centime, demi éloigné de zéro. */
export const montantAuTaux = (base: number, taux: number) => arrondi((base * taux) / 100, 2)

/** « 20 % », « 2,5 % ». */
export const tauxLisible = (taux: number) => `${nombre(taux, 0, 4)}${INSECABLE}%`

/** La note sous le champ Taux : « 20 % de 3 105 220,40 MAD (valeur en douane + droits + TPI) ». */
export const noteDuTaux = (taux: number, base: BaseDuTaux) =>
  `${tauxLisible(taux)} de ${montantPrecis(base.montant, 'MAD')} (${base.libelle})`
