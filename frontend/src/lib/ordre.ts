/**
 * LE moteur de saisie d'un ordre de fabrication, unique pour le bureau (`/ordres/nouveau`, lot F2)
 * et le téléphone (`/atelier/envoyer`, lot F3) — ECRANS-PRO « Logique de l'envoi » : la demande
 * (date, magasin, métier, observations, qualités et m², ou ordre hors recette), la proposition du
 * serveur (les lots les plus anciens présents à la date), les prises corrigées au réel, les
 * matières ajoutées à la main, l'écart au prévu, ce que le serveur refusera, le corps envoyé,
 * l'enregistrement (brouillon, puis validation ; un refus laisse le brouillon enregistré).
 *
 * Les quantités sont tenues **en kilos** (`Prise.kg`, la vérité de la ligne ; `unite` est celle où
 * on la compte, le composant `Quantite` convertit et dit l'arrondi) et partent en kilos. Le
 * disponible d'un lot est lu **à la date de l'ordre** (H-19, P2-23, an. 23). Les phrases de refus
 * sont celles du serveur (`services/ordres/proposition.empechements`, `ordres/blocages`,
 * `periode.date_permise`), « commentaire » dit « observations » (vocabulaire, an. 8).
 * Les deux crochets d'état (`sorties/useSaisieOrdre`, `atelier/useSaisieSortie` qui garde la saisie
 * sur le téléphone) n'ont plus de règle à eux.
 */
import { api, ErreurApi, messageErreur } from './api'
import { arrondi } from './format'
import type { Schema } from './types'
import { contenance, type Conditionnement, type Unite } from './unites'

type LigneProposee = Schema<'LigneProposee'>
type LigneOrdre = Schema<'LigneOrdre'>
type LotSolde = Schema<'LotSolde'>
type OrdreFiche = Schema<'OrdreFiche'>
type Proposition = Schema<'Proposition'>

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
  /** L'unité où on la compte (kg, bobines, palettes). */
  unite: Unite
}

/** Une qualité à fabriquer et ses m². */
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
export const nouvelleCle = () => `p${Date.now().toString(36)}${++compteur}`

export const conditionnement = (p: Prise): Conditionnement => ({
  poidsBobine: p.poids_bobine,
  bobinesPalette: p.bobines_palette,
  kgParMl: p.kg_par_ml,
})

/** Les kilos d'une prise (0 tant que rien n'est saisi). */
export const kgDe = (p: Prise): number => p.kg ?? 0

interface MatiereDuLot {
  matiere_id: number
  reference: string
  designation: string
  kg_par_ml: number
  poids_bobine: number
  bobines_palette: number
}

/** Une prise d'un lot, en kilos (`null` : rien de saisi). */
export function priseDe(
  m: MatiereDuLot,
  lot: { lot_id: number; lot: string; poids_bobine?: number },
  kilos: number | null = null,
): Prise {
  return {
    cle: nouvelleCle(),
    matiere_id: m.matiere_id,
    reference: m.reference,
    designation: m.designation,
    kg_par_ml: m.kg_par_ml,
    poids_bobine: lot.poids_bobine || m.poids_bobine,
    bobines_palette: m.bobines_palette,
    lot_id: lot.lot_id,
    lot: lot.lot,
    kg: kilos == null ? null : arrondi(kilos, 3),
    unite: 'kg',
  }
}

/** La ligne d'un brouillon rouvert : comptée en bobines si le compte tombe juste, sinon au gramme. */
export function priseRouverte(l: LigneOrdre): Prise {
  const p = priseDe(l, { lot_id: l.lot_id, lot: l.lot, poids_bobine: l.poids_bobine }, l.quantite)
  return l.bobines != null && l.bobines >= 1 ? { ...p, unite: 'bobine' } : p
}

/** La prise d'un lot choisi dans la liste des lots du magasin (matière ajoutée à la main). */
export const priseDuSolde = (x: LotSolde): Prise =>
  priseDe(x, { lot_id: x.lot_id, lot: x.lot, poids_bobine: x.poids_bobine })

