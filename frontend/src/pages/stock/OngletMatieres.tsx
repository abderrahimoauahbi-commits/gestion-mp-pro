/**
 * Stock › Par matière (`/stock?onglet=matieres`) : une ligne par matière, sous trois vues
 * (`?vue=appro|classement|ou`), la recherche à la frappe sur dix champs, des filtres liés, les cases
 * « En stock » et « À commander », le pied de totaux. Les indicateurs comptent les lignes affichées
 * et un clic sur « Ruptures » ou « Critiques » pose le filtre. Une ligne ouvre la fiche de la matière.
 */
import { useMemo } from 'react'
import { useSearchParams } from 'react-router'

import { Bascule, useVueAdresse, type Vue } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { champsCherches } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import { passe, trouve } from '../../composants/tableaux/filtrage'
import { avecParametre } from '../../lib/adresse'
import { formule } from '../../lib/aide'
import { date, kg, montant, montantCourt, nombre } from '../../lib/format'
import { cleStock } from '../../lib/statuts'
import {
  aCommander,
  colonnesMatieres,
  filtresMatieres,
  rangStatut,
  stockDetenu,
  type LigneMatiere,
  type VueMatieres,
} from './colonnesMatieres'
import { useEtatStock, useMagasins, useMatieres } from './donnees'
import { FiltresCases } from './FiltresCases'
import styles from './stock.module.css'
import { POUSSIERE, type EtatStock, type MatiereResume } from './types'

const VUES: readonly Vue<VueMatieres>[] = [
  { cle: 'appro', libelle: 'Approvisionnement', titre: 'Couverture, commandes, ce qu’il faut commander' },
  { cle: 'classement', libelle: 'Classement et risque', titre: 'ABC, XYZ, sourcing, dormants' },
  { cle: 'ou', libelle: 'Où se trouve la matière', titre: 'Magasins, métiers, quarantaine, commandé' },
]

export const CLES_MATIERES = [
  'statut',
  'fournisseur',
  'role',
  'composition',
  'type_fil',
  'titrage',
  'abc',
  'xyz',
  'magasin',
  'en_stock',
  'a_commander',
] as const

/** Les lignes du stock, avec le rôle et le fournisseur du catalogue, du plus urgent au plus calme. */
export function lignesMatieres(etat: EtatStock | undefined, matieres: readonly MatiereResume[] | undefined) {
  const parId = new Map((matieres ?? []).map((m) => [m.id, m]))
  return (etat?.lignes ?? [])
    .map((l): LigneMatiere => {
      const m = l.matiere_id != null ? parId.get(l.matiere_id) : undefined
      return { ...l, role: m?.role ?? '', fournisseur_id: l.fournisseur_id ?? null }
    })
    .sort(
      (a, b) =>
        rangStatut(a.statut) - rangStatut(b.statut) ||
        (a.couverture_jours ?? 1e9) - (b.couverture_jours ?? 1e9),
    )
}

/** Les cases et le magasin, appliqués avant les filtres du tableau. */
function passeCases(l: LigneMatiere, cases: { magasin: string; enStock: boolean; aCommander: boolean }) {
  if (cases.enStock && stockDetenu(l) <= POUSSIERE) return false
  if (cases.aCommander && !aCommander(l)) return false
  return !cases.magasin || Math.abs(l.par_magasin?.[cases.magasin] ?? 0) > POUSSIERE
}

function Indicateurs5({
  lignes,
  total,
  voitPrix,
}: {
  lignes: readonly LigneMatiere[]
  total: number
  voitPrix: boolean
}) {
  const [params] = useSearchParams()
  const vers = (statut: string) => `/stock?${avecParametre(params, 'statut', statut).toString()}`
  const ruptures = lignes.filter((l) => cleStock(l.statut) === 'RUPTURE').length
  const critiques = lignes.filter((l) => cleStock(l.statut) === 'CRITIQUE').length
  const budget = lignes.reduce((t, l) => t + (l.montant_a_commander_mad ?? 0), 0)
  return (
    <Indicateurs>
      <Kpi
        titre="Matières affichées"
        valeur={nombre(lignes.length)}
        detail={`sur ${nombre(total)}`}
        formule={formule('matieres_affichees')}
      />
      <Kpi
        titre="Stock affiché"
        valeur={kg(lignes.reduce((t, l) => t + stockDetenu(l), 0))}
        detail="magasins et sur les métiers"
        formule={formule('stock_detenu')}
      />
      <Kpi
        titre="Ruptures"
        valeur={nombre(ruptures)}
        detail="stock projeté à zéro"
        ton={ruptures ? 'rupture' : 'ok'}
        lien={vers('RUPTURE')}
        formule={formule('ruptures')}
      />
      <Kpi
        titre="Critiques"
        valeur={nombre(critiques)}
        detail="projeté ≤ 50 % du seuil d’alerte"
        ton={critiques ? 'critique' : 'ok'}
        lien={vers('CRITIQUE')}
        formule={formule('critiques')}
      />
      {voitPrix ? (
        <Kpi
          titre="Budget à commander"
          valeur={montantCourt(budget, 'MAD')}
          exact={montant(budget, 'MAD')}
          detail={`${nombre(lignes.filter(aCommander).length)} matière(s)`}
          ton={budget > 0 ? 'attention' : 'ok'}
          lien="/plan-achat"
          formule={formule('budget_a_commander')}
        />
      ) : null}
    </Indicateurs>
  )
}

