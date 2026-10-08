/**
 * Unités de saisie : kilos, bobines, palettes (REGLES-ECRAN § 3, ECRANS heritage § 0.4).
 *
 * Le stock est **toujours en kilos** (le cuir, les franges et le ruban compris ; leurs mètres
 * s'affichent à titre indicatif). Une bobine pèse le poids mesuré sur le lot, sinon celui du
 * catalogue ; une palette porte `bobinesPalette` bobines. Le serveur ramène toute saisie aux kilos
 * (API : `unite` = `kg` | `bobine` | `palette`) ; l'écran convertit pour montrer, et **dit
 * l'arrondi** quand une conversion en change la quantité (« arrondi : 7,49 kg au lieu de 7,5 kg »).
 */
import { arrondi, estAffichable, INSECABLE, kgTelephone, nombre } from './format'

export type Unite = 'kg' | 'bobine' | 'palette'

/** Ce qu'il faut savoir d'une matière (ou d'un lot) pour convertir. */
export interface Conditionnement {
  /** Le poids d'une bobine (kg) : celui mesuré sur le lot, sinon celui du catalogue. */
  poidsBobine?: number | null
  /** Le nombre de bobines d'une palette complète. */
  bobinesPalette?: number | null
  /** La densité d'un cuir, de franges, d'un ruban (kg/ml), pour les mètres indicatifs. */
  kgParMl?: number | null
}

const positif = (v: number | null | undefined): v is number => estAffichable(v) && v > 0

/** Les unités qui ont un sens pour cette matière, le kilo en premier. */
export function unitesPossibles(c: Conditionnement): Unite[] {
  if (!positif(c.poidsBobine)) return ['kg']
  return positif(c.bobinesPalette) ? ['kg', 'bobine', 'palette'] : ['kg', 'bobine']
}

/** Ce que vaut une unité, en kilos ; `null` si on ne le sait pas (poids de bobine inconnu). */
export function contenance(c: Conditionnement, unite: Unite): number | null {
  if (unite === 'kg') return 1
  if (!positif(c.poidsBobine)) return null
  if (unite === 'bobine') return c.poidsBobine
  return positif(c.bobinesPalette) ? c.poidsBobine * c.bobinesPalette : null
}

/** « kg », « bobines (2,4952 kg) », « palettes (40 bob.) ». */
export function libelleUnite(c: Conditionnement, unite: Unite): string {
  if (unite === 'bobine') return `bobines (${nombre(c.poidsBobine, 0, 4)}${INSECABLE}kg)`
  if (unite === 'palette') return `palettes (${nombre(c.bobinesPalette, 0, 3)}${INSECABLE}bob.)`
  return 'kg'
}

/** Les kilos d'une quantité saisie dans une unité, au gramme ; `null` si l'unité est inconnue. */
export function versKg(quantite: number, unite: Unite, c: Conditionnement): number | null {
  const k = contenance(c, unite)
  return k == null ? null : arrondi(quantite * k, 3)
}

/** Le pas d'arrondi d'une unité : une bobine se compte entière, une palette au centième, le kilo au gramme. */
export function decimalesDe(unite: Unite): number {
  return unite === 'bobine' ? 0 : unite === 'palette' ? 2 : 3
}

export interface Conversion {
  /** La quantité dans l'unité demandée, arrondie comme on la compte. */
  quantite: number
  /** Les kilos que vaut réellement cette quantité. */
  kg: number
  /** Vrai si l'arrondi a changé les kilos. */
  arrondi: boolean
}

/** La même quantité dans une autre unité, arrondie comme on la compterait ; `null` si impossible. */
export function depuisKg(kilos: number, vers: Unite, c: Conditionnement): Conversion | null {
  const k = contenance(c, vers)
  if (k == null) return null
  const quantite = arrondi(kilos / k, decimalesDe(vers))
  const kg = arrondi(quantite * k, 3)
  return { quantite, kg, arrondi: Math.abs(kg - kilos) >= 0.0005 }
}

/** « arrondi : 7,49 kg au lieu de 7,5 kg », ou rien si la conversion ne change rien de visible. */
export function direArrondi(conversion: Conversion | null, kilosDemandes: number): string {
  if (!conversion || !conversion.arrondi) return ''
  const obtenu = kgTelephone(conversion.kg)
  const demande = kgTelephone(kilosDemandes)
  return obtenu === demande ? '' : `arrondi : ${obtenu} au lieu de ${demande}`
}

/** « 3 bobines = 7,49 kg » ; rien pour une saisie en kilos ou une unité inconnue. */
export function direConversion(quantite: number, unite: Unite, c: Conditionnement): string {
  if (unite === 'kg') return ''
  const kg = versKg(quantite, unite, c)
  return kg == null ? '' : `${quantiteEnUnites(quantite, unite)} = ${kgTelephone(kg)}`
}

/**
 * Tout ce qui reste à rendre, dans l'unité choisie, sans jamais dépasser le net parti : arrondi
 * **vers le bas** (bobine entière, centième de palette, gramme). Arrondir au plus près rendait
 * 581,7 kg pour 581,65 partis, et le serveur refusait le retour (Gestion MP).
 */
export function toutRendre(c: Conditionnement, net: number, unite: Unite): number {
  const k = contenance(c, unite)
  if (k == null || net <= 0) return 0
  const pas = 10 ** decimalesDe(unite)
  // Le millionième absorbe le bruit des flottants (581,65 × 1000 = 581 649,999…).
  return Math.floor((net / k) * pas + 1e-6) / pas
}

/** Le pas des boutons − / + : 0,1 kg sous 10 kg, 1 kg sous 100 kg, puis 10 kg ; une bobine ; une palette. */
export function pasPour(valeur: number, unite: Unite): number {
  if (unite !== 'kg') return 1
  const v = Math.abs(valeur)
  return v < 10 ? 0.1 : v < 100 ? 1 : 10
}

const NOMS: Record<Unite, [string, string]> = {
  kg: ['kg', 'kg'],
  bobine: ['bobine', 'bobines'],
  palette: ['palette', 'palettes'],
}

/**
 * « 3 palettes », « 1,5 bobine », « 2 076 kg » : le nombre sans zéros inutiles (deux décimales au
 * plus), l'unité accordée à la française (pluriel à partir de 2 ; le kilo ne prend pas de s). Une
 * unité de commande libre (« Fût », « Sac ») s'accorde de même.
 */
export function quantiteEnUnites(n: number, unite: Unite | string): string {
  const texte = nombre(n, 0, 2)
  const connu = unite === 'kg' || unite === 'bobine' || unite === 'palette' ? NOMS[unite] : null
  const mot = unite.toLowerCase()
  const [singulier, pluriel] = connu ?? [mot, /[sxz]$|^(ml|m|m²)$/.test(mot) ? mot : `${mot}s`]
  return `${texte}${INSECABLE}${Math.abs(arrondi(n, 2)) >= 2 ? pluriel : singulier}`
}

/** « ≈ 12 bobines » pour des kilos, ou rien sans poids de bobine. */
export function bobinesApprochees(kilos: number | null | undefined, c: Conditionnement): string {
  if (!estAffichable(kilos) || !positif(c.poidsBobine)) return ''
  return `≈${INSECABLE}${quantiteEnUnites(arrondi(kilos / c.poidsBobine, 0), 'bobine')}`
}
