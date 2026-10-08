/**
 * Le bandeau rouge en tête d'Envoyer, Retour, Déplacer : ce que le serveur refusera (inventaire
 * en cours, date trop ancienne, magasin en quarantaine), dit **dès l'ouverture**, pas au clic.
 */
import { Icone } from '../mise-en-page/Icone'
import styles from './BandeauBlocages.module.css'

export function BandeauBlocages({ blocages }: { blocages: readonly string[] | null | undefined }) {
  if (!blocages?.length) return null
  return (
    <div className={styles.bandeau} role="alert">
      <Icone nom="attention" taille={20} />
      <div>
        <strong>Sera refusé à la validation :</strong>
        <ul className={styles.liste}>
          {blocages.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
