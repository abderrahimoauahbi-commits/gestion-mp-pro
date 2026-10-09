/**
 * Analyse › Matrice (`/analyse?onglet=matrice`) : le prix moyen pondéré de chaque matière, mois
 * par mois (le plus récent à gauche), **dans la devise de la facture** — une ligne par matière et
 * par devise (E-04). Chaque case est teintée face au dernier prix antérieur (règle du serveur).
 * Filtres liés (composition, type, titrage, couleur, fournisseur) et recherche dans l'adresse
 * (`mq`, `m_*`) ; cases à cocher pour comparer au plus 8 matières sur une même courbe (P8-6).
 */
import { useMemo, useState } from 'react'

import { Carte } from '../../../composants/mise-en-page/Carte'
import { Chargement } from '../../../composants/retour/Chargement'
import { Erreur } from '../../../composants/retour/Erreur'
import { Bouton } from '../../../composants/saisie/Bouton'
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { trouve, type Filtre } from '../../../composants/tableaux/filtrage'
import { moisCourt, nombre, partSignee, prix } from '../../../lib/format'
import { useEtatListe } from '../../catalogue/etatListe'
import { Deux } from '../briques'
import styles from '../analyse.module.css'
import { useHistoriquePrix, useMatrice } from '../donnees'
import type { LigneMatrice, MatricePrix } from '../types'
import { IndicateursPrix, Legende, MOUVEMENTS, mouvement, seuilsDe, type Seuils } from './commun'
import { Evolution, MAX_COURBES, type MatiereComparee } from './Evolution'

export const titrageDe = (x: LigneMatrice) =>
  [x.titrage, x.titrage_unite].filter((v) => v != null && v !== '').join(' ')

const cleDe = (x: LigneMatrice) => `${x.matiere_id ?? x.reference}|${x.devise}`

const FILTRES: readonly Filtre<LigneMatrice>[] = [
  { cle: 'm_composition', libelle: 'Composition', valeur: (x) => x.composition },
  { cle: 'm_type', libelle: 'Type de fil', valeur: (x) => x.type_fil },
  { cle: 'm_titrage', libelle: 'Titrage', valeur: titrageDe },
  { cle: 'm_couleur', libelle: 'Couleur', valeur: (x) => x.couleur },
  { cle: 'm_fournisseur', libelle: 'Fournisseur', valeur: (x) => x.fournisseur },
]

interface Case {
  prix: number
  avant: number | null
  variation: number | null
}

/** Les cases d'une ligne dans l'ordre du temps : chaque prix face au dernier connu avant lui. */
export function cases(prixDuMois: readonly (number | null)[]): (Case | null)[] {
  let precedent: number | null = null
  return prixDuMois.map((p) => {
    if (p == null) return null
    const avant: number | null = precedent
    precedent = p
    return { prix: p, avant, variation: avant == null ? null : (p - avant) / avant }
  })
}

function CaseMois({ c, devise, seuils }: { c: Case | null; devise: string; seuils: Seuils }) {
  if (!c) return <span className={styles.note}>·</span>
  const genre = MOUVEMENTS[mouvement(c.variation, seuils)]
  const titre =
    c.variation == null || c.avant == null
      ? `${genre.libelle} : ${prix(c.prix)} ${devise} / kg`
      : `${genre.libelle} : ${partSignee(c.variation)} (${prix(c.avant)} → ${prix(c.prix)} ${devise} / kg)`
  return (
    <span className={styles.cellule} data-ton={genre.ton} title={titre}>
      {prix(c.prix)}
    </span>
  )
}

interface Coches {
  coches: readonly string[]
  basculer: (x: LigneMatrice) => void
}

/** La référence et sa case à cocher : 8 au plus (P8-6), la raison dite sur la case grisée. */
function CaseReference({ x, coches, basculer }: Coches & { x: LigneMatrice }) {
  const coche = coches.includes(cleDe(x))
  const plein = !coche && coches.length >= MAX_COURBES
  return (
    <label
      className={styles.case}
      title={plein ? `${MAX_COURBES} matières au plus sur une même courbe` : undefined}
    >
      <input
        type="checkbox"
        aria-label={`Comparer ${x.reference}`}
        checked={coche}
        disabled={plein}
        onChange={() => basculer(x)}
      />
      <span>
        <Deux
          coupe
          haut={x.reference}
          titre={x.reference}
          bas={[x.composition, x.type_fil, titrageDe(x), x.couleur].filter(Boolean).join(' · ')}
        />
      </span>
    </label>
  )
}

function colonnesDuMois(mois: readonly string[], seuils: Seuils): Colonne<LigneMatrice>[] {
  const n = mois.length
  return [...mois].reverse().map((m, i): Colonne<LigneMatrice> => ({
    cle: `mois_${m}`,
    titre: moisCourt(m),
    droite: true,
    valeur: (x) => x.prix[n - 1 - i] ?? null,
    rendu: (x) => <CaseMois c={cases(x.prix)[n - 1 - i] ?? null} devise={x.devise} seuils={seuils} />,
  }))
}

/** Coche ou décoche une ligne. */
const basculee = (x: LigneMatrice) => (c: string[]) =>
  c.includes(cleDe(x)) ? c.filter((k) => k !== cleDe(x)) : [...c, cleDe(x)]

const CLES_FILTRES = FILTRES.map((f) => f.cle)

