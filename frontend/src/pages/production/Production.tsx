/**
 * « Production & besoins » (`/production?onglet=plan|glissant|realise|besoins`) : le plan de
 * production (saisi par la direction), le plan glissant des douze mois à venir, le plan face au
 * réalisé des douze mois écoulés, et les besoins matière qui en découlent par les recettes, perte
 * comprise. D'où vient le besoin d'une matière : `/production/besoins/:matiereId` (fenêtre).
 *
 * Ce que la direction a tapé survit au changement d'onglet (le brouillon vit ici) ; quitter la
 * page le demande (`useGardeSaisie`, P2-10).
 */
import type { UseQueryResult } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { useGardeSaisie } from '../../composants/coque/garde'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { avecParametre } from '../../lib/adresse'
import type { ErreurApi } from '../../lib/api'
import { moisCourt, nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { BesoinMatiere } from './BesoinMatiere'
import { IndicateursProduction } from './IndicateursProduction'
import { OngletBesoins } from './OngletBesoins'
import { OngletGlissant } from './OngletGlissant'
import { OngletPlan } from './OngletPlan'
import { OngletRealise } from './OngletRealise'
import type { BesoinsDetailles, BrouillonPlan, PlanEtRealise, PlanProduction } from './plan'

type OngletProduction = 'plan' | 'glissant' | 'realise' | 'besoins'
const ONGLETS: readonly { cle: OngletProduction; libelle: string }[] = [
  { cle: 'plan', libelle: 'Plan de production' },
  { cle: 'glissant', libelle: 'Plan glissant' },
  { cle: 'realise', libelle: 'Plan et réalisé' },
  { cle: 'besoins', libelle: 'Besoins matière' },
]

/** Le besoin ouvert par l'adresse (`/production/besoins/12`), ou `null`. */
export function besoinOuvert(chemin: string): number | null {
  const m = /^\/production\/besoins\/(\d+)$/.exec(chemin)
  return m ? Number(m[1]) : null
}

/** Une lecture en cours, en échec, ou son contenu. */
function Lu<T>({
  l,
  quoi,
  children,
}: {
  l: UseQueryResult<T, ErreurApi>
  quoi: string
  children: (d: T) => ReactNode
}) {
  if (l.isPending) return <Chargement quoi={quoi} />
  if (l.isError) return <Erreur erreur={l.error} onReessayer={() => void l.refetch()} />
  return <>{children(l.data)}</>
}

function OngletsProduction({
  onglet,
  modifiees,
  besoins,
}: {
  onglet: OngletProduction
  modifiees: number
  besoins?: BesoinsDetailles
}) {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const choisir = (o: OngletProduction) => {
    const p = avecParametre(params, 'onglet', o === 'plan' ? null : o)
    p.delete('volet')
    navigate(`/production${p.toString() ? `?${p.toString()}` : ''}`, { replace: true })
  }
  return (
    <Onglets<OngletProduction>
      libelle="Onglets de la production"
      actif={onglet}
      onChange={choisir}
      onglets={ONGLETS.map((o) => ({
        ...o,
        compte:
          o.cle === 'besoins'
            ? besoins?.lignes.filter((x) => x.total > 0 || x.total_retenu > 0).length
            : undefined,
        sale: o.cle === 'plan' && modifiees > 0,
        libelle:
          o.cle === 'plan' && modifiees
            ? `${o.libelle} (${nombre(modifiees)} modifiée${modifiees > 1 ? 's' : ''})`
            : o.libelle,
      }))}
    />
  )
}

function Besoins({
  besoins,
  besoin,
  voitAchats,
}: {
  besoins: UseQueryResult<BesoinsDetailles, ErreurApi>
  besoin: number | null
  voitAchats: boolean
}) {
  const navigate = useNavigate()
  const { search } = useLocation()
  return (
    <Lu l={besoins} quoi="les besoins matière">
      {(b) => (
        <>
          <OngletBesoins
            besoins={b}
            voitAchats={voitAchats}
            onOuvrir={(id) => navigate(`/production/besoins/${id}${search}`)}
          />
          {besoin != null ? (
            <BesoinMatiere
              id={besoin}
              besoins={b}
              voitAchats={voitAchats}
              onFermer={() => navigate(`/production${search || '?onglet=besoins'}`)}
            />
          ) : null}
        </>
      )}
    </Lu>
  )
}

export default function Production() {
  const { role } = useSession()
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const besoin = besoinOuvert(pathname)
  const demande = params.get('onglet') ?? params.get('volet')
  const onglet: OngletProduction =
    besoin != null ? 'besoins' : (ONGLETS.find((o) => o.cle === demande)?.cle ?? 'plan')
  const plan = useLecture<PlanProduction>('/production/plan')
  const realise = useLecture<PlanEtRealise>('/production/realise')
  const besoins = useLecture<BesoinsDetailles>(onglet === 'besoins' ? '/production/besoins' : null)
  const [brouillon, setBrouillon] = useState<BrouillonPlan>({})
  const modifiees = Object.keys(brouillon).length
  useGardeSaisie(modifiees > 0)
  const direction = role === 'direction'
  const p = plan.data
  const sous = `Plan glissant sur douze mois dès ${p ? moisCourt(p.mois[0] ?? p.date_reference) : '…'} (base mensuelle × saisonnalité) ; les besoins matière en découlent par les recettes, perte comprise.${direction ? '' : ' Lecture seule : seule la direction modifie le plan.'}`
  return (
    <Page titre="Production & besoins">
      <EnTete titre="Production & besoins" sous={sous} aide="production" />
      {plan.isPending ? <Chargement quoi="le plan de production" /> : null}
      {plan.isError ? <Erreur erreur={plan.error} onReessayer={() => void plan.refetch()} /> : null}
      {p && onglet !== 'besoins' ? <IndicateursProduction plan={p} realise={realise.data} /> : null}
      <OngletsProduction onglet={onglet} modifiees={modifiees} besoins={besoins.data} />
      {p && onglet === 'plan' ? (
        <OngletPlan plan={p} brouillon={brouillon} setBrouillon={setBrouillon} modifiable={direction} />
      ) : null}
      {p && onglet === 'glissant' ? <OngletGlissant plan={p} nonEnregistrees={modifiees} /> : null}
      {onglet === 'realise' ? (
        <Lu l={realise} quoi="le réalisé">
          {(r) => <OngletRealise realise={r} />}
        </Lu>
      ) : null}
      {onglet === 'besoins' ? (
        <Besoins besoins={besoins} besoin={besoin} voitAchats={role !== 'alimentation'} />
      ) : null}
    </Page>
  )
}
