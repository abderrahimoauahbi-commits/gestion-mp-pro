/**
 * Écrans du domaine « Réceptions » (lot F4), rassemblés par `routes.ts`. Les fiches (réception,
 * réclamation) et la saisie s'ouvrent en fenêtre par-dessus la liste (même page, adresse stable) ;
 * les chemins fixes passent avant les chemins à paramètre.
 */
import type { Ecran } from '../../routes'

const page = () => import('./Receptions')
const roles = ['direction', 'achats'] as const

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/receptions',
    titre: 'Réceptions',
    groupe: 'Achats',
    roles,
    aide: 'receptions',
    onglets: [
      { cle: 'brouillon', libelle: 'Brouillons' },
      { cle: 'validee', libelle: 'Validées' },
      { cle: 'annulee', libelle: 'Annulées' },
      { cle: 'reclamations', libelle: 'Réclamations' },
      { cle: 'bobines', libelle: 'Poids des bobines', court: 'Bobines' },
      { cle: 'pesees', libelle: 'Archive des pesées', court: 'Pesées' },
    ],
    page,
  },
  {
    chemin: '/receptions/nouvelle',
    titre: 'Nouvelle réception',
    parent: '/receptions',
    roles,
    aide: 'reception_saisie',
    page,
  },
  {
    chemin: '/receptions/:id',
    titre: 'Réception',
    parent: '/receptions',
    roles,
    aide: 'reception',
    onglets: [
      { cle: 'lignes', libelle: 'Lignes pesées' },
      { cle: 'reclamations', libelle: 'Réclamations' },
      { cle: 'pieces', libelle: 'Pièces jointes' },
      { cle: 'historique', libelle: 'Historique' },
    ],
    page,
  },
  {
    chemin: '/reclamations/nouvelle',
    titre: 'Nouvelle réclamation',
    parent: '/receptions',
    roles,
    aide: 'reclamation',
    page,
  },
  {
    chemin: '/reclamations/:id',
    titre: 'Réclamation',
    parent: '/receptions',
    roles,
    aide: 'reclamation',
    onglets: [
      { cle: 'reponse', libelle: 'Réponse du fournisseur' },
      { cle: 'pieces', libelle: 'Pièces jointes' },
      { cle: 'historique', libelle: 'Historique' },
    ],
    page,
  },
]
