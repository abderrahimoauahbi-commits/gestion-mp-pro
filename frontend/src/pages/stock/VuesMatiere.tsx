/**
 * Le bas de la fiche matière : d'où vient son besoin (qualité par qualité, mois par mois), ses lots
 * et ce qui est monté sur les métiers. Les kilos du besoin s'additionnent à l'écran comme ils sont
 * écrits : chaque colonne tombe sur son total (`repartir`), chaque ligne sur le sien.
 */
import { useNavigate } from 'react-router'

import { Cadre } from '../../composants/tableaux/Cadre'
import { Badge } from '../../composants/retour/Badge'
import { Vide } from '../../composants/retour/Vide'
import { date, kgEtMetres, moisCourt, nombre, part, poidsBobine } from '../../lib/format'
import { ajouterJours, moisCourant } from '../../lib/heure'
import { tableauJuste } from './addition'
import { Kg } from './cellules'
import styles from './stock.module.css'
import {
  estQuarantaine,
  type BesoinDeQualite,
  type FilSurMetier,
  type LigneStock,
  type LotSolde,
} from './types'

/** Les douze mois du plan glissant, dès le mois en cours de l'usine : « 2026-10 », « 2026-11 »… */
export function moisGlissants(n = 12, depuis = moisCourant()): string[] {
  const mois: string[] = []
  let jour = `${depuis}-15`
  for (let i = 0; i < n; i += 1) {
    mois.push(jour.slice(0, 7))
    jour = ajouterJours(jour, 31).slice(0, 8) + '15'
  }
  return mois
}

const somme = (v: readonly number[]) => v.reduce((a, b) => a + b, 0)

function TeteMois({ mois }: { mois: readonly string[] }) {
  return (
    <thead>
      <tr>
        <th className={styles.fige}>Qualité</th>
        <th
          className={styles.droite}
          title="Kilos de cette matière par m² de la qualité, hors perte (les kilos du mois la comprennent)"
        >
          kg/m²
        </th>
        {mois.map((m) => (
          <th key={m} className={styles.droite}>
            {moisCourt(m)}
          </th>
        ))}
        <th className={styles.droite}>Total (kg)</th>
      </tr>
    </thead>
  )
}

export function BesoinsDuPlan({ l, qualites }: { l: LigneStock; qualites: readonly BesoinDeQualite[] }) {
  const besoins = l.besoins ?? []
  if (!besoins.length) return <Vide>Aucun besoin : la matière n’est dans aucune recette au plan.</Vide>
  const mois = moisGlissants(besoins.length)
  const { lignes, totaux } = tableauJuste(
    qualites.map((q) => q.kg),
    besoins,
  )
  return (
    <Cadre hauteur="fenetre">
      <table className={styles.tableSimple} aria-label="Besoins du plan, mois par mois (kg)">
        <TeteMois mois={mois} />
        <tbody>
          {qualites.map((q, r) => (
            <tr key={q.qualite}>
              <td className={styles.fige}>
                <strong>{q.qualite}</strong>{' '}
                <span className={styles.note}>{part(q.pourcentage / 100, 0)}</span>
              </td>
              <td className={styles.droite}>{nombre(q.kg_par_m2, 3)}</td>
              {(lignes[r] ?? []).map((v, i) => (
                <td key={i} className={styles.droite}>
                  {v ? nombre(v) : '—'}
                </td>
              ))}
              <td className={styles.droite}>
                <strong>{nombre(somme(lignes[r] ?? []))}</strong>
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td className={styles.fige}>Besoin du plan (kg)</td>
            <td />
            {totaux.map((v, i) => (
              <td key={i} className={styles.droite}>
                {nombre(v)}
              </td>
            ))}
            <td className={styles.droite}>{nombre(somme(totaux))}</td>
          </tr>
        </tfoot>
      </table>
    </Cadre>
  )
}

export function LotsDeLaMatiere({ lots }: { lots: readonly LotSolde[] }) {
  const navigate = useNavigate()
  if (!lots.length) return <Vide>Aucun lot en stock.</Vide>
  return (
    <Cadre hauteur="fenetre">
      <table className={styles.tableSimple} aria-label="Lots de la matière">
        <thead>
          <tr>
            <th>Lot</th>
            <th>Entré le</th>
            <th>Magasins</th>
            <th className={styles.droite}>Reste (kg)</th>
            <th className={styles.droite}>Bobines</th>
          </tr>
        </thead>
        <tbody>
          {lots.map((x) => (
            <tr key={x.lot_id}>
              <td>
                <button
                  type="button"
                  className={styles.lien}
                  onClick={() => navigate(`/lots/${x.lot_id}?onglet=lots`)}
                >
                  {x.lot}
                </button>{' '}
                {x.statut !== 'disponible' ? <Badge famille="lot" valeur={x.statut} /> : null}
              </td>
              <td>{date(x.entre_le)}</td>
              <td>
                {x.magasins.map((g) => (
                  <span key={g.magasin_id} className={styles.nowrap}>
                    {estQuarantaine(g.type) ? <Badge ton="critique">{g.magasin}</Badge> : g.magasin}{' '}
                    {nombre(g.quantite, 1)}{' '}
                  </span>
                ))}
              </td>
              <td className={styles.droite}>
                <Kg v={x.quantite} kgParMl={x.kg_par_ml} />
              </td>
              <td className={styles.droite}>{x.bobines ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Cadre>
  )
}

export function SurLesMetiers({ fils }: { fils: readonly FilSurMetier[] }) {
  if (!fils.length) return <Vide>Rien de cette matière n’est monté sur les métiers.</Vide>
  return (
    <Cadre hauteur="fenetre">
      <table className={styles.tableSimple} aria-label="Sur les métiers">
        <thead>
          <tr>
            <th>Métier</th>
            <th className={styles.droite}>Étage</th>
            <th className={styles.droite}>Mètres</th>
            <th className={styles.droite}>Part</th>
            <th className={styles.droite}>Poids d’une bobine</th>
            <th className={styles.droite}>Sur le métier (kg)</th>
          </tr>
        </thead>
        <tbody>
          {fils.map((f) => (
            <tr key={`${f.metier}-${f.etage}`}>
              <td>{f.metier}</td>
              <td className={styles.droite}>{f.etage}</td>
              <td className={styles.droite}>{nombre(f.metres)}</td>
              <td className={styles.droite}>{part(f.pourcentage / 100, 0)}</td>
              <td className={styles.droite}>{poidsBobine(f.poids_bobine)}</td>
              <td className={styles.droite}>{kgEtMetres(f.poids)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Cadre>
  )
}
