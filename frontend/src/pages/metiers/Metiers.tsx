/**
 * Métiers à tisser (`/metiers`) : quatre indicateurs, la liste (recherche sur les fils montés,
 * « Montrer les métiers arrêtés », tri, totaux, export Excel), la fiche d'un métier en fenêtre à
 * adresse stable (`/metiers/:id`) et la création (`/metiers/nouveau`, direction ; les autres rôles
 * reviennent à la liste avec la raison, an. 15). Aucune valeur pour l'alimentation.
 */
import { useEffect } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Page } from '../../composants/mise-en-page/Page'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { dire } from '../../composants/retour/Messages'
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { avecParametre } from '../../lib/adresse'
import { formule } from '../../lib/aide'
import { montantCourt, nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Role } from '../../lib/types'
import type { MetierFiche } from '../atelier/types'
import { COLONNES } from './colonnes'
import { FicheMetier } from './FicheMetier'
import { NouveauMetier } from './NouveauMetier'

/** La fiche ouverte par l'adresse : un identifiant, « nouveau », ou rien. */
export function ficheDe(chemin: string): number | 'nouveau' | null {
  const m = /^\/metiers\/(\d+|nouveau)$/.exec(chemin)
  if (!m) return null
  return m[1] === 'nouveau' ? 'nouveau' : Number(m[1])
}

/** Le sous-titre de la page, selon le rôle. */
export function sousTitre(role: Role): string {
  const debut =
    'Chaque métier porte plusieurs étages, et chaque étage se garnit sur toute sa laize. Bobines = mètres × ' +
    'densité ; poids = bobines × kg / bobine × remplissage des bobines. Ce poids, « Sur les métiers », est du stock : il compte ' +
    'dans le stock global, sa valeur, le disponible et le projeté. Monter n’écrit aucun mouvement : le fil a déjà ' +
    'été sorti par un ordre.'
  if (role === 'alimentation') return `${debut} Vous montez les fils ; la direction règle les métiers.`
  if (role === 'achats')
    return `${debut} Lecture seule : l’alimentation monte les fils, la direction règle les métiers.`
  return `${debut} L’alimentation monte les fils ; vous réglez les métiers.`
}

function IndicateursMetiers({ metiers, voitPrix }: { metiers: readonly MetierFiche[]; voitPrix: boolean }) {
  const actifs = metiers.filter((m) => m.actif)
  const somme = (f: (m: MetierFiche) => number) => actifs.reduce((t, m) => t + f(m), 0)
  const valeur = somme((m) => m.valeur_mad ?? 0)
  return (
    <Indicateurs libelle="Indicateurs des métiers">
      <Kpi
        titre="Métiers en service"
        valeur={nombre(actifs.length)}
        detail={`${nombre(metiers.length - actifs.length)} arrêté(s)`}
        formule={formule('metiers_en_service')}
      />
      <Kpi
        titre="Sur les métiers"
        valeur={nombre(somme((m) => m.sur_les_metiers))}
        unite="kg"
        detail={voitPrix ? `${montantCourt(valeur, 'MAD')} au coût moyen` : 'métiers en service'}
        formule={formule('sur_les_metiers')}
      />
      <Kpi
        titre="Étages garnis"
        valeur={nombre(somme((m) => m.etages_garnis))}
        detail={`sur ${nombre(somme((m) => m.etages))} disponibles`}
        formule={formule('etages_garnis')}
      />
      <Kpi
        titre="Bobines"
        valeur={nombre(somme((m) => m.bobines))}
        detail="montées sur les métiers en service"
        formule={formule('bobines_montees')}
      />
    </Indicateurs>
  )
}

function Liste({ metiers, onOuvrir }: { metiers: MetierFiche[]; onOuvrir: (id: number) => void }) {
  const etat = useEtatTableAdresse([])
  const [params, setParams] = useSearchParams()
  const arretes = params.get('arretes') === '1'
  const lignes = arretes ? metiers : metiers.filter((m) => m.actif)
  return (
    <DataTable
      libelle="Métiers à tisser"
      lignes={lignes}
      colonnes={COLONNES}
      cle={(m) => m.id}
      recherche={etat.recherche}
      choix={etat.choix}
      placeholder="Métier, fil monté, couleur…"
      rechercheCachee={(m) => m.fils.map((f) => `${f.reference} ${f.designation}`)}
      cliquable={(m) => onOuvrir(m.id)}
      exporter={{ route: '/export/metiers' }}
      outils={
        <Interrupteur
          valeur={arretes}
          libelle="Montrer les métiers arrêtés"
          onChange={(v) => setParams((p) => avecParametre(p, 'arretes', v ? '1' : null), { replace: true })}
        />
      }
      vide={
        <Vide>
          {metiers.length ? 'Aucun métier ne correspond.' : 'Aucun métier. La direction les crée ici.'}
        </Vide>
      }
    />
  )
}

export default function Metiers() {
  const { role } = useSession()
  const { pathname, search } = useLocation()
  const naviguer = useNavigate()
  const metiers = useLecture<MetierFiche[]>('/metiers')
  const fiche = ficheDe(pathname)
  const direction = role === 'direction'
  const liste = () => {
    const p = new URLSearchParams(search)
    p.delete('onglet')
    return `/metiers${p.size ? `?${p.toString()}` : ''}`
  }
  const ouvrir = (id: number) => void naviguer(`/metiers/${id}${search}`)
  useEffect(() => {
    if (fiche !== 'nouveau' || direction) return
    dire('La création d’un métier est réservée à la direction.', 'attention')
    void naviguer('/metiers', { replace: true })
  }, [fiche, direction, naviguer])
  return (
    <Page titre="Métiers à tisser">
      <EnTete
        titre="Métiers à tisser"
        sous={sousTitre(role)}
        actions={
          direction ? (
            <Bouton
              variante="principal"
              icone="plus"
              onClick={() => void naviguer(`/metiers/nouveau${search}`)}
            >
              Nouveau métier
            </Bouton>
          ) : null
        }
      />
      {metiers.data ? <IndicateursMetiers metiers={metiers.data} voitPrix={role !== 'alimentation'} /> : null}
      <Carte serre remplir titre="Les métiers à tisser">
        {metiers.isError ? (
          <Erreur erreur={metiers.error} onReessayer={() => void metiers.refetch()} />
        ) : null}
        {metiers.isPending ? <Chargement quoi="les métiers" /> : null}
        {metiers.data ? <Liste metiers={metiers.data} onOuvrir={ouvrir} /> : null}
      </Carte>
      {fiche === 'nouveau' && direction ? (
        <NouveauMetier
          onFermer={() => void naviguer(liste())}
          onCree={(id) => void naviguer(`/metiers/${id}`, { replace: true })}
        />
      ) : null}
      {typeof fiche === 'number' ? (
        <FicheMetier key={fiche} id={fiche} role={role} onFermer={() => void naviguer(liste())} />
      ) : null}
    </Page>
  )
}
