/**
 * Réglages › Période close (`/reglages?onglet=periode`) : la date jusqu'à laquelle rien ne s'écrit
 * plus. La direction la pose (au plus hier, à l'heure de l'usine), la recule ou la rouvre — chaque
 * fois dans une `FenetreConfirmation` qui dit l'effet, **motif obligatoire** (P8-9, H-18) ; route 26
 * à la version lue. Les achats lisent la date ; la direction lit aussi l'historique des clôtures
 * (date avant → après, motif, par, quand).
 */
import { useState } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Definitions } from '../../composants/mise-en-page/Definitions'
import { FenetreConfirmation } from '../../composants/mise-en-page/FenetreConfirmation'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api } from '../../lib/api'
import { date, horodatage, nombre } from '../../lib/format'
import { jourDansN } from '../../lib/heure'
import { useEcriture, useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import type { Reglage } from './parametres/logique'
import styles from './reglages.module.css'

type Changement = Schema<'ReglageHistorique'>

const COLONNES: readonly Colonne<Changement>[] = [
  { cle: 'quand', titre: 'Quand', rendu: (c) => horodatage(c.quand) },
  { cle: 'avant', titre: 'Avant', rendu: (c) => (c.avant ? date(c.avant) : 'aucune') },
  { cle: 'apres', titre: 'Après', rendu: (c) => (c.apres ? date(c.apres) : 'rouverte') },
  { cle: 'motif', titre: 'Motif' },
  { cle: 'par', titre: 'Par' },
]

/** Ce que la fenêtre dit avant de clore (ou de reculer la date). */
export function texteCloture(jour: string, actuelle: string | null) {
  const recul = actuelle && jour < actuelle
  return (
    <>
      {recul ? (
        <p>{`Vous rouvrez du ${date(jour)} (exclu) au ${date(actuelle)} : ces jours redeviennent ouverts à l’écriture.`}</p>
      ) : null}
      <p>{`Après la clôture, plus rien ne s’écrira au ${date(jour)} ni avant :`}</p>
      <ul className={styles.liste}>
        <li>
          aucune écriture datée de la période (réceptions, sorties, opérations, inventaires, règlements) ;
        </li>
        <li>aucun coût d’une marchandise importée entrée dans la période (dossiers d’importation) ;</li>
        <li>
          les brouillons datés de la période doivent être validés, supprimés ou redatés d’abord — sinon la
          clôture est refusée.
        </li>
      </ul>
      <p>
        Pour corriger un mois clos, la direction rouvre la période (c’est tracé), on saisit, puis elle la
        referme.
      </p>
    </>
  )
}

function Historique() {
  const p = useListePaginee<Changement>('/parametres/historique', { cle: 'date_cloture' })
  return (
    <DataTable<Changement>
      libelle="Historique des clôtures"
      lignes={p.lignes}
      colonnes={COLONNES}
      cle={(c) => c.id}
      recherche={false}
      serveur
      total={p.total}
      chargerPlus={p.chargerPlus}
      vide={p.requete.isPending ? 'Chargement…' : 'Aucune clôture pour le moment.'}
    />
  )
}

type Geste = { genre: 'clore'; jour: string } | { genre: 'rouvrir' } | null

interface GestesProps {
  actuelle: string | null
  onGeste: (g: Geste) => void
}

type BrouillonsPeriode = Schema<'BrouillonsPeriode'>

/**
 * Les brouillons datés jusqu'à la date choisie, annoncés avant la fenêtre (route 246) : « Clore la
 * période… » est grisé avec le refus que dirait le serveur, et la liste dit lesquels valider ou
 * supprimer (ou redater) d'abord.
 */
function useBrouillonsPeriode(jour: string) {
  const lu = useLecture<BrouillonsPeriode>(jour ? '/periode-close/brouillons' : null, { date: jour })
  return jour ? lu.data : undefined
}

function NoteBrouillons({ b }: { b: BrouillonsPeriode | undefined }) {
  if (!b?.total) return null
  return (
    <Note ton="attention">
      {`${nombre(b.total)} brouillon(s) datés jusqu’au ${date(b.jusqu_au)} : `}
      {b.genres
        .filter((g) => g.nombre > 0)
        .map((g) => `${nombre(g.nombre)} ${g.libelle}(s)`)
        .join(', ')}
      . Les valider, les supprimer ou les redater d’abord.
    </Note>
  )
}

/** La date à poser (au plus hier, à l'heure de l'usine), « Clore la période… », « Rouvrir… ». */
function GestesPeriode({ actuelle, onGeste }: GestesProps) {
  const hier = jourDansN(-1)
  const [jour, setJour] = useState('')
  const brouillons = useBrouillonsPeriode(jour && jour <= hier ? jour : '')
  const grise =
    jour && jour > hier
      ? `On ne clôt qu’une période passée : au plus tard hier (${date(hier)}).`
      : jour === actuelle
        ? 'C’est déjà la date de clôture.'
        : undefined
  return (
    <>
      <div className={styles.rangee}>
        <span className={styles.champDate}>
          <DateChamp libelle="Clore jusqu’au" valeur={jour} max={hier} onChange={setJour} />
        </span>
        <Bouton
          variante="principal"
          manque={jour ? [] : ['la date de clôture']}
          blocages={brouillons?.message ? [brouillons.message] : undefined}
          grise={grise}
          onClick={() => onGeste({ genre: 'clore', jour })}
        >
          Clore la période…
        </Bouton>
        <Bouton
          grise={actuelle ? undefined : 'Aucune période close à rouvrir.'}
          onClick={() => onGeste({ genre: 'rouvrir' })}
        >
          Rouvrir la période…
        </Bouton>
      </div>
      <NoteBrouillons b={brouillons} />
    </>
  )
}

interface ConfirmationProps {
  geste: Geste
  actuelle: string | null
  clore: (jour: string | null, motif: string) => Promise<void>
  onFermer: () => void
}

/** La fenêtre qui dit l'effet et reçoit le motif (obligatoire). */
function Confirmation({ geste, actuelle, clore, onFermer }: ConfirmationProps) {
  if (geste?.genre === 'clore') {
    return (
      <FenetreConfirmation
        titre={`Clore la période jusqu’au ${date(geste.jour)} ?`}
        texte={texteCloture(geste.jour, actuelle)}
        oui="Clore la période"
        motif="exige"
        onOui={(motif) => clore(geste.jour, motif)}
        onFermer={onFermer}
      />
    )
  }
  if (geste?.genre === 'rouvrir') {
    return (
      <FenetreConfirmation
        titre="Rouvrir la période ?"
        texte={
          <p>{`La période close jusqu’au ${date(actuelle)} redevient ouverte à l’écriture. Le motif est tracé.`}</p>
        }
        oui="Rouvrir la période"
        motif="exige"
        variante="danger"
        onOui={(motif) => clore(null, motif)}
        onFermer={onFermer}
      />
    )
  }
  return null
}

export function PeriodeClose({ reglage, direction }: { reglage: Reglage | undefined; direction: boolean }) {
  const actuelle = reglage?.valeur || null
  const [geste, setGeste] = useState<Geste>(null)
  const ecrire = useEcriture((e: { date_cloture: string | null; motif: string }) =>
    api.put('/periode-close', { ...e, version: reglage?.version ?? 0 }),
  )
  const clore = async (date_cloture: string | null, motif: string) => {
    await ecrire.mutateAsync({ date_cloture, motif })
    dire(
      date_cloture
        ? `Période close jusqu’au ${date(date_cloture)}.`
        : 'Période rouverte : rien n’est plus clos.',
    )
  }
  return (
    <Carte titre="Période close" remplir className={styles.carteListe}>
      <div className={styles.periode}>
        <Definitions
          colonnes={1}
          items={[['Période close jusqu’au', actuelle ? date(actuelle) : 'Aucune période close']]}
        />
        <Note>
          Rien ne s’écrit plus à cette date ni avant : une écriture datée de la période est refusée, et le
          coût d’une marchandise importée entrée dans la période ne change plus.
        </Note>
        {direction ? <GestesPeriode actuelle={actuelle} onGeste={setGeste} /> : null}
      </div>
      {direction ? <Historique /> : null}
      <Confirmation geste={geste} actuelle={actuelle} clore={clore} onFermer={() => setGeste(null)} />
    </Carte>
  )
}
