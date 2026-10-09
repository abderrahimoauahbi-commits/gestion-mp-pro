/**
 * Écrans du domaine « Atelier au téléphone » (lot F3), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F3 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/atelier',
    titre: 'Écran atelier (téléphone)',
    groupe: 'Tous les jours',
    detail: 'Envoyer aux machines, retour, trouver un lot, déplacer, monter un fil, signaler un besoin',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    lot: 'F3',
    page: aVenir,
  },
  {
    chemin: '/atelier/lots/:id',
    titre: 'Fiche du lot',
    parent: '/atelier',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    lot: 'F3',
    page: aVenir,
  },
]