/** Les lignes, la vue, les filtres de l'adresse et ce qui est affiché. */
function useOngletMatieres(voitPrix: boolean) {
  const etat = useEtatStock()
  const matieres = useMatieres()
  const magasins = useMagasins()
  const [vue, setVue] = useVueAdresse<VueMatieres>(['appro', 'classement', 'ou'], 'appro')
  const table = useEtatTableAdresse(CLES_MATIERES)
  const v = table.choix.valeurs
  const magasin = v.magasin ?? ''
  const enStock = v.en_stock === '1'
  const seulementACommander = voitPrix && v.a_commander === '1'
  const toutes = useMemo(() => lignesMatieres(etat.data, matieres.data), [etat.data, matieres.data])
  const avant = useMemo(
    () => toutes.filter((l) => passeCases(l, { magasin, enStock, aCommander: seulementACommander })),
    [toutes, magasin, enStock, seulementACommander],
  )
  const filtres = useMemo(() => filtresMatieres(voitPrix), [voitPrix])
  const listeMagasins = (magasins.data ?? []).map((g) => ({ code: g.code, type: g.type }))
  const preparer = (l: LigneMatiere) =>
    aCommander(l) && l.fournisseur_id ? `/plan-achat/preparer/${l.fournisseur_id}` : null
  const colonnes = colonnesMatieres(vue, voitPrix, listeMagasins, avant, preparer)
  const affichees = avant.filter(
    (l) => passe(l, filtres, v) && trouve(champsCherches(colonnes, l), table.recherche.valeur),
  )
  const avecStock = listeMagasins
    .map((g) => g.code)
    .filter((c) => toutes.some((l) => Math.abs(l.par_magasin?.[c] ?? 0) > POUSSIERE))
  return { etat, vue, setVue, table, toutes, avant, filtres, colonnes, affichees, avecStock }
}

export function OngletMatieres({
  voitPrix,
  onOuvrir,
}: {
  voitPrix: boolean
  onOuvrir: (id: number) => void
}) {
  const o = useOngletMatieres(voitPrix)
  if (o.etat.isPending) return <Chargement quoi="le stock" />
  if (o.etat.isError) return <Erreur erreur={o.etat.error} onReessayer={() => void o.etat.refetch()} />
  const aide = VUES.find((x) => x.cle === o.vue)?.titre
  return (
    <>
      <Indicateurs5 lignes={o.affichees} total={o.toutes.length} voitPrix={voitPrix} />
      <Carte
        titre={<Bascule vues={VUES} valeur={o.vue} onChange={o.setVue} libelle="Vue du stock par matière" />}
        actions={voitPrix ? <ExportExcel route="/export/pilotage" /> : null}
        sous={`${aide}. Un clic sur une ligne ouvre la fiche de la matière ; un clic sur un en-tête trie. Situation au ${date(o.etat.data.date_reference)}.`}
        serre
        remplir
        className={styles.carteListe}
      >
        <DataTable<LigneMatiere>
          libelle="Stock par matière"
          lignes={o.avant}
          colonnes={o.colonnes}
          filtres={o.filtres}
          cle={(l) => l.matiere_id ?? l.reference ?? ''}
          recherche={o.table.recherche}
          choix={o.table.choix}
          placeholder="Référence, couleur, fournisseur, titrage… plusieurs mots affinent"
          cliquable={(l) => (l.matiere_id != null ? onOuvrir(l.matiere_id) : undefined)}
          vide="Aucune matière au stock."
          outils={<FiltresCases table={o.table} magasins={o.avecStock} aCommander={voitPrix} />}
        />
      </Carte>
    </>
  )
}
