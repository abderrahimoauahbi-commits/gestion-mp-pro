/**
 * Les liens de l'analyse vers les fiches : un n° de dossier mène à `/dossiers/:id` (son
 * identifiant lu dans `ids_dossiers`) en emportant l'adresse de l'analyse (`state.retour`) : la
 * fiche, fermée, ramène à l'analyse telle qu'on l'avait filtrée (ECRANS-PRO 5.16, 5.17). Une
 * référence mène à sa fiche matière quand le rôle peut l'ouvrir.
 *
 * `LienDocument` ne porte pas d'état de navigation : le lien du dossier reprend son adresse
 * (`adresseDocument`) et son texte (`numeroOuEtat`) avec un `Link` qui le porte.
 */
import { Link, useLocation } from 'react-router'

import { adresseDocument, LienDocument } from '../../../composants/documents/LienDocument'
import { nombre } from '../../../lib/format'
import { numeroOuEtat } from '../../../lib/statuts'
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
  const id = liens.ids[numero]
  const texte = numeroOuEtat(numero)
  if (id == null) return <span>{texte}</span>
  return (
    <Link
      to={adresseDocument('dossier', id)}
      state={{ retour: liens.retour }}
      title="Ouvrir le dossier"
      onClick={(e) => e.stopPropagation()}
    >
      {texte}
    </Link>
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
