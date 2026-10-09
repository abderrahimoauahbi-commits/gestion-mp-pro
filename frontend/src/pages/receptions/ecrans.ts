/**
 * Écrans du domaine « Réceptions » (lot F4), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F4 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/receptions',
    titre: 'Réceptions',
    groupe: 'Achats',
    roles: ['direction', 'achats'],
    aide: 'receptions',
    onglets: [
      { cle: 'brouillon', libelle: 'Brouillons' },
      { cle: 'validee', libelle: 'Validées' },
      { cle: 'annulee', libelle: 'Annulées' },
      { cle: 'reclamations', libelle: 'Réclamations' },
      { cle: 'bobines', libelle: 'Poids des bobines', court: 'Bobines' },
      { cle: 'pesees', libelle: 'Archive des pesées', court: 'Pesées' },
    ],
    lot: 'F4',
    page: aVenir,
  },
  {
    chemin: '/receptions/nouvelle',
    titre: 'Nouvelle réception',
    parent: '/receptions',
    roles: ['direction', 'achats'],
    aide: 'receptions',
    lot: 'F4',
    page: aVenir,
  },
]
