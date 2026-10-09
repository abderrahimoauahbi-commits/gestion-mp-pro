/**
 * Écrans des métiers à tisser (lot F3, ECRANS-PRO partie 3), rassemblés par `routes.ts`. La fiche
 * d'un métier et la création s'ouvrent en fenêtre par-dessus la liste (même page, adresse stable) ;
 * le chemin fixe `/metiers/nouveau` passe avant `/metiers/:id`. La création est ouverte aux trois
 * rôles par l'adresse, pour que la page dise aux achats et à l'alimentation qu'elle est réservée à
 * la direction (an. 15) ; le serveur la refuse de toute façon (403).
 */
import type { Ecran } from '../../routes'

const page = () => import('./Metiers')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/metiers',
    titre: 'Métiers à tisser',
    groupe: 'Référentiels',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'metiers',
    page,
  },
  {
    chemin: '/metiers/nouveau',
    titre: 'Nouveau métier',
    parent: '/metiers',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'metiers',
    page,
  },
  {
    chemin: '/metiers/:id',
    titre: 'Métier',
    parent: '/metiers',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'metiers',
    onglets: [
      { cle: 'fils', libelle: 'Fils montés' },
      { cle: 'reglages', libelle: 'Réglages du métier', court: 'Réglages' },
      { cle: 'historique', libelle: 'Historique' },
    ],
    page,
  },
]
