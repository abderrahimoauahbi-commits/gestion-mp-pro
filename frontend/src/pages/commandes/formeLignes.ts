/**
 * Le volet « Lignes et livraison » d'un bon, sans écran (ECRANS-PRO 4.8) : la forme saisie (date
 * promise, remarques au fournisseur, lignes en kilos avec leur unité de commande), ce qui manque
 * avant d'enregistrer, et le corps de `PUT /commandes/{id}` — la date absente quand elle n'a pas
 * changé, `null` quand on la vide (recalcul envoi + délai, anom. 4.1).
 */
import { arrondi } from '../../lib/format'
import { unitesDe } from '../plan-achat/calculPreparation'
import type { Matiere, UniteCommande } from '../plan-achat/types'
import type { CommandeFiche, CommandeModification } from './types'

export interface LigneForme {
  matiere_id: number
  unite: string
  contenance: number
  /** En kilos. */
  quantite: number
}

export interface FormeLignes {
  livraison: string
  observations: string
  lignes: LigneForme[]
}

export function versFormeLignes(c: CommandeFiche): FormeLignes {
  return {
    livraison: c.date_livraison_prevue ?? '',
    observations: c.observations,
    lignes: c.lignes.map((l) => ({
      matiere_id: l.matiere_id,
      unite: l.unite_achat || 'kg',
      contenance: l.contenance || 1,
      quantite: l.quantite,
    })),
  }
}

/** Les unités d'une ligne : celles de la fiche matière, plus celle déjà sur le bon (anom. 4.15). */
export function unitesDeLigne(l: LigneForme, m: Matiere | undefined): UniteCommande[] {
  const u = m ? unitesDe(m) : [{ unite: 'kg', contenance: 1 }]
  return u.some((x) => x.unite === l.unite) ? u : [...u, { unite: l.unite, contenance: l.contenance }]
}

/** Une matière ajoutée au bon : une unité entière (la dernière permise), ou son minimum au kilo. */
export function ligneAjoutee(m: Matiere): LigneForme {
  const u = unitesDe(m)
  const choisie = u[u.length - 1] ?? { unite: 'kg', contenance: 1 }
  return {
    matiere_id: m.id,
    unite: choisie.unite,
    contenance: choisie.contenance || 1,
    quantite: choisie.contenance > 1 ? choisie.contenance : Math.max(m.minimum_commande ?? 0, 1),
  }
}

/** Ce qui empêche d'enregistrer (le bouton le dit). */
export function manquesLignes(f: FormeLignes): string[] {
  if (f.lignes.some((l) => !(l.quantite > 0)))
    return ['une quantité à chaque ligne (retirez celles qu’on ne commande plus)']
  return []
}

export function corpsLignes(f: FormeLignes, initiale: FormeLignes, version: number): CommandeModification {
  const corps: CommandeModification = {
    version,
    observations: f.observations.trim(),
    lignes: f.lignes.map((l) => ({
      matiere_id: l.matiere_id,
      quantite: arrondi(l.quantite, 3),
      unite_achat: l.unite,
      contenance: l.contenance || 1,
    })),
  }
  if (f.livraison !== initiale.livraison) corps.date_livraison_prevue = f.livraison || null
  return corps
}
