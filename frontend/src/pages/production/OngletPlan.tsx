/**
 * Production › Plan de production (`/production?onglet=plan`) : la saisie de toutes les qualités
 * en un tableau, en coefficients ou en m² par mois (`?vue=`). Une ligne modifiée est marquée tant
 * qu'elle n'est pas enregistrée ; « Enregistrer » la ligne, « Enregistrer tout (N) » d'un bloc (tout
 * ou rien), « Tout annuler » confirmé. Un coefficient hors de 0 à 20 grise l'enregistrement avec la
 * raison (P2-12). La direction saisit, les autres rôles lisent.
 */
import { useSearchParams } from 'react-router'

import { Bascule, useVueAdresse } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { DataTable } from '../../composants/tableaux/DataTable'
import { Recherche } from '../../composants/tableaux/Recherche'
import { api } from '../../lib/api'
import { avecParametre, useRechercheAdresse } from '../../lib/adresse'
import { nombre } from '../../lib/format'
import { moisCourant } from '../../lib/heure'
import { filtrer } from '../../lib/recherche'
import { useEcriture } from '../../lib/requetes'
import styles from './production.module.css'
import { colonnesPlan, type ContextePlan, type ModePlan } from './colonnesPlan'
import {
  horsBornes,
  modifier,
  oublier,
  saisieDe,
  somme,
  type BrouillonPlan,
  type PlanProduction,
  type QualitePlan,
  type SaisiePlan,
} from './plan'

const MODES = [
  { cle: 'coef' as const, libelle: 'Coefficients' },
  { cle: 'm2' as const, libelle: 'm² par mois' },
]

function Pied({
  lignes,
  valeurs,
}: {
  lignes: readonly QualitePlan[]
  valeurs: (q: QualitePlan) => SaisiePlan
}) {
  const actives = lignes.filter((q) => q.actif)
  const mois = Array.from({ length: 12 }, (_, i) =>
    somme(actives.map((q) => valeurs(q).base_mensuelle * (valeurs(q).saisonnalite[i] ?? 0))),
  )
  return (
    <tr>
      <td>Total (m²)</td>
      <td className="nombre">{nombre(somme(actives.map((q) => valeurs(q).base_mensuelle)))}</td>
      {mois.map((v, i) => (
        <td key={i} className="nombre">
          {nombre(v)}
        </td>
      ))}
      <td className="nombre">{nombre(somme(mois))}</td>
      <td className={styles.note}>qualités actives affichées</td>
    </tr>
  )
}

type Changer = (f: (b: BrouillonPlan) => BrouillonPlan) => void

/** Les écritures du plan : une qualité (PUT 90), ou toutes celles modifiées d'un bloc (PUT 146). */
function useEcrituresPlan(brouillon: BrouillonPlan, setBrouillon: Changer) {
  const unique = useEcriture((x: { q: QualitePlan; s: SaisiePlan }) =>
    api.put(`/qualites/${x.q.id}/plan`, {
      base_mensuelle: x.s.base_mensuelle,
      coefficients: x.s.saisonnalite,
      version: x.q.version,
    }),
  )
  const tout = useEcriture((lignes: unknown[]) => api.put('/production/plan', { qualites: lignes }))
  const valeurs = (x: QualitePlan) => brouillon[x.id] ?? saisieDe(x)
  return {
    valeurs,
    occupe: unique.isPending || tout.isPending,
    enregistrer: async (x: QualitePlan) => {
      const s = brouillon[x.id]
      if (!s) return
      await unique.mutateAsync({ q: x, s })
      setBrouillon((b) => oublier(b, [x.id]))
      dire(`Plan de ${x.code} enregistré : besoins en matière et plan d’achat sont recalculés.`)
    },
    enregistrerTout: async (modifiees: readonly QualitePlan[]) => {
      await tout.mutateAsync(
        modifiees.map((x) => ({
          qualite_id: x.id,
          base_mensuelle: valeurs(x).base_mensuelle,
          coefficients: valeurs(x).saisonnalite,
          version: x.version,
        })),
      )
      setBrouillon((b) =>
        oublier(
          b,
          modifiees.map((x) => x.id),
        ),
      )
      dire(
        `Plan enregistré pour ${modifiees.length} qualité(s) : besoins en matière et plan d’achat sont recalculés.`,
      )
    },
  }
}

function CaseInactives({ plan }: { plan: PlanProduction }) {
  const [params, setParams] = useSearchParams()
  const nb = plan.qualites.filter((x) => !x.actif).length
  if (!nb) return null
  return (
    <label className={styles.case}>
      <input
        type="checkbox"
        checked={params.get('inactives') === '1'}
        onChange={(ev) =>
          setParams((p) => avecParametre(p, 'inactives', ev.target.checked ? '1' : null), { replace: true })
        }
      />
      Inactives ({nb})
    </label>
  )
}

