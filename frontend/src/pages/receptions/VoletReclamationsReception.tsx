/**
 * Fiche réception › Réclamations (ECRANS-PRO 4.19) : celles ouvertes sur cette réception ; la
 * référence reste même sans lot (ligne refusée, anom. 4.17) ; une ligne ouvre la réclamation.
 */
import { Badge } from '../../composants/retour/Badge'
import type { Colonne } from '../../composants/tableaux/colonnes'
import styles from '../plan-achat/achats.module.css'
import { DataTable } from '../../composants/tableaux/DataTable'
import { date, nombre } from '../../lib/format'
import type { Schema } from '../../lib/types'
import { statut } from '../../lib/statuts'
import { useMotifs } from './donnees'
import type { ReceptionFiche } from './types'

type Reclamation = Schema<'ReclamationDeReception'>

function colonnes(motifs: ReadonlyMap<string, string>): Colonne<Reclamation>[] {
  return [
    { cle: 'numero', titre: 'N°' },
    { cle: 'ouverte_le', titre: 'Ouverte le', rendu: (x) => date(x.ouverte_le) },
    {
      cle: 'lot',
      titre: 'Lot · référence',
      valeur: (x) => [x.lot, x.reference].filter(Boolean).join(' · ') || 'toute la réception',
    },
    { cle: 'motif', titre: 'Motif', valeur: (x) => motifs.get(x.motif) ?? x.motif },
    { cle: 'quantite', titre: 'Quantité (kg)', droite: true, rendu: (x) => nombre(x.quantite) },
    {
      cle: 'issue',
      titre: 'Issue',
      valeur: (x) => (x.issue ? statut('issue_reclamation', x.issue).libelle : 'ouverte'),
      rendu: (x) =>
        x.issue ? (
          <Badge famille="issue_reclamation" valeur={x.issue} />
        ) : (
          <Badge ton="attention">ouverte</Badge>
        ),
    },
  ]
}

export function VoletReclamationsReception({
  r,
  onOuvrir,
}: {
  r: ReceptionFiche
  onOuvrir: (id: number) => void
}) {
  const motifs = useMotifs()
  const noms = new Map((motifs.data?.reclamation_motifs ?? []).map((m) => [m.code, m.libelle]))
  return (
    <div className={styles.tableFenetre}>
      <DataTable<Reclamation>
        libelle="Réclamations de la réception"
        lignes={r.reclamations}
        colonnes={colonnes(noms)}
        cle={(x) => x.id}
        recherche={false}
        hauteur="fenetre"
        cliquable={(x) => onOuvrir(x.id)}
        vide="Aucune réclamation sur cette réception."
      />
    </div>
  )
}
