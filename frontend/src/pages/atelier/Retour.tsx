/**
 * Retour des machines (`/atelier/retour`) : de quel ordre revient la matière ? Les 10 derniers
 * ordres validés, ou la recherche au serveur (sans accents) dès qu'il y en a plus de 10 ; ce qui
 * n'est pas montré est dit (an. 18). `?ordre=ID` ouvre la saisie du retour (`RetourSaisie`).
 */
import { useState } from 'react'
import { useSearchParams } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { Vide } from '../../composants/retour/Vide'
import { Recherche } from '../../composants/tableaux/Recherche'
import { nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { attente, NoteAtelier } from './briques'
import { useDiffere } from './commun'
import styles from './atelier.module.css'
import { CarteOrdre, ChargerSuivants, trierOrdres } from './Ordres'
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

function ChoixOrdre() {
  const [q, setQ] = useState('')
  const mots = useDiffere(q.trim())
  const tous = useLecture<OrdreResume[]>('/ordres', { statut: 'valide' })
  const trouves = useLecture<OrdreResume[]>(mots ? '/ordres' : null, { statut: 'valide', q: mots })
  const [nb, setNb] = useState(0)
  const lecture = mots ? trouves : tous
  const liste = trierOrdres(lecture.data ?? [])
  const pas = mots ? AVEC_RECHERCHE : SANS_RECHERCHE
  const montres = Math.min(liste.length, pas + nb)
  return (
    <EcranAtelier titre="Retour des machines" retour="/atelier">
      <NoteAtelier>De quel ordre revient la matière ?</NoteAtelier>
      {(tous.data?.length ?? 0) > SANS_RECHERCHE ? (
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
          {piedRetour(montres, liste.length, Boolean(mots)) ? (
            <NoteAtelier>{piedRetour(montres, liste.length, Boolean(mots))}</NoteAtelier>
          ) : null}
          <ChargerSuivants montres={montres} total={liste.length} onCharger={() => setNb(nb + pas)} />
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
