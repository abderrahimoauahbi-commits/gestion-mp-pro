/**
 * Écrans du domaine « Réglages » (lot F8), rassemblés par `routes.ts` : une page à six onglets
 * (ECRANS-PRO partie 8). « Postes de frais » et « Codes douaniers » sont réalisés par le lot F5 et
 * montés par la page ; les fenêtres ont leur adresse sur la page (`&magasin=`, `&poste=`, `&code=`).
 */
import type { Ecran } from '../../routes'

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
    page: () => import('./Reglages'),
  },
]
