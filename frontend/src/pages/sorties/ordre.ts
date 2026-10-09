/**
 * Le moteur de saisie d'un ordre de fabrication (ECRANS-PRO « Logique de l'envoi », règles
 * partagées bureau / téléphone) : la demande (date, magasin, métier, commentaire, qualités et m²,
 * ou ordre hors recette), la proposition du serveur (les lots les plus anciens présents à la date),
 * les prises corrigées au réel (kilos, bobines ou palettes), les matières ajoutées à la main.
 *
 * Les quantités sont tenues **en kilos** (le composant `Quantite` convertit et dit l'arrondi) et
 * partent en kilos. Le disponible d'un lot est lu **à la date de l'ordre** (`GET lots?magasin=&date=`,
 * H-19, P2-23). Ce que le serveur refusera est annoncé avant l'envoi (`blocagesSaisie`).
 * Fonctions pures ici ; l'état est dans `useSaisieOrdre.ts`.
 */
import { date as dateLisible, kg } from '../../lib/format'
import type { Unite } from '../../lib/unites'
import type { LigneProposee } from './donnees'

/** Un lot pris dans l'ordre. */
export interface Prise {
  cle: string
  matiere_id: number
  reference: string
  designation: string
  kg_par_ml: number
  poids_bobine: number
  bobines_palette: number
  lot_id: number
  lot: string
  /** Les kilos pris (la vérité de la ligne), `null` tant que rien n'est saisi. */
  kg: number | null
  unite: Unite
}

export interface Fabrication {
  qualite_id: number | null
  m2: number | null
}

/** Une matière de l'ordre : ce que les recettes en demandent, et ce qu'on en prend. */
export interface Fil {
  matiere_id: number
  reference: string
  designation: string
  kg_par_ml: number
  besoin?: LigneProposee
  prises: Prise[]
  sorti: number
  ecart: number | null
}

let compteur = 0
export const nouvelleCle = () => `p${++compteur}`

/** Les fils de l'ordre : un par matière, besoins du serveur d'abord, matières ajoutées ensuite. */
export function filsDe(besoins: readonly LigneProposee[], prises: readonly Prise[]): Fil[] {
  const groupes = new Map<number, Fil>()
  for (const b of besoins)
    groupes.set(b.matiere_id, {
      matiere_id: b.matiere_id,
      reference: b.reference,
      designation: b.designation,
      kg_par_ml: b.kg_par_ml,
      besoin: b,
      prises: [],
      sorti: 0,
      ecart: null,
    })
  for (const p of prises) {
    const f = groupes.get(p.matiere_id) ?? {
      matiere_id: p.matiere_id,
      reference: p.reference,
      designation: p.designation,
      kg_par_ml: p.kg_par_ml,
      prises: [],
      sorti: 0,
      ecart: null,
    }
    f.prises.push(p)
    groupes.set(p.matiere_id, f)
  }
  for (const f of groupes.values()) {
    f.sorti = f.prises.reduce((t, p) => t + (p.kg ?? 0), 0)
    f.ecart = f.besoin ? f.sorti - f.besoin.prevu : null
  }
  return [...groupes.values()]
}

/** Les prises que propose le serveur (les lots les plus anciens, au gramme près). */
export function prisesProposees(lignes: readonly LigneProposee[]): Prise[] {
  return lignes.flatMap((l) =>
    l.lots.map((lot) => ({
      cle: nouvelleCle(),
      matiere_id: l.matiere_id,
      reference: l.reference,
      designation: l.designation,
      kg_par_ml: l.kg_par_ml,
      poids_bobine: lot.poids_bobine || l.poids_bobine,
      bobines_palette: l.bobines_palette,
      lot_id: lot.lot_id,
      lot: lot.lot,
      kg: Math.round(lot.propose * 1000) / 1000,
      unite: 'kg' as const,
    })),
  )
}

/**
 * Recalculer remplace les lots proposés et garde les matières ajoutées à la main (celles
 * qu'aucune recette ne demande, avant comme après).
 */
export function recalculer(
  prises: readonly Prise[],
  avant: readonly LigneProposee[],
  apres: readonly LigneProposee[],
): Prise[] {
  const demandees = new Set([...avant, ...apres].map((l) => l.matiere_id))
  return [...prisesProposees(apres), ...prises.filter((p) => !demandees.has(p.matiere_id))]
}

