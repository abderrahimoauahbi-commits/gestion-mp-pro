/**
 * Analyse › Coût de revient (ECRANS-PRO 5.15 à 5.18) : ce que la matière importée a coûté, rendue
 * usine — l'achat en MAD plus toutes les charges sauf la TVA, qui se récupère.
 *
 * Trois vues dans la carte (`?vue=`) : « Regroupé » (par titrage par défaut, `?axe=`), « Lot par
 * lot » (`detail=true`, axe forcé à la référence) et « Recette d'une qualité » (route 207). Tout
 * l'état est dans l'adresse (`etat.ts`) : recharger ou copier le lien rend la même vue, et la fiche
 * d'un dossier ouverte d'ici ramène à l'analyse filtrée. La recherche s'affiche à la frappe et part
 * au serveur 300 ms après ; les résultats précédents restent affichés pendant le rechargement.
 *
 * Monté sans `Page` autour, sous les onglets de la page Analyse (`?onglet=revient`).
 */
import { keepPreviousData } from '@tanstack/react-query'
import { useMemo } from 'react'

import { Bascule, type Vue } from '../../../composants/mise-en-page/Bascule'
import { Carte } from '../../../composants/mise-en-page/Carte'
import { Chargement } from '../../../composants/retour/Chargement'
import { Erreur } from '../../../composants/retour/Erreur'
import { Selecteur } from '../../../composants/saisie/Selecteur'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { ExportExcel } from '../../../composants/tableaux/ExportExcel'
import { qs } from '../../../lib/api'
import { useLecture } from '../../../lib/requetes'
import { colonnesGroupe, colonnesLots, PiedGroupe, PiedLots, type Analyse, type Groupe } from './colonnes'
import { premierMot } from './criteres'
import {
  AXE_DEFAUT,
  AXES,
  CRITERES,
  parametresServeur,
  useDiffere,
  useEtatRevient,
  type Axe,
  type EtatRevient,
  type Modifier,
  type VueRevient,
} from './etat'
import { FiltresRevient } from './FiltresRevient'
import { IndicateursRevient } from './Indicateurs'
import { useRetour, type Liens } from './liens'
import { useReferentiels } from './referentiels'
import styles from './revient.module.css'
import { VueQualite } from './VueQualite'

const VUES_CARTE: readonly Vue<VueRevient>[] = [
  { cle: 'groupe', libelle: 'Regroupé', titre: 'Les lignes regroupées par un axe (titrage, dossier…)' },
  { cle: 'lots', libelle: 'Lot par lot', titre: 'Chaque lot importé, d’où vient chaque kilo' },
  {
    cle: 'qualite',
    libelle: 'Recette d’une qualité',
    titre: 'Le coût matière d’une qualité, par sa recette',
  },
]

const VIDE_ANALYSE = 'Aucune marchandise importée ne répond à ces critères.'
const INVITE = 'Dossier, référence, lot, fournisseur, couleur…'

const OPTIONS_AXES = AXES.map((a) => ({ id: a.cle, titre: `Par ${a.libelle.toLowerCase()}` }))

/** « Regrouper par » : l'axe de la vue « Regroupé », dans la barre du tableau. */
function ChoixAxe({ axe, modifier }: { axe: Axe; modifier: Modifier }) {
  return (
    <span className={styles.axe} title="Regrouper par">
      <Selecteur<Axe>
        valeur={axe}
        options={OPTIONS_AXES}
        effacable={false}
        libelle="Regrouper par"
        onChange={(v) => v && modifier({ axe: v === AXE_DEFAUT ? null : v })}
      />
    </span>
  )
}

interface TableProps {
  r: Analyse
  etat: EtatRevient
  modifier: Modifier
  liens: Liens
}

/** Vue « Regroupé » : une ligne par valeur de l'axe ; un axe combinable s'ouvre sur ses références. */
function TableGroupe({ r, etat, modifier, liens }: TableProps) {
  const critere = CRITERES.find((c) => c.cle === etat.axe)
  const approfondir = (g: Groupe) => {
    if (!critere || !g.valeur || g.valeur === '—') return
    const valeur = critere.cle === 'titrage' ? premierMot(g.valeur) : g.valeur
    modifier({ [critere.adresse]: valeur, axe: 'reference' })
  }
  const colonnes = colonnesGroupe(r.libelle_axe, liens).map((c) =>
    c.cle === 'valeur' && critere ? { ...c, aide: 'Cliquer une ligne : voir ses références une à une' } : c,
  )
  return (
    <DataTable
      libelle="Coût de revient regroupé"
      lignes={r.lignes}
      colonnes={colonnes}
      cle={(g) => g.valeur}
      serveur
      recherche={{ valeur: etat.q, onChange: (q) => modifier({ q }) }}
      placeholder={INVITE}
      triInitial={{ cle: 'revient_mad', sens: -1 }}
      cliquable={critere ? approfondir : undefined}
      pied={r.lignes.length > 1 ? <PiedGroupe r={r} /> : undefined}
      vide={VIDE_ANALYSE}
      outils={<ChoixAxe axe={etat.axe} modifier={modifier} />}
    />
  )
}

