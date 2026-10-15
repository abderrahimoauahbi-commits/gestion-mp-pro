/**
 * Retour des machines (`/atelier/retour`) : de quel ordre revient la matière ? Les 10 derniers
 * ordres validés, ou la recherche au serveur (sans accents) dès qu'il y en a plus de 10 ; ce qui
 * n'est pas montré est dit (an. 18). `?ordre=ID` ouvre la saisie du retour (`RetourSaisie`).
 * Le téléphone ne lit que ce qu'il montre, le total en plus (route 135, le plus récent d'abord) :
 * plus tous les ordres validés depuis l'origine (3 Mo, 1,1 s à trois ans ; lot CONFORT-LENTEURS).
 */
import { keepPreviousData, type QueryKey } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { Vide } from '../../composants/retour/Vide'
import { Recherche } from '../../composants/tableaux/Recherche'
import { nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import type { Page } from '../../lib/types'
import { attente, NoteAtelier } from './briques'
import { useDiffere } from './commun'
import styles from './atelier.module.css'
import { CarteOrdre, ChargerSuivants } from './Ordres'
import { RetourSaisie } from './RetourSaisie'
import type { OrdreResume } from './types'

const SANS_RECHERCHE = 10
const AVEC_RECHERCHE = 30

/** Le pied de la liste : ce qui n'est pas montré, et comment le trouver. */
export function piedRetour(montres: number, total: number, cherche: boolean): string {
  if (montres >= total) return ''
  if (cherche) return `${nombre(total - montres)} autre(s) : préciser la recherche`
  return `les ${nombre(montres)} derniers sur ${nombre(total)} : chercher un ordre plus ancien`
}

/** Les mots d'une lecture déjà faite (sa clé), pour ne garder ses résultats que pour eux. */
export function motsDe(cle: QueryKey | undefined): string | undefined {
  const params = cle?.[1]
  return params && typeof params === 'object' && 'q' in params ? String(params.q) : undefined
}

function ChoixOrdre() {
  const [q, setQ] = useState('')
  const mots = useDiffere(q.trim())
  const [nb, setNb] = useState(0)
  const pas = mots ? AVEC_RECHERCHE : SANS_RECHERCHE
  const tous = useLecture<Page<OrdreResume>>(
    '/ordres',
    { statut: 'valide', limite: SANS_RECHERCHE + (mots ? 0 : nb) },
    { placeholderData: keepPreviousData },
  )
  // « Charger les suivants » garde les cartes affichées ; une autre recherche, non.
  const trouves = useLecture<Page<OrdreResume>>(
    mots ? '/ordres' : null,
    { statut: 'valide', q: mots, limite: AVEC_RECHERCHE + nb },
    { placeholderData: (avant, requete) => (motsDe(requete?.queryKey) === mots ? avant : undefined) },
  )
  const lecture = mots ? trouves : tous
  const liste = lecture.data?.elements ?? []
  const total = lecture.data?.total ?? 0
  const montres = Math.min(total, pas + nb)
  return (
    <EcranAtelier titre="Retour des machines" retour="/atelier">
      <NoteAtelier>De quel ordre revient la matière ?</NoteAtelier>
      {(tous.data?.total ?? 0) > SANS_RECHERCHE ? (
        <Recherche
          valeur={q}
          onChange={(v) => {
            setQ(v)
            setNb(0)
          }}
          placeholder="N° d’ordre, qualité, métier…"
          libelle="Chercher un ordre"
        />
      ) : null}
      {attente([lecture], 'les ordres') ?? (
        <>
          {!liste.length ? <Vide>{mots ? 'Aucun ordre ne correspond.' : 'Aucun ordre validé.'}</Vide> : null}
          <ul className={styles.liste}>
            {liste.slice(0, montres).map((o) => (
              <li key={o.id}>
                <CarteOrdre o={o} vers={`/atelier/retour?ordre=${o.id}`} />
              </li>
            ))}
          </ul>
          {piedRetour(montres, total, Boolean(mots)) ? (
            <NoteAtelier>{piedRetour(montres, total, Boolean(mots))}</NoteAtelier>
          ) : null}
          <ChargerSuivants montres={montres} total={total} onCharger={() => setNb(nb + pas)} />
        </>
      )}
    </EcranAtelier>
  )
}

export default function Retour() {
  const [params] = useSearchParams()
  const ordre = Number(params.get('ordre')) || null
  return ordre ? <RetourSaisie key={ordre} id={ordre} /> : <ChoixOrdre />
}
