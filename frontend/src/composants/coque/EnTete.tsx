/**
 * L'en-tête d'une page (ECRANS-PRO § 3, `EnTete`) : titre (h1), sous-titre, bouton « ? » qui
 * ouvre l'aide de l'écran (A7), et les boutons de la page **à place fixe** à droite (ils ne
 * changent pas de place selon l'état, REGLES-ECRAN § 3). Au second niveau (une page sous une
 * autre), le fil d'Ariane est obligatoire : `fil`.
 */
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import type { CleAide } from '../../routes'
import { Icone } from '../mise-en-page/Icone'
import { useOuvrirAide } from './ouvrirAide'
import styles from './EnTete.module.css'

export interface ElementFil {
  libelle: string
  vers?: string
}

export interface EnTeteProps {
  titre: ReactNode
  sous?: ReactNode
  /** Le chemin jusqu'à cette page (sans elle) : obligatoire au second niveau. */
  fil?: readonly ElementFil[]
  actions?: ReactNode
  /** La section d'aide, si ce n'est pas celle de l'écran courant ; `false` : pas de « ? ». */
  aide?: CleAide | false
}

export function EnTete({ titre, sous, fil, actions, aide }: EnTeteProps) {
  const ouvrir = useOuvrirAide()
  return (
    <header className={styles.entete}>
      <div className={styles.titres}>
        {fil?.length ? (
          <nav aria-label="Fil d’Ariane de la page" className={styles.fil}>
            {fil.map((f) => (
              <span key={f.libelle} className={styles.etape}>
                {f.vers ? <Link to={f.vers}>{f.libelle}</Link> : f.libelle}
                <Icone nom="chevron" taille={12} />
              </span>
            ))}
          </nav>
        ) : null}
        <div className={styles.ligne}>
          <h1 className={styles.titre}>{titre}</h1>
          {ouvrir && aide !== false ? (
            <button
              type="button"
              className={styles.aide}
              aria-label="Aide de l’écran"
              title="Aide de l’écran"
              onClick={() => ouvrir(aide || undefined)}
            >
              <Icone nom="aide" taille={18} />
            </button>
          ) : null}
        </div>
        {sous ? <p className={styles.sous}>{sous}</p> : null}
      </div>
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </header>
  )
}
