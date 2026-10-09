/**
 * L'historique d'une fiche (`GET historique/{objet}/{id}`, API 51, `LigneHistorique` de S2) : qui a
 * fait quoi, quand — le plus récent en tête — et pour une modification chaque champ changé
 * « champ : avant → après » à la française (`libellesHistorique`). Une création ou une
 * suppression garde ses valeurs repliées. Les prix sont retirés par le serveur pour qui ne les
 * voit pas ; un champ vide des deux côtés n'est pas montré, ils n'apparaissent donc nulle part.
 */

import { horodatage } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import { Chargement } from '../retour/Chargement'
import { Erreur } from '../retour/Erreur'
import { Vide } from '../retour/Vide'
import styles from './Historique.module.css'
import { changementsDe, type Changement, type NomsHistorique } from './libellesHistorique'

export type LigneHistorique = Schema<'LigneHistorique'>

const majuscule = (texte: string) => texte.charAt(0).toUpperCase() + texte.slice(1)

/** Les champs changés : « Prix : 2,50 → 2,80 ». */
function Differences({ changements }: { changements: Changement[] }) {
  return (
    <ul className={styles.changements}>
      {changements.map((c) => (
        <li key={c.champ}>
          {c.libelle} : <span className={styles.avant}>{c.avant}</span> →{' '}
          <span className={styles.apres}>{c.apres}</span>
        </li>
      ))}
    </ul>
  )
}

/** Les valeurs d'une fiche créée ou supprimée, repliées (« Référence : IMP 2900 »). */
function Valeurs({ titre, valeurs }: { titre: string; valeurs: { cle: string; texte: string }[] }) {
  if (!valeurs.length) return null
  return (
    <details className={styles.valeurs}>
      <summary>{titre}</summary>
      <ul className={styles.changements}>
        {valeurs.map((v) => (
          <li key={v.cle}>{v.texte}</li>
        ))}
      </ul>
    </details>
  )
}

/** Ce qu'une ligne a changé : différences, ou valeurs d'une création ou d'une suppression. */
function Contenu({ l, noms }: { l: LigneHistorique; noms?: NomsHistorique }) {
  if (l.avant && l.apres) {
    const changements = changementsDe(l.avant, l.apres, noms)
    return changements.length ? <Differences changements={changements} /> : null
  }
  const creation = l.apres != null
  const valeurs = changementsDe(l.avant, l.apres, noms).map((c) => ({
    cle: c.champ,
    texte: `${c.libelle} : ${creation ? c.apres : c.avant}`,
  }))
  return (
    <Valeurs titre={creation ? 'Valeurs à la création' : 'Valeurs avant suppression'} valeurs={valeurs} />
  )
}

export interface HistoriqueProps {
  objet: string
  id: number
  /** Les noms des identifiants que la page connaît déjà (fournisseur, classification…). */
  noms?: NomsHistorique
}

export function Historique({ objet, id, noms }: HistoriqueProps) {
  const lignes = useLecture<LigneHistorique[]>(`/historique/${objet}/${id}`)
  if (lignes.isPending) return <Chargement quoi="l’historique" />
  if (lignes.isError) return <Erreur erreur={lignes.error} onReessayer={() => void lignes.refetch()} />
  if (!lignes.data.length) return <Vide>Aucune modification enregistrée.</Vide>
  return (
    <ol className={styles.historique} aria-label="Historique">
      {[...lignes.data].reverse().map((l) => (
        <li key={l.id} className={styles.ligne}>
          <div className={styles.tete}>
            <strong>{majuscule(l.action)}</strong>
            <span className={styles.qui}>
              {horodatage(l.quand)} · {l.utilisateur}
            </span>
          </div>
          {l.detail ? <p className={styles.detail}>{l.detail}</p> : null}
          <Contenu l={l} noms={noms} />
        </li>
      ))}
    </ol>
  )
}
