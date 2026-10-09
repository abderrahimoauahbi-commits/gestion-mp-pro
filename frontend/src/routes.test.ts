/**
 * Le registre des écrans contre ECRANS-PRO § 2.1 : le menu de chaque rôle (groupes, entrées, ordre,
 * libellés), chaque entrée permise, chaque écran avec son aide, chaque lien de l'aide vers un écran
 * déclaré.
 */
import { describe, expect, it } from 'vitest'

import { AIDE_ECRANS, liensDeLAide } from './lib/aide'
import { menuDe, permis } from './lib/droits'
import type { Role } from './lib/types'
import { ECRANS, ecranDeAdresse, entreesDuMenu, ORDRE_DU_MENU } from './routes'

/** Le tableau de ECRANS-PRO § 2.1, rôle par rôle (groupe › entrées dans l'ordre). */
const MENUS: Record<Role, Record<string, string[]>> = {
  direction: {
    'Tous les jours': [
      'Cockpit',
      'Stock, lots & mouvements',
      'Sorties vers les machines',
      'Production & besoins',
      'Écran atelier (téléphone)',
    ],
    Achats: ['Plan d’achat', 'Commandes', 'Réceptions', 'Importations & coût de revient'],
    Stock: ['Inventaire', 'Ouvertures, transferts, ajustements'],
    Référentiels: ['Matières, classification, fournisseurs', 'Qualités et recettes', 'Métiers à tisser'],
    Pilotage: ['Analyse', 'Réglages', 'Administration'],
    Aide: ['Mode d’emploi'],
  },
  achats: {
    'Tous les jours': [
      'Ma journée',
      'Stock, lots & mouvements',
      'Sorties vers les machines',
      'Production & besoins',
    ],
    Achats: ['Plan d’achat', 'Commandes', 'Réceptions', 'Importations & coût de revient'],
    Stock: ['Inventaire', 'Ouvertures, transferts, ajustements'],
    Référentiels: ['Matières, classification, fournisseurs', 'Qualités et recettes', 'Métiers à tisser'],
    Pilotage: ['Analyse', 'Réglages'],
    Aide: ['Mode d’emploi'],
  },
  alimentation: {
    'Tous les jours': [
      'Ma journée',
      'Stock, lots & mouvements',
      'Sorties vers les machines',
      'Production & besoins',
      'Écran atelier (téléphone)',
    ],
    Stock: ['Ouvertures, transferts, ajustements'],
    Référentiels: ['Matières, classification, fournisseurs', 'Qualités et recettes', 'Métiers à tisser'],
    Aide: ['Mode d’emploi'],
  },
  administrateur: {
    Pilotage: ['Administration'],
    Aide: ['Mode d’emploi'],
  },
}

const ROLES: Role[] = ['direction', 'achats', 'alimentation', 'administrateur']

describe('Registre des écrans (routes.ts)', () => {
  it.each(ROLES)('le menu de « %s » est celui du tableau de ECRANS-PRO § 2.1', (role) => {
    const menu = Object.fromEntries(menuDe(role).map((g) => [g.groupe, g.entrees.map((e) => e.titre)]))
    expect(menu).toEqual(MENUS[role])
  })

  it.each(ROLES)('chaque entrée du menu de « %s » lui est permise, et lui seul voit les siennes', (role) => {
    for (const g of menuDe(role)) for (const e of g.entrees) expect(permis(role, e.chemin)).toBe(true)
    const vues = new Set(menuDe(role).flatMap((g) => g.entrees.map((e) => e.chemin)))
    for (const e of entreesDuMenu()) if (!vues.has(e.chemin)) expect(permis(role, e.chemin)).toBe(false)
  })

  it('la direction n’a pas Ma journée ; l’administrateur n’ouvre aucun écran métier', () => {
    expect(permis('direction', '/accueil')).toBe(false)
    const metier = ECRANS.filter((e) => !['/administration', '/aide', '/compte'].includes(e.chemin))
    for (const e of metier) expect(e.roles).not.toContain('administrateur')
  })

  it('chaque écran a son aide ; le titre de l’aide d’une entrée de menu est celui de l’écran', () => {
    for (const e of ECRANS) expect(AIDE_ECRANS[e.aide], e.chemin).toBeDefined()
    for (const e of entreesDuMenu()) expect(AIDE_ECRANS[e.aide]?.titre).toBe(e.titre)
  })

  it('l’ordre du menu et les entrées déclarées se répondent ; les chemins sont uniques', () => {
    expect(entreesDuMenu().map((e) => e.chemin)).toEqual(ORDRE_DU_MENU)
    const chemins = ECRANS.map((e) => e.chemin)
    expect(new Set(chemins).size).toBe(chemins.length)
    for (const e of ECRANS) if (e.parent) expect(ECRANS.some((p) => p.chemin === e.parent)).toBe(true)
  })

  it('chaque lien de l’aide vise un écran déclaré', () => {
    const liens = liensDeLAide()
    expect(liens.length).toBeGreaterThan(5)
    for (const l of liens) expect(ecranDeAdresse(l), l).toBeDefined()
  })

  it('une adresse trouve son écran, le chemin fixe avant le chemin à paramètre', () => {
    expect(ecranDeAdresse('/commandes/nouvelle?fournisseur=3')?.titre).toBe('Nouvelle commande')
    expect(ecranDeAdresse('/lots/884')?.chemin).toBe('/lots/:id')
    expect(ecranDeAdresse('/stock?onglet=lots')?.chemin).toBe('/stock')
    expect(ecranDeAdresse('/nulle-part')).toBeUndefined()
  })

  it('le menu de la direction a 18 entrées en 6 groupes', () => {
    expect(menuDe('direction').flatMap((g) => g.entrees)).toHaveLength(18)
  })
})
