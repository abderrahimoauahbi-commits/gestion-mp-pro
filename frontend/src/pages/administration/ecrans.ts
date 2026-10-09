/**
 * Écrans du domaine « Administration » (lot F8), rassemblés par `routes.ts` : une page à onglets
 * (ECRANS-PRO partie 8), pour la direction et l'administrateur technique ; « Données brutes »
 * (route 7) pour la direction seule. Les fenêtres ont leur adresse sur la page (`&compte=ID`).
 */
import type { Ecran } from '../../routes'

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
      { cle: 'donnees', libelle: 'Données brutes', court: 'Données', roles: ['direction'] },
    ],
    page: () => import('./Administration'),
  },
]
