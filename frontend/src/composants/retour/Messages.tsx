/**
 * Les messages de l'écran (toasts) : `dire(texte, ton)` de n'importe où, `<Messages />` posé une
 * fois à la racine de l'application (coque et atelier). Un succès reste visible même si la
 * fenêtre qui l'a dit se ferme (P2-14) ; une erreur reste jusqu'à ce qu'on la ferme ; le refus du
 * serveur est dit tel quel (son `detail`).
 */
import { useEffect, useState } from 'react'

import { messageErreur } from '../../lib/api'
import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import styles from './Messages.module.css'

export type TonMessage = 'succes' | 'info' | 'attention' | 'erreur'

interface Message {
  id: number
  texte: string
  ton: TonMessage
}

/** Le temps d'affichage d'un message qui n'est pas une erreur (ms). */
export const DUREE_MESSAGE = 5000
/** Le nombre de messages gardés à l'écran (les plus anciens s'en vont). */
const GARDES = 4

let suivant = 1
const auditeurs = new Set<(m: Message) => void>()

/** Dit un message à l'écran. */
export function dire(texte: string, ton: TonMessage = 'succes'): void {
  const m = { id: suivant++, texte, ton }
  for (const a of auditeurs) a(m)
}

/** Dit une erreur, d'où qu'elle vienne (refus du serveur, réseau coupé, exception). */
export function direErreur(e: unknown): void {
  dire(messageErreur(e), 'erreur')
}

const ICONES = { succes: 'coche', info: 'info', attention: 'attention', erreur: 'attention' } as const

export function Messages() {
  const [liste, setListe] = useState<Message[]>([])
  useEffect(() => {
    const minuteries = new Set<ReturnType<typeof setTimeout>>()
    const recevoir = (m: Message) => {
      setListe((l) => [...l.slice(-(GARDES - 1)), m])
      if (m.ton === 'erreur') return
      const t = setTimeout(() => {
        minuteries.delete(t)
        setListe((l) => l.filter((x) => x.id !== m.id))
      }, DUREE_MESSAGE)
      minuteries.add(t)
    }
    auditeurs.add(recevoir)
    return () => {
      auditeurs.delete(recevoir)
      for (const t of minuteries) clearTimeout(t)
    }
  }, [])
  return (
    <div className={styles.messages} role="status" aria-live="polite">
      {liste.map((m) => (
        <div key={m.id} className={classes(styles.message, styles[m.ton])}>
          <Icone nom={ICONES[m.ton]} />
          <span className={styles.texte}>{m.texte}</span>
          <button
            type="button"
            className={styles.fermer}
            aria-label="Fermer le message"
            onClick={() => setListe((l) => l.filter((x) => x.id !== m.id))}
          >
            <Icone nom="croix" taille={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