function colonnes(
  m: MatricePrix | undefined,
  c: Coches,
  courbe: (x: LigneMatrice) => void,
): Colonne<LigneMatrice>[] {
  return [
    {
      cle: 'reference',
      titre: 'Référence',
      aide: 'Prix moyen du mois, pondéré par les quantités, dans la devise de la facture ; le mois le plus récent à gauche',
      recherche: (x) => [
        x.nature,
        x.designation,
        x.composition,
        x.type_fil,
        x.couleur,
        titrageDe(x),
        x.devise,
      ],
      rendu: (x) => <CaseReference x={x} {...c} />,
    },
    { cle: 'fournisseur', titre: 'Fournisseur' },
    {
      cle: 'devise',
      titre: 'Prix en',
      aide: 'La monnaie de la facture ; le prix est au kilo',
      rendu: (x) => `${x.devise} / kg`,
    },
    {
      cle: 'courbe',
      titre: '',
      triable: false,
      exporte: false,
      rendu: (x) => (
        <Bouton taille="petit" titre={`La courbe des prix de ${x.reference}`} onClick={() => courbe(x)}>
          Courbe
        </Bouton>
      ),
    },
    ...colonnesDuMois(m?.mois ?? [], seuilsDe(m?.seuils)),
  ]
}

interface ActionsProps {
  affichees: readonly LigneMatrice[]
  cochees: readonly LigneMatrice[]
  comparer: (l: readonly LigneMatrice[]) => void
  decocher: () => void
}

function ActionsMatrice({ affichees, cochees, comparer, decocher }: ActionsProps) {
  const n = affichees.length
  const raison = !n
    ? 'Aucune matière affichée.'
    : n > MAX_COURBES
      ? `Filtrer jusqu’à ${MAX_COURBES} matières au plus pour les comparer toutes`
      : undefined
  return (
    <>
      <Bouton
        grise={raison}
        titre="Toutes les matières du tableau sur une même courbe"
        onClick={() => comparer(affichees)}
      >
        {raison ? 'Comparer les matières affichées' : `Comparer les ${n} matières affichées`}
      </Bouton>
      <Bouton
        variante="principal"
        grise={
          cochees.length
            ? undefined
            : 'Cocher des matières dans le tableau, puis voir leurs prix sur une même courbe'
        }
        onClick={() => comparer(cochees)}
      >
        {cochees.length
          ? `Comparer les ${cochees.length} matières cochées`
          : 'Cocher des matières à comparer'}
      </Bouton>
      {cochees.length ? <Bouton onClick={decocher}>Tout décocher</Bouton> : null}
    </>
  )
}

const comparee = (x: LigneMatrice): MatiereComparee => ({
  reference: x.reference,
  matiere_id: x.matiere_id ?? null,
})

export function Matrice() {
  const lu = useMatrice()
  const h = useHistoriquePrix()
  const etat = useEtatListe('mq', CLES_FILTRES)
  const [coches, setCoches] = useState<string[]>([])
  const [aComparer, setAComparer] = useState<MatiereComparee[] | null>(null)
  const cols = useMemo(
    () =>
      colonnes(lu.data, { coches, basculer: (x) => setCoches(basculee(x)) }, (x) =>
        setAComparer([comparee(x)]),
      ),
    [lu.data, coches],
  )
  if (lu.isPending || h.isPending) return <Chargement quoi="les prix" />
  const relire = () => void Promise.all([lu.refetch(), h.refetch()])
  if (lu.isError || h.isError) return <Erreur erreur={lu.error ?? h.error} onReessayer={relire} />
  const { lignes } = lu.data
  const affichees = filtrees(lignes, etat)
  return (
    <>
      <IndicateursPrix h={h.data} m={lu.data} />
      <Carte
        titre={`Matrice des prix — ${nombre(affichees.length)} matière(s)`}
        sous={<Legende seuils={seuilsDe(lu.data.seuils)} />}
        actions={
          <ActionsMatrice
            affichees={affichees}
            cochees={lignes.filter((x) => coches.includes(cleDe(x)))}
            comparer={(l) => setAComparer(l.map(comparee))}
            decocher={() => setCoches([])}
          />
        }
        serre
        remplir
        className={styles.carteListe}
      >
        <DataTable<LigneMatrice>
          libelle="Matrice des prix"
          lignes={lignes}
          colonnes={cols}
          filtres={FILTRES}
          cle={cleDe}
          recherche={etat.recherche}
          choix={etat.choix}
          placeholder="Référence, fournisseur, couleur… plusieurs mots"
          triInitial={{ cle: 'reference', sens: 1 }}
          vide="La matrice se remplira à la première réception validée : une colonne par mois, jusqu’à trente-six mois."
          exporter={{ route: '/export/prix' }}
        />
      </Carte>
      {aComparer ? <Evolution matieres={aComparer} onFermer={() => setAComparer(null)} /> : null}
    </>
  )
}

/** Les lignes que la recherche et les filtres gardent (pour compter et comparer « les affichées »). */
function filtrees(lignes: readonly LigneMatrice[], etat: ReturnType<typeof useEtatListe>) {
  const q = etat.recherche.valeur.trim()
  return lignes.filter(
    (x) =>
      FILTRES.every((f) => !etat.choix.valeurs[f.cle] || f.valeur(x) === etat.choix.valeurs[f.cle]) &&
      (!q || correspondLigne(x, q)),
  )
}

function correspondLigne(x: LigneMatrice, q: string): boolean {
  const champs = [x.reference, x.fournisseur, x.nature, x.designation, x.composition, x.type_fil, x.couleur]
  return trouve([...champs, titrageDe(x), x.devise, 'kg'], q)
}
