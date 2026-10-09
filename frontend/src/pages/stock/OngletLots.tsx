/**
 * Stock › Lots (`/stock?onglet=lots`) : chaque lot, ses soldes par magasin, son statut et son
 * histoire (entré, sorti net des retours, reste, ordres servis). Filtres liés dans l'adresse
 * (`?matiere=ID` pose la matière), case « Voir aussi les lots épuisés », cases à cocher pour les
 * étiquettes, export. Une ligne ouvre la fiche du lot (`/lots/:id`), « Suivre » sa traçabilité.
 */
import { useMemo, useState } from 'react'

import { BoutonImprimer } from '../../composants/documents/BoutonImprimer'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Bouton } from '../../composants/saisie/Bouton'
import { champsCherches } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import { passe, trouve, type Filtre } from '../../composants/tableaux/filtrage'
import { formule } from '../../lib/aide'
import { kg, nombre } from '../../lib/format'
import { colonnesLots } from './colonnesLots'
import type { Suivi } from './donnees'
import { useLots, useMagasins } from './donnees'
import styles from './stock.module.css'
import { POUSSIERE, type LotSolde } from './types'

/** Les filtres de l'onglet, sous des noms à lui (ceux de « Par matière » ne le filtrent pas) ; `matiere` : ECRANS-PRO. */
export const CLES_LOTS = [
  'fournisseur_lot',
  'matiere',
  'role_lot',
  'magasin_lot',
  'epuises',
  'quarantaine',
] as const

function filtresLots(lots: readonly LotSolde[]): Filtre<LotSolde>[] {
  const references = new Map(lots.map((l) => [String(l.matiere_id), l.reference]))
  return [
    { cle: 'fournisseur_lot', libelle: 'Fournisseur', valeur: (l) => l.fournisseur },
    {
      cle: 'matiere',
      libelle: 'Matière',
      valeur: (l) => String(l.matiere_id),
      libelleValeur: (v) => references.get(v) ?? `matière n° ${v}`,
    },
    { cle: 'role_lot', libelle: 'Rôle', valeur: (l) => l.role },
  ]
}

const passeCases = (l: LotSolde, magasin: string, quarantaine: boolean) =>
  (!magasin || l.magasins.some((g) => g.magasin === magasin)) && (!quarantaine || l.quarantaine > POUSSIERE)

/** Les lots, les filtres de l'adresse, les cases cochées. */
function useOngletLots(onSuivre: (s: Suivi) => void) {
  const table = useEtatTableAdresse(CLES_LOTS)
  const v = table.choix.valeurs
  const epuises = v.epuises === '1'
  const lots = useLots(epuises)
  const [coches, setCoches] = useState<ReadonlySet<number>>(new Set())
  const toutes = useMemo(
    () =>
      [...(lots.data ?? [])].sort(
        (a, b) =>
          a.reference.localeCompare(b.reference, 'fr', { numeric: true }) ||
          a.entre_le.localeCompare(b.entre_le),
      ),
    [lots.data],
  )
  const magasin = v.magasin_lot ?? ''
  const quarantaine = v.quarantaine === '1'
  const avant = useMemo(
    () => toutes.filter((l) => passeCases(l, magasin, quarantaine)),
    [toutes, magasin, quarantaine],
  )
  const filtres = useMemo(() => filtresLots(toutes), [toutes])
  const colonnes = colonnesLots({ coches, setCoches, onSuivre })
  const affiches = avant.filter(
    (l) => passe(l, filtres, v) && trouve(champsCherches(colonnes, l), table.recherche.valeur),
  )
  return { table, v, epuises, lots, coches, setCoches, toutes, avant, filtres, colonnes, affiches, magasin }
}

