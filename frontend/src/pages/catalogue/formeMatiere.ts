/**
 * La saisie d'une fiche matière, sans écran : la forme tenue par la fenêtre, d'où elle part
 * (fiche lue ou défauts d'une création), le corps envoyé au serveur (la fiche entière, API-PRO
 * § 1.24), et ce qui manque pour enregistrer — dit avant le clic, avec l'onglet où le corriger
 * (R6). Les règles sont celles du serveur (`services/matieres.py`) ; il les revérifie.
 *
 * La « priorité dans le groupe » n'est plus saisie : le calcul ne la lit pas (Gestion MP corrigé,
 * A-26, H-28) ; la fiche la renvoie telle qu'elle est.
 */
import { messageNombre } from '../../composants/saisie/Nombre'
import { nombre } from '../../lib/format'
import { BORNES_MATIERE, type ChampBorne } from './bornes'
import type { Classification, MatiereCorps, MatiereFiche } from './types'

export type Volet = 'classification' | 'achat' | 'conditionnement' | 'pieces' | 'historique'

export interface FormeMatiere {
  reference: string
  designation: string
  role_id: number | null
  composition_id: number | null
  type_fil_id: number | null
  titrage_id: number | null
  couleur_id: number | null
  couleur_code: string
  /** La marque de fin du fournisseur (« Hs ») : sert à composer la référence, n'est pas gardée. */
  suffixe: string
  densite: number | null
  fournisseur_id: number | null
  prix: number | null
  unite_prix: 'kg' | 'ml'
  devise: string
  /** Vide : l'unité d'achat se déduit (palette, bobine ou kilo). */
  unite_achat: string
  contenance_achat: number | null
  minimum_commande: number | null
  poids_bobine: number | null
  bobines_palette: number | null
  stock_min: number | null
  couv_min_mois: number | null
  groupe_equiv: string
  code_douanier_id: number | null
  actif: boolean
}

/** Les unités d'achat proposées (liste fermée, sans « ml » : la commande se compte en kilos, P7-20). */
export const UNITES_ACHAT = ['Fût', 'Sac', 'Big-bag', 'Palette', 'Bobine', 'Carton', 'Rouleau'] as const

/** Les défauts d'une création, repris des filtres posés sur la liste. */
export interface DefautsCreation {
  role_id?: number | null
  composition_id?: number | null
  type_fil_id?: number | null
  titrage_id?: number | null
  couleur_id?: number | null
  fournisseur_id?: number | null
  devise?: string | null
}

const nul = (v: number | null | undefined) => (v ? v : null)

/** La forme d'une fiche lue, ou d'une création (1er rôle, MAD, prix au kilo, en service). */
export function versForme(
  m: MatiereFiche | null,
  c: Classification,
  defauts: DefautsCreation = {},
): FormeMatiere {
  const declaree = m && m.unite_achat !== 'kg' ? m.unite_achat : ''
  return {
    reference: m?.reference ?? '',
    designation: m?.designation ?? '',
    role_id: m?.role_id ?? defauts.role_id ?? c.roles[0]?.id ?? null,
    composition_id: m ? m.composition_id : (defauts.composition_id ?? null),
    type_fil_id: m ? m.type_fil_id : (defauts.type_fil_id ?? null),
    titrage_id: m ? m.titrage_id : (defauts.titrage_id ?? null),
    couleur_id: m ? m.couleur_id : (defauts.couleur_id ?? null),
    couleur_code: m?.couleur_code ?? '',
    suffixe: '',
    densite: nul(m?.densite),
    fournisseur_id: m ? m.fournisseur_id : (defauts.fournisseur_id ?? null),
    prix: nul(m?.prix),
    unite_prix: m?.unite_prix === 'ml' ? 'ml' : 'kg',
    devise: m?.devise ?? defauts.devise ?? 'MAD',
    unite_achat: declaree,
    contenance_achat: declaree ? nul(m?.contenance_achat) : null,
    minimum_commande: nul(m?.minimum_commande),
    poids_bobine: nul(m?.poids_bobine),
    bobines_palette: nul(m?.bobines_palette),
    stock_min: nul(m?.stock_min),
    couv_min_mois: nul(m?.couv_min_mois),
    groupe_equiv: m?.groupe_equiv ?? '',
    code_douanier_id: m?.code_douanier_id ?? null,
    actif: m?.actif ?? true,
  }
}

/** La modification d'une valeur de classification de la forme (`composition_id`…). */
export function avecClasse(
  champ: 'composition_id' | 'type_fil_id' | 'titrage_id' | 'couleur_id',
  id: number | null,
): Partial<FormeMatiere> {
  const modif: Partial<FormeMatiere> = {}
  modif[champ] = id
  return modif
}

