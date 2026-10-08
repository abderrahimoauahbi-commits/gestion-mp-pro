/** L'écran « Mode d'emploi » (lot E2), rassemblé par `routes.ts`. */
import type { Ecran } from '../../routes'

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/aide',
    titre: 'Mode d’emploi',
    groupe: 'Aide',
    roles: ['direction', 'achats', 'alimentation', 'administrateur'],
    aide: 'aide',
    onglets: [
      { cle: 'regles', libelle: 'Les règles' },
      { cle: 'roles', libelle: 'Qui fait quoi' },
      { cle: 'pas', libelle: 'Pas à pas' },
      { cle: 'calculs', libelle: 'Les calculs' },
      { cle: 'analyse', libelle: 'L’analyse' },
      { cle: 'ecrans', libelle: 'Les écrans de l’ERP Fil', court: 'Écrans de l’ERP Fil' },
      { cle: 'telephone', libelle: 'Le téléphone' },
    ],
    page: () => import('./ModeEmploi'),
  },
]
