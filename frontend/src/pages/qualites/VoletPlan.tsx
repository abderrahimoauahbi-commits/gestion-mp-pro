/**
 * Onglet « Plan de production » de la fiche qualité, **en lecture** : le plan se saisit dans la
 * page Production, toutes qualités ensemble (P7-33). Base mensuelle, total de l'année, les douze
 * coefficients, et les versions du plan (route 91).
 */
import { Link } from 'react-router'

import { Definitions } from '../../composants/mise-en-page/Definitions'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { horodatage, m2, nombre } from '../../lib/format'
import styles from '../catalogue/catalogue.module.css'
import { useVersionsPlan } from './donnees'
import type { QualiteFiche, VersionPlan } from './types'

const MOIS = [
  'janvier',
  'février',
  'mars',
  'avril',
  'mai',
  'juin',
  'juillet',
  'août',
  'septembre',
  'octobre',
  'novembre',
  'décembre',
]

/** Ce que la qualité pèse sur l'année : Σ base × coefficient du mois (0 si elle est arrêtée). */
export function surLAnnee(q: Pick<QualiteFiche, 'base_mensuelle' | 'saisonnalite' | 'actif'>): number {
  return q.actif ? q.saisonnalite.reduce((s, k) => s + q.base_mensuelle * k, 0) : 0
}

const COLONNES: Colonne<VersionPlan>[] = [
  {
    cle: 'valide_depuis',
    titre: 'Depuis',
    rendu: (v) => (
      <>
        {v.depuis_toujours ? 'toujours' : horodatage(v.valide_depuis)}
        {v.en_vigueur ? (
          <>
            {' '}
            <Badge ton="accent">en vigueur</Badge>
          </>
        ) : null}
      </>
    ),
  },
  { cle: 'base_mensuelle', titre: 'Base', droite: true, rendu: (v) => m2(v.base_mensuelle) },
  { cle: 'en_service', titre: 'État', valeur: (v) => (v.en_service ? 'en service' : 'arrêtée') },
  { cle: 'par', titre: 'Par', valeur: (v) => v.par?.nom ?? '—' },
  { cle: 'motif', titre: 'Motif', valeur: (v) => v.motif || v.origine },
]

export function VoletPlan({ q }: { q: QualiteFiche }) {
  const versions = useVersionsPlan(q.id)
  return (
    <div className={styles.volet}>
      <Note>
        Le plan de production (base mensuelle et saisonnalité) se saisit dans la page Production, toutes
        qualités ensemble.{' '}
        <Link className={styles.lien} to="/production?onglet=plan">
          Ouvrir le plan de production
        </Link>
      </Note>
      <Definitions
        colonnes={3}
        items={[
          ['Base mensuelle', `${m2(q.base_mensuelle)} par mois ordinaire (coefficient 1)`],
          [
            'Sur l’année',
            q.actif ? m2(surLAnnee(q)) : `${m2(0)} — qualité arrêtée : elle ne compte pas dans les besoins`,
          ],
          ...q.saisonnalite.map((k, i): [string, string] => [
            MOIS[i] ?? '',
            `${m2(q.base_mensuelle * k)} (× ${nombre(k, 2)})`,
          ]),
        ]}
      />
      <p className={styles.note}>
        m² prévus chaque mois ; la croissance annuelle réglée s’y ajoute pour les mois à venir.
      </p>
      {versions.isPending ? <Chargement quoi="les versions du plan" /> : null}
      {versions.isError ? (
        <Erreur erreur={versions.error} onReessayer={() => void versions.refetch()} />
      ) : null}
      {versions.data ? (
        <DataTable
          libelle="Versions du plan"
          lignes={versions.data}
          colonnes={COLONNES}
          cle={(v) => v.id}
          recherche={false}
          hauteur="fenetre"
        />
      ) : null}
    </div>
  )
}
