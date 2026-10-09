/**
 * Production › Plan glissant (`/production?onglet=glissant`) : les m² planifiés des douze mois à
 * venir (base × coefficient du mois, croissance comprise), le tissé du mois en cours, ce que le plan
 * demandera de matière. Tableau ou graphique (`?vue=`), recherche, export.
 */
import { Link } from 'react-router'

import { Bascule, useVueAdresse } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Barres } from '../../composants/graphiques/Barres'
import type { Serie } from '../../composants/graphiques/echelle'
import { Note } from '../../composants/retour/Note'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import { Recherche } from '../../composants/tableaux/Recherche'
import { useRechercheAdresse } from '../../lib/adresse'
import { moisCourt, nombre, part, VIDE } from '../../lib/format'
import { filtrer } from '../../lib/recherche'
import { Double } from '../stock/cellules'
import styles from './production.module.css'
import { somme, type PlanProduction, type QualitePlan } from './plan'

export const VUES = [
  { cle: 'tableau' as const, libelle: 'Tableau' },
  { cle: 'graphique' as const, libelle: 'Graphique' },
]

function colonnes(plan: PlanProduction): Colonne<QualitePlan>[] {
  const mois: Colonne<QualitePlan>[] = plan.mois.map((m, i) => ({
    cle: `m${i}`,
    titre: `${moisCourt(m)}${i === 0 ? ' (en cours)' : ''}`,
    aide: i === 0 ? 'Le mois en cours ; dessous, ce que l’atelier a déjà tissé' : `M+${i}`,
    droite: true,
    valeur: (q) => q.glissant[i] ?? null,
    rendu: (q) => {
      const v = q.glissant[i] ?? 0
      return (
        <Double
          haut={v ? nombre(v) : VIDE}
          bas={
            i === 0 && q.tisse_mois_en_cours
              ? `tissé ${nombre(q.tisse_mois_en_cours)}${v ? ` · ${part(q.tisse_mois_en_cours / v, 0)}` : ''}`
              : undefined
          }
        />
      )
    },
  }))
  return [
    {
      cle: 'code',
      titre: 'Qualité',
      valeur: (q) => q.code,
      recherche: (q) => [q.nom],
      rendu: (q) => (
        <Link to={`/qualites/${q.id}?onglet=plan`} onClick={(e) => e.stopPropagation()} title={q.nom}>
          <Double haut={q.code} bas={q.nom} />
        </Link>
      ),
    },
    ...mois,
    {
      cle: 'total',
      titre: 'Total 12 mois',
      droite: true,
      valeur: (q) => q.total_glissant,
      rendu: (q) => <strong>{nombre(q.total_glissant)}</strong>,
    },
    {
      cle: 'kg_m2',
      titre: 'Matière (kg/m²)',
      aide: 'Matière consommée par m², perte comprise',
      droite: true,
      valeur: (q) => q.kg_m2 || null,
      rendu: (q) =>
        q.kg_m2 ? (
          nombre(q.kg_m2, 2)
        ) : (
          <span className={styles.bas} title="Aucune recette : ce plan ne tire aucune matière">
            {VIDE}
          </span>
        ),
    },
  ]
}

function Pied({ plan, lignes }: { plan: PlanProduction; lignes: readonly QualitePlan[] }) {
  const totaux = plan.mois.map((_, i) => somme(lignes.map((q) => q.glissant[i] ?? 0)))
  const matiere = plan.mois.map((_, i) => somme(lignes.map((q) => (q.glissant[i] ?? 0) * q.kg_m2)))
  const tisse = somme(lignes.map((q) => q.tisse_mois_en_cours))
  return (
    <>
      <tr>
        <td>Total (m²)</td>
        {totaux.map((v, i) => (
          <td key={i} className="nombre">
            {nombre(v)}
            {i === 0 && tisse ? <span className={styles.note}> · tissé {nombre(tisse)}</span> : null}
          </td>
        ))}
        <td className="nombre">{nombre(somme(totaux))}</td>
        <td />
      </tr>
      <tr title="Le poids de tout ce que ce plan consommera, perte comprise : les mêmes kilos que les besoins matière">
        <td>Matière nécessaire (kg)</td>
        {matiere.map((v, i) => (
          <td key={i} className="nombre">
            {nombre(v)}
          </td>
        ))}
        <td className="nombre">{nombre(somme(matiere))}</td>
        <td />
      </tr>
    </>
  )
}

