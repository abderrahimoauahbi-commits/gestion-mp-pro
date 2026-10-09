/**
 * Analyse › Prix payés (`/analyse?onglet=historique`) : chaque prix payé face au précédent de la
 * même matière chez le même fournisseur, dans la même devise ; le plus récent d'abord. Un clic sur
 * une ligne montre la courbe de cette matière ; le n° du bon mène à sa fiche. Recherche (`hq`) et
 * « seulement les hausses » (`hausses`) dans l'adresse.
 */
import { useMemo, useState } from 'react'

import { Carte } from '../../../composants/mise-en-page/Carte'
import { Badge } from '../../../composants/retour/Badge'
import { Chargement } from '../../../composants/retour/Chargement'
import { Erreur } from '../../../composants/retour/Erreur'
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { date, kg, nombre, partSignee, prixUnite, VIDE } from '../../../lib/format'
import { permis } from '../../../lib/droits'
import { useSession } from '../../../lib/session'
import type { Role } from '../../../lib/types'
import { useEtatListe } from '../../catalogue/etatListe'
import styles from '../analyse.module.css'
import { Case, Criteres, Deux } from '../briques'
import { useHistoriquePrix, useMatrice } from '../donnees'
import type { HistoriquePrix, PrixPaye } from '../types'
import { IndicateursPrix, Legende, MOUVEMENTS, mouvement, seuilsDe, type Seuils } from './commun'
import { Evolution, type MatiereComparee } from './Evolution'

type Achat = PrixPaye & { rang: number }

const MILIEU: readonly Colonne<Achat>[] = [
  {
    cle: 'reference',
    titre: 'Référence',
    recherche: (x) => [x.nature, x.designation, x.devise],
    rendu: (x) => (
      <Deux
        coupe
        haut={x.reference}
        titre={x.reference}
        bas={[x.nature, x.designation].filter(Boolean).join(' · ')}
      />
    ),
  },
  { cle: 'fournisseur', titre: 'Fournisseur' },
  {
    cle: 'quantite',
    titre: 'Quantité (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    rendu: (x) => kg(x.quantite),
  },
  {
    cle: 'prix_achat',
    titre: 'Prix payé',
    droite: true,
    rendu: (x) => prixUnite(x.prix_achat, x.devise, 'kg'),
  },
  {
    cle: 'prix_precedent',
    titre: 'Prix précédent',
    droite: true,
    rendu: (x) => (x.prix_precedent == null ? VIDE : prixUnite(x.prix_precedent, x.devise, 'kg')),
  },
]

function colonnes(seuils: Seuils, role: Role): Colonne<Achat>[] {
  const bon = (x: Achat) => (x.commande_id ? `/commandes/${x.commande_id}` : null)
  return [
    { cle: 'date_bc', titre: 'Date', rendu: (x) => date(x.date_bc) },
    {
      cle: 'numero_bc',
      titre: 'Bon',
      lien: (x) => {
        const a = bon(x)
        return a && permis(role, a) ? a : null
      },
      rendu: (x) => x.numero_bc || VIDE,
    },
    ...MILIEU,
    {
      cle: 'evolution',
      titre: 'Évolution',
      droite: true,
      rendu: (x) => (
        <Badge ton={MOUVEMENTS[mouvement(x.evolution, seuils)].ton}>
          {x.evolution == null ? '1er prix' : partSignee(x.evolution)}
        </Badge>
      ),
    },
    {
      cle: 'montant_mad',
      titre: 'Montant (MAD)',
      droite: true,
      unite: 'MAD',
      total: true,
      rendu: (x) => nombre(x.montant_mad),
    },
  ]
}

/** Les achats retenus : tous, ou seulement les hausses (au-delà du « stable »). */
function useAchats(h: HistoriquePrix | undefined, hausses: boolean): Achat[] {
  const stable = seuilsDe(h?.seuils).stable
  return useMemo(
    () =>
      (h?.lignes ?? [])
        .map((x, rang) => ({ ...x, rang }))
        .filter((x) => !hausses || (x.evolution ?? 0) > stable),
    [h, hausses, stable],
  )
}

export function PrixPayes() {
  const { role } = useSession()
  const lu = useHistoriquePrix()
  const m = useMatrice()
  const etat = useEtatListe('hq', ['hausses'])
  const hausses = etat.lire('hausses') === '1'
  const [aComparer, setAComparer] = useState<MatiereComparee[] | null>(null)
  const lignes = useAchats(lu.data, hausses)
  const forte = seuilsDe(lu.data?.seuils).forte
  const cols = useMemo(() => colonnes({ stable: 0.005, forte }, role), [forte, role])
  if (lu.isPending || m.isPending) return <Chargement quoi="les prix payés" />
  if (lu.isError || m.isError) {
    return (
      <Erreur
        erreur={lu.error ?? m.error}
        onReessayer={() => void Promise.all([lu.refetch(), m.refetch()])}
      />
    )
  }
  const criteres = (etat.recherche.valeur.trim() ? 1 : 0) + (hausses ? 1 : 0)
  return (
    <>
      <IndicateursPrix h={lu.data} m={m.data} />
      <Carte
        titre={`Historique des achats — ${nombre(lignes.length)} prix payé(s)`}
        sous={<Legende seuils={seuilsDe(lu.data.seuils)} />}
        actions={
          <span className={styles.note}>le plus récent d’abord · cliquer un achat la montre en courbe</span>
        }
        serre
        remplir
        className={styles.carteListe}
      >
        <DataTable<Achat>
          libelle="Prix payés"
          lignes={lignes}
          colonnes={cols}
          cle={(x) => x.rang}
          recherche={etat.recherche}
          placeholder="Référence, fournisseur, n° de bon… plusieurs mots"
          cliquable={(x) => setAComparer([{ reference: x.reference, matiere_id: x.matiere_id ?? null }])}
          vide="L’historique se remplira à la première réception validée."
          exporter={{ route: '/export/prix' }}
          outils={
            <>
              <Case valeur={hausses} onChange={(v) => etat.choix.poser('hausses', v ? '1' : null)}>
                seulement les hausses
              </Case>
              <Criteres nombre={criteres} onEffacer={etat.choix.effacer} />
            </>
          }
        />
      </Carte>
      {aComparer ? <Evolution matieres={aComparer} onFermer={() => setAComparer(null)} /> : null}
    </>
  )
}
