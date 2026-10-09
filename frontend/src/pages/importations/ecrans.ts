/**
 * Écrans du domaine « Importations & coût de revient » (lot F5), rassemblés par `routes.ts` : la
 * page à trois onglets (`?onglet=ouverts|clos|rattacher`), le nouveau dossier
 * (`/dossiers/nouveau?onglet=facture|main`) et la fiche d'un dossier
 * (`/dossiers/:id?onglet=familles|marchandises|frais|echeancier|pieces|facture|main|historique`),
 * en fenêtres à adresse stable par-dessus la liste : les trois chemins mènent à la même page.
 * Direction et achats seulement (ECRANS-PRO partie 5).
 *
 * Le « Coût de revient » (`/analyse?onglet=revient`), les « Postes de frais » et les « Codes
 * douaniers » (`/reglages?onglet=postes|codes`) sont des onglets des pages du lot F8 : leurs
 * contenus sont ici (`revient/`, `reglages/`), montés par `PageAnalyse` et `PageReglages`.
 */
import type { Ecran } from '../../routes'

const page = () => import('./Importations')
const roles = ['direction', 'achats'] as const

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/importations',
    titre: 'Importations & coût de revient',
    groupe: 'Achats',
    roles,
    aide: 'importations',
    onglets: [
      { cle: 'ouverts', libelle: 'Dossiers ouverts' },
      { cle: 'clos', libelle: 'Dossiers clos' },
      { cle: 'rattacher', libelle: 'En attente de dossier' },
    ],
    page,
  },
  {
    chemin: '/dossiers/nouveau',
    titre: 'Nouveau dossier d’importation',
    parent: '/importations',
    roles,
    aide: 'importations',
    page,
  },
  {
    chemin: '/dossiers/:id',
    titre: 'Dossier d’importation',
    parent: '/importations',
    roles,
    aide: 'importations',
    page,
  },
]
