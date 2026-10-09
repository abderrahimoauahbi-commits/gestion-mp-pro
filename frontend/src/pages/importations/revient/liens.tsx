/**
 * Les liens de l'analyse vers les fiches : un n° de dossier mène à `/dossiers/:id` (son
 * identifiant lu dans `ids_dossiers`) en emportant l'adresse de l'analyse (`state.retour`) : la
 * fiche, fermée, ramène à l'analyse telle qu'on l'avait filtrée (ECRANS-PRO 5.16, 5.17). Une
 * référence mène à sa fiche matière quand le rôle peut l'ouvrir.
 */
import { useLocation } from 'react-router'

import { LienDocument } from '../../../composants/documents/LienDocument'
import { nombre } from '../../../lib/format'
import styles from './revient.module.css'

/** Ce que les colonnes savent pour faire leurs liens. */
export interface Liens {
  /** Numéro de dossier → identifiant. */
  ids: Readonly<Record<string, number>>
  /** L'adresse de l'analyse, où revenir en fermant la fiche. */
  retour: string
  /** L'identifiant de la matière d'une référence, si le rôle peut ouvrir sa fiche. */
  matiere: (reference: string) => number | undefined
}

/** L'adresse actuelle de l'analyse (chemin et paramètres). */
export function useRetour(): string {
  const { pathname, search } = useLocation()
  return `${pathname}${search}`
}

/** Le n° d'un dossier, lien vers sa fiche (l'adresse de l'analyse en retour). */
export function LienDossier({ numero, liens }: { numero: string; liens: Liens }) {
  return (
    <LienDocument
      genre="dossier"
      id={liens.ids[numero]}
      numero={numero}
      titre="Ouvrir le dossier"
      state={{ retour: liens.retour }}
    />
  )
}

/** Les quatre premiers dossiers d'une ligne, puis « +N » (la liste entière en infobulle). */
export function Dossiers({ numeros, liens }: { numeros: readonly string[]; liens: Liens }) {
  const reste = numeros.length - 4
  return (
    <span className={styles.dossiers}>
      {numeros.slice(0, 4).map((n) => (
        <LienDossier key={n} numero={n} liens={liens} />
      ))}
      {reste > 0 ? (
        <span className={styles.note} title={numeros.join(', ')}>
          +{nombre(reste)}
        </span>
      ) : null}
    </span>
  )
}

/** Une référence, lien vers sa fiche matière quand on la connaît. */
export function LienMatiere({ reference, liens }: { reference: string; liens: Liens }) {
  return <LienDocument genre="matiere" id={liens.matiere(reference)} numero={reference} />
}
