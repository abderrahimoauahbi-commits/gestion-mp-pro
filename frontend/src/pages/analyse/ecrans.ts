/**
 * Écrans du domaine « Analyse » (lot F8), rassemblés par `routes.ts` : une page à neuf onglets
 * (ECRANS-PRO partie 8). Les fenêtres ont leur adresse sur la page (`&fournisseur=ID`,
 * `&controle=Cxx`, `&ordre=ID`) ; le « Coût de revient » est un onglet réalisé par le lot F5.
 */
import type { Ecran } from '../../routes'

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/analyse',
    titre: 'Analyse',
    groupe: 'Pilotage',
    detail: 'Prix, fournisseurs, valorisation, coût de revient, contrôles',
    roles: ['direction', 'achats'],
    aide: 'analyse',
    onglets: [
      { cle: 'valorisation', libelle: 'Valorisation', court: 'Valeur' },
      { cle: 'matrice', libelle: 'Matrice' },
      { cle: 'historique', libelle: 'Prix payés' },
      { cle: 'opportunites', libelle: 'Opportunités d’économies', court: 'Opportunités' },
      { cle: 'fournisseurs', libelle: 'Fournisseurs' },
      { cle: 'revient', libelle: 'Coût de revient' },
      { cle: 'echeancier', libelle: 'Échéancier' },
      { cle: 'controles', libelle: 'Contrôles' },
      { cle: 'production', libelle: 'Production' },
    ],
    page: () => import('./Analyse'),
  },
]
