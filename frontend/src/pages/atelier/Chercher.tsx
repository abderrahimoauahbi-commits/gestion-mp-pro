/**
 * Trouver un lot (`/atelier/chercher`) : la recherche part 250 ms après la frappe, au serveur,
 * sans accents (chaque mot dans la référence, la désignation, le n° de lot, le rôle, le magasin,
 * le fournisseur) ; ou la caméra lit le QR de l'étiquette (`ScanQR`) et ouvre la fiche du lot.
 * 50 lots, puis « charger les suivants » (an. 18) ; une coupure dit « Pas de réseau » (an. 3).
 */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { ScanQR } from '../../composants/atelier/ScanQR'
import { Badge } from '../../composants/retour/Badge'
import { Vide } from '../../composants/retour/Vide'
import { Recherche } from '../../composants/tableaux/Recherche'
import { date, kgEtMetres } from '../../lib/format'
import { useRechercheAdresse } from '../../lib/adresse'
import { useLecture } from '../../lib/requetes'
import { bobinesApprochees } from '../../lib/unites'
import { attente } from './briques'
import { qte, useDiffere } from './commun'
import styles from './atelier.module.css'
import { ChargerSuivants, PAGE_ATELIER } from './Ordres'
import type { LotSolde } from './types'

export function CarteLot({ l, vers }: { l: LotSolde; vers: string }) {
  return (
    <Link to={vers} className={styles.carteLien}>
      <span className={styles.ligne}>
        <strong>{l.reference}</strong>
        <span className={styles.valeur}>{kgEtMetres(l.quantite, l.kg_par_ml, true)}</span>
      </span>
      <span className={styles.ligne}>
        <span className={styles.note}>
          lot {l.lot} · entré le {date(l.entre_le)}
        </span>
        <span className={styles.note}>Reste</span>
      </span>
      <span className={styles.ligne}>
        <span className={styles.note}>{l.magasins.map((m) => m.magasin).join(', ')}</span>
        <span className={styles.note}>{bobinesApprochees(l.quantite, { poidsBobine: l.poids_bobine })}</span>
      </span>
      {l.quarantaine > 0.001 ? <Badge ton="critique">{`${qte(l.quarantaine)} en quarantaine`}</Badge> : null}
    </Link>
  )
}

export default function Chercher() {
  const naviguer = useNavigate()
  const [q, setQ] = useRechercheAdresse()
  const mots = useDiffere(q.trim())
  const [nb, setNb] = useState(PAGE_ATELIER)
  const lots = useLecture<LotSolde[]>('/lots', { q: mots, non_nuls: true })
  const liste = (lots.data ?? []).filter((l) => l.quantite > 0.001)
  return (
    <EcranAtelier titre="Trouver un lot" retour="/atelier">
      <div className={styles.pile}>
        <Recherche
          valeur={q}
          onChange={(v) => {
            setQ(v)
            setNb(PAGE_ATELIER)
          }}
          placeholder="Référence, couleur, numéro de lot…"
          libelle="Chercher un lot"
        />
        <ScanQR onLot={(id) => void naviguer(`/atelier/lots/${id}`)} />
        {attente([lots], 'les lots') ?? (
          <>
            {!liste.length ? <Vide>Aucun lot en stock ne correspond.</Vide> : null}
            <ul className={styles.liste}>
              {liste.slice(0, nb).map((l) => (
                <li key={l.lot_id}>
                  <CarteLot l={l} vers={`/atelier/lots/${l.lot_id}`} />
                </li>
              ))}
            </ul>
            <ChargerSuivants
              montres={Math.min(nb, liste.length)}
              total={liste.length}
              onCharger={() => setNb(nb + PAGE_ATELIER)}
            />
          </>
        )}
      </div>
    </EcranAtelier>
  )
}
