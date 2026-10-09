/**
 * Envoyer aux machines (`/atelier/envoyer`, `?ordre=ID` pour un brouillon) : aiguillage, puis la
 * demande et les lots (`EnvoyerDemande`, `EnvoyerLots`), puis « Sortie enregistrée ». Un ordre
 * qui ne se lit pas n'ouvre jamais un ordre vierge (H-04, an. 3) : « Ordre introuvable » sur un
 * 404, « Pas de réseau » + « Réessayer » sur une coupure ; un ordre validé ou annulé mène à sa fiche.
 */
import { useState } from 'react'
import { Navigate, useLocation, useNavigate, useSearchParams } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import { useLecture } from '../../lib/requetes'
import { attente, EcranEnAttente, Fiche, LienBouton, Ligne } from './briques'
import { estIntrouvable, qte, useNomMetier } from './commun'
import styles from './atelier.module.css'
import { EnvoyerDemande } from './EnvoyerDemande'
import { EnvoyerLots } from './EnvoyerLots'
import type { OrdreFiche } from './types'
import { useSaisieSortie } from './useSaisieSortie'

/** La note posée sur la fiche d'un ordre qu'on voulait modifier mais qui ne se modifie plus (an. 10). */
export function noteNonModifiable(statut: string): string {
  return statut === 'annule'
    ? 'Cet ordre est annulé : il ne se modifie plus (en refaire un).'
    : 'Cet ordre est déjà validé : il ne se modifie plus (l’annuler, puis en refaire un).'
}

export default function Envoyer() {
  const [params] = useSearchParams()
  const { key } = useLocation()
  const id = params.get('ordre')
  const ordre = useLecture<OrdreFiche>(id ? `/ordres/${id}` : null, undefined, { staleTime: 0 })
  if (!id) return <SaisieTelephone key={`nouveau-${key}`} ordre={null} />
  if (ordre.isError && estIntrouvable(ordre.error))
    return (
      <EcranAtelier titre="Ordre introuvable" retour="/atelier/ordres">
        <Vide>Cet ordre n’existe pas (brouillon supprimé ?).</Vide>
      </EcranAtelier>
    )
  const enAttente = attente([ordre], 'l’ordre')
  if (enAttente || !ordre.data)
    return <EcranEnAttente titre="Modifier l’ordre (brouillon)" retour="/atelier/ordres" corps={enAttente} />
  if (ordre.data.statut !== 'brouillon')
    return (
      <Navigate
        to={`/atelier/ordres/${ordre.data.id}`}
        replace
        state={{ note: noteNonModifiable(ordre.data.statut) }}
      />
    )
  return <SaisieTelephone key={`${id}-${key}`} ordre={ordre.data} />
}

function SaisieTelephone({ ordre }: { ordre: OrdreFiche | null }) {
  const s = useSaisieSortie(ordre)
  const [fait, setFait] = useState<OrdreFiche | null>(null)
  if (fait) return <SortieEnregistree ordre={fait} />
  if (s.e.etape === 'demande') return <EnvoyerDemande s={s} />
  return <EnvoyerLots s={s} onFait={setFait} />
}

function SortieEnregistree({ ordre }: { ordre: OrdreFiche }) {
  const naviguer = useNavigate()
  const nomMetier = useNomMetier()
  const valide = ordre.statut === 'valide'
  return (
    <EcranAtelier titre="Sortie enregistrée" retour="/atelier">
      <Fiche ton="ok" titre={valide ? `Ordre ${ordre.numero ?? ''} validé` : 'Ordre gardé en brouillon'}>
        <Ligne libelle={valide ? 'Matière sortie' : 'Matière à sortir'} grand>
          {qte(ordre.total)}
        </Ligne>
        <Ligne libelle="Magasin">{ordre.magasin}</Ligne>
        {ordre.metier_id ? <Ligne libelle="Métier">{nomMetier(ordre.metier_id, ordre.metier)}</Ligne> : null}
      </Fiche>
      <div className={styles.gestes}>
        <Bouton taille="atelier" variante="principal" bloc onClick={() => naviguer('/atelier/envoyer')}>
          Nouvel ordre
        </Bouton>
        <LienBouton vers={`/atelier/ordres/${ordre.id}`}>Voir l’ordre</LienBouton>
        <LienBouton vers="/atelier">Revenir à l’accueil</LienBouton>
      </div>
    </EcranAtelier>
  )
}