function GestesModifiees({
  modifiees,
  fautives,
  e,
  setBrouillon,
}: {
  modifiees: readonly QualitePlan[]
  fautives: readonly QualitePlan[]
  e: ReturnType<typeof useEcrituresPlan>
  setBrouillon: Changer
}) {
  const raison = fautives.length
    ? `Un coefficient reste entre 0 et 20 : corriger ${fautives.map((x) => x.code).join(', ')} (cellules en rouge).`
    : undefined
  return (
    <>
      <Confirmer
        question={`Oublier les ${modifiees.length} modifications ?`}
        oui="Oui, tout annuler"
        titre="Oublier les qualités modifiées, sans rien enregistrer"
        onOui={() => setBrouillon(() => ({}))}
      >
        Tout annuler
      </Confirmer>
      <Bouton
        variante="principal"
        grise={raison}
        titre="Enregistrer toutes les qualités modifiées, en une fois"
        attente="Enregistrement…"
        onClick={() => e.enregistrerTout(modifiees)}
      >
        Enregistrer tout ({modifiees.length})
      </Bouton>
    </>
  )
}

function ActionsPlan(p: {
  plan: PlanProduction
  modifiees: readonly QualitePlan[]
  modifiable: boolean
  fautives: readonly QualitePlan[]
  e: ReturnType<typeof useEcrituresPlan>
  setBrouillon: Changer
}) {
  return (
    <>
      <Recherche_ />
      <CaseInactives plan={p.plan} />
      {p.modifiable && p.modifiees.length ? (
        <GestesModifiees
          modifiees={p.modifiees}
          fautives={p.fautives}
          e={p.e}
          setBrouillon={p.setBrouillon}
        />
      ) : null}
    </>
  )
}

function Recherche_() {
  const [q, setQ] = useRechercheAdresse()
  return <Recherche valeur={q} onChange={setQ} placeholder="Qualité, nom…" />
}

function contextePlan(
  mode: ModePlan,
  modifiable: boolean,
  brouillon: BrouillonPlan,
  setBrouillon: Changer,
  e: ReturnType<typeof useEcrituresPlan>,
): ContextePlan {
  return {
    mode,
    modifiable,
    valeurs: e.valeurs,
    modifiee: (x) => Boolean(brouillon[x.id]),
    modifier: (x, s) => setBrouillon((b) => modifier(b, x, s)),
    annuler: (x) => setBrouillon((b) => oublier(b, [x.id])),
    enregistrer: e.enregistrer,
    occupe: e.occupe,
    moisCourant: Number(moisCourant().slice(5, 7)) - 1,
  }
}

/** Les qualités affichées : actives, inactives si demandé, et toute qualité modifiée ; cherchées. */
function lignesPlan(plan: PlanProduction, brouillon: BrouillonPlan, params: URLSearchParams) {
  const inactives = params.get('inactives') === '1'
  return filtrer(
    plan.qualites.filter((x) => inactives || x.actif || brouillon[x.id]),
    params.get('q') ?? '',
    (x) => [x.code, x.nom],
  )
}

const VIDE_PLAN = 'Aucune qualité : créez-les dans l’écran Qualités et recettes.'

const sousPlan = (plan: PlanProduction, mode: ModePlan, modifiable: boolean) =>
  `${mode === 'coef' ? 'Un coefficient de 1,2 en janvier veut dire « 20 % de plus que la base en janvier ».' : 'En m² par mois, les m² d’un mois donnent son coefficient (m² ÷ base) ; la base ne change que si vous la saisissez.'} Le plan glissant lit les mois dans l’ordre des mois à venir${plan.croissance_annuelle ? `, avec la croissance annuelle de ${nombre(plan.croissance_annuelle * 100, 1)} %` : ''}.${modifiable ? ' Une ligne modifiée reste marquée tant qu’elle n’est pas enregistrée.' : ' Lecture seule : seule la direction modifie le plan.'}`

export function OngletPlan({
  plan,
  brouillon,
  setBrouillon,
  modifiable,
}: {
  plan: PlanProduction
  brouillon: BrouillonPlan
  setBrouillon: Changer
  modifiable: boolean
}) {
  const [params] = useSearchParams()
  const [mode, setMode] = useVueAdresse<ModePlan>(['coef', 'm2'], 'coef')
  const e = useEcrituresPlan(brouillon, setBrouillon)
  const modifiees = plan.qualites.filter((x) => brouillon[x.id])
  const lignes = lignesPlan(plan, brouillon, params)
  const contexte = contextePlan(mode, modifiable, brouillon, setBrouillon, e)
  const fautives = modifiees.filter((x) => horsBornes(e.valeurs(x)))
  return (
    <Carte
      titre={
        <span className={styles.titre}>
          Plan de production — m² par qualité
          <Bascule vues={MODES} valeur={mode} onChange={setMode} libelle="Saisie du plan" />
        </span>
      }
      sous={sousPlan(plan, mode, modifiable)}
      actions={
        <ActionsPlan
          plan={plan}
          modifiees={modifiees}
          modifiable={modifiable}
          fautives={fautives}
          e={e}
          setBrouillon={setBrouillon}
        />
      }
      serre
      remplir
      className={styles.carteListe}
    >
      <DataTable<QualitePlan>
        libelle="Plan de production"
        lignes={lignes}
        colonnes={colonnesPlan(contexte)}
        cle={(x) => x.id}
        recherche={false}
        serre
        figee
        marquee={(x) => Boolean(brouillon[x.id])}
        pied={lignes.length ? <Pied lignes={lignes} valeurs={e.valeurs} /> : undefined}
        vide={plan.qualites.length ? 'Aucune qualité ne correspond.' : VIDE_PLAN}
      />
    </Carte>
  )
}
