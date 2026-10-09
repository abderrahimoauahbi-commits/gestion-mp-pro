/**
 * Écrans du domaine « Analyse » (lot F8), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F8 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/analyse',
    titre: 'Analyse',
    groupe: 'Pilotage',
    detail: 'Prix, fournisseurs, valorisation, coût de revient, contrôles',
    roles: ['direction', 'achats'],
    aide: 'analyse',
    onglets: [
      { cle: 'valorisation', libelle: 'Valorisation' },
      { cle: 'matrice', libelle: 'Matrice' },
      { cle: 'historique', libelle: 'Prix payés' },
      { cle: 'opportunites', libelle: 'Opportunités d’économies', court: 'Opportunités' },
      { cle: 'fournisseurs', libelle: 'Fournisseurs' },
      { cle: 'revient', libelle: 'Coût de revient' },
      { cle: 'echeancier', libelle: 'Échéancier' },
      { cle: 'controles', libelle: 'Contrôles' },
      { cle: 'production', libelle: 'Production' },
    ],
    lot: 'F8',
    page: aVenir,
  },
]
