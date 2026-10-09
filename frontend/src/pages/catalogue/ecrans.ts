/**
 * Écrans du domaine « Matières, classification, fournisseurs » (lot F7), rassemblés par
 * `routes.ts`. Les fiches s'ouvrent en fenêtre par-dessus la liste (même page, adresse stable) ;
 * les chemins fixes passent avant les chemins à paramètre.
 */
import type { Ecran } from '../../routes'

const page = () => import('./Catalogue')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/catalogue',
    titre: 'Matières, classification, fournisseurs',
    groupe: 'Référentiels',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'catalogue',
    onglets: [
      { cle: 'matieres', libelle: 'Matières' },
      { cle: 'classification', libelle: 'Classification', roles: ['direction', 'achats'] },
      { cle: 'fournisseurs', libelle: 'Fournisseurs', roles: ['direction', 'achats'] },
    ],
    page,
  },
  {
    chemin: '/catalogue/tableur',
    titre: 'Le catalogue par tableur',
    parent: '/catalogue',
    roles: ['direction', 'achats'],
    aide: 'tableur_matieres',
    page,
  },
  {
    chemin: '/matieres/nouvelle',
    titre: 'Nouvelle matière',
    parent: '/catalogue',
    roles: ['direction', 'achats'],
    aide: 'matiere',
    page,
  },
  {
    chemin: '/matieres/:id',
    titre: 'Fiche matière',
    parent: '/catalogue',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'matiere',
    page,
  },
  {
    chemin: '/fournisseurs/nouveau',
    titre: 'Nouveau fournisseur',
    parent: '/catalogue',
    roles: ['direction', 'achats'],
    aide: 'fournisseur',
    page,
  },
  {
    chemin: '/fournisseurs/:id',
    titre: 'Fiche fournisseur',
    parent: '/catalogue',
    roles: ['direction', 'achats'],
    aide: 'fournisseur',
    page,
  },
]
