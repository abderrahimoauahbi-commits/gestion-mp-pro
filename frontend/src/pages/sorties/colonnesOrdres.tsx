/**
 * Les colonnes de la liste des ordres : le n° (« Brouillon » tant qu'il n'est pas validé, et
 * « sera refusé » avec ses raisons), la date, ce qu'on tisse, le métier, le prévu par la recette,
 * le sorti net (« À sortir » sur l'onglet Brouillons, P2-4), l'écart, les retours, qui.
 */
import { LienDocument } from '../../composants/documents/LienDocument'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { date, nombre, VIDE } from '../../lib/format'
import { permis } from '../../lib/droits'
import type { Role } from '../../lib/types'
import { Double, Kg } from '../stock/cellules'
import styles from '../stock/stock.module.css'
import type { OrdreResume } from './donnees'
import { EcartRecette } from './ecart'

export const fabricationDe = (o: OrdreResume) =>
  o.qualites.length ? o.qualites.map((q) => `${q.qualite} · ${nombre(q.m2)} m²`).join(', ') : 'hors recette'

function Numero({ o }: { o: OrdreResume }) {
  return (
    <span className={styles.double}>
      <span className={styles.mono}>{o.numero ?? 'Brouillon'}</span>
      {o.blocages.length ? (
        <span className={styles.alerte} title={o.blocages.join(' · ')}>
          sera refusé
        </span>
      ) : null}
    </span>
  )
}

function Retours({ o, role }: { o: OrdreResume; role: Role }) {
  return (
    <span onClick={(e) => e.stopPropagation()}>
      {o.retours.map((r, i) => (
        <span key={`${r.numero}${i}`} className={styles.dessous}>
          {r.id != null && permis(role, `/operations/${r.id}`) ? (
            <LienDocument genre="operation" id={r.id} numero={r.numero} />
          ) : (
            r.numero || `retour repris de l’ERP Fil du ${date(r.date)}`
          )}
        </span>
      ))}
    </span>
  )
}

const sortiOuASortir = (o: OrdreResume) => (o.statut === 'brouillon' ? o.total : o.net)

const DEBUT: Colonne<OrdreResume>[] = [
  {
    cle: 'numero',
    titre: 'Ordre',
    valeur: (o) => o.numero ?? 'Brouillon',
    recherche: (o) => [
      o.commentaire,
      o.magasin,
      o.cree_par,
      o.valide_par,
      ...o.lots,
      ...o.matieres,
      ...o.qualites.map((q) => `${q.qualite} ${q.nom}`),
    ],
    rendu: (o) => <Numero o={o} />,
  },
  { cle: 'date', titre: 'Date', valeur: (o) => o.date, rendu: (o) => date(o.date) },
  {
    cle: 'fabrication',
    titre: 'Fabrication',
    valeur: fabricationDe,
    rendu: (o) => <Double haut={fabricationDe(o)} bas={o.commentaire} />,
  },
  { cle: 'metier', titre: 'Métier', valeur: (o) => o.metier },
  {
    cle: 'prevu',
    titre: 'Prévu par la recette (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    valeur: (o) => o.prevu || null,
    rendu: (o) => (o.prevu ? nombre(o.prevu, 1) : <span className={styles.nul}>{VIDE}</span>),
  },
]

const ECART: Colonne<OrdreResume> = {
  cle: 'ecart',
  titre: 'Écart',
  droite: true,
  valeur: (o) => o.ecart_relatif ?? null,
  rendu: (o) => <EcartRecette relatif={o.ecart_relatif} />,
}

const PAR: Colonne<OrdreResume> = { cle: 'par', titre: 'Par', valeur: (o) => o.valide_par || o.cree_par }

export function colonnesOrdres(brouillons: boolean, role: Role): Colonne<OrdreResume>[] {
  const net: Colonne<OrdreResume> = {
    cle: 'net',
    titre: brouillons ? 'À sortir (kg)' : 'Sorti net (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    valeur: sortiOuASortir,
    rendu: (o) => (
      <Double
        haut={<Kg v={sortiOuASortir(o)} />}
        bas={o.revenu ? `dont ${nombre(o.revenu, 1)} revenus` : undefined}
      />
    ),
  }
  const retours: Colonne<OrdreResume> = {
    cle: 'retours',
    titre: 'Retours',
    triable: false,
    valeur: (o) => o.retours.map((r) => r.numero).join(' '),
    rendu: (o) => <Retours o={o} role={role} />,
  }
  return [...DEBUT, net, ECART, retours, PAR]
}