function IndicateursLots({ affiches }: { affiches: readonly LotSolde[] }) {
  const enQuarantaine = affiches.filter((l) => l.quarantaine > POUSSIERE)
  const ordres = new Set(affiches.flatMap((l) => l.historique.ordres.map((o) => o.id))).size
  return (
    <Indicateurs>
      <Kpi
        titre="Lots affichés"
        valeur={nombre(affiches.length)}
        detail={`${nombre(affiches.filter((l) => l.statut !== 'epuise').length)} en stock`}
        formule={formule('lots_affiches')}
      />
      <Kpi
        titre="Reste"
        valeur={kg(affiches.reduce((t, l) => t + l.quantite, 0))}
        detail="dans les lots affichés"
        formule={formule('reste_lot')}
      />
      <Kpi
        titre="En quarantaine"
        valeur={nombre(enQuarantaine.length)}
        detail={
          enQuarantaine.length
            ? `${kg(enQuarantaine.reduce((t, l) => t + l.quarantaine, 0))} à libérer ou rendre`
            : 'aucun lot bloqué'
        }
        ton={enQuarantaine.length ? 'attention' : 'ok'}
        lien="/stock?onglet=lots&quarantaine=1"
        formule={formule('quarantaine')}
      />
      <Kpi
        titre="Ordres servis"
        valeur={nombre(ordres)}
        detail="par les lots affichés"
        formule={formule('ordres_servis')}
      />
    </Indicateurs>
  )
}

function Actions({ o }: { o: ReturnType<typeof useOngletLots> }) {
  const magasins = useMagasins()
  const choisis = o.affiches.filter((l) => o.coches.has(l.lot_id)).map((l) => l.lot_id)
  const magasinId = magasins.data?.find((g) => g.code === o.magasin)?.id
  return (
    <>
      <label className={styles.case}>
        <input
          type="checkbox"
          checked={o.affiches.length > 0 && o.affiches.every((l) => o.coches.has(l.lot_id))}
          onChange={(e) =>
            o.setCoches(e.target.checked ? new Set(o.affiches.map((l) => l.lot_id)) : new Set())
          }
        />
        Cocher tous les lots affichés
      </label>
      {choisis.length ? (
        <BoutonImprimer
          route="/documents/etiquettes"
          parametres={{ lots: choisis.join(',') }}
          libelle={`Étiquettes (${choisis.length})`}
          titre="Les étiquettes QR des lots cochés, dans un nouvel onglet"
        />
      ) : (
        <Bouton taille="petit" manque={['cocher au moins un lot']}>
          Étiquettes (0)
        </Bouton>
      )}
      <ExportExcel
        route="/export/lots"
        parametres={{
          q: o.table.recherche.valeur.trim() || undefined,
          matiere: o.v.matiere,
          magasin: magasinId,
          non_nuls: o.epuises ? 'false' : undefined,
        }}
      />
    </>
  )
}

function Outils({ o }: { o: ReturnType<typeof useOngletLots> }) {
  const codes = [...new Set(o.toutes.flatMap((l) => l.magasins.map((g) => g.magasin)))].sort()
  return (
    <>
      <select
        aria-label="Magasin"
        className={styles.selecteur}
        value={o.magasin}
        onChange={(e) => o.table.choix.poser('magasin_lot', e.target.value || null)}
      >
        <option value="">Magasin : tous</option>
        {codes.map((m) => (
          <option key={m}>{m}</option>
        ))}
      </select>
      <label className={styles.case}>
        <input
          type="checkbox"
          checked={o.epuises}
          onChange={(e) => o.table.choix.poser('epuises', e.target.checked ? '1' : null)}
        />
        Voir aussi les lots épuisés
      </label>
    </>
  )
}

export function OngletLots({
  onOuvrir,
  onSuivre,
}: {
  onOuvrir: (id: number) => void
  onSuivre: (s: Suivi) => void
}) {
  const o = useOngletLots(onSuivre)
  if (o.lots.isPending) return <Chargement quoi="les lots" />
  if (o.lots.isError) return <Erreur erreur={o.lots.error} onReessayer={() => void o.lots.refetch()} />
  return (
    <>
      <IndicateursLots affiches={o.affiches} />
      <Carte titre="Lots" actions={<Actions o={o} />} serre remplir className={styles.carteListe}>
        <DataTable<LotSolde>
          libelle="Lots"
          lignes={o.avant}
          colonnes={o.colonnes}
          filtres={o.filtres}
          cle={(l) => l.lot_id}
          recherche={o.table.recherche}
          choix={o.table.choix}
          placeholder="Lot, matière, couleur, fournisseur, ordre… plusieurs mots affinent"
          cliquable={(l) => onOuvrir(l.lot_id)}
          vide={
            o.epuises
              ? 'Aucun lot : les lots naissent des réceptions et des stocks d’ouverture.'
              : 'Aucun lot en stock.'
          }
          outils={<Outils o={o} />}
        />
      </Carte>
    </>
  )
}
