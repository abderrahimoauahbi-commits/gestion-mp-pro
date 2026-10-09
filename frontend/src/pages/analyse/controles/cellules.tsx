/**
 * Les cellules du détail d'un contrôle : colonnes nommées et typées par le serveur (`unite` :
 * texte, date, nombre, kg, MAD, j, %), formatées **une seule fois** à la française — un écart
 * relatif arrive en fraction et se lit « 12,4 % » (P8-3) ; la clé d'une colonne ne s'affiche
 * jamais. Une cellule qui nomme une fiche mène à cette fiche, par son id (plus de recherche par
 * texte), si le rôle peut l'ouvrir.
 */
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { date, kg, montant, nombre, part, VIDE } from '../../../lib/format'
import { permis } from '../../../lib/droits'
import type { Role } from '../../../lib/types'
import type { ColonneControle, LigneControle } from '../types'

/** La colonne qui nomme une fiche → l'id que la ligne porte et l'adresse de la fiche. */
const FICHES: Readonly<Record<string, readonly [string, string]>> = {
  reference: ['matiere_id', '/stock/matieres'],
  lot: ['lot_id', '/lots'],
  numero_of: ['ordre_id', '/ordres'],
  ordre: ['ordre_id', '/ordres'],
  metier: ['metier_id', '/metiers'],
  numero: ['commande_id', '/commandes'],
  dossier: ['dossier_id', '/dossiers'],
  reception: ['reception_id', '/receptions'],
  qualite: ['qualite_id', '/qualites'],
  fournisseur: ['fournisseur_id', '/fournisseurs'],
}

/** La fiche qu'une cellule nomme, si le rôle peut l'ouvrir. */
export function lienDeCellule(cle: string, ligne: LigneControle, role: Role): string | null {
  const fiche = FICHES[cle]
  if (!fiche) return null
  const id = ligne[fiche[0]]
  if (typeof id !== 'number') return null
  const adresse = `${fiche[1]}/${id}`
  return permis(role, adresse) ? adresse : null
}

/** Une valeur du détail, dans l'unité de sa colonne. */
export function celluleLisible(valeur: unknown, unite: string): string {
  if (valeur == null || valeur === '') return VIDE
  if (typeof valeur === 'boolean') return valeur ? 'Oui' : 'Non'
  if (Array.isArray(valeur)) return valeur.map((v) => celluleLisible(v, unite)).join(', ')
  if (typeof valeur === 'number') {
    if (unite === '%') return part(valeur)
    if (unite === 'kg') return kg(valeur)
    if (unite === 'MAD') return montant(valeur, 'MAD')
    if (unite === 'j') return `${nombre(valeur)} j`
    return Number.isInteger(valeur) ? nombre(valeur) : nombre(valeur, 2)
  }
  if (typeof valeur === 'string' && /^\d{4}-\d{2}-\d{2}/.test(valeur)) return date(valeur)
  if (typeof valeur === 'object') return JSON.stringify(valeur)
  return String(valeur)
}

/** Les colonnes du tableau d'un contrôle. */
export function colonnesDetail(colonnes: readonly ColonneControle[], role: Role): Colonne<LigneControle>[] {
  return colonnes.map((c) => ({
    cle: c.cle,
    titre: c.libelle,
    droite: ['nombre', 'kg', 'MAD', 'j', '%'].includes(c.unite),
    valeur: (l) => {
      const v = l[c.cle]
      return typeof v === 'number' || typeof v === 'string' || typeof v === 'boolean' ? v : null
    },
    rendu: (l) => celluleLisible(l[c.cle], c.unite),
    lien: (l) => lienDeCellule(c.cle, l, role),
  }))
}
