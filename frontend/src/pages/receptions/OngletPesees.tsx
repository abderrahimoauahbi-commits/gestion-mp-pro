/**
 * Réceptions › Archive des pesées (ECRANS-PRO 4.27) : chaque ligne reçue, lot par lot, la plus
 * récente d'abord ; la recherche et les filtres partent au serveur (liste paginée, « Charger les
 * 500 suivants »), les indicateurs comptent **toutes** les lignes filtrées. « Annoncé BL (kg) » est
 * le BL seul ; l'écart dit à quoi il se compare (anom. 4.11).
 */
import { Link } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import type { EtatTable } from '../../composants/tableaux/etatAdresse'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { formule } from '../../lib/aide'
import { date, kg, nombre, part, partSignee, VIDE } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { statut } from '../../lib/statuts'
import styles from '../plan-achat/achats.module.css'
import { deux } from '../plan-achat/colonnesFournisseurs'
import { useDiffere } from './differe'
import { useFournisseursActifs, useMagasins } from './donnees'
import type { PagePesees, Pesee } from './types'

export const CLES_FILTRES_PESEES = ['fournisseur', 'qualite', 'magasin', 'ecarts'] as const

function lien(to: string, texte: string) {
  return (
    <Link to={to} onClick={(e) => e.stopPropagation()}>
      {texte}
    </Link>
  )
}

function Bobines({ p }: { p: Pesee }) {
  return (
    <>
      {nombre(p.nb_bobines)}
      {p.nb_palettes ? ` (${nombre(p.nb_palettes, 0, 3)} pal.)` : ''}
      {p.poids_moyen_bobine == null ? null : (
        <span className={styles.dessous}>
          <Badge
            ton={p.bobine_hors_tolerance ? 'attention' : 'ok'}
          >{`${nombre(p.poids_moyen_bobine, 2)} kg`}</Badge>
          {p.poids_bobine_catalogue
            ? ` cat. ${nombre(p.poids_bobine_catalogue, 2)} (${partSignee(p.ecart_bobine)})`
            : ''}
        </span>
      )}
    </>
  )
}

const COLONNES: Colonne<Pesee>[] = [
  {
    cle: 'numero',
    titre: 'Réception',
    rendu: (p) =>
      deux(
        <span className={styles.sansCoupure}>
          {lien(
            `/receptions/${p.reception_id}`,
            p.statut_reception === 'brouillon' || !p.numero ? 'Brouillon' : p.numero,
          )}
        </span>,
        p.statut_reception !== 'validee'
          ? `${date(p.date)} · ${statut('document', p.statut_reception).libelle}`
          : date(p.date),
      ),
  },
  {
    cle: 'reference',
    titre: 'Référence',
    rendu: (p) =>
      deux(
        <span className={styles.ref}>{p.reference}</span>,
        p.commande_id ? lien(`/commandes/${p.commande_id}`, `bon ${p.numero_bc}`) : 'hors commande',
      ),
  },
  {
    cle: 'lot',
    titre: 'Lot · magasin',
    rendu: (p) => deux(p.lot_id ? lien(`/lots/${p.lot_id}`, p.lot) : p.lot || VIDE, p.magasin || null),
    recherche: (p) => [p.magasin],
  },
  { cle: 'fournisseur', titre: 'Fournisseur' },
  {
    cle: 'quantite_bl',
    titre: 'Annoncé BL (kg)',
    aide: 'Le bon de livraison seul (« — » sans BL)',
    droite: true,
    rendu: (p) => (p.quantite_bl ? nombre(p.quantite_bl) : VIDE),
  },
  { cle: 'quantite_pesee', titre: 'Pesé (kg)', droite: true, rendu: (p) => nombre(p.quantite_pesee) },
  {
    cle: 'ecart',
    titre: 'Écart',
    droite: true,
    rendu: (p) =>
      p.ecart_relatif == null || p.ecart == null
        ? VIDE
        : deux(
            <Badge ton={p.hors_tolerance ? 'critique' : 'ok'}>{partSignee(p.ecart_relatif)}</Badge>,
            `${p.ecart > 0 ? '+' : ''}${nombre(p.ecart, 0, 2)} kg${p.compare_au === 'reste' ? ' vs reste à livrer' : ''}`,
          ),
  },
  {
    cle: 'nb_bobines',
    titre: 'Bobines',
    aide: 'Les bobines comptées (et les palettes), puis le poids moyen d’une bobine face au catalogue',
    droite: true,
    rendu: (p) => (p.nb_bobines ? <Bobines p={p} /> : VIDE),
  },
  {
    cle: 'qualite',
    titre: 'Qualité',
    rendu: (p) => deux(<Badge famille="qualite_reception" valeur={p.qualite} />, p.observations || null),
  },
]