/** La méthode du plan glissant, et ce qui n'est pas affiché. */
function sousGlissant(plan: PlanProduction, horsPlan: number): string {
  const croissance = plan.croissance_annuelle
    ? ` × croissance annuelle de ${nombre(plan.croissance_annuelle * 100, 1)} %`
    : ''
  const caches = horsPlan ? ` ${horsPlan} qualité(s) sans plan ou inactive(s) ne sont pas affichées.` : ''
  const horsDuPlan = plan.tisse_hors_plan.length
    ? ` Tissé ce mois-ci hors plan : ${plan.tisse_hors_plan.map((x) => `${x.qualite} (${nombre(x.m2)} m²)`).join(', ')}.`
    : ''
  return `Base mensuelle × coefficient du mois${croissance}, arrondi au m² ; la matière nécessaire suit les recettes, perte de ${nombre(plan.taux_perte * 100, 1)} % comprise.${caches}${horsDuPlan}`
}

/** Les qualités les plus planifiées, une série chacune ; les autres en une série « Autres ». */
export const SERIES_MAX = 7

/** Les séries du graphique : sept qualités empilées (les plus grosses) et « Autres » (gris). */
export function seriesGlissant(plan: PlanProduction, lignes: readonly QualitePlan[]): Serie[] {
  const parVolume = [...lignes].sort((a, b) => b.total_glissant - a.total_glissant)
  const tetes = parVolume.slice(0, SERIES_MAX)
  const reste = parVolume.slice(SERIES_MAX)
  const series: Serie[] = tetes.map((q) => ({ nom: q.code, unite: 'm²', valeurs: [...q.glissant] }))
  if (reste.length)
    series.push({
      nom: 'Autres',
      unite: 'm²',
      couleur: 'var(--graphe-axe)',
      valeurs: plan.mois.map((_, i) => somme(reste.map((x) => x.glissant[i] ?? 0))),
    })
  series.push({
    nom: 'Matière nécessaire',
    unite: 'kg',
    couleur: 'var(--ton-accent)',
    valeurs: plan.mois.map((_, i) => somme(lignes.map((x) => (x.glissant[i] ?? 0) * x.kg_m2))),
  })
  return series
}

function Graphique({ plan, lignes }: { plan: PlanProduction; lignes: readonly QualitePlan[] }) {
  return (
    <div className={styles.graphique}>
      <Barres
        libelle="Plan glissant"
        empiler
        etiquettes={plan.mois.map((m) => moisCourt(m))}
        series={seriesGlissant(plan, lignes)}
      />
    </div>
  )
}

export function OngletGlissant({ plan, nonEnregistrees }: { plan: PlanProduction; nonEnregistrees: number }) {
  const [vue, setVue] = useVueAdresse<'tableau' | 'graphique'>(['tableau', 'graphique'], 'tableau')
  const [q, setQ] = useRechercheAdresse()
  const auPlan = plan.qualites.filter((x) => x.total_glissant > 0 || x.tisse_mois_en_cours > 0)
  const lignes = filtrer(auPlan, q, (x) => [x.code, x.nom])
  return (
    <Carte
      titre={
        <span className={styles.titre}>
          Plan glissant — m² planifiés
          <Bascule vues={VUES} valeur={vue} onChange={setVue} libelle="Vue du plan glissant" />
        </span>
      }
      sous={sousGlissant(plan, plan.qualites.length - auPlan.length)}
      actions={
        <>
          <Recherche valeur={q} onChange={setQ} placeholder="Qualité, nom…" />
          <ExportExcel route="/export/production" parametres={{ onglet: 'glissant' }} />
        </>
      }
      serre
      remplir
      className={styles.carteListe}
    >
      {nonEnregistrees ? (
        <Note>
          {nonEnregistrees} qualité(s) modifiée(s) dans le plan de production ne sont pas encore enregistrées
          : le plan glissant les montrera une fois enregistrées.
        </Note>
      ) : null}
      {vue === 'tableau' ? (
        <DataTable<QualitePlan>
          libelle="Plan glissant"
          lignes={lignes}
          colonnes={colonnes(plan)}
          cle={(x) => x.id}
          recherche={false}
          pied={lignes.length ? <Pied plan={plan} lignes={lignes} /> : undefined}
          vide={
            auPlan.length
              ? 'Aucune qualité ne correspond.'
              : 'Aucune qualité au plan : saisissez une base mensuelle dans le plan de production.'
          }
        />
      ) : (
        <Graphique plan={plan} lignes={lignes} />
      )}
    </Carte>
  )
}
