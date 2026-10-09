/**
 * La fenêtre « Besoin signalé par {par} » (`/accueil?signalement=ID`, `/cockpit?signalement=ID`) :
 * le besoin de l'atelier, une réponse facultative, « Marquer traité » (route 223). L'adresse est
 * stable : la cloche et le Cockpit y mènent aussi. Une réponse tapée n'est jamais perdue sans la
 * question (`sale`, P1-22 : « Annuler » passe par la garde).
 */
import { useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'

import { Definitions } from '../../composants/mise-en-page/Definitions'
import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Zone } from '../../composants/saisie/Zone'
import { api } from '../../lib/api'
import { horodatage } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import type { PageSignalements, SignalementFiche, Traitement } from './types'

/** Le besoin ouvert par l'adresse (`?signalement=12`), ou `null`. */
export function besoinOuvert(params: URLSearchParams): number | null {
  const v = params.get('signalement')
  return v && /^\d+$/.test(v) ? Number(v) : null
}

function Annuler() {
  const fermer = useFermerFenetre()
  return <Bouton onClick={fermer}>Annuler</Bouton>
}

function Lecture({ x }: { x: SignalementFiche }) {
  return (
    <Definitions
      colonnes={2}
      items={[
        ['Matière', x.reference || 'non précisée'],
        ['Urgence', x.urgence === 'urgente' ? <Badge ton="critique">urgent</Badge> : 'normale'],
        ['Signalé le', horodatage(x.quand)],
        ['Par', x.par],
      ]}
    />
  )
}

function Traiter({ x, fermer }: { x: SignalementFiche; fermer: () => void }) {
  const [reponse, setReponse] = useState('')
  const envoi = useEcriture((t: Traitement) => api.post(`/signalements/${x.id}/traiter`, t))
  const traiter = async () => {
    await envoi.mutateAsync({ reponse: reponse.trim() })
    dire('Besoin traité.')
    fermer()
  }
  return (
    <Fenetre
      titre={`Besoin signalé par ${x.par}`}
      sous={`${x.reference ? `${x.reference} : ` : ''}« ${x.texte} »`}
      onFermer={fermer}
      sale={reponse.trim() !== ''}
      pied={
        <>
          <Annuler />
          <Bouton variante="principal" attente="Enregistrement…" onClick={traiter}>
            Marquer traité
          </Bouton>
        </>
      }
    >
      <Grille colonnes={1}>
        <Lecture x={x} />
        <Champ
          libelle="Réponse à l’atelier"
          aide="Ce qui est fait : commandé, en route, remplacé par… — l’atelier la lit sur son téléphone."
        >
          <Zone valeur={reponse} onChange={setReponse} max={500} lignes={3} autoFocus />
        </Champ>
      </Grille>
    </Fenetre>
  )
}

/** Un besoin déjà traité (lien d'une notification ancienne) : sa réponse, en lecture. */
function DejaTraite({ x, fermer }: { x: SignalementFiche; fermer: () => void }) {
  return (
    <Fenetre titre={`Besoin signalé par ${x.par}`} sous={`« ${x.texte} »`} onFermer={fermer}>
      <Grille colonnes={1}>
        <Lecture x={x} />
        <Note ton="ok">
          Traité par {x.traite_par || '—'} le {horodatage(x.traite_le)}
          {x.reponse ? ` : « ${x.reponse} »` : '.'}
        </Note>
      </Grille>
    </Fenetre>
  )
}

/** La fenêtre du besoin de l'adresse, s'il y en a un ; fermer rend la page sans `?signalement=`. */
export function BesoinSignale() {
  const [params] = useSearchParams()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const id = besoinOuvert(params)
  const tous = useLecture<PageSignalements>(id == null ? null : '/signalements')
  if (id == null) return null
  const fermer = () => {
    const p = new URLSearchParams(params)
    p.delete('signalement')
    navigate(`${pathname}${p.toString() ? `?${p.toString()}` : ''}`)
  }
  const x = tous.data?.elements.find((s) => s.id === id)
  if (x) return x.traite ? <DejaTraite x={x} fermer={fermer} /> : <Traiter x={x} fermer={fermer} />
  return (
    <Fenetre titre="Besoin signalé" onFermer={fermer}>
      {tous.isPending ? <Chargement quoi="le besoin" /> : null}
      <Erreur erreur={tous.error} onReessayer={() => void tous.refetch()} />
      {tous.data ? <Note ton="attention">Signalement introuvable.</Note> : null}
    </Fenetre>
  )
}
