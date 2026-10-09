/**
 * Le lien d'un document par son numéro (M74, A5) : un n° mène à sa fiche, à son adresse stable
 * (`/commandes/12`). Un document sans numéro s'appelle « Brouillon » (ou « À approuver » pour un
 * bon soumis à la direction), jamais « Brouillon n° 331 ».
 *
 * `state` part avec la navigation (`state.retour` : l'adresse où la fiche, fermée, ramène — une
 * analyse filtrée, le Cockpit). Le clic ne remonte pas à la ligne d'un tableau cliquable (il
 * ouvrirait une autre fiche) ; la garde de saisie, qui écoute en capture, le voit toujours.
 */
import { Link } from 'react-router'

import { numeroOuEtat } from '../../lib/statuts'

/** L'adresse de la liste de chaque genre de document (sa fiche est `<base>/<id>`). */
export const BASES = {
  commande: '/commandes',
  reception: '/receptions',
  reclamation: '/reclamations',
  ordre: '/ordres',
  operation: '/operations',
  dossier: '/dossiers',
  inventaire: '/inventaires',
  lot: '/lots',
  matiere: '/matieres',
  fournisseur: '/fournisseurs',
  qualite: '/qualites',
  metier: '/metiers',
} as const

export type GenreDocument = keyof typeof BASES

/** L'adresse stable de la fiche d'un document. */
export function adresseDocument(genre: GenreDocument, id: number): string {
  return `${BASES[genre]}/${id}`
}

export function LienDocument({
  genre,
  id,
  numero,
  statut,
  state,
  titre,
}: {
  genre: GenreDocument
  id: number | null | undefined
  numero: string | null | undefined
  statut?: string
  /** L'état de navigation (`{ retour }`). */
  state?: unknown
  /** L'infobulle (« Ouvrir le dossier »). */
  titre?: string
}) {
  const texte = numeroOuEtat(numero, statut)
  if (id == null) return <span>{texte}</span>
  return (
    <Link to={adresseDocument(genre, id)} state={state} title={titre} onClick={(e) => e.stopPropagation()}>
      {texte}
    </Link>
  )
}
