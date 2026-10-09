/**
 * Écrans du domaine « Cockpit » (lot F1), rassemblés par `routes.ts`. La fenêtre d'un besoin
 * signalé s'ouvre par l'adresse (`/cockpit?signalement=ID`), sur la même page.
 */
import type { Ecran } from '../../routes'

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/cockpit',
    titre: 'Cockpit',
    groupe: 'Tous les jours',
    roles: ['direction'],
    aide: 'cockpit',
    onglets: [
      { cle: 'faire', libelle: 'À faire et à valider' },
      { cle: 'alertes', libelle: 'Matières en alerte' },
      { cle: 'ensemble', libelle: 'Vue d’ensemble' },
      { cle: 'evolution', libelle: 'Évolution' },
      { cle: 'economies', libelle: 'Opportunités d’économies', court: 'Opportunités' },
    ],
    page: () => import('./Cockpit'),
  },
]
