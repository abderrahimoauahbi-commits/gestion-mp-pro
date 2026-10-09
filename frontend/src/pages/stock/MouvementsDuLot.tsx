/**
 * Le journal d'un lot dans sa fiche (le plus récent d'abord), et le lien du document d'un mouvement,
 * partagé avec l'onglet « Mouvements de stock » : un n° mène à sa fiche si le rôle peut l'ouvrir ;
 * un retour des machines que l'alimentation ne pourrait pas ouvrir mène à son ordre.
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import { Cadre } from '../../composants/tableaux/Cadre'
import { date } from '../../lib/format'
import { permis } from '../../lib/droits'
import { useSession } from '../../lib/session'
import type { Role } from '../../lib/types'
import { Signe } from './cellules'
import styles from './stock.module.css'
import type { LotFiche, MouvementLigne } from './types'

const BASES: Record<string, string> = {
  ordre: '/ordres',
  operation: '/operations',
  reception: '/receptions',
  inventaire: '/inventaires',
}

/** L'adresse du document d'un mouvement, si ce rôle peut l'ouvrir ; sinon `null`. */
export function lienMouvement(
  m: Pick<MouvementLigne, 'document' | 'document_id' | 'ordre_id'>,
  role: Role,
): string | null {
  const base = BASES[m.document]
  if (base && m.document_id != null) {
    const vers = `${base}/${m.document_id}`
    if (permis(role, vers)) return vers
  }
  return m.ordre_id != null && permis(role, `/ordres/${m.ordre_id}`) ? `/ordres/${m.ordre_id}` : null
}

export function NumeroDocument({ m }: { m: MouvementLigne }) {
  const { role } = useSession()
  const vers = lienMouvement(m, role)
  return (
    <span className={styles.mono}>
      {vers ? <Link to={vers}>{m.document_numero}</Link> : m.document_numero}
    </span>
  )
}

export function MouvementsDuLot({ l }: { l: LotFiche }) {
  const lignes = [...l.mouvements].reverse()
  return (
    <Cadre hauteur="fenetre">
      <table className={styles.tableSimple} aria-label="Mouvements du lot">
        <thead>
          <tr>
            <th>Date</th>
            <th>Mouvement</th>
            <th>Document</th>
            <th>Magasin</th>
            <th className={styles.droite}>Quantité (kg)</th>
            <th>Par</th>
          </tr>
        </thead>
        <tbody>
          {lignes.map((m) => (
            <tr key={m.id} title={m.commentaire || undefined}>
              <td className={styles.nowrap}>{date(m.date)}</td>
              <td>
                {m.libelle}
                {m.contrepasse_id ? (
                  <>
                    {' '}
                    <Badge ton="neutre">annulation</Badge>
                  </>
                ) : null}
                {m.motif ? <span className={styles.note}> · {m.motif}</span> : null}
              </td>
              <td>
                <NumeroDocument m={m} />
              </td>
              <td>{m.magasin}</td>
              <td className={styles.droite}>
                <Signe v={m.quantite} />
              </td>
              <td>{m.auteur}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Cadre>
  )
}
