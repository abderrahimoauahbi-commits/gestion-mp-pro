/**
 * Cockpit › Vue d'ensemble (`/cockpit?onglet=ensemble`) : les matières par statut (une barre par
 * statut, qui ouvre le Stock filtré), le classement, le stock dormant ; le budget à commander par
 * devise (l'exposition au change), le coût matière, la rotation, le cycle de trésorerie. Tous les
 * chiffres sont ceux du Cockpit reçu.
 */
import { Link } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Cadre } from '../../composants/tableaux/Cadre'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { jours, montant, nombre, part } from '../../lib/format'
import { useSession } from '../../lib/session'
import type { Schema } from '../../lib/types'
import { siPermis } from '../accueil/taches'
import type { Cockpit } from '../accueil/types'
import styles from './cockpit.module.css'

type Exposition = Schema<'ExpositionDevise'>

/** Les six statuts dans l'ordre de l'urgence, leur compte reçu, leur filtre du Stock. */
export function repartition(c: Cockpit) {
  const s = c.stock
  return [
    { cle: 'RUPTURE', libelle: 'RUPTURE', n: s.ruptures, ton: 'rupture' },
    { cle: 'CRITIQUE', libelle: 'CRITIQUE', n: s.critiques, ton: 'critique' },
    { cle: 'URGENT', libelle: 'URGENT', n: s.urgents, ton: 'urgent' },
    { cle: 'ATTENTION', libelle: 'ATTENTION', n: s.attentions, ton: 'attention' },
    { cle: 'OK', libelle: 'OK', n: s.ok, ton: 'ok' },
    { cle: 'NON_CONSOMMEE', libelle: 'Sans consommation', n: s.sans_consommation, ton: 'neutre' },
  ] as const
}

function Repartition({ cockpit }: { cockpit: Cockpit }) {
  const { role } = useSession()
  const lignes = repartition(cockpit)
  const max = Math.max(1, ...lignes.map((l) => l.n))
  return (
    <ul className={styles.barres} aria-label="Les matières par statut">
      {lignes.map((l) => {
        const vers = siPermis(role, `/stock?statut=${l.cle}`)
        const contenu = (
          <>
            <span className={styles.libelleBarre}>{l.libelle}</span>
            <span className={styles.piste}>
              <span
                className={`${styles.barre} ${styles[l.ton]}`}
                style={{ width: `${(l.n / max) * 100}%` }}
              />
            </span>
            <span className={styles.valeurBarre}>{nombre(l.n)}</span>
          </>
        )
        return (
          <li key={l.cle}>
            {vers ? (
              <Link
                to={vers}
                className={styles.ligneBarre}
                title={`${nombre(l.n)} matière(s) : ouvrir le Stock filtré`}
              >
                {contenu}
              </Link>
            ) : (
              <span className={styles.ligneBarre}>{contenu}</span>
            )}
          </li>
        )
      })}
    </ul>
  )
}

const COLONNES: Colonne<Exposition>[] = [
  { cle: 'devise', titre: 'Devise' },
  { cle: 'references', titre: 'Matières', droite: true, total: true },
  {
    cle: 'montant_mad',
    titre: 'Montant MAD',
    droite: true,
    unite: 'MAD',
    total: true,
    rendu: (x) => montant(x.montant_mad, 'MAD'),
  },
  { cle: 'part', titre: 'Part', droite: true, rendu: (x) => part(x.part) },
]

/** Le classement, les sources, le stock dormant. */
function lignesStock(c: Cockpit): [string, string][] {
  const { abc, sourcing, dormant } = c
  return [
    [
      'Classement',
      `${nombre(abc.A ?? 0)} matière(s) en A (l’essentiel de la dépense), ${nombre(abc.B ?? 0)} en B, ${nombre(abc.C ?? 0)} en C.`,
    ],
    [
      'Sources',
      `${nombre(sourcing.mono_source ?? 0)} matière(s) n’ont qu’un seul fournisseur possible ; ${nombre(sourcing.multi_source ?? 0)} en ont plusieurs.`,
    ],
    [
      'Stock dormant',
      `Ni sortie ni entrée depuis ${nombre(dormant.seuil_jours)} jours : ${nombre(dormant.nb_references)} matière(s), ${montant(dormant.valeur_mad, 'MAD')} immobilisés, soit ${part(dormant.part_valeur)} de la valeur du stock.`,
    ],
  ]
}

/** Le coût matière, la rotation, le cycle de trésorerie, les fournisseurs. */
function lignesFinance(c: Cockpit): [string, string][] {
  const f = c.finance
  const base =
    f.base_rotation === 'consommation'
      ? `${montant(f.cout_rotation_annuel_mad, 'MAD')} consommés sur les douze derniers mois, au coût moyen, face au stock au coût moyen`
      : 'pas encore de consommation : le plan au prix du catalogue, face au stock au catalogue'
  return [
    [
      'Coût matière',
      `${montant(f.cout_matiere_annuel_mad, 'MAD')} par an, ${montant(f.cout_matiere_mensuel_mad, 'MAD')} par mois, au plan de production.`,
    ],
    [
      'Rotation',
      `${nombre(f.rotation_stock, 2)} fois par an — le stock représente ${jours(f.dio_jours)} de consommation (${base}).`,
    ],
    [
      'Cycle de trésorerie',
      `${jours(f.ccc_jours)} = stock ${jours(f.dio_jours)} + clients ${jours(f.dso_jours)} − fournisseurs ${jours(f.dpo_jours)} (délai de paiement moyen, pondéré par les montants reçus sur douze mois).`,
    ],
    ['Fournisseurs', `${nombre(c.achats.fournisseurs_actifs)} fournisseur(s) en service.`],
  ]
}

/** Des phrases courtes, chacune avec son sujet en gras (comme Gestion MP). */
function Lignes({ lignes }: { lignes: readonly [string, string][] }) {
  return (
    <ul className={styles.phrases}>
      {lignes.map(([sujet, texte]) => (
        <li key={sujet}>
          <strong>{sujet}</strong> : {texte}
        </li>
      ))}
    </ul>
  )
}

export function OngletEnsemble({ cockpit }: { cockpit: Cockpit }) {
  const { role } = useSession()
  const plan = siPermis(role, '/plan-achat')
  return (
    <div className={styles.deux}>
      <Carte titre="Les matières par statut" actions={<Link to="/stock">Stock →</Link>}>
        <Cadre>
          <Repartition cockpit={cockpit} />
          <Lignes lignes={lignesStock(cockpit)} />
        </Cadre>
      </Carte>
      <Carte
        titre="Le budget à commander, par devise"
        actions={plan ? <Link to={plan}>Plan d’achat →</Link> : null}
      >
        <DataTable
          lignes={cockpit.devises}
          colonnes={COLONNES}
          cle={(x) => x.devise}
          recherche={false}
          hauteur="court"
          libelle="Le budget à commander, par devise"
          vide="Rien à commander."
        />
        <Cadre>
          <Lignes lignes={lignesFinance(cockpit)} />
        </Cadre>
      </Carte>
    </div>
  )
}
