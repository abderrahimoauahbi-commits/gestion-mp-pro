/**
 * Cockpit › Opportunités d'économies (`/cockpit?onglet=economies`) : les cinq plus fortes, au coût
 * rendu usine, telles que le Cockpit les reçoit ; une ligne ouvre la fiche matière.
 */
import { Link, useNavigate } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { Note } from '../../composants/retour/Note'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { date, montant, nombre, part, prix } from '../../lib/format'
import { useSession } from '../../lib/session'
import type { Schema } from '../../lib/types'
import { siPermis } from '../accueil/taches'
import type { Cockpit } from '../accueil/types'
import { Double } from '../stock/cellules'

type Opportunite = Schema<'OpportuniteLigne'>

const base = (b: string, jour: string | null) => (jour ? `${b} du ${date(jour)}` : 'catalogue, non daté')

const COLONNES: Colonne<Opportunite>[] = [
  {
    cle: 'reference',
    titre: 'Référence · fournisseur',
    rendu: (o) => <Double haut={o.reference} bas={o.fournisseur_actuel} />,
    recherche: (o) => [o.fournisseur_actuel],
  },
  {
    cle: 'composition',
    titre: 'Composition',
    aide: 'Composition · type · titrage',
    valeur: (o) =>
      [o.composition || o.nature, o.type_fil, o.titrage].filter((v) => v != null && v !== '').join(' · '),
  },
  {
    cle: 'prix_actuel_mad',
    titre: 'Prix (MAD/kg)',
    aide: 'Prix actuel au kilo, coût rendu usine',
    droite: true,
    rendu: (o) => <Double haut={prix(o.prix_actuel_mad)} bas={base(o.base_prix, o.date_prix)} />,
  },
  {
    cle: 'reference_alternative',
    titre: 'Comparable · chez',
    aide: 'Comparable moins cher, et son fournisseur',
    rendu: (o) => <Double haut={o.reference_alternative || '—'} bas={o.fournisseur_alternatif} />,
  },
  {
    cle: 'prix_minimum_mad',
    titre: 'Son prix',
    aide: 'Prix du comparable (MAD/kg), coût rendu usine',
    droite: true,
    rendu: (o) => (
      <Double haut={prix(o.prix_minimum_mad)} bas={base(o.base_prix_minimum, o.date_prix_minimum)} />
    ),
  },
  {
    cle: 'ecart',
    titre: 'Écart',
    droite: true,
    rendu: (o) => <Badge ton="attention">−{part(o.ecart)}</Badge>,
  },
  { cle: 'conso_annuelle', titre: 'Conso/an (kg)', droite: true, rendu: (o) => nombre(o.conso_annuelle) },
  {
    cle: 'economie_mad',
    titre: 'Économie/an',
    droite: true,
    unite: 'MAD',
    total: true,
    rendu: (o) => <strong>{montant(o.economie_mad, 'MAD')}</strong>,
  },
]

export function OngletEconomies({ cockpit }: { cockpit: Cockpit }) {
  const { role } = useSession()
  const navigate = useNavigate()
  const e = cockpit.economies
  const toutes = siPermis(role, '/analyse?onglet=opportunites')
  return (
    <Carte
      titre={`Les plus fortes opportunités d’économies — ${nombre(e.nb_opportunites)} au total, ${montant(e.total_mad, 'MAD')} par an`}
      actions={toutes ? <Link to={toutes}>Toutes les opportunités →</Link> : null}
      remplir
    >
      <Note uneLigne="Un fil de même composition, même type et même titrage s’achète moins cher ailleurs, à la même époque, au coût rendu usine (droits, fret, transit compris quand le dossier d’importation est saisi). C’est une opportunité à négocier, pas une décision : la qualité réelle et la disponibilité ne se lisent pas ici. Économie / an = (prix − comparable) × consommation annuelle.">
        Un fil de même composition, même type et même titrage s’achète moins cher ailleurs, au coût rendu
        usine : une opportunité à négocier, pas une décision.
      </Note>
      <DataTable
        lignes={e.top}
        colonnes={COLONNES}
        cle={(o) => `${o.reference}-${o.reference_alternative}`}
        recherche={false}
        cliquable={(o) => {
          const vers = o.matiere_id != null ? siPermis(role, `/stock/matieres/${o.matiere_id}`) : null
          if (vers) navigate(vers)
        }}
        libelle="Opportunités d’économies"
        vide="Aucune opportunité d’économie détectée."
      />
    </Carte>
  )
}
