/**
 * Les lectures de Ma journée et du Cockpit : une clé par route (ARCHITECTURE § 10.1), si bien que
 * deux écrans qui lisent la même route lisent le même chiffre. Le Cockpit se relit toutes les trois
 * minutes (comme Gestion MP) ; le reste suit la règle commune (frais 15 s, relu au retour).
 */
import { useLecture } from '../../lib/requetes'
import type {
  Brouillons,
  Cockpit,
  CommandeResume,
  EnAttente,
  EtatSauvegardes,
  InventaireResume,
  PageSignalements,
  ReclamationResume,
} from './types'

export const useCockpit = () => useLecture<Cockpit>('/cockpit', undefined, { refetchInterval: 180_000 })
export const useCommandesToutes = (lire = true) => useLecture<CommandeResume[]>(lire ? '/commandes' : null)
export const useBrouillons = () => useLecture<Brouillons>('/brouillons')
export const useAttente = (lire = true) => useLecture<EnAttente>(lire ? '/dossiers/a-rattacher' : null)
/** Les besoins signalés en attente, le plus récent d'abord (route 221). */
export const useBesoins = () => useLecture<PageSignalements>('/signalements', { a_traiter: true })
export const useReclamationsOuvertes = () =>
  useLecture<ReclamationResume[]>('/reclamations', { statut: 'ouverte' })
export const useInventairesOuverts = () =>
  useLecture<InventaireResume[]>('/inventaires', { statut: 'ouvert' })
export const useSauvegardes = () => useLecture<EtatSauvegardes>('/sauvegardes')