/** Ce qui sera envoyé : les prises d'au moins un gramme. */
export const aEnvoyer = (prises: readonly Prise[]) => prises.filter((p) => (p.kg ?? 0) >= 0.001)

export interface ContexteBlocages {
  jour: string
  aujourdhui: string
  /** Dernier jour de la période close, s'il y en a une. */
  cloture: string | null
  /** La date du dernier ordre validé ou annulé (les numéros suivent les dates). */
  dernier: string | null
  magasin: string
  inventaires: readonly {
    numero: string
    date: string
    magasin: string | null
    matieres: readonly number[]
  }[]
  /** Le disponible de chaque lot dans le magasin, à la date de l'ordre ; `null` tant qu'il se lit. */
  dispo: ReadonlyMap<number, number> | null
}

/**
 * Ce que le serveur refusera à la validation, dit d'avance avec ses mots (REGLES ; services
 * `ordres/proposition.empechements`, `ordres/blocages`, `periode.date_permise`).
 */
export function blocagesSaisie(prises: readonly Prise[], c: ContexteBlocages): string[] {
  const raisons: string[] = []
  if (c.jour > c.aujourdhui)
    raisons.push(`Date dans le futur (${dateLisible(c.jour)}) : un mouvement se saisit le jour où il a lieu.`)
  if (c.cloture && c.jour && c.jour <= c.cloture)
    raisons.push(
      `La période jusqu'au ${dateLisible(c.cloture)} est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir.`,
    )
  const matieres = new Set(aEnvoyer(prises).map((p) => p.matiere_id))
  for (const i of c.inventaires) {
    if (i.magasin && i.magasin !== c.magasin) continue
    if (!i.matieres.some((m) => matieres.has(m))) continue
    raisons.push(
      `L'inventaire ${i.numero} (${i.magasin ?? 'tous les magasins'}, du ${dateLisible(i.date)}) est en cours : les mouvements y sont suspendus jusqu'à sa validation. Garder en brouillon, ou attendre.`,
    )
  }
  if (c.dernier && c.jour && c.jour < c.dernier)
    raisons.push(
      `Un ordre du ${dateLisible(c.dernier)} est déjà validé : les numéros suivent les dates, cet ordre ne peut pas être daté avant. Pour un oubli, le dater du ${dateLisible(c.dernier)} et écrire la vraie date dans le commentaire.`,
    )
  const voulu = new Map<number, { p: Prise; kg: number }>()
  for (const p of aEnvoyer(prises)) {
    const v = voulu.get(p.lot_id)
    voulu.set(p.lot_id, { p, kg: (v?.kg ?? 0) + (p.kg ?? 0) })
  }
  for (const { p, kg: demande } of voulu.values()) {
    if (!c.dispo) break
    const present = c.dispo.get(p.lot_id) ?? 0
    if (demande > present + 0.0005)
      raisons.push(
        `lot ${p.lot} de ${p.reference} : ${present > 0.0005 ? `${kg(present)} seulement` : 'épuisé'} dans « ${c.magasin} », ${kg(demande)} demandés`,
      )
  }
  return raisons
}

/** Ce qui manque pour garder en brouillon (P2-11) : une ligne, et des bobines qui ont un poids. */
export function manqueBrouillon(prises: readonly Prise[]): string[] {
  const manque: string[] = []
  if (!aEnvoyer(prises).length) manque.push('au moins une ligne de plus d’un gramme')
  const sansPoids = prises.filter((p) => p.unite !== 'kg' && !(p.poids_bobine > 0))
  if (sansPoids.length)
    manque.push(`le poids en kg de ${sansPoids.map((p) => p.reference).join(', ')} (poids de bobine inconnu)`)
  return manque
}

/** Ce qui manque pour demander la proposition (P2-11). */
export function manqueProposer(f: {
  jour: string
  magasin: number | null
  fabrications: readonly Fabrication[]
}): string[] {
  const manque: string[] = []
  if (!f.magasin) manque.push('le magasin')
  if (!f.jour) manque.push('la date')
  if (!f.fabrications.length || f.fabrications.some((x) => !x.qualite_id))
    manque.push('la qualité de chaque ligne')
  if (f.fabrications.some((x) => !(x.m2 && x.m2 > 0))) manque.push('les m² à tisser de chaque qualité')
  return manque
}
