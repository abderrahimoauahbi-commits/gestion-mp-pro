/**
 * Oui ou non, au clic ou à la barre d'espace (rôle `switch`). Le libellé est à côté et le nomme.
 *
 * Comme `Bouton`, il ne se grise **jamais sans dire pourquoi** : `manque`, `blocages` (du serveur)
 * ou `grise` (une raison dite, « Nature figée : … ») ; la raison est l'infobulle, la description
 * accessible et `data-raison`. `desactive` reste pour une fiche en lecture seule (comme `Saisie`).
 */
import { useId, type ReactNode } from 'react'

import { classes } from '../mise-en-page/classes'
import { raisonGrise, type BoutonProps } from './Bouton'
import styles from './Interrupteur.module.css'

export function Interrupteur({
  valeur,
  onChange,
  libelle,
  desactive,
  manque,
  blocages,
  grise,
}: {
  valeur: boolean
  onChange: (valeur: boolean) => void
  libelle: ReactNode
  desactive?: boolean
} & Pick<BoutonProps, 'manque' | 'blocages' | 'grise'>) {
  const id = useId()
  const raison = raisonGrise({ manque, blocages, grise })
  return (
    <>
      <button
        type="button"
        role="switch"
        aria-checked={valeur}
        disabled={desactive || Boolean(raison)}
        aria-describedby={raison ? `${id}-raison` : undefined}
        data-raison={raison || undefined}
        title={raison || undefined}
        className={classes(styles.interrupteur, valeur && styles.actif)}
        onClick={() => onChange(!valeur)}
      >
        <span className={styles.piste} aria-hidden="true" />
        <span>{libelle}</span>
      </button>
      {raison ? (
        <span id={`${id}-raison`} className="masque-accessible">
          {raison}
        </span>
      ) : null}
    </>
  )
}
