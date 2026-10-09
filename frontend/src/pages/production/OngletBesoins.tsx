/**
 * Production › Besoins matière (`/production?onglet=besoins`) : la matière que le plan consommera,
 * référence par référence, mois par mois — le besoin du plan, ou ce que le plan d'achat en retient
 * (corrigé par le réel, `?vue=retenu`). Filtres liés (rôle, fournisseur), qualité, « Avec besoin
 * seulement », export. Une ligne ouvre d'où vient le besoin (`/production/besoins/:matiereId`).
 * L'alimentation n'a pas la colonne « À commander » (H-03).
 */
import { useMemo } from 'react'
import { useNavigate } from 'react-router'

import { Bascule, useVueAdresse } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse, type EtatTable } from '../../composants/tableaux/etatAdresse'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { jours, moisCourt, nombre, VIDE } from '../../lib/format'
import { cleStock } from '../../lib/statuts'
import { Double, Kg } from '../stock/cellules'
import { AIDE_DISPONIBLE } from '../stock/colonnesMatieres'
import stock from '../stock/stock.module.css'
import styles from './production.module.css'
import type { BesoinMatiere, BesoinsDetailles } from './plan'

type Lecture = 'plan' | 'retenu'

export const CLES_BESOINS = ['role', 'fournisseur', 'qualite', 'tous'] as const

const FILTRES: Filtre<BesoinMatiere>[] = [
  { cle: 'role', libelle: 'Rôle', valeur: (x) => x.role },
  { cle: 'fournisseur', libelle: 'Fournisseur', valeur: (x) => x.fournisseur },
]

const kgDe = (x: BesoinMatiere, l: Lecture) => (l === 'plan' ? x.kg : x.retenu)
const totalDe = (x: BesoinMatiere, l: Lecture) => (l === 'plan' ? x.total : x.total_retenu)

const DEBUT: Colonne<BesoinMatiere>[] = [
  {
    cle: 'reference',
    titre: 'Référence',
    valeur: (x) => x.reference,
    recherche: (x) => [x.nature, x.designation, ...x.qualites.map((q) => q.qualite)],
    rendu: (x) => (
      <span className={stock.ref}>
        <Double haut={x.reference} bas={[x.nature, x.designation].filter(Boolean).join(' · ')} />
      </span>
    ),
  },
  { cle: 'role_', titre: 'Rôle', valeur: (x) => x.role },
  { cle: 'fournisseur_', titre: 'Fournisseur', valeur: (x) => x.fournisseur },
]

const FIN: Colonne<BesoinMatiere>[] = [
  {
    cle: 'disponible',
    titre: 'Disponible',
    aide: AIDE_DISPONIBLE,
    droite: true,
    unite: 'kg',
    total: true,
    valeur: (x) => x.stock_disponible,
    rendu: (x) => nombre(x.stock_disponible),
  },
  {
    cle: 'couverture',
    titre: 'Couverture',
    aide: 'Jours de consommation couverts par le stock projeté',
    droite: true,
    valeur: (x) => x.couverture_jours ?? null,
    rendu: (x) =>
      x.statut ? (
        <Badge
          famille="stock"
          valeur={cleStock(x.statut)}
          titre={x.couverture_jours == null ? undefined : jours(x.couverture_jours)}
        />
      ) : (
        VIDE
      ),
  },
]

const A_COMMANDER: Colonne<BesoinMatiere> = {
  cle: 'a_commander',
  titre: 'À commander (kg)',
  droite: true,
  unite: 'kg',
  total: true,
  valeur: (x) => x.quantite_a_commander ?? null,
  rendu: (x) =>
    (x.quantite_a_commander ?? 0) > 0 ? <Kg v={x.quantite_a_commander} kgParMl={x.kg_par_ml} /> : VIDE,
}

function colonnes(b: BesoinsDetailles, lecture: Lecture, voitAchats: boolean): Colonne<BesoinMatiere>[] {
  const mois: Colonne<BesoinMatiere>[] = b.mois.map((m, i) => ({
    cle: `m${i}`,
    titre: `${moisCourt(m)}${i === 0 ? ' (en cours)' : ''}`,
    droite: true,
    unite: 'kg',
    total: true,
    valeur: (x) => kgDe(x, lecture)[i] ?? 0,
    rendu: (x) => (kgDe(x, lecture)[i] ? nombre(kgDe(x, lecture)[i]) : VIDE),
  }))
  const total: Colonne<BesoinMatiere> = {
    cle: 'total',
    titre: 'Total 12 mois (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    valeur: (x) => totalDe(x, lecture),
    rendu: (x) => (
      <Double
        haut={<Kg v={totalDe(x, lecture)} kgParMl={x.kg_par_ml} />}
        bas={
          lecture === 'retenu' && x.coefficient_realisation != null
            ? `× ${nombre(x.coefficient_realisation, 2)}`
            : undefined
        }
      />
    ),
  }
  return [...DEBUT, ...mois, total, ...FIN, ...(voitAchats ? [A_COMMANDER] : [])]
}

