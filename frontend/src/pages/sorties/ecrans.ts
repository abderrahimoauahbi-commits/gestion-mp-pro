/**
 * Écrans du domaine « Sorties vers les machines » (lot F2), rassemblés par `routes.ts`. La fiche,
 * la saisie et le retour s'ouvrent en fenêtre par-dessus la liste (même page, adresse stable) ; le
 * chemin fixe `/ordres/nouveau` passe avant `/ordres/:id`.
 */
import type { Ecran } from '../../routes'

const page = () => import('./Sorties')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/sorties',
    titre: 'Sorties vers les machines',
    groupe: 'Tous les jours',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'sorties',
    onglets: [
      { cle: 'valide', libelle: 'Validés' },
      { cle: 'brouillon', libelle: 'Brouillons' },
      { cle: 'annule', libelle: 'Annulés' },
    ],
    page,
  },
  {
    chemin: '/ordres/nouveau',
    titre: 'Nouvelle sortie',
    parent: '/sorties',
    roles: ['direction', 'alimentation'],
    aide: 'sorties',
    page,
  },
  {
    chemin: '/ordres/:id',
    titre: 'Ordre de fabrication',
    parent: '/sorties',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'sorties',
    page,
  },
  {
    chemin: '/ordres/:id/retour',
    titre: 'Retour des machines',
    parent: '/sorties',
    roles: ['direction', 'alimentation'],
    aide: 'sorties',
    page,
  },
]
