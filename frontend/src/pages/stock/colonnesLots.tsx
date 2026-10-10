/**
 * Les colonnes de l'onglet « Lots » : la case des étiquettes, le lot et son statut, la référence,
 * le dernier mouvement, l'entré, le sorti (net des retours), le reste, les bobines, les magasins
 * (quarantaine en rouge), les ordres servis, « Suivre ».
 */
import type { Dispatch, SetStateAction } from 'react'

import { LienDocument } from '../../composants/documents/LienDocument'
import { Badge } from '../../composants/retour/Badge'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { date, nombre, VIDE } from '../../lib/format'
import { Double, Kg } from './cellules'
import type { Suivi } from './donnees'
import styles from './stock.module.css'
import { estQuarantaine, type LotSolde } from './types'

function Lot({ l }: { l: LotSolde }) {
  return (
    <span className={styles.nowrap}>
      <Double haut={l.lot} bas={`entré le ${date(l.entre_le)}`} mono />{' '}
      {l.statut !== 'disponible' ? <Badge famille="lot" valeur={l.statut} /> : null}
    </span>
  )
}

function Magasins({ l }: { l: LotSolde }) {
  return (
    <span className={styles.note}>
      {l.magasins.map((g) => (
        <span key={g.magasin_id} className={styles.dessous}>
          {estQuarantaine(g.type) ? <Badge ton="critique">{g.magasin}</Badge> : g.magasin}{' '}
          {nombre(g.quantite, 0, 2)}
        </span>
      ))}
    </span>
  )
}

function Ordres({ l }: { l: LotSolde }) {
  const o = l.historique.ordres
  if (!o.length) return <span className={styles.nul}>{VIDE}</span>
  if (o.length > 2)
    return (
      <span className={styles.note} title={o.map((x) => x.numero).join(' · ')}>
        {o.length} ordres
      </span>
    )
  return (
    <span className={styles.note} onClick={(e) => e.stopPropagation()}>
      {o.map((x, i) => (
        <span key={x.id}>
          {i ? ' · ' : ''}
          <LienDocument genre="ordre" id={x.id} numero={x.numero} />
        </span>
      ))}
    </span>
  )
}

const kgLot = (
  cle: string,
  titre: string,
  valeur: (l: LotSolde) => number,
  aide?: string,
): Colonne<LotSolde> => ({
  cle,
  titre,
  aide,
  droite: true,
  valeur,
  rendu: (l) => <Kg v={valeur(l)} kgParMl={l.kg_par_ml} />,
})

const COLONNES: Colonne<LotSolde>[] = [
  { cle: 'lot', titre: 'Lot', valeur: (l) => l.lot, rendu: (l) => <Lot l={l} /> },
  {
    cle: 'reference',
    titre: 'Référence',
    valeur: (l) => l.reference,
    recherche: (l) => [
      l.designation,
      l.fournisseur,
      l.role,
      ...l.historique.ordres.map((o) => o.numero),
      ...l.magasins.map((g) => g.magasin),
    ],
    rendu: (l) => (
      <span className={styles.ref} title={l.designation}>
        <Double haut={l.reference} bas={[l.role, l.fournisseur].filter(Boolean).join(' · ')} />
      </span>
    ),
  },
  {
    cle: 'dernier',
    titre: 'Dernier mouvement',
    valeur: (l) => l.historique.dernier_mouvement ?? '',
    rendu: (l) => date(l.historique.dernier_mouvement),
  },
  { cle: 'entre_le', titre: 'Entré le', valeur: (l) => l.entre_le, cache: true },
  kgLot('entre', 'Entré (kg)', (l) => l.historique.entre),
  kgLot('sorti', 'Sorti (kg)', (l) => l.historique.sorti, 'Net des retours des machines'),
  { ...kgLot('reste', 'Reste (kg)', (l) => l.quantite), unite: 'kg', total: true },
  { cle: 'bobines', titre: 'Bobines', droite: true, valeur: (l) => l.bobines ?? null },
  {
    cle: 'magasins',
    titre: 'Magasins',
    triable: false,
    valeur: (l) => l.magasins.map((g) => g.magasin).join(' '),
    rendu: (l) => <Magasins l={l} />,
  },
  {
    cle: 'ordres',
    titre: 'Ordres servis',
    valeur: (l) => l.historique.ordres.length,
    rendu: (l) => <Ordres l={l} />,
  },
]

export function colonnesLots({
  coches,
  setCoches,
  onSuivre,
}: {
  coches: ReadonlySet<number>
  setCoches: Dispatch<SetStateAction<ReadonlySet<number>>>
  onSuivre: (s: Suivi) => void
}): Colonne<LotSolde>[] {
  const basculer = (id: number, oui: boolean) =>
    setCoches((avant) => {
      const suite = new Set(avant)
      if (oui) suite.add(id)
      else suite.delete(id)
      return suite
    })
  const caseLot: Colonne<LotSolde> = {
    cle: 'case',
    titre: '',
    triable: false,
    exporte: false,
    largeur: 32,
    rendu: (l) => (
      <input
        type="checkbox"
        aria-label={`Étiquette du lot ${l.lot}`}
        checked={coches.has(l.lot_id)}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => basculer(l.lot_id, e.target.checked)}
      />
    ),
  }
  const suivre: Colonne<LotSolde> = {
    cle: 'suivre',
    titre: '',
    triable: false,
    exporte: false,
    rendu: (l) => (
      <span onClick={(e) => e.stopPropagation()}>
        <Bouton
          taille="petit"
          titre="D’où vient ce lot, quels ordres il a servis, et quand"
          onClick={() => onSuivre({ lot: l.lot_id })}
        >
          Suivre
        </Bouton>
      </span>
    ),
  }
  return [caseLot, ...COLONNES, suivre]
}
