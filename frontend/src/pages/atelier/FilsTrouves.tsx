/**
 * « Trouver un lot » regroupé par fil (demande de Mohamed, 14/10/2026) : l'homme de l'atelier
 * cherche un fil et voit d'un coup où il est — en stock (chaque lot, et ce qu'il porte dans chaque
 * magasin) et **à l'atelier**, monté sur les métiers (kilos par métier, `GET /metiers`). Un fil
 * qui n'est plus en magasin mais encore sur un métier apparaît aussi. Aucun prix.
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import { date, kgEtMetres } from '../../lib/format'
import { correspond, texteDe } from '../../lib/recherche'
import { bobinesApprochees } from '../../lib/unites'
import { qte } from './commun'
import styles from './atelier.module.css'
import type { LotSolde, MetierFiche } from './types'

/** Un fil monté sur un métier en service : ses kilos sur ce métier. */
interface SurMetier {
  metier: string
  kg: number
}

export interface FilTrouve {
  matiereId: number
  reference: string
  designation: string
  kgParMl: number
  lots: LotSolde[]
  stock: number
  atelier: SurMetier[]
  atelierKg: number
}

/** Les kilos montés par matière, métier par métier (seulement les métiers en service). */
function surLesMetiers(metiers: readonly MetierFiche[]) {
  const par = new Map<number, { reference: string; designation: string; kgParMl: number; sur: SurMetier[] }>()
  for (const m of metiers) {
    if (!m.actif || m.sur_les_metiers <= 0) continue
    for (const f of m.fils) {
      if (f.poids <= 0) continue
      const x = par.get(f.matiere_id) ?? {
        reference: f.reference,
        designation: f.designation,
        kgParMl: 0,
        sur: [],
      }
      const deja = x.sur.find((s) => s.metier === m.code)
      if (deja) deja.kg += f.poids
      else x.sur.push({ metier: m.code, kg: f.poids })
      par.set(f.matiere_id, x)
    }
  }
  return par
}

/**
 * Les fils trouvés : ceux des lots (dans l'ordre du serveur), puis ceux qui ne sont plus que sur
 * les métiers et que la recherche nomme.
 */
export function grouperParFil(
  lots: readonly LotSolde[],
  metiers: readonly MetierFiche[],
  q: string,
): FilTrouve[] {
  const montes = surLesMetiers(metiers)
  const fils = new Map<number, FilTrouve>()
  for (const l of lots) {
    const f = fils.get(l.matiere_id) ?? {
      matiereId: l.matiere_id,
      reference: l.reference,
      designation: l.designation,
      kgParMl: l.kg_par_ml,
      lots: [],
      stock: 0,
      atelier: montes.get(l.matiere_id)?.sur ?? [],
      atelierKg: 0,
    }
    f.lots.push(l)
    f.stock += l.quantite
    fils.set(l.matiere_id, f)
  }
  if (q.trim())
    for (const [id, m] of montes) {
      if (fils.has(id) || !correspond(texteDe([m.reference, m.designation]), q)) continue
      fils.set(id, {
        matiereId: id,
        reference: m.reference,
        designation: m.designation,
        kgParMl: 0,
        lots: [],
        stock: 0,
        atelier: m.sur,
        atelierKg: 0,
      })
    }
  return [...fils.values()].map((f) => ({ ...f, atelierKg: f.atelier.reduce((t, s) => t + s.kg, 0) }))
}

/** Un lot : son reste, et ce qu'il porte dans chaque magasin. */
export function CarteLot({ l, vers }: { l: LotSolde; vers: string }) {
  const magasins = l.magasins.filter((m) => m.quantite > 0.001)
  return (
    <Link to={vers} className={styles.carteLien}>
      <span className={styles.ligne}>
        <strong>lot {l.lot}</strong>
        <span className={styles.valeur}>{kgEtMetres(l.quantite, l.kg_par_ml, true)}</span>
      </span>
      <span className={styles.ligne}>
        <span className={styles.note}>entré le {date(l.entre_le)}</span>
        <span className={styles.note}>{bobinesApprochees(l.quantite, { poidsBobine: l.poids_bobine })}</span>
      </span>
      {magasins.map((m) => (
        <span key={m.magasin_id} className={styles.ligne}>
          <span>{m.magasin}</span>
          <span className={styles.valeur}>{qte(m.quantite)}</span>
        </span>
      ))}
      {l.quarantaine > 0.001 ? <Badge ton="critique">{`${qte(l.quarantaine)} en quarantaine`}</Badge> : null}
    </Link>
  )
}

/** L'en-tête d'un fil : en stock, à l'atelier (sur les métiers), puis ses lots. */
export function BlocFil({ f }: { f: FilTrouve }) {
  return (
    <section className={styles.blocFil} aria-label={f.reference}>
      <div className={styles.enteteFil}>
        <strong className={styles.titreFiche}>{f.reference}</strong>
        {f.designation ? <span className={styles.note}>{f.designation}</span> : null}
        <span className={styles.ligne}>
          <span>En stock</span>
          <span className={styles.valeur}>
            {f.lots.length ? kgEtMetres(f.stock, f.kgParMl, true) : 'aucun lot'}
          </span>
        </span>
        <span className={styles.ligne}>
          <span>À l’atelier (sur les métiers)</span>
          <span className={styles.valeur}>{f.atelierKg > 0.001 ? qte(f.atelierKg) : '—'}</span>
        </span>
        {f.atelier.length ? (
          <span className={styles.note}>
            {f.atelier.map((s) => `${s.metier} : ${qte(s.kg)}`).join(' · ')}
          </span>
        ) : null}
      </div>
      <ul className={styles.liste}>
        {f.lots.map((l) => (
          <li key={l.lot_id}>
            <CarteLot l={l} vers={`/atelier/lots/${l.lot_id}`} />
          </li>
        ))}
      </ul>
    </section>
  )
}