/** Les prises que propose le serveur (les lots les plus anciens, au gramme près). */
export function prisesProposees(lignes: readonly LigneProposee[]): Prise[] {
  return lignes.flatMap((l) => l.lots.map((lot) => priseDe(l, lot, lot.propose)))
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
export const aEnvoyer = (prises: readonly Prise[]) => prises.filter((p) => kgDe(p) >= 0.001)

/** Les fils de l'ordre : un par matière, besoins du serveur d'abord, matières ajoutées ensuite. */
export function filsDe(besoins: readonly LigneProposee[], prises: readonly Prise[]): Fil[] {
  const fils = new Map<number, Fil>()
  const fil = (m: MatiereDuLot, besoin?: LigneProposee): Fil => ({
    matiere_id: m.matiere_id,
    reference: m.reference,
    designation: m.designation,
    kg_par_ml: m.kg_par_ml,
    besoin,
    prises: [],
    sorti: 0,
    ecart: null,
  })
  for (const b of besoins) fils.set(b.matiere_id, fil(b, b))
  for (const p of prises) {
    const f = fils.get(p.matiere_id) ?? fil(p)
    f.prises.push(p)
    fils.set(p.matiere_id, f)
  }
  for (const f of fils.values()) {
    f.sorti = arrondi(
      f.prises.reduce((t, p) => t + kgDe(p), 0),
      3,
    )
    f.ecart = f.besoin ? arrondi(f.sorti - f.besoin.prevu, 3) : null
  }
  return [...fils.values()]
}

export {
  depasse,
  ecartLisible,
  ecartRelatif,
  filConforme,
  SEUIL_ECART,
  tonEcart,
  type EcartLisible,
} from './ordreEcarts'
export {
  blocageDate,
  blocagesSaisie,
  dernierOrdre,
  texteInventaire,
  type ContexteBlocages,
} from './ordreBlocages'

/** Ce qui manque pour garder en brouillon (P2-11) : une ligne, et des bobines qui ont un poids. */
export function manqueBrouillon(prises: readonly Prise[]): string[] {
  const manque: string[] = []
  if (!aEnvoyer(prises).length) manque.push('au moins une ligne de plus d’un gramme')
  const sansPoids = prises.filter((p) => contenance(conditionnement(p), p.unite) == null)
  if (sansPoids.length)
    manque.push(`le poids en kg de ${sansPoids.map((p) => p.reference).join(', ')} (poids de bobine inconnu)`)
  return manque
}

/** Ce qui manque pour demander la proposition (P2-11), dans l'ordre où on remplit. */
export function manqueProposer(f: {
  jour: string
  magasin: number | null
  horsRecette?: boolean
  fabrications: readonly Fabrication[]
}): string[] {
  const manque: string[] = []
  if (!f.magasin) manque.push('le magasin')
  if (!f.jour) manque.push('la date')
  if (f.horsRecette) return manque
  if (!f.fabrications.length || f.fabrications.some((x) => !x.qualite_id))
    manque.push('la qualité de chaque ligne')
  if (f.fabrications.some((x) => !(x.m2 && x.m2 > 0))) manque.push('les m² à tisser de chaque qualité')
  return manque
}

/** La demande d'un ordre, telle que l'écran la tient. */
export interface Demande {
  jour: string
  metier: number | null
  commentaire: string
  horsRecette: boolean
  fabrications: readonly Fabrication[]
}

/** Les qualités envoyées : aucune hors recette, les lignes complètes sinon. */
export function qualitesDuCorps(d: Pick<Demande, 'horsRecette' | 'fabrications'>) {
  if (d.horsRecette) return []
  return d.fabrications.flatMap((f) =>
    f.qualite_id != null && f.m2 ? [{ qualite_id: f.qualite_id, m2: f.m2 }] : [],
  )
}

/** Les lignes partent en kilos. */
const KG: Unite = 'kg'

/** Ce qui part au serveur : la demande, et les prises d'au moins un gramme, en kilos. */
export function corpsOrdre(d: Demande, magasin: number | null, prises: readonly Prise[]) {
  return {
    date: d.jour,
    magasin_id: magasin,
    metier_id: d.metier,
    commentaire: d.commentaire.trim(),
    qualites: qualitesDuCorps(d),
    lignes: aEnvoyer(prises).map((x) => ({
      lot_id: x.lot_id,
      matiere_id: x.matiere_id,
      quantite: kgDe(x),
      unite: KG,
    })),
  }
}

export type CorpsOrdre = ReturnType<typeof corpsOrdre>

/** La proposition du serveur pour la demande (route 136). */
export function demanderProposition(d: Demande, magasin: number | null): Promise<Proposition> {
  return api.post<Proposition>('/ordres/proposition', {
    date: d.jour,
    magasin_id: magasin,
    metier_id: d.metier,
    qualites: qualitesDuCorps(d),
  })
}

/**
 * Enregistre le brouillon (créé, ou modifié à sa version), puis le valide si demandé. Un refus à
 * la validation laisse le brouillon enregistré (`garde` le reçoit) et le dit : une seconde
 * tentative le modifie, sans doublon.
 */
export async function enregistrerOrdre(
  cible: { id: number; version: number } | null,
  corps: CorpsOrdre,
  valider: boolean,
  garde: (fiche: OrdreFiche) => void,
): Promise<OrdreFiche> {
  const fiche = cible
    ? await api.put<OrdreFiche>(`/ordres/${cible.id}`, { ...corps, version: cible.version })
    : await api.post<OrdreFiche>('/ordres', corps)
  garde(fiche)
  if (!valider) return fiche
  try {
    return await api.post<OrdreFiche>(`/ordres/${fiche.id}/valider`, { version: fiche.version })
  } catch (e) {
    throw new ErreurApi(
      `${messageErreur(e)} — l’ordre est gardé en brouillon, modifiable.`,
      e instanceof ErreurApi ? e.statut : 0,
      e instanceof ErreurApi ? e.code : null,
    )
  }
}