/** Le corps de `POST /matieres` ou `PUT /matieres/{id}` : la fiche entière. */
export function versCorps(f: FormeMatiere, fiche: MatiereFiche | null): Omit<MatiereCorps, 'version'> {
  const unite = f.unite_achat.trim()
  return {
    reference: f.reference.trim(),
    designation: f.designation.trim(),
    role_id: f.role_id ?? 0,
    composition_id: f.composition_id,
    type_fil_id: f.type_fil_id,
    titrage_id: f.titrage_id,
    couleur_id: f.couleur_id,
    couleur_code: f.couleur_code.trim(),
    unite_prix: f.unite_prix,
    densite: f.densite ?? 0,
    fournisseur_id: f.fournisseur_id,
    prix: f.prix ?? 0,
    devise: f.devise,
    unite_achat: unite || 'kg',
    contenance_achat: unite ? (f.contenance_achat ?? 0) : 1,
    minimum_commande: f.minimum_commande ?? 0,
    poids_bobine: f.poids_bobine ?? 0,
    bobines_palette: f.bobines_palette ?? 0,
    stock_min: f.stock_min ?? 0,
    couv_min_mois: f.couv_min_mois ?? 0,
    groupe_equiv: f.groupe_equiv.trim(),
    priorite_equiv: f.groupe_equiv.trim() ? (fiche?.priorite_equiv ?? null) : null,
    code_douanier_id: f.code_douanier_id,
    actif: f.actif,
  }
}

/** Deux formes disent-elles la même fiche (le suffixe n'est pas gardé) ? */
export function memeFiche(a: FormeMatiere, b: FormeMatiere): boolean {
  return JSON.stringify({ ...a, suffixe: '' }) === JSON.stringify({ ...b, suffixe: '' })
}

/** L'unité d'achat que le plan d'achat retiendra sans déclaration (règle du serveur). */
export function uniteDeduite(f: Pick<FormeMatiere, 'poids_bobine' | 'bobines_palette'>) {
  const bobine = f.poids_bobine ?? 0
  const palette = f.bobines_palette ?? 0
  if (bobine && palette) return { unite: 'Palette', contenance: bobine * palette }
  if (bobine) return { unite: 'Bobine', contenance: bobine }
  return { unite: 'kg', contenance: 1 }
}

export interface Manque {
  quoi: string
  volet: Volet
}

const NOMS_VOLETS: Record<Volet, string> = {
  classification: 'Classification et référence',
  achat: 'Achat',
  conditionnement: 'Conditionnement et stock',
  pieces: 'Pièces jointes',
  historique: 'Historique',
}

export const nomVolet = (v: Volet) => NOMS_VOLETS[v]

const BORNES_DITES: { cle: ChampBorne; nom: string; unite: string; volet: Volet }[] = [
  { cle: 'prix', nom: 'le prix', unite: '', volet: 'achat' },
  { cle: 'contenance_achat', nom: 'la contenance', unite: 'kg', volet: 'achat' },
  { cle: 'minimum_commande', nom: 'le minimum de commande', unite: 'kg', volet: 'achat' },
  { cle: 'poids_bobine', nom: 'le poids d’une bobine', unite: 'kg', volet: 'conditionnement' },
  { cle: 'bobines_palette', nom: 'les bobines par palette', unite: '', volet: 'conditionnement' },
  { cle: 'stock_min', nom: 'le stock minimum', unite: 'kg', volet: 'conditionnement' },
  { cle: 'couv_min_mois', nom: 'la couverture minimum', unite: 'mois', volet: 'conditionnement' },
]

/** Ce qui manque pour enregistrer (vide : la fiche peut partir), avec l'onglet où le corriger. */
export function manques(f: FormeMatiere, c: Classification, voitAchat = true): Manque[] {
  const role = c.roles.find((r) => r.id === f.role_id)
  const m: Manque[] = []
  if (f.reference.trim().length < 2) m.push({ quoi: 'la référence', volet: 'classification' })
  if (!role) m.push({ quoi: 'le rôle', volet: 'classification' })
  const densiteRequise = Boolean(role?.lineaire) || f.unite_prix === 'ml'
  const voletDensite: Volet = role?.lineaire ? 'classification' : 'achat'
  if (densiteRequise && !f.densite) m.push({ quoi: 'la densité (kg par mètre)', volet: voletDensite })
  if (messageNombre(f.densite, { min: 0, max: BORNES_MATIERE.densite[1] }))
    m.push({
      quoi: `la densité entre 0 et ${nombre(BORNES_MATIERE.densite[1])} kg / ml`,
      volet: voletDensite,
    })
  if (!voitAchat) return m
  if (f.actif && !f.fournisseur_id) m.push({ quoi: 'le fournisseur', volet: 'achat' })
  if (f.unite_achat.trim() && !f.contenance_achat)
    m.push({ quoi: `la contenance d’une unité d’achat (${f.unite_achat.trim()})`, volet: 'achat' })
  for (const b of BORNES_DITES) {
    const [bas, haut] = BORNES_MATIERE[b.cle]
    if (messageNombre(f[b.cle], { min: bas, max: haut }))
      m.push({ quoi: `${b.nom} entre 0 et ${nombre(haut)}${b.unite ? ` ${b.unite}` : ''}`, volet: b.volet })
  }
  return m
}

/** « la référence (onglet Classification et référence) » : ce qui manque, dit avec son onglet. */
export function manqueLisible(m: readonly Manque[]): string[] {
  return m.map((x) => `${x.quoi} (onglet ${nomVolet(x.volet)})`)
}
