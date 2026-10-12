/**
 * Les deux tableaux de la fiche d'ordre : ses lots (sortis ou à sortir, chacun vers sa fiche) et,
 * matière par matière, le prévu par la recette face au sorti net.
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import { CadreAgrandissable } from '../../composants/tableaux/Cadre'
import { kgEtMetres, nombre, nombreSigne, VIDE } from '../../lib/format'
import styles from '../stock/stock.module.css'
import type { OrdreFiche, ParMatiere } from './donnees'
import { EcartRecette } from './ecart'

export function LotsDeLOrdre({ o }: { o: OrdreFiche }) {
  const brouillon = o.statut === 'brouillon'
  return (
    <CadreAgrandissable>
      <table className={styles.tableSimple} aria-label={brouillon ? 'Lots à sortir' : 'Lots sortis'}>
        <thead>
          <tr>
            <th>Référence</th>
            <th>Lot</th>
            <th className={styles.droite}>{brouillon ? 'À sortir (kg)' : 'Sorti (kg)'}</th>
          </tr>
        </thead>
        <tbody>
          {o.lignes.map((l) => (
            <tr key={l.id}>
              <td title={l.designation}>{l.reference}</td>
              <td className={styles.mono}>
                <Link to={`/lots/${l.lot_id}`}>{l.lot}</Link>
              </td>
              <td className={styles.droite}>{kgEtMetres(l.quantite, l.kg_par_ml)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </CadreAgrandissable>
  )
}

export interface TotauxPrevu {
  prevu: number
  net: number
  ecart: number | null
  ecart_relatif: number | null
}

/** Une matière : son nom, ou le lien qui la suit (traçabilité), et ses précisions. */
function NomMatiere({ f, onSuivre }: { f: ParMatiere; onSuivre?: (matiere: number) => void }) {
  const id = f.matiere_id
  return (
    <>
      {id && onSuivre ? (
        <button
          type="button"
          className={styles.lien}
          title="Suivre cette matière"
          onClick={() => onSuivre(id)}
        >
          {f.reference}
        </button>
      ) : (
        f.reference
      )}{' '}
      {f.hors_recette ? <Badge ton="attention">hors recette</Badge> : null}
      {!f.quantite ? <span className={styles.note}> · pas sorti</span> : null}
    </>
  )
}

/** Le prévu par la recette face au sorti net, matière par matière, et le total de l'ordre. */
export function TablePrevuSorti({
  lignes,
  totaux,
  onSuivre,
}: {
  lignes: readonly ParMatiere[]
  totaux: TotauxPrevu
  onSuivre?: (matiere: number) => void
}) {
  return (
    <CadreAgrandissable>
      <table className={styles.tableSimple} aria-label="Prévu par la recette et sorti net, par matière">
        <thead>
          <tr>
            <th>Référence</th>
            <th className={styles.droite}>Prévu par la recette (kg)</th>
            <th className={styles.droite}>Sorti net (kg)</th>
            <th className={styles.droite}>Écart (kg)</th>
            <th className={styles.droite}>Écart %</th>
          </tr>
        </thead>
        <tbody>
          {lignes.map((f) => (
            <tr key={f.reference}>
              <td>
                <NomMatiere f={f} onSuivre={onSuivre} />
              </td>
              <td className={styles.droite}>{f.prevu ? nombre(f.prevu, 0, 2) : VIDE}</td>
              <td className={styles.droite}>{nombre(f.quantite, 0, 2)}</td>
              <td className={styles.droite}>{f.ecart == null ? VIDE : nombreSigne(f.ecart, 0, 2)}</td>
              <td className={styles.droite}>
                <EcartRecette relatif={f.ecart != null && f.prevu ? f.ecart / f.prevu : null} />
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td>Total</td>
            <td className={styles.droite}>{nombre(totaux.prevu, 0, 2)}</td>
            <td className={styles.droite}>{nombre(totaux.net, 0, 2)}</td>
            <td className={styles.droite}>{totaux.ecart == null ? VIDE : nombreSigne(totaux.ecart, 0, 2)}</td>
            <td className={styles.droite}>
              <EcartRecette relatif={totaux.ecart_relatif} />
            </td>
          </tr>
        </tfoot>
      </table>
    </CadreAgrandissable>
  )
}

export function PrevuParMatiere({ o }: { o: OrdreFiche }) {
  return <TablePrevuSorti lignes={o.par_matiere} totaux={o} />
}
