/**
 * La fenêtre par-dessus la page (A4, A5) : fiche, saisie, choix. Normale, large ou très large, ou
 * tiroir à droite ; en-tête avec ×, corps qui défile, pied de boutons alignés.
 *
 * Ne jamais perdre une saisie : avec `sale`, fermer (×, Échap, clic sur le voile, et les boutons
 * « Fermer » / « Annuler » qui passent par `useFermerFenetre`) demande d'abord, dans la fenêtre :
 * « Des modifications ne sont pas enregistrées. Les abandonner ? » · « Non, continuer la saisie »
 * · « Oui, abandonner ». Recharger ou fermer l'onglet du navigateur est retenu aussi.
 *
 * Pile : Échap ne ferme que la fenêtre du dessus ; le focus entre dans la fenêtre, y tourne (Tab)
 * et revient d'où il venait à la fermeture ; la page dessous ne défile pas.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from 'react'

import { Bouton } from '../saisie/Bouton'
import { classes } from './classes'
import styles from './Fenetre.module.css'
import { Icone } from './Icone'
import { auDessus, depiler, empiler, marquerSale } from './pile'

export const QUESTION_ABANDON = 'Des modifications ne sont pas enregistrées. Les abandonner ?'

export interface FenetreProps {
  titre: ReactNode
  sous?: ReactNode
  onFermer: () => void
  children: ReactNode
  taille?: 'normale' | 'large' | 'tresLarge'
  tiroir?: boolean
  /** Une saisie n'est pas enregistrée : fermer demande d'abord. */
  sale?: boolean
  pied?: ReactNode
}

const FermerFenetre = createContext<(() => void) | null>(null)

/** La fermeture gardée de la fenêtre qui contient ce composant (pour « Fermer », « Annuler »). */
export function useFermerFenetre(): () => void {
  const fermer = useContext(FermerFenetre)
  if (!fermer) throw new Error('useFermerFenetre hors d’une Fenetre.')
  return fermer
}

const FOCUSABLES =
  'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/** Tab et Maj+Tab tournent dans la fenêtre, pas dans la page derrière. */
function garderLeFocus(e: KeyboardEvent, boite: HTMLElement): void {
  const liste = [...boite.querySelectorAll<HTMLElement>(FOCUSABLES)]
  const debut = liste[0]
  const fin = liste[liste.length - 1]
  if (!debut || !fin) return
  if (e.shiftKey && document.activeElement === debut) {
    e.preventDefault()
    fin.focus()
  } else if (!e.shiftKey && document.activeElement === fin) {
    e.preventDefault()
    debut.focus()
  }
}

/** Entrée dans la pile, focus, clavier ; `demander` est la fermeture gardée. */
function usePile(boite: RefObject<HTMLDivElement | null>, demander: () => void, sale: boolean) {
  const [moi] = useState(() => Symbol('fenetre'))
  const derniere = useRef(demander)
  useEffect(() => {
    derniere.current = demander
  })
  useEffect(() => {
    empiler(moi, boite.current)
    const avant = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const premier = boite.current?.querySelector<HTMLElement>(
      'input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [autofocus]',
    )
    if (!boite.current?.contains(document.activeElement)) (premier ?? boite.current)?.focus()
    const clavier = (e: KeyboardEvent) => {
      if (!auDessus(moi)) return
      if (e.key === 'Escape') {
        e.preventDefault()
        derniere.current()
      } else if (e.key === 'Tab' && boite.current) garderLeFocus(e, boite.current)
    }
    document.addEventListener('keydown', clavier)
    return () => {
      document.removeEventListener('keydown', clavier)
      depiler(moi)
      avant?.focus()
    }
  }, [moi, boite])
  useEffect(() => marquerSale(moi, sale), [moi, sale])
}

/** « Des modifications ne sont pas enregistrées. Les abandonner ? », dans la fenêtre même. */
function QuestionAbandon({ onNon, onOui }: { onNon: () => void; onOui: () => void }) {
  return (
    <div className={styles.question} role="alert">
      <span>{QUESTION_ABANDON}</span>
      <Bouton onClick={onNon}>Non, continuer la saisie</Bouton>
      <Bouton variante="danger" onClick={onOui}>
        Oui, abandonner
      </Bouton>
    </div>
  )
}

export function Fenetre({
  titre,
  sous,
  onFermer,
  children,
  taille = 'normale',
  tiroir,
  sale = false,
  pied,
}: FenetreProps) {
  const id = useId()
  const boite = useRef<HTMLDivElement>(null)
  const [question, setQuestion] = useState(false)
  const demander = useCallback(() => {
    if (question) setQuestion(false)
    else if (sale) setQuestion(true)
    else onFermer()
  }, [question, sale, onFermer])
  const fermerGarde = useCallback(() => (sale ? setQuestion(true) : onFermer()), [sale, onFermer])
  usePile(boite, demander, sale)
  return (
    <div
      className={classes(styles.voile, tiroir && styles.voileTiroir)}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) fermerGarde()
      }}
    >
      <div
        ref={boite}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${id}-titre`}
        tabIndex={-1}
        className={classes(styles.fenetre, tiroir ? styles.tiroir : styles[taille])}
      >
        <header className={styles.entete}>
          <div className={styles.titres}>
            <h2 id={`${id}-titre`}>{titre}</h2>
            {sous ? <p className={styles.sous}>{sous}</p> : null}
          </div>
          <button type="button" className={styles.fermer} aria-label="Fermer" onClick={fermerGarde}>
            <Icone nom="croix" taille={18} />
          </button>
        </header>
        {question ? <QuestionAbandon onNon={() => setQuestion(false)} onOui={onFermer} /> : null}
        <FermerFenetre.Provider value={fermerGarde}>
          <div className={styles.corps}>{children}</div>
          {pied ? <footer className={styles.pied}>{pied}</footer> : null}
        </FermerFenetre.Provider>
      </div>
    </div>
  )
}
