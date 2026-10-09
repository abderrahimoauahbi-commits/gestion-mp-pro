/**
 * Écrans du domaine « Commandes » (lot F4), rassemblés par `routes.ts`. Les fiches s'ouvrent en
 * fenêtre par-dessus la liste (même page, adresse stable) ; le chemin fixe passe avant le chemin à
 * paramètre.
 */
import type { Ecran } from '../../routes'

const page = () => import('./Commandes')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/commandes',
    titre: 'Commandes',
    groupe: 'Achats',
    roles: ['direction', 'achats'],
    aide: 'commandes',
    onglets: [
      { cle: 'brouillon', libelle: 'Brouillons' },
      { cle: 'a_approuver', libelle: 'À approuver' },
      { cle: 'envoyee', libelle: 'Envoyées' },
      { cle: 'confirmee', libelle: 'Confirmées' },
      { cle: 'clos', libelle: 'Soldées / annulées' },
    ],
    page,
  },
  {
    chemin: '/commandes/nouvelle',
    titre: 'Nouvelle commande',
    parent: '/commandes',
    roles: ['direction', 'achats'],
    aide: 'nouvelle_commande',
    page,
  },
  {
    chemin: '/commandes/:id',
    titre: 'Bon de commande',
    parent: '/commandes',
    roles: ['direction', 'achats'],
    aide: 'commande',
    onglets: [
      { cle: 'lignes', libelle: 'Lignes et livraison' },
      { cle: 'prix', libelle: 'Prix du fournisseur', court: 'Prix' },
      { cle: 'expedition', libelle: 'Suivi de l’expédition', court: 'Expédition' },
      { cle: 'receptions', libelle: 'Réceptions' },
      { cle: 'approbation', libelle: 'Approbation' },
      { cle: 'pieces', libelle: 'Pièces jointes' },
      { cle: 'historique', libelle: 'Historique' },
    ],
    page,
  },
]
