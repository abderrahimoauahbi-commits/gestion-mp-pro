/**
 * Écrans du domaine « Administration » (lot F8), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F8 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/administration',
    titre: 'Administration',
    groupe: 'Pilotage',
    detail: 'Comptes, appareils, sauvegardes, journal des actions, courriel, serveur, téléphone',
    roles: ['direction', 'administrateur'],
    aide: 'administration',
    onglets: [
      { cle: 'comptes', libelle: 'Comptes' },
      { cle: 'appareils', libelle: 'Appareils' },
      { cle: 'sauvegardes', libelle: 'Sauvegardes' },
      { cle: 'journal', libelle: 'Journal des actions', court: 'Journal' },
      { cle: 'courriel', libelle: 'Courriel du lundi', court: 'Courriel' },
      { cle: 'serveur', libelle: 'Serveur' },
      { cle: 'telephone', libelle: 'Téléphone' },
      { cle: 'technique', libelle: 'Technique' },
      { cle: 'reprise', libelle: 'Reprise de Gestion MP', court: 'Reprise' },
    ],
    lot: 'F8',
    page: aVenir,
  },
]
