/** Des données d'exemple pour la démonstration (inventées, à la forme de celles de l'usine). */
import { ajouterJours, aujourdhui } from '../../lib/heure'

export interface LotExemple {
  id: number
  numero: string
  matiere: string
  fournisseur: string
  couleur: string
  magasin: string
  reste: number
  unite: 'kg' | 'ml'
  entree: string
  statut: 'disponible' | 'partiel' | 'quarantaine' | 'epuise'
  code: string
}

const MATIERES = [
  ['IMP FRISÉ ROUGE 2900', 'HASIRCI', 'Rouge', 'kg', 'C5N'],
  ['IMP FRISÉ BEIGE 2900', 'HASIRCI', 'Beige', 'kg', 'B12'],
  ['PP HEAT-SET Bleu marine 1500', 'BELKA', 'Bleu marine', 'kg', 'N07'],
  ['PES Vison 1500', 'BELKA', 'Vison', 'kg', 'V22'],
  ['Coton écru 8/2', 'FILATURE DU NORD', 'Écru', 'kg', 'CO8'],
  ['Jute naturel', 'JUTE BENGAL', 'Naturel', 'kg', 'JT1'],
  ['Cuir camel 3 cm', 'TANNERIE FÈS', 'Camel', 'ml', 'CU3'],
  ['Franges coton blanc', 'FRANGES ATLAS', 'Blanc', 'ml', 'FR1'],
] as const

const MAGASINS = ['Principal', 'Annexe', 'Quarantaine']
const STATUTS: LotExemple['statut'][] = [
  'disponible',
  'disponible',
  'disponible',
  'partiel',
  'quarantaine',
  'epuise',
]

/** 300 lots : assez pour que le tableau défile dans son cadre. */
export const LOTS: LotExemple[] = Array.from({ length: 300 }, (_, i) => {
  const [matiere, fournisseur, couleur, unite, code] = MATIERES[i % MATIERES.length] ?? MATIERES[0]
  const statut = STATUTS[(i * 7) % STATUTS.length] ?? 'disponible'
  return {
    id: i + 1,
    numero: `LOT-2026-${String(i + 1).padStart(4, '0')}`,
    matiere,
    fournisseur,
    couleur,
    magasin: statut === 'quarantaine' ? 'Quarantaine' : (MAGASINS[i % 2] ?? 'Principal'),
    reste: statut === 'epuise' ? 0 : Math.round(((i * 137) % 900) * 10 + 15) / 10,
    unite,
    entree: ajouterJours(aujourdhui(), -((i * 3) % 240)),
    statut,
    code,
  }
})

export const MOIS = [
  'nov.',
  'déc.',
  'janv.',
  'févr.',
  'mars',
  'avr.',
  'mai',
  'juin',
  'juil.',
  'août',
  'sept.',
  'oct.',
]

export const MATIERES_CHOIX = MATIERES.map(([reference, fournisseur, couleur, , code], i) => ({
  id: i + 1,
  reference,
  fournisseur,
  couleur,
  composition: reference.split(' ')[0] ?? '',
  type: reference.includes('FRISÉ') ? 'Frisé' : reference.includes('HEAT') ? 'Heat-set' : 'Autre',
  titrage: reference.match(/\d{4}/)?.[0] ?? null,
  recherche: code,
}))