/** Vue « Lot par lot » : chaque lot, dans l'ordre du serveur (arrivée puis dossier, décroissants). */
function TableLots({ r, etat, modifier, liens }: TableProps) {
  const lignes = useMemo(() => r.detail_lignes.map((l, n) => ({ ...l, n })), [r.detail_lignes])
  return (
    <DataTable
      libelle="Coût de revient lot par lot"
      lignes={lignes}
      colonnes={colonnesLots(liens)}
      cle={(l) => l.n}
      serveur
      recherche={{ valeur: etat.q, onChange: (q) => modifier({ q }) }}
      placeholder={INVITE}
      pied={lignes.length ? <PiedLots r={r} /> : undefined}
      vide={VIDE_ANALYSE}
    />
  )
}

/** Les vues « Regroupé » et « Lot par lot » : filtres, indicateurs, tableau. */
function VueAnalyse({
  etat,
  modifier,
  referentiels,
  retour,
}: {
  etat: EtatRevient
  modifier: Modifier
  referentiels: ReturnType<typeof useReferentiels>
  retour: string
}) {
  // La frappe part 300 ms après ; une recherche vidée (« Effacer les filtres ») part tout de suite.
  const differe = useDiffere(etat.q, 300)
  const q = etat.q.trim() ? differe : ''
  const lots = etat.vue === 'lots'
  const parametres = useMemo(
    () => ({ ...parametresServeur(etat, q), detail: lots || undefined }),
    [etat, q, lots],
  )
  const lecture = useLecture<Analyse>('/analyse/revient', parametres, { placeholderData: keepPreviousData })
  const r = lecture.data
  const liens: Liens | null = r ? { ids: r.ids_dossiers, retour, matiere: referentiels.matiere } : null
  return (
    <>
      <FiltresRevient
        etat={etat}
        modifier={modifier}
        qualites={referentiels.optionsQualites}
        matieres={referentiels.optionsMatieres}
        options={referentiels.options}
        reference={referentiels.reference}
      />
      {lecture.isError ? (
        <Erreur erreur={lecture.error} onReessayer={() => void lecture.refetch()} />
      ) : !r || !liens ? (
        <Chargement quoi="l’analyse" />
      ) : (
        <>
          <IndicateursRevient r={r} liens={liens} />
          <div className={styles.tableau}>
            {lots ? (
              <TableLots r={r} etat={etat} modifier={modifier} liens={liens} />
            ) : (
              <TableGroupe r={r} etat={etat} modifier={modifier} liens={liens} />
            )}
          </div>
        </>
      )}
    </>
  )
}

export default function AnalyseRevient() {
  const { etat, modifier } = useEtatRevient()
  const referentiels = useReferentiels(etat.criteres)
  const retour = useRetour()
  const exporter = qs(parametresServeur(etat, etat.q))
  return (
    <Carte
      remplir
      serre
      titre="Ce que la matière importée a coûté, rendue usine"
      actions={
        <>
          <Bascule<VueRevient>
            libelle="Vue de l’analyse"
            vues={VUES_CARTE}
            valeur={etat.vue}
            onChange={(v) => modifier({ vue: v === 'groupe' ? null : v })}
          />
          {etat.vue !== 'qualite' ? (
            <span title="Le regroupement et le détail lot par lot dans un classeur">
              <ExportExcel route={`/export/revient${exporter}`} />
            </span>
          ) : null}
        </>
      }
    >
      <div className={styles.corps}>
        {etat.vue === 'qualite' ? (
          <VueQualite
            etat={etat}
            modifier={modifier}
            qualites={referentiels.optionsQualites}
            liens={(ids) => ({ ids, retour, matiere: referentiels.matiere })}
          />
        ) : (
          <VueAnalyse etat={etat} modifier={modifier} referentiels={referentiels} retour={retour} />
        )}
      </div>
    </Carte>
  )
}
