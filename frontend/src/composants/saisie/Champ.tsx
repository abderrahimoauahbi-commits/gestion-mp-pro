/**
 * Un champ de formulaire : libellé, contrôle, aide, erreur (ECRANS-PRO § 3). Le libellé est le
 * **nom accessible** du contrôle, l'aide et l'erreur sa **description** (REGLES-ECRAN § 3,
 * accessibilité : Gestion MP mettait l'aide en `title`, qui remplaçait le nom). Les contrôles du
 * système (`Saisie`, `Zone`, `Nombre`, `DateChamp`, `Selecteur`…) lisent ces liens dans le
 * contexte du champ (`useChamp`) ; un contrôle à plusieurs boutons (`Segments`) est un groupe
 * nommé par le libellé.
 *
 * `erreur` : le refus du serveur pour ce champ (`ErreurApi.champs`, voir `erreurDuChamp`), écrit
 * sous le champ. `large` : le champ prend toute la rangée d'une `Grille`.
 *
 * Trois étages toujours présents (libellé, contrôle, aide et erreur) : dans une `Grille`, ils
 * s'alignent d'un champ à l'autre (sous-grille), quelle que soit la longueur des libellés et des aides.
 */
import { createContext, useContext, useId, type ReactNode } from 'react'

import { ErreurApi } from '../../lib/api'
import { classes } from '../mise-en-page/classes'
import styles from './Champ.module.css'

export interface LiensDuChamp {
  /** L'identifiant du contrôle (cible du `<label>`). */
  id: string
  /** L'identifiant du libellé (pour un groupe : `aria-labelledby`). */
  libelleId: string
  /** Les identifiants de l'aide et de l'erreur (`aria-describedby`), ou `undefined`. */
  decritPar: string | undefined
  /** Vrai si le champ porte une erreur (`aria-invalid`). */
  invalide: boolean
  obligatoire: boolean
  /** Un champ groupe (plusieurs contrôles) : chaque contrôle garde son propre nom. */
  groupe: boolean
}

const Contexte = createContext<LiensDuChamp | null>(null)

/** Les liens du champ qui contient ce contrôle (`null` hors d'un `Champ`). */
export function useChamp(): LiensDuChamp | null {
  return useContext(Contexte)
}

/**
 * Les attributs d'accessibilité d'un contrôle : dans un `Champ` simple, le `<label>` le nomme et
 * l'aide le décrit ; hors d'un champ, ou dans un champ groupe (plusieurs contrôles), il se nomme
 * lui-même (`libelle`).
 */
export function attributsDuChamp(liens: LiensDuChamp | null, decritAussi?: string, libelle?: string) {
  const simple = liens && !liens.groupe ? liens : null
  const decrit = [simple?.decritPar, decritAussi].filter(Boolean).join(' ') || undefined
  return {
    id: simple?.id,
    'aria-label': simple ? undefined : libelle,
    'aria-describedby': decrit,
    'aria-invalid': simple?.invalide || undefined,
    'aria-required': simple?.obligatoire || undefined,
  }
}

/** Le message du serveur pour un champ (`champs` d'un refus 422), ou `undefined`. */
export function erreurDuChamp(erreur: unknown, chemin: string): string | undefined {
  return erreur instanceof ErreurApi ? erreur.champs[chemin] : undefined
}

export interface ChampProps {
  libelle: ReactNode
  children: ReactNode
  aide?: ReactNode
  erreur?: string | null
  obligatoire?: boolean
  large?: boolean
  /** Un contrôle à plusieurs boutons (segments, puces) : un groupe nommé, pas un `<label>`. */
  groupe?: boolean
  className?: string
}

/** Le libellé, et « * » (caché aux lecteurs d'écran, qui entendent `aria-required`) s'il est obligatoire. */
function Etiquette({ libelle, obligatoire }: { libelle: ReactNode; obligatoire: boolean }) {
  return (
    <>
      {libelle}
      {obligatoire ? (
        <span className={styles.obligatoire} aria-hidden="true">
          {' '}
          *
        </span>
      ) : null}
    </>
  )
}

export function Champ({
  libelle,
  children,
  aide,
  erreur,
  obligatoire = false,
  large,
  groupe,
  className,
}: ChampProps) {
  const base = useId()
  const liens: LiensDuChamp = {
    id: `${base}-controle`,
    libelleId: `${base}-libelle`,
    decritPar:
      [aide ? `${base}-aide` : '', erreur ? `${base}-erreur` : ''].filter(Boolean).join(' ') || undefined,
    invalide: Boolean(erreur),
    obligatoire,
    groupe: Boolean(groupe),
  }
  const etiquette = <Etiquette libelle={libelle} obligatoire={obligatoire} />
  return (
    <div
      className={classes(styles.champ, large && styles.large, erreur && styles.enErreur, className)}
      role={groupe ? 'group' : undefined}
      aria-labelledby={groupe ? liens.libelleId : undefined}
      aria-describedby={groupe ? liens.decritPar : undefined}
    >
      {groupe ? (
        <span id={liens.libelleId} className={styles.libelle}>
          {etiquette}
        </span>
      ) : (
        <label id={liens.libelleId} htmlFor={liens.id} className={styles.libelle}>
          {etiquette}
        </label>
      )}
      <div className={styles.controle}>
        <Contexte.Provider value={liens}>{children}</Contexte.Provider>
      </div>
      <div className={styles.pied}>
        {aide ? (
          <span id={`${base}-aide`} className={styles.aide}>
            {aide}
          </span>
        ) : null}
        {erreur ? (
          <span id={`${base}-erreur`} className={styles.erreur}>
            {erreur}
          </span>
        ) : null}
      </div>
    </div>
  )
}
