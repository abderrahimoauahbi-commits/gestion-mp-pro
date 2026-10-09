/**
 * Réglages › Postes de frais (ECRANS-PRO 5.19) : `/reglages?onglet=postes`, monté sans `Page` sous
 * les onglets de la page Réglages. Les frais d'un dossier d'importation, récupérables ou non,
 * répartis à la valeur ou au poids ; leur usage par les dossiers ouverts et clos. Recherche à la
 * frappe sur le code et le libellé (`?pq=`), tri par ordre puis code ; une ligne ouvre le poste en
 * fenêtre (`&poste=ID`, `&poste=nouveau`). La direction écrit ; les achats lisent.
 */
import { useMemo } from 'react'

import { Carte } from '../../../composants/mise-en-page/Carte'
import { Fenetre } from '../../../composants/mise-en-page/Fenetre'
import { Badge } from '../../../composants/retour/Badge'
import { Chargement } from '../../../composants/retour/Chargement'
import { Erreur } from '../../../composants/retour/Erreur'
import { Note } from '../../../composants/retour/Note'
import { Bouton } from '../../../composants/saisie/Bouton'
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { comparer, trouve } from '../../../composants/tableaux/filtrage'
import { ErreurApi } from '../../../lib/api'
import { VIDE } from '../../../lib/format'
import { useLecture } from '../../../lib/requetes'
import { useSession } from '../../../lib/session'
import { useEtatListe } from '../../catalogue/etatListe'
import type { PosteFiche } from '../types'
import { FenetrePoste } from './FenetrePoste'
import { useFenetreAdresse, type FenetreAdresse } from './fenetreAdresse'
import { AIDE_SYSTEME, CLES, fraisSaisis, lireCle, nature } from './formePoste'
import styles from './reglages.module.css'

function Code({ p }: { p: PosteFiche }) {
  return (
    <span className={styles.rangee}>
      <span className={styles.code}>{p.code}</span>
      {p.systeme ? (
        <Badge ton="neutre" titre={AIDE_SYSTEME}>
          calculs
        </Badge>
      ) : null}
    </span>
  )
}

const COLONNES: readonly Colonne<PosteFiche>[] = [
  { cle: 'ordre', titre: 'Ordre', droite: true },
  { cle: 'code', titre: 'Code', rendu: (p) => <Code p={p} /> },
  { cle: 'libelle', titre: 'Libellé' },
  {
    cle: 'cle',
    titre: 'Répartition',
    valeur: (p) => (p.recuperable ? '' : CLES[lireCle(p.cle)]),
    rendu: (p) =>
      p.recuperable ? (
        VIDE
      ) : (
        <Badge ton={lireCle(p.cle) === 'poids' ? 'accent' : 'neutre'}>{CLES[lireCle(p.cle)]}</Badge>
      ),
  },
  {
    cle: 'nature',
    titre: 'Nature',
    valeur: (p) => nature(p.recuperable),
    rendu: (p) => (p.recuperable ? <Badge ton="attention">{nature(true)}</Badge> : nature(false)),
  },
  { cle: 'frais', titre: 'Frais saisis', droite: true, valeur: fraisSaisis },
  { cle: 'dossiers_ouverts', titre: 'Dossiers ouverts', droite: true },
  { cle: 'dossiers_clos', titre: 'Dossiers clos', droite: true },
]

/** Par ordre, puis par code. */
const parOrdre = (a: PosteFiche, b: PosteFiche) => a.ordre - b.ordre || comparer(a.code, b.code)

/** La fenêtre demandée par l'adresse : un poste, un nouveau (direction seule), ou rien. */
function FenetreDemandee({
  fen,
  postes,
  ecrit,
}: {
  fen: FenetreAdresse
  postes: readonly PosteFiche[] | undefined
  ecrit: boolean
}) {
  const commun = { ecrit, volet: fen.volet, onVolet: fen.choisirVolet, onFermer: fen.fermer }
  if (fen.nouveau && ecrit) return <FenetrePoste key="nouveau" poste={null} {...commun} />
  if (fen.id == null) return null
  const poste = postes?.find((p) => p.id === fen.id)
  if (poste) return <FenetrePoste key={poste.id} poste={poste} {...commun} />
  return (
    <Fenetre titre="Poste de frais" onFermer={fen.fermer}>
      {postes ? (
        <Erreur erreur={new ErreurApi('Poste de frais introuvable.', 404, 'introuvable')} />
      ) : (
        <Chargement quoi="le poste de frais" />
      )}
    </Fenetre>
  )
}

export function PostesFrais() {
  const { role } = useSession()
  const ecrit = role === 'direction'
  const lu = useLecture<PosteFiche[]>('/postes-frais')
  const fen = useFenetreAdresse('poste')
  const etat = useEtatListe('pq', [])
  const q = etat.recherche.valeur
  const lignes = useMemo(
    () => (lu.data ?? []).filter((p) => trouve([p.code, p.libelle], q)).sort(parOrdre),
    [lu.data, q],
  )
  const actions = ecrit ? (
    <Bouton variante="principal" icone="plus" onClick={() => fen.ouvrir('nouveau')}>
      Nouveau poste
    </Bouton>
  ) : null
  return (
    <Carte
      titre="Postes de frais d’importation"
      sous="Les frais d’un dossier d’importation : récupérables ou non, répartis à la valeur ou au poids."
      actions={actions}
      serre
      remplir
    >
      <div className={styles.tete}>
        <Note>
          Un frais global d’un dossier se répartit entre ses marchandises <strong>à la valeur</strong> (au
          prorata de ce que vaut chaque marchandise) ou <strong>au poids</strong> (au prorata de ses kilos),
          selon le réglage de son poste. Un poste récupérable (la TVA) reste hors du coût. Changer une clé
          recalcule les dossiers ouverts ; les dossiers clos gardent leur répartition.{' '}
          {ecrit ? 'Cliquer sur un poste pour le modifier.' : 'Cliquer sur un poste pour le consulter.'}
        </Note>
      </div>
      {lu.isPending ? <Chargement quoi="les postes de frais" /> : null}
      {lu.isError ? <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} /> : null}
      {lu.data ? (
        <DataTable<PosteFiche>
          libelle="Postes de frais"
          lignes={lignes}
          colonnes={COLONNES}
          cle={(p) => p.id}
          recherche={etat.recherche}
          choix={etat.choix}
          placeholder="Code, libellé…"
          cliquable={(p) => fen.ouvrir(p.id)}
          vide={lu.data.length ? 'Aucun poste ne correspond.' : 'Aucun poste de frais.'}
        />
      ) : null}
      <FenetreDemandee fen={fen} postes={lu.data} ecrit={ecrit} />
    </Carte>
  )
}
