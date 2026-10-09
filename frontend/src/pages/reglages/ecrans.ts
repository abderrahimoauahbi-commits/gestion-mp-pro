/**
 * Écrans du domaine « Réglages » (lot F8), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F8 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

// Page provisoire du lot F5 (onglets « Postes de frais », « Codes douaniers ») tant que le lot F8 n'a pas livré la sienne.
const aVenir = () => import('../importations/PageReglages')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/reglages',
    titre: 'Réglages',
    groupe: 'Pilotage',
    detail:
      'Paramètres, devises, magasins, postes de frais, codes douaniers, période close (achats : devises en écriture)',
    roles: ['direction', 'achats'],
    aide: 'reglages',
    onglets: [
      { cle: 'parametres', libelle: 'Paramètres' },
      { cle: 'devises', libelle: 'Devises' },
      { cle: 'magasins', libelle: 'Magasins' },
      { cle: 'postes', libelle: 'Postes de frais', court: 'Frais' },
      { cle: 'codes', libelle: 'Codes douaniers', court: 'Douane' },
      { cle: 'periode', libelle: 'Période close', court: 'Période' },
    ],
    lot: 'F8',
    page: aVenir,
  },
]
