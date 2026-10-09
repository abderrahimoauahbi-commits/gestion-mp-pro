/**
 * « Classer le catalogue d'après les références » (fenêtre de l'onglet Classification ;
 * direction, achats). Le serveur lit chaque référence et propose de compléter les cases vides
 * (composition, type, titrage, couleur, code couleur) — jamais de remplacer ce qui est renseigné.
 * « Classer le catalogue (N matière(s)) » écrit les matières montrées, à leur version lue.
 */
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Vide } from '../../composants/retour/Vide'
import { Confirmer } from '../../composants/saisie/Confirmer'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api } from '../../lib/api'
import { nombre, VIDE } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import styles from './catalogue.module.css'
import type { ApercuClassement } from './types'

type Proposition = ApercuClassement['propositions'][number]

const champ = (cle: string, titre: string): Colonne<Proposition> => ({
  cle,
  titre,
  valeur: (p) => p.changements[cle] ?? VIDE,
})

const COLONNES: Colonne<Proposition>[] = [
  { cle: 'reference', titre: 'Référence', rendu: (p) => <span className={styles.code}>{p.reference}</span> },
  champ('composition', 'Composition'),
  champ('type_fil', 'Type'),
  champ('titrage', 'Titrage'),
  champ('couleur', 'Couleur'),
  champ('couleur_code', 'Code couleur'),
]

const NOMS: Record<string, string> = {
  composition: 'Compositions',
  type_fil: 'Types de fil',
  titrage: 'Titrages',
  couleur: 'Couleurs',
}

/** « Compositions : PP, PES · Types de fil : FRZ » (les listes vides sont tues). */
export function valeursNouvelles(a: ApercuClassement): string {
  return Object.entries(a.a_creer)
    .filter(([, codes]) => codes.length)
    .map(([liste, codes]) => `${NOMS[liste] ?? liste} : ${codes.join(', ')}`)
    .join(' · ')
}

function Pied({ a, onFermer }: { a: ApercuClassement | undefined; onFermer: () => void }) {
  const ecriture = useEcriture((corps: { ids: number[]; versions: number[] }) =>
    api.post<ApercuClassement>('/matieres/classement', corps),
  )
  const n = a?.propositions.length ?? 0
  const classer = async () => {
    if (!a) return
    await ecriture.mutateAsync({
      ids: a.propositions.map((p) => p.matiere_id),
      versions: a.propositions.map((p) => p.version),
    })
    dire('Catalogue classé.')
    onFermer()
  }
  return (
    <div className={styles.pied}>
      <span className={styles.pousse} />
      <Confirmer
        variante="principal"
        question={`Compléter ${nombre(n)} matière${n > 1 ? 's' : ''} ?`}
        oui="Oui, classer"
        titre="Écrire la classification déduite dans les cases vides"
        grise={n ? undefined : 'Rien à compléter.'}
        attente="Classement…"
        onOui={classer}
      >
        {`Classer le catalogue (${nombre(n)} matière${n > 1 ? 's' : ''})`}
      </Confirmer>
    </div>
  )
}

export function Classer({ onFermer }: { onFermer: () => void }) {
  const lu = useLecture<ApercuClassement>('/matieres/classement')
  const a = lu.data
  return (
    <Fenetre
      titre="Classer le catalogue d’après les références"
      onFermer={onFermer}
      taille="tresLarge"
      pied={<Pied a={a} onFermer={onFermer} />}
    >
      <Note>
        Chaque référence dit sa composition, son type, son titrage et sa couleur. Les cases vides sont
        complétées d’après elle ; ce qui est déjà renseigné n’est jamais remplacé.
      </Note>
      {lu.isPending ? <Chargement quoi="les références" /> : null}
      {lu.isError ? <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} /> : null}
      {a && !a.propositions.length ? (
        <Vide>Toutes les matières sont déjà classées : rien à compléter.</Vide>
      ) : null}
      {a?.propositions.length ? (
        <>
          <DataTable
            libelle="Ce que le classement complétera"
            lignes={a.propositions}
            colonnes={COLONNES}
            cle={(p) => p.matiere_id}
            hauteur="fenetre"
          />
          {valeursNouvelles(a) ? (
            <Note>Valeurs nouvelles qui seront ajoutées à la classification : {valeursNouvelles(a)}</Note>
          ) : null}
        </>
      ) : null}
    </Fenetre>
  )
}
