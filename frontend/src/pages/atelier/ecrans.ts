/**
 * Écrans de l'atelier au téléphone (lot F3, ECRANS-PRO partie 3), hors de la coque du bureau,
 * rassemblés par `routes.ts`. Direction et alimentation ; les achats et l'administrateur sont
 * renvoyés à leur accueil avec la raison (`EcranReserve`, an. 2). Le QR `/lot/:id` mène à la fiche
 * du lot de l'atelier pour l'alimentation au téléphone, à celle du bureau sinon (App, lot E2).
 * Chaque entrée est écrite en entier : `scripts/generer_notice.py` lit `chemin` et `aide` ici.
 */
import type { Ecran } from '../../routes'

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/atelier',
    titre: 'Écran atelier (téléphone)',
    groupe: 'Tous les jours',
    detail: 'Envoyer aux machines, retour, trouver un lot, déplacer, monter un fil, signaler un besoin',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    page: () => import('./Accueil'),
  },
  {
    chemin: '/atelier/envoyer',
    titre: 'Envoyer aux machines',
    parent: '/atelier',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    page: () => import('./Envoyer'),
  },
  {
    chemin: '/atelier/ordres',
    titre: 'Ordres',
    parent: '/atelier',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    page: () => import('./Ordres'),
  },
  {
    chemin: '/atelier/ordres/:id',
    titre: 'Ordre',
    parent: '/atelier',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    page: () => import('./Ordre'),
  },
  {
    chemin: '/atelier/retour',
    titre: 'Retour des machines',
    parent: '/atelier',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    page: () => import('./Retour'),
  },
  {
    chemin: '/atelier/chercher',
    titre: 'Trouver un lot',
    parent: '/atelier',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    page: () => import('./Chercher'),
  },
  {
    chemin: '/atelier/lots/:id',
    titre: 'Fiche du lot',
    parent: '/atelier',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    page: () => import('./LotFiche'),
  },
  {
    chemin: '/atelier/deplacer',
    titre: 'Déplacer',
    parent: '/atelier',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    page: () => import('./Deplacer'),
  },
  {
    chemin: '/atelier/montage',
    titre: 'Monter les fils',
    parent: '/atelier',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    page: () => import('./Montage'),
  },
  {
    chemin: '/atelier/signaler',
    titre: 'Signaler un besoin',
    parent: '/atelier',
    roles: ['direction', 'alimentation'],
    aide: 'atelier',
    atelier: true,
    page: () => import('./Signaler'),
  },
]
