/**
 * Onglet « Versions » de la fiche qualité : chaque version de la recette (née à chaque changement
 * de lignes ou de poids, signée), et la comparaison d'une version à celle en vigueur. Une version
 * vaut à son horodatage (pas de date d'effet, P7-32). La direction peut « Revenir à cette
 * version », motif exigé, sans autre saisie en cours.
 */
import { useState } from 'react'

import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { Vide } from '../../composants/retour/Vide'
import { Confirmer } from '../../composants/saisie/Confirmer'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { horodatage, nombre } from '../../lib/format'
import styles from '../catalogue/catalogue.module.css'
import { deux } from '../catalogue/colonnesMatieres'
import type { Matiere } from '../catalogue/types'
import { ecartLisible, ecarts, ecartsPoids, type Ecart } from './comparaison'
import { useVersions } from './donnees'
import type { VersionRecette } from './types'
import type { FicheQualiteEtat } from './useFicheQualite'

const parQui = (v: VersionRecette) => v.par?.nom ?? (v.origine === 'reprise' ? 'reprise de Gestion MP' : '—')

const COLONNES: Colonne<VersionRecette>[] = [
  {
    cle: 'valide_depuis',
    titre: 'Enregistrée le',
    rendu: (v) => deux(horodatage(v.valide_depuis), v.en_vigueur ? 'en vigueur' : null),
  },
  { cle: 'par', titre: 'Par', valeur: parQui },
  { cle: 'lignes', titre: 'Matières', droite: true, valeur: (v) => v.lignes.length },
  {
    cle: 'motif',
    titre: 'Motif',
    valeur: (v) => v.motif || (v.restauree_de ? `retour à la version ${v.restauree_de}` : ''),
  },
]

const COL_ECARTS: Colonne<Ecart>[] = [
  { cle: 'role', titre: 'Rôle' },
  { cle: 'reference', titre: 'Référence', rendu: (e) => <span className={styles.code}>{e.reference}</span> },
  {
    cle: 'ici',
    titre: 'Part dans cette version',
    droite: true,
    rendu: (e) => (e.ici == null ? '—' : `${nombre(e.ici, 2)} %`),
  },
  {
    cle: 'enVigueur',
    titre: 'Part en vigueur',
    droite: true,
    rendu: (e) => (e.enVigueur == null ? '—' : `${nombre(e.enVigueur, 2)} %`),
  },
  { cle: 'ecart', titre: 'Écart', valeur: (e) => ecartLisible(e, nombre) },
]

/** Ce qui empêche de revenir à une version. */
export function blocagesRetour(v: VersionRecette, sale: boolean, catalogue: ReadonlySet<number>): string[] {
  const b: string[] = []
  if (sale) b.push('Enregistrer ou abandonner d’abord la saisie en cours')
  if (v.en_vigueur) b.push('C’est déjà la recette en vigueur')
  const parties = v.lignes.filter((l) => !catalogue.has(l.matiere_id)).map((l) => l.reference)
  if (parties.length)
    b.push(
      `Ces matières n’existent plus au catalogue : ${parties.join(', ')}. La version ne peut pas revenir telle quelle`,
    )
  return b
}

function Comparaison({
  v,
  vigueur,
  f,
  ecrit,
  catalogue,
}: {
  v: VersionRecette
  vigueur: VersionRecette
  f: FicheQualiteEtat
  ecrit: boolean
  catalogue: ReadonlySet<number>
}) {
  const diff = ecarts(v, vigueur)
  const poids = ecartsPoids(v, vigueur)
  return (
    <>
      <Note>
        Version du {horodatage(v.valide_depuis)} par {parQui(v)}, comparée à la recette en vigueur :{' '}
        {diff.length ? `${nombre(diff.length)} différence(s).` : 'identique.'}{' '}
        {v.poids == null
          ? 'Poids au m² non gardés avec cette version.'
          : poids.length
            ? `Poids au m² : ${poids.map((p) => `${p.role} ${nombre(p.ici, 3)} (en vigueur : ${nombre(p.enVigueur, 3)})`).join(', ')}.`
            : ''}
      </Note>
      {diff.length ? (
        <DataTable
          libelle="Différences avec la recette en vigueur"
          lignes={diff}
          colonnes={COL_ECARTS}
          cle={(e) => e.cle}
          recherche={false}
          hauteur="fenetre"
        />
      ) : null}
      {ecrit ? (
        <span>
          <Confirmer
            variante="danger"
            motif="exige"
            question="Remplacer la recette en vigueur par cette version ?"
            oui="Oui, revenir à cette version"
            blocages={blocagesRetour(v, f.sale, catalogue)}
            titre="La recette reprend les parts et les poids au m² de cette version ; une nouvelle version est signée"
            onOui={(motif) => f.restaurer(v.id, motif)}
          >
            Revenir à cette version
          </Confirmer>
        </span>
      ) : null}
    </>
  )
}

export function VoletVersions({
  f,
  ecrit,
  matieres,
}: {
  f: FicheQualiteEtat
  ecrit: boolean
  matieres: readonly Matiere[]
}) {
  const lu = useVersions(f.base?.id ?? 0)
  const [choisie, setChoisie] = useState<number | null>(null)
  if (lu.isPending) return <Chargement quoi="les versions" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const versions = lu.data
  if (!versions.length)
    return (
      <Vide>
        Aucune version enregistrée : la recette n’a pas été modifiée depuis la mise en service du suivi des
        versions.
      </Vide>
    )
  const vigueur = versions.find((v) => v.en_vigueur) ?? versions[0]
  const v = versions.find((x) => x.id === choisie) ?? versions[1] ?? versions[0]
  const catalogue = new Set(matieres.map((m) => m.id))
  return (
    <div className={styles.volet}>
      <p className={styles.note}>
        Une version vaut à partir de son enregistrement : une recette passée se juge sur la version de son
        époque.
      </p>
      <DataTable
        libelle="Versions de la recette"
        lignes={versions}
        colonnes={COLONNES}
        cle={(x) => x.id}
        recherche={false}
        cliquable={(x) => setChoisie(x.id)}
        marquee={(x) => x.id === v?.id}
        hauteur="fenetre"
      />
      {v && vigueur ? (
        <Comparaison v={v} vigueur={vigueur} f={f} ecrit={ecrit} catalogue={catalogue} />
      ) : null}
    </div>
  )
}
