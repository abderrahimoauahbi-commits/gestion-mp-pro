/**
 * Production › Plan et réalisé (`/production?onglet=realise`) : ce que l'atelier a tissé (d'après les
 * ordres) face au plan en vigueur chaque mois, sur les douze mois écoulés. Chaque cellule dit le
 * tissé et, dessous, le prévu ; un mois clos à plus de 10 % sous le plan est rouge, au-dessus orange.
 * L'écart se juge sur les mois clos depuis la mise en service. Un clic sur une qualité ouvre son
 * graphique (`?vue=graphique&qualite=`).
 */
import { useSearchParams } from 'react-router'

import { Bascule, useVueAdresse } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Barres } from '../../composants/graphiques/Barres'
import { Badge } from '../../composants/retour/Badge'
import { classes } from '../../composants/mise-en-page/classes'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import { Recherche } from '../../composants/tableaux/Recherche'
import { avecParametre, useRechercheAdresse } from '../../lib/adresse'
import { moisCourt, nombre, partSignee, VIDE } from '../../lib/format'
import { filtrer } from '../../lib/recherche'
import { Double } from '../stock/cellules'
import stock from '../stock/stock.module.css'
import { VUES } from './OngletGlissant'
import styles from './production.module.css'
import {
  debutAffiche,
  debutCompte,
  somme,
  tonEcartPlan,
  type PlanEtRealise,
  type RealiseQualite,
} from './plan'

const SEUIL = 0.1

/** La teinte du tissé d'un mois clos : sous le plan de plus de 10 % (rouge), au-dessus (orange). */
export function teinteMois(
  prevu: number,
  fait: number,
  i: number,
  debut: number,
  clos: number,
): 'bas' | 'haut' | null {
  if (i < debut || i >= clos || !prevu) return null
  const e = (fait - prevu) / prevu
  return e < -SEUIL ? 'bas' : e > SEUIL ? 'haut' : null
}

function colonnes(r: PlanEtRealise): Colonne<RealiseQualite>[] {
  const debut = debutCompte(r)
  const clos = r.mois_clos
  const affiche = debutAffiche(r)
  // Masquage d'affichage : on filtre les colonnes par leur index `i` (les données
  // restent lues en `realise[i]`/`plan[i]`), sans jamais ré-indexer les tableaux.
  const mois: Colonne<RealiseQualite>[] = r.mois
    .map((m, i) => ({
      cle: `m${i}`,
      titre: `${moisCourt(m)}${i >= clos ? ' (en cours)' : i < debut ? ' (non compté)' : ''}`,
      aide:
        i < debut
          ? 'Avant la mise en service : hors écart'
          : 'Tissé, et dessous le prévu du plan en vigueur ce mois-là',
      droite: true,
      triable: false,
      valeur: (x: RealiseQualite) => x.realise[i] ?? null,
      rendu: (x: RealiseQualite) => {
        const t = teinteMois(x.plan[i] ?? 0, x.realise[i] ?? 0, i, debut, clos)
        return (
          <Double
            haut={
              <span className={classes(t === 'bas' && styles.bas, t === 'haut' && styles.haut)}>
                {x.realise[i] ? nombre(x.realise[i]) : VIDE}
              </span>
            }
            bas={`prévu ${nombre(x.plan[i] ?? 0)}`}
          />
        )
      },
    }))
    .filter((_, i) => i >= affiche)
  return [
    {
      cle: 'qualite',
      titre: 'Qualité',
      valeur: (x) => x.qualite,
      rendu: (x) => <strong title="Cliquer pour voir son graphique">{x.qualite}</strong>,
    },
    ...mois,
    {
      cle: 'total',
      titre: 'Total',
      droite: true,
      valeur: (x) => x.total_realise,
      rendu: (x) => <Double haut={nombre(x.total_realise)} bas={`prévu ${nombre(x.total_plan)}`} />,
    },
    {
      cle: 'ecart',
      titre: 'Écart (mois clos)',
      droite: true,
      valeur: (x) => x.ecart ?? null,
      rendu: (x) => {
        const ton = tonEcartPlan(x.ecart)
        if (x.ecart != null && ton) return <Badge ton={ton}>{partSignee(x.ecart)}</Badge>
        return <span className={styles.note}>{x.total_plan ? VIDE : 'hors plan'}</span>
      },
    },
  ]
}

