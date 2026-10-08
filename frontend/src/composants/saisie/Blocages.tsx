/**
 * Ce que le serveur refusera, dit **avant** de cliquer (A8, P7) : « Sera refusé : » et la liste
 * des raisons calculées par le serveur (`blocages` d'une fiche ou d'une proposition). Rien s'il
 * n'y en a pas.
 */
import styles from './Blocages.module.css'

export function Blocages({
  blocages,
  titre = 'Sera refusé :',
}: {
  blocages: readonly string[] | null | undefined
  titre?: string
}) {
  if (!blocages?.length) return null
  return (
    <div className={styles.blocages} role="note" aria-label={titre}>
      <strong>{titre}</strong>
      <ul>
        {blocages.map((b) => (
          <li key={b}>{b}</li>
        ))}
      </ul>
    </div>
  )
}
