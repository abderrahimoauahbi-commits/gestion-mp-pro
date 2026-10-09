/**
 * Les règles d'un compte, sans écran, dites **avant** le clic avec les mots du serveur (lot S2,
 * `services/comptes.py` et `services/utilisateurs.py`) : l'alimentation a un code d'exactement
 * 4 chiffres, les achats et la direction 8 caractères au moins, l'administrateur technique 12 ;
 * un changement de rôle qui ne convient plus au code gardé en exige un nouveau (F-01).
 */
import type { Role } from '../../lib/types'

export const ROLES: readonly { cle: Role; libelle: string; aide: string }[] = [
  {
    cle: 'direction',
    libelle: 'Direction',
    aide: 'voit et peut tout : approbations, réglages, comptes, sauvegardes',
  },
  {
    cle: 'achats',
    libelle: 'Responsable achats',
    aide: 'commandes, réceptions, inventaire, importations, matières',
  },
  {
    cle: 'alimentation',
    libelle: 'Responsable alimentation machines',
    aide: 'sorties vers les métiers, au téléphone ; aucun prix',
  },
  {
    cle: 'administrateur',
    libelle: 'Administrateur technique',
    aide: 'comptes, appareils, sauvegardes, journal, serveur : aucune donnée métier',
  },
]

export const LONGUEUR_MINI: Readonly<Record<Role, number>> = {
  alimentation: 4,
  achats: 8,
  direction: 8,
  administrateur: 12,
}

/** La consigne du code d'un rôle. */
export function consigne(role: Role): string {
  return role === 'alimentation'
    ? '4 chiffres exactement (tapés au téléphone)'
    : `${LONGUEUR_MINI[role]} caractères au moins`
}

/** Pourquoi ce code ne convient pas à ce rôle (`''` s'il convient) — phrase du serveur. */
export function defautDuCode(role: Role, code: string): string {
  if (role === 'alimentation')
    return /^[0-9]{4}$/.test(code) ? '' : 'Le code de l’atelier est fait de 4 chiffres.'
  const mini = LONGUEUR_MINI[role]
  return code.length < mini ? `Le code doit faire au moins ${mini} caractères.` : ''
}

/** Le code gardé ne convient plus au nouveau rôle : vers l'alimentation, depuis elle, ou plus long. */
export function exigeNouveauCode(ancien: Role | null, nouveau: Role): boolean {
  if (ancien === nouveau) return false
  if (ancien === 'alimentation' || nouveau === 'alimentation') return true
  return LONGUEUR_MINI[nouveau] > (ancien ? LONGUEUR_MINI[ancien] : 0)
}

export interface FormeCompte {
  nom: string
  identifiant: string
  role: Role
  email: string
  code: string
  code2: string
}

/** Ce qui manque ou ne va pas avant d'enregistrer (raisons du bouton). */
export function manquesCompte(f: FormeCompte, nouveau: boolean, ancien: Role | null): string[] {
  const codeRequis = nouveau || exigeNouveauCode(ancien, f.role)
  const raisons: string[] = []
  if (f.nom.trim().length < 2) raisons.push('Le nom affiché fait au moins 2 caractères')
  if (nouveau && f.identifiant.trim().length < 2) raisons.push('L’identifiant fait au moins 2 caractères')
  if (codeRequis && !f.code) {
    raisons.push(
      nouveau
        ? `Le code : ${consigne(f.role)}`
        : `Nouveau rôle : un nouveau code est nécessaire, ${consigne(f.role)}`,
    )
  }
  if (f.code) {
    const d = defautDuCode(f.role, f.code)
    if (d) raisons.push(d)
    if (f.code !== f.code2) raisons.push('Les deux codes diffèrent')
  }
  return raisons
}
