/**
 * Écrans du domaine « Inventaire » (lot F6), rassemblés par `routes.ts` : la liste et ses deux
 * fenêtres à adresse stable, `/inventaires/nouveau` (ouvrir) et `/inventaires/:id` (comptage,
 * volets `?onglet=lots|pieces`). Les trois chemins mènent à la même page (la liste dessous).
 */
import type { Ecran } from '../../routes'

const page = () => import('./Inventaire')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/inventaire',
    titre: 'Inventaire',
    groupe: 'Stock',
    roles: ['direction', 'achats'],
    aide: 'inventaire',
    onglets: [
      { cle: 'cours', libelle: 'En cours de comptage' },
      {
        cle: 'passes',
        libelle: 'Inventaires clos : validés, abandonnés et annulés',
        court: 'Inventaires clos',
      },
    ],
    page,
  },
  {
    chemin: '/inventaires/nouveau',
    titre: 'Ouvrir un inventaire',
    parent: '/inventaire',
    roles: ['direction', 'achats'],
    aide: 'inventaire',
    page,
  },
  {
    chemin: '/inventaires/:id',
    titre: 'Comptage d’un inventaire',
    parent: '/inventaire',
    roles: ['direction', 'achats'],
    aide: 'inventaire',
    onglets: [
      { cle: 'lots', libelle: 'Lots à compter' },
      { cle: 'pieces', libelle: 'Pièces jointes' },
    ],
    page,
  },
]
