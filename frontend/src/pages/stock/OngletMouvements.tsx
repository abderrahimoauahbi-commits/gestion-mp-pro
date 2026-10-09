/**
 * Stock › Mouvements de stock (`/stock?onglet=mouvements`) : le journal du stock, le plus récent
 * d'abord, par pages de 500 (« Charger les 500 suivants »). La recherche (sans accents, tous les
 * mots) et les filtres (type, magasin, du, au) partent au serveur, qui rend les types présents
 * compte tenu des autres filtres. Prix et valeur pour la direction et les achats seulement.
 */
import { useEffect, useState } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { Erreur } from '../../composants/retour/Erreur'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { date, horodatage, nombre, prixUnite, VIDE } from '../../lib/format'
import { Double, Signe } from './cellules'
import { useMagasins } from './donnees'
import { NumeroDocument } from './MouvementsDuLot'
import { Periode } from './Periode'
import styles from './stock.module.css'
import type { MouvementLigne } from './types'

/** Le libellé de chaque type de mouvement (celui du serveur, `services/tracabilite.LIBELLES`). */
export const TYPES_MOUVEMENT: Record<string, string> = {
  OUVERTURE: 'Stock d’ouverture',
  RECEPTION: 'Entrée de réception',
  SORTIE: 'Sortie vers les machines',
  RETOUR_MACHINE: 'Retour des machines',
  RETOUR_FOURNISSEUR: 'Retour au fournisseur',
  AJUSTEMENT: 'Ajustement d’inventaire',
  TRANSFERT: 'Transfert entre magasins',
}

/** Les types présents que rend la première page (`PageMouvements.types`), pour le filtre lié. */
function typesPresents(page: unknown): string[] {
  if (!page || typeof page !== 'object' || !('types' in page) || !Array.isArray(page.types)) return []
  return page.types.filter((t): t is string => typeof t === 'string')
}

/** Les filtres de l'onglet, sous des noms à lui (le magasin y est un identifiant). */
export const CLES_MOUVEMENTS = ['type', 'magasin_mvt', 'du', 'au'] as const

/** La valeur différée d'une saisie (la recherche part au serveur après 300 ms sans frappe). */
function useDiffere<T>(valeur: T, ms = 300): T {
  const [v, setV] = useState(valeur)
  useEffect(() => {
    const t = setTimeout(() => setV(valeur), ms)
    return () => clearTimeout(t)
  }, [valeur, ms])
  return v
}

const PRIX: Colonne<MouvementLigne>[] = [
  {
    cle: 'prix',
    titre: 'Prix',
    droite: true,
    triable: false,
    valeur: (m) => m.prix ?? null,
    rendu: (m) => (m.prix ? prixUnite(m.prix, m.devise, 'kg') : <span className={styles.nul}>{VIDE}</span>),
  },
  {
    cle: 'valeur',
    titre: 'Valeur MAD',
    droite: true,
    triable: false,
    valeur: (m) => m.valeur_mad ?? null,
    rendu: (m) => (
      <span title={m.cout_mad ? `coût unitaire ${prixUnite(m.cout_mad, 'MAD', 'kg')}` : undefined}>
        {nombre(m.valeur_mad)}
      </span>
    ),
  },
]

function Type({ m }: { m: MouvementLigne }) {
  return (
    <>
      {m.libelle}
      {m.contrepasse_id ? (
        <>
          {' '}
          <Badge ton="neutre">annulation</Badge>
        </>
      ) : null}
    </>
  )
}

const AVANT: Colonne<MouvementLigne>[] = [
  {
    cle: 'date',
    titre: 'Date',
    triable: false,
    valeur: (m) => m.date,
    rendu: (m) => <Double haut={date(m.date)} bas={`saisi ${horodatage(m.saisi_le)}`} />,
  },
  { cle: 'type', titre: 'Type', triable: false, valeur: (m) => m.libelle, rendu: (m) => <Type m={m} /> },
  {
    cle: 'document',
    titre: 'Document',
    triable: false,
    valeur: (m) => m.document_numero,
    rendu: (m) => <NumeroDocument m={m} />,
  },
  { cle: 'reference', titre: 'Référence', triable: false, valeur: (m) => m.reference },
]