function IndicateursPesees({ i }: { i: PagePesees | undefined }) {
  return (
    <Indicateurs libelle="Indicateurs des pesées">
      <Kpi
        titre="Lignes pesées"
        valeur={i ? nombre(i.total) : VIDE}
        formule={formule('pesees_lignes')}
        detail={i ? `${kg(i.kg_pesees)} pesés` : undefined}
      />
      <Kpi
        titre="Écarts de pesée"
        valeur={i ? nombre(i.hors_tolerance) : VIDE}
        formule={formule('pesees_ecarts')}
        ton={i?.hors_tolerance ? 'critique' : 'ok'}
        detail={`au-delà de ±${part(i?.tolerance ?? 0.02, 0)} de l’annonce`}
      />
      <Kpi
        titre="Lignes non conformes"
        valeur={i ? nombre(i.non_conformes) : VIDE}
        formule={formule('pesees_non_conformes')}
        ton={i?.non_conformes ? 'attention' : 'ok'}
        detail="sous réserve ou refusées"
      />
      <Kpi
        titre="Bobines hors catalogue"
        valeur={i ? nombre(i.bobines_hors_tolerance) : VIDE}
        formule={formule('bobines_hors_catalogue')}
        ton={i?.bobines_hors_tolerance ? 'attention' : 'ok'}
        detail={`kg / bobine à ±${part(i?.tolerance_bobine ?? 0.05, 0)} et plus`}
      />
    </Indicateurs>
  )
}

/** Les filtres de l'archive : leurs options sont fixées (la liste est paginée au serveur). */
function filtresPesees(
  noms: ReadonlyMap<string, string>,
  codes: ReadonlyMap<string, string>,
): Filtre<Pesee>[] {
  return [
    {
      cle: 'fournisseur',
      libelle: 'Fournisseur',
      valeur: (p) => String(p.fournisseur_id),
      options: [...noms.keys()],
      libelleValeur: (v) => noms.get(v) ?? v,
    },
    {
      cle: 'qualite',
      libelle: 'Qualité',
      valeur: (p) => p.qualite,
      options: ['conforme', 'reserve', 'refuse'],
      libelleValeur: (v) => statut('qualite_reception', v).libelle,
    },
    {
      cle: 'magasin',
      libelle: 'Magasin',
      valeur: () => '',
      options: [...codes.keys()],
      libelleValeur: (v) => codes.get(v) ?? v,
    },
  ]
}

const VIDE_PESEES =
  'Aucune pesée ne correspond. Chaque pesée saisie viendra s’inscrire ici, avec son lot et son écart.'

export function OngletPesees({
  etat,
  ecarts,
  onEcarts,
}: {
  etat: EtatTable
  ecarts: boolean
  onEcarts: (v: boolean) => void
}) {
  const fournisseurs = useFournisseursActifs()
  const magasins = useMagasins()
  const q = useDiffere(etat.recherche.valeur.trim())
  const c = etat.choix.valeurs
  const params = {
    q: q || undefined,
    ecarts: ecarts || undefined,
    fournisseur: c.fournisseur,
    qualite: c.qualite,
    magasin: c.magasin,
  }
  const liste = useListePaginee<Pesee>('/receptions/pesees', params)
  const ind = useLecture<PagePesees>('/receptions/pesees', { ...params, limite: 1 })
  const i = ind.data
  const noms = new Map((fournisseurs.data ?? []).map((f) => [String(f.id), f.nom]))
  const codes = new Map((magasins.data ?? []).map((m) => [String(m.id), m.code]))
  return (
    <>
      <IndicateursPesees i={i} />
      {liste.requete.isError ? (
        <Erreur erreur={liste.requete.error} onReessayer={() => void liste.requete.refetch()} />
      ) : null}
      <Carte
        titre={i ? `${nombre(i.total)} ligne(s) · ${kg(i.kg_pesees)} pesés` : 'Archive des pesées'}
        serre
        remplir
        className={styles.carteListe}
      >
        <DataTable<Pesee>
          libelle="Archive des pesées"
          lignes={liste.lignes}
          colonnes={COLONNES}
          serveur
          total={liste.total}
          chargerPlus={liste.chargerPlus}
          filtres={filtresPesees(noms, codes)}
          cle={(p) => p.id}
          recherche={etat.recherche}
          choix={etat.choix}
          placeholder="Référence, lot, fournisseur, réception, bon…"
          outils={<Interrupteur valeur={ecarts} onChange={onEcarts} libelle="Écarts seulement" />}
          exporter={{ route: '/export/receptions/pesees', parametres: { ecarts: ecarts || undefined } }}
          vide={liste.requete.isPending ? 'Chargement des pesées…' : VIDE_PESEES}
        />
      </Carte>
    </>
  )
}