function Outils({ table, qualites }: { table: EtatTable; qualites: readonly string[] }) {
  const v = table.choix.valeurs
  return (
    <>
      <select
        aria-label="Qualité"
        className={stock.selecteur}
        value={v.qualite ?? ''}
        onChange={(e) => table.choix.poser('qualite', e.target.value || null)}
      >
        <option value="">Qualité : toutes</option>
        {qualites.map((q) => (
          <option key={q}>{q}</option>
        ))}
      </select>
      <label className={styles.case}>
        <input
          type="checkbox"
          checked={v.tous !== '1'}
          onChange={(e) => table.choix.poser('tous', e.target.checked ? null : '1')}
        />
        Avec besoin seulement
      </label>
    </>
  )
}

function Actions({ lignes, voitAchats }: { lignes: readonly BesoinMatiere[]; voitAchats: boolean }) {
  const navigate = useNavigate()
  const aCommander = voitAchats ? lignes.filter((x) => (x.quantite_a_commander ?? 0) > 0).length : 0
  return (
    <>
      <span className={stock.note}>
        {nombre(lignes.length)} référence(s){aCommander ? ` · ${nombre(aCommander)} à commander` : ''}
      </span>
      {voitAchats ? (
        <Bouton
          titre="Ce qu’il faut commander, regroupé par fournisseur"
          onClick={() => navigate('/plan-achat')}
        >
          Ouvrir le plan d’achat →
        </Bouton>
      ) : null}
      <ExportExcel route="/export/production" parametres={{ onglet: 'besoins' }} />
    </>
  )
}

const explication = (b: BesoinsDetailles, lecture: Lecture) =>
  `${
    lecture === 'plan'
      ? `Besoin du plan : m² planifiés × kg/m² des recettes (pour le cuir, les franges, le ruban : leurs ml/m² × la densité), majorés de la perte de ${nombre(b.taux_perte * 100, 1)} %.`
      : `Retenu par le plan d’achat : le besoin du plan corrigé par le rapport entre le consommé et le prévu des derniers mois clos (fenêtre de ${nombre(b.fenetre_realisation_jours)} jours, entre × 0,5 et × 1,5).`
  } Cliquer sur une référence pour voir les qualités qui la tirent.`

/** Les lignes affichées : avec besoin (sauf « tous »), de la qualité choisie, les plus lourdes d'abord. */
function useLignes(besoins: BesoinsDetailles, lecture: Lecture, table: EtatTable) {
  const { tous, qualite } = table.choix.valeurs
  return useMemo(
    () =>
      besoins.lignes
        .filter(
          (x) =>
            (tous === '1' || x.total > 0 || x.total_retenu > 0) &&
            (!qualite || x.qualites.some((q) => q.qualite === qualite)),
        )
        .sort((a, b) => totalDe(b, lecture) - totalDe(a, lecture)),
    [besoins.lignes, tous, qualite, lecture],
  )
}

function Titre({ lecture, onLecture }: { lecture: Lecture; onLecture: (l: Lecture) => void }) {
  return (
    <span
      className={styles.titre}
      title="En kg, le cuir, les franges et le ruban compris (leurs mètres dessous, à titre indicatif)"
    >
      Besoins matière (MRP)
      <Bascule
        vues={[
          { cle: 'plan', libelle: 'Besoin du plan' },
          { cle: 'retenu', libelle: 'Retenu par le plan d’achat' },
        ]}
        valeur={lecture}
        onChange={onLecture}
        libelle="Lecture des besoins"
      />
    </span>
  )
}

export function OngletBesoins({
  besoins,
  voitAchats,
  onOuvrir,
}: {
  besoins: BesoinsDetailles
  voitAchats: boolean
  onOuvrir: (id: number) => void
}) {
  const [lecture, setLecture] = useVueAdresse<Lecture>(['plan', 'retenu'], 'plan')
  const table = useEtatTableAdresse(CLES_BESOINS)
  const lignes = useLignes(besoins, lecture, table)
  const qualites = [...new Set(besoins.lignes.flatMap((x) => x.qualites.map((q) => q.qualite)))].sort()
  return (
    <Carte
      titre={<Titre lecture={lecture} onLecture={setLecture} />}
      sous={explication(besoins, lecture)}
      actions={<Actions lignes={lignes} voitAchats={voitAchats} />}
      serre
      remplir
      className={styles.carteListe}
    >
      <DataTable<BesoinMatiere>
        libelle="Besoins matière"
        lignes={lignes}
        colonnes={colonnes(besoins, lecture, voitAchats)}
        filtres={FILTRES}
        cle={(x) => x.matiere_id ?? x.reference}
        recherche={table.recherche}
        choix={table.choix}
        placeholder="Référence, couleur, fournisseur, qualité…"
        cliquable={(x) => (x.matiere_id != null ? onOuvrir(x.matiere_id) : undefined)}
        vide={
          besoins.lignes.length
            ? 'Aucune référence avec besoin.'
            : 'Aucun besoin : le plan de production est vide ou les recettes ne sont pas saisies.'
        }
        outils={<Outils table={table} qualites={qualites} />}
      />
    </Carte>
  )
}