const APRES: Colonne<MouvementLigne>[] = [
  {
    cle: 'motif',
    titre: 'Motif',
    triable: false,
    valeur: (m) => m.motif,
    rendu: (m) => <Double haut={m.motif || ''} bas={m.commentaire} />,
  },
  { cle: 'auteur', titre: 'Par', triable: false, valeur: (m) => m.auteur },
]

function colonneLot(onOuvrirLot: (id: number) => void): Colonne<MouvementLigne> {
  return {
    cle: 'lot',
    titre: 'Lot · magasin',
    triable: false,
    valeur: (m) => m.lot,
    rendu: (m) => (
      <span className={styles.nowrap}>
        <button
          type="button"
          className={styles.lien}
          title="La fiche du lot"
          onClick={(e) => {
            e.stopPropagation()
            onOuvrirLot(m.lot_id)
          }}
        >
          {m.lot}
        </button>
        <span className={styles.dessous}>{m.magasin}</span>
      </span>
    ),
  }
}

const QUANTITE: Colonne<MouvementLigne> = {
  cle: 'quantite',
  titre: 'Quantité (kg)',
  droite: true,
  triable: false,
  valeur: (m) => m.quantite,
  rendu: (m) => <Signe v={m.quantite} />,
}

export function colonnesMouvements(voitPrix: boolean, onOuvrirLot: (id: number) => void) {
  return [...AVANT, colonneLot(onOuvrirLot), QUANTITE, ...(voitPrix ? PRIX : []), ...APRES]
}

/** La liste paginée, ses filtres envoyés au serveur, et les filtres liés qu'il rend. */
function useMouvements(voitPrix: boolean) {
  const table = useEtatTableAdresse(CLES_MOUVEMENTS)
  const v = table.choix.valeurs
  const q = useDiffere(table.recherche.valeur.trim())
  const magasins = useMagasins()
  const serveur = { q: q || undefined, type: v.type, magasin: v.magasin_mvt, du: v.du, au: v.au }
  const parametres = { ...serveur, avec_valeur: voitPrix || undefined }
  const liste = useListePaginee<MouvementLigne>('/mouvements', parametres)
  const codes = new Map((magasins.data ?? []).map((g) => [String(g.id), g.code]))
  const filtres: Filtre<MouvementLigne>[] = [
    {
      cle: 'type',
      libelle: 'Type',
      valeur: (m) => m.type,
      options: typesPresents(liste.requete.data?.pages[0]),
      libelleValeur: (t) => TYPES_MOUVEMENT[t] ?? t,
    },
    {
      cle: 'magasin_mvt',
      libelle: 'Magasin',
      valeur: (m) => String(m.magasin_id),
      options: [...codes.keys()],
      libelleValeur: (id) => codes.get(id) ?? id,
    },
  ]
  return { table, liste, filtres, parametres }
}

export function OngletMouvements({
  voitPrix,
  onOuvrirLot,
}: {
  voitPrix: boolean
  onOuvrirLot: (id: number) => void
}) {
  const { table, liste, filtres, parametres } = useMouvements(voitPrix)
  const charges = liste.lignes.length
  const encore = liste.total > charges
  return (
    <Carte
      titre="Mouvements de stock"
      sous={`${nombre(charges)} mouvement(s) affiché(s)${encore ? ', d’autres plus anciens suivent' : ''} — le plus récent d’abord.${voitPrix ? ' La valeur est au coût moyen du moment (une entrée d’achat, à son coût).' : ''} Le document s’ouvre d’un clic.`}
      actions={<ExportExcel route="/export/mouvements" parametres={parametres} />}
      serre
      remplir
      className={styles.carteListe}
    >
      {liste.requete.isError ? (
        <Erreur erreur={liste.requete.error} onReessayer={() => void liste.requete.refetch()} />
      ) : null}
      <DataTable<MouvementLigne>
        libelle="Mouvements de stock"
        lignes={liste.lignes}
        colonnes={colonnesMouvements(voitPrix, onOuvrirLot)}
        filtres={filtres}
        serveur
        total={liste.total}
        chargerPlus={liste.chargerPlus}
        cle={(m) => m.id}
        recherche={table.recherche}
        choix={table.choix}
        placeholder="Référence, lot, n° de document, motif, personne…"
        vide={
          liste.requete.isPending
            ? 'Un instant — chargement : les mouvements…'
            : 'Aucun mouvement ne correspond.'
        }
        outils={<Periode choix={table.choix} />}
      />
    </Carte>
  )
}
