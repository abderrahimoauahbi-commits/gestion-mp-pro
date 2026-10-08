/**
 * Écrans du domaine « Commandes » (lot F4), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F4 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/commandes',
    titre: 'Commandes',
    groupe: 'Achats',
    roles: ['direction', 'achats'],
    aide: 'commandes',
    onglets: [
      { cle: 'brouillon', libelle: 'Brouillons' },
      { cle: 'a_approuver', libelle: 'À approuver' },
      { cle: 'envoyee', libelle: 'Envoyées' },
      { cle: 'confirmee', libelle: 'Confirmées' },
      { cle: 'clos', libelle: 'Soldées / annulées' },
    ],
    lot: 'F4',
    page: aVenir,
  },
  {
    chemin: '/commandes/nouvelle',
    titre: 'Nouvelle commande',
    parent: '/commandes',
    roles: ['direction', 'achats'],
    aide: 'commandes',
    lot: 'F4',
    page: aVenir,
  },
]