function GraphiqueRealise({ realise, choisie }: { realise: PlanEtRealise; choisie: string }) {
  const focus = realise.lignes.find((x) => x.qualite === choisie)
  const affiche = debutAffiche(realise)
  // Même début que le tableau : on garde les mois d'index `i >= affiche`.
  const indices = realise.mois.map((_, i) => i).filter((i) => i >= affiche)
  const serie = (f: (x: RealiseQualite) => readonly number[]) =>
    indices.map((i) => (focus ? (f(focus)[i] ?? 0) : somme(realise.lignes.map((x) => f(x)[i] ?? 0))))
  return (
    <div className={styles.graphique}>
      <Barres
        libelle={focus ? `Plan et tissé de ${focus.qualite}` : 'Plan et tissé, toutes les qualités'}
        etiquettes={indices.map((i) => moisCourt(realise.mois[i] ?? ''))}
        series={[
          { nom: 'Plan', unite: 'm²', valeurs: serie((x) => x.plan) },
          { nom: 'Tissé', unite: 'm²', valeurs: serie((x) => x.realise) },
        ]}
      />
    </div>
  )
}

function Choix({
  realise,
  choisie,
  onChoix,
}: {
  realise: PlanEtRealise
  choisie: string
  onChoix: (q: string) => void
}) {
  return (
    <select
      aria-label="Qualité du graphique"
      className={stock.selecteur}
      value={choisie}
      onChange={(e) => onChoix(e.target.value)}
    >
      <option value="">Toutes les qualités</option>
      {realise.lignes.map((x) => (
        <option key={x.qualite}>{x.qualite}</option>
      ))}
    </select>
  )
}

export function OngletRealise({ realise }: { realise: PlanEtRealise }) {
  const [params, setParams] = useSearchParams()
  const [vue, setVue] = useVueAdresse<'tableau' | 'graphique'>(['tableau', 'graphique'], 'tableau')
  const [q, setQ] = useRechercheAdresse()
  const choisie = params.get('qualite') ?? ''
  const choisir = (code: string) =>
    setParams((p) => avecParametre(avecParametre(p, 'qualite', code || null), 'vue', 'graphique'), {
      replace: true,
    })
  return (
    <Carte
      titre={
        <span className={styles.titre}>
          Plan et réalisé — m², douze mois écoulés
          <Bascule vues={VUES} valeur={vue} onChange={setVue} libelle="Vue du réalisé" />
        </span>
      }
      sous="Tissé d’après les ordres de fabrication ; chaque mois clos est jugé sur le plan en vigueur pendant ce mois ; les mois d’avant la mise en service ne comptent pas. Un écart durable dit qu’il faut revoir la base ou la saisonnalité de la qualité."
      actions={
        <>
          {vue === 'graphique' ? (
            <Choix realise={realise} choisie={choisie} onChoix={choisir} />
          ) : (
            <Recherche valeur={q} onChange={setQ} placeholder="Qualité…" />
          )}
          <ExportExcel route="/export/production" parametres={{ onglet: 'realise' }} />
        </>
      }
      serre
      remplir
      className={styles.carteListe}
    >
      {vue === 'tableau' ? (
        <DataTable<RealiseQualite>
          libelle="Plan et réalisé"
          lignes={filtrer(realise.lignes, q, (x) => [x.qualite])}
          colonnes={colonnes(realise)}
          cle={(x) => x.qualite}
          recherche={false}
          cliquable={(x) => choisir(x.qualite)}
          vide={
            realise.lignes.length
              ? 'Aucune qualité ne correspond.'
              : 'Aucune qualité au plan, et aucun ordre de fabrication.'
          }
        />
      ) : (
        <GraphiqueRealise realise={realise} choisie={choisie} />
      )}
    </Carte>
  )
}
