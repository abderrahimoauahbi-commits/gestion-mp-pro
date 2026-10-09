/**
 * Écrans du domaine « Stock, lots & mouvements » (lot F2), rassemblés par `routes.ts`. Les fiches
 * s'ouvrent en fenêtre par-dessus la liste (même page, adresse stable, A5) : `/stock/matieres/:id`,
 * `/lots/:id`, `/tracabilite?lot=|ordre=|matiere=`.
 */
import type { Ecran } from '../../routes'

const page = () => import('./Stock')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/stock',
    titre: 'Stock, lots & mouvements',
    groupe: 'Tous les jours',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'stock',
    onglets: [
      { cle: 'matieres', libelle: 'Par matière' },
      { cle: 'lots', libelle: 'Lots' },
      { cle: 'mouvements', libelle: 'Mouvements de stock' },
      { cle: 'ordres', libelle: 'Ordres de fabrication' },
      { cle: 'a-valider', libelle: 'À valider' },
    ],
    page,
  },
  {
    chemin: '/stock/matieres/:id',
    titre: 'Fiche matière',
    parent: '/stock',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'stock',
    page,
  },
  {
    chemin: '/lots/:id',
    titre: 'Fiche de lot',
    parent: '/stock',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'lot',
    page,
  },
  {
    chemin: '/tracabilite',
    titre: 'Suivi de traçabilité',
    parent: '/stock',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'tracabilite',
    page,
  },
]
