/**
 * Ce que partagent les pages publiques (connexion, installation, enrôlement) : le champ de code,
 * l'entrée après connexion (cache vidé, adresse demandée rouverte si elle est permise), l'en-tête.
 */
import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import { attributsDuChamp, useChamp } from '../../composants/saisie/Champ'
import controle from '../../composants/saisie/controle.module.css'
import { destinationApresConnexion } from '../../lib/droits'
import type { Moi } from '../../lib/types-coque'
import styles from './connexion.module.css'

/** Les lectures publiques, gardées quand on vide le cache de la session précédente. */
const PUBLIQUES = ['/etat', '/visages']

/** À l'arrivée sur une page publique, rien de la session précédente ne reste en mémoire. */
export function useOublierLaSession(): void {
  const client = useQueryClient()
  useEffect(() => {
    client.removeQueries({ predicate: (q) => !PUBLIQUES.includes(String(q.queryKey[0])) })
  }, [client])
}

/** Entrer après la connexion ou l'installation : l'adresse demandée si elle est permise, sinon l'accueil. */
export function useEntrer(): (moi: Moi) => void {
  const client = useQueryClient()
  const naviguer = useNavigate()
  const [params] = useSearchParams()
  const retour = params.get('retour')
  return useCallback(
    (moi: Moi) => {
      client.removeQueries()
      naviguer(destinationApresConnexion(moi.role, retour), { replace: true })
    },
    [client, naviguer, retour],
  )
}

/** « Code d'Ahmed », « Code de Karim » (élision devant une voyelle ou un h). */
export function libelleCode(nom: string): string {
  return /^[aeiouyéèêëàâîïôûh]/i.test(nom.trim()) ? `Code d’${nom}` : `Code de ${nom}`
}

/** Le champ du code : masqué, clavier numérique pour l'alimentation. */
export function ChampCode({
  valeur,
  onChange,
  numerique,
  autoFocus,
}: {
  valeur: string
  onChange: (v: string) => void
  numerique?: boolean
  autoFocus?: boolean
}) {
  const liens = useChamp()
  return (
    <input
      {...attributsDuChamp(liens, undefined, 'Code')}
      className={controle.controle}
      type="password"
      autoComplete="current-password"
      inputMode={numerique ? 'numeric' : 'text'}
      autoFocus={autoFocus}
      value={valeur}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

/** L'en-tête des pages publiques : la marque, la société. */
export function TetePublique({ titre, children }: { titre: string; children?: ReactNode }) {
  return (
    <header className={styles.tete}>
      <h1 className={styles.titre}>{titre}</h1>
      {children ? <p className={styles.note}>{children}</p> : null}
    </header>
  )
}
