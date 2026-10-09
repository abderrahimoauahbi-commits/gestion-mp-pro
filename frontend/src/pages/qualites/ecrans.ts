/**
 * Écrans du domaine « Qualités et recettes » (lot F7), rassemblés par `routes.ts`. La fiche d'une
 * qualité s'ouvre en fenêtre par-dessus la liste (même page, adresse stable) ; le chemin fixe
 * `/qualites/nouvelle` passe avant `/qualites/:id`.
 */
import type { Ecran } from '../../routes'

const page = () => import('./Qualites')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/qualites',
    titre: 'Qualités et recettes',
    groupe: 'Référentiels',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'qualites',
    onglets: [
      { cle: 'qualites', libelle: 'Qualités' },
      { cle: 'nomenclature', libelle: 'Nomenclature' },
    ],
    page,
  },
  {
    chemin: '/qualites/nouvelle',
    titre: 'Nouvelle qualité',
    parent: '/qualites',
    roles: ['direction'],
    aide: 'qualite',
    page,
  },
  {
    chemin: '/qualites/:id',
    titre: 'Qualité',
    parent: '/qualites',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'qualite',
    onglets: [
      { cle: 'recette', libelle: 'Recette' },
      { cle: 'plan', libelle: 'Plan de production' },
      { cle: 'versions', libelle: 'Versions' },
      { cle: 'historique', libelle: 'Historique' },
    ],
    page,
  },
]
