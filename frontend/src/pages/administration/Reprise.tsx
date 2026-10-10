/**
 * Administration › Reprise (`/administration?onglet=reprise`, lot C1, routes 243–244) : le miroir
 * de Gestion MP. Tant que PRO n'est pas mis en service, sa base reflète celle de Gestion MP ;
 * l'onglet dit si le miroir est à jour (signature de la source = celle de la dernière reprise),
 * si PRO porte une activité saisie chez lui, et liste les dernières reprises. La direction
 * rafraîchit le miroir (une sauvegarde « avant reprise » est faite d'abord) ; une activité
 * saisie dans PRO ne se remplace qu'en cochant « Remplacer l'activité » et en tapant REMPLACER.
 * L'administrateur technique voit l'état, sans le rapport (il cite des matières et des valeurs).
 */
import { useState } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api } from '../../lib/api'
import { horodatage, nombre } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Schema } from '../../lib/types'
import styles from './administration.module.css'

type Etat = Schema<'EtatMiroir'>
type Execution = Schema<'ExecutionMiroir'>

export const MOT_REMPLACER = 'REMPLACER'
/** Le temps entre deux lectures de l'état pendant une reprise. */
export const PAS_DU_MIROIR = 2000

const STATUTS: Readonly<Record<string, { libelle: string; ton: 'ok' | 'critique' | 'accent' }>> = {
  reussie: { libelle: 'réussie', ton: 'ok' },
  echouee: { libelle: 'échouée', ton: 'critique' },
  en_cours: { libelle: 'en cours', ton: 'accent' },
}

function colonnes(voir: (e: Execution) => void): Colonne<Execution>[] {
  return [
    { cle: 'debut', titre: 'Commencée le', rendu: (e) => horodatage(e.debut) },
    {
      cle: 'statut',
      titre: 'Issue',
      rendu: (e) => {
        const s = STATUTS[e.statut] ?? { libelle: e.statut, ton: 'accent' as const }
        return <Badge ton={s.ton}>{s.libelle}</Badge>
      },
    },
    { cle: 'base_source', titre: 'Depuis' },
    { cle: 'mode', titre: 'Mode' },
    { cle: 'creees', titre: 'Lignes créées', droite: true, rendu: (e) => nombre(e.creees) },
    {
      cle: 'duree_s',
      titre: 'Durée',
      droite: true,
      rendu: (e) => (e.duree_s == null ? '—' : `${nombre(e.duree_s, 1)} s`),
    },
    {
      cle: 'geste',
      titre: '',
      triable: false,
      exporte: false,
      rendu: (e) =>
        e.rapport ? (
          <Bouton taille="petit" onClick={() => voir(e)}>
            Rapport
          </Bouton>
        ) : null,
    },
  ]
}

/** Ce que l'état dit en une phrase, et son ton. */
export function verdict(e: Etat): { ton: 'ok' | 'attention' | 'critique' | 'info'; texte: string } {
  if (e.en_cours) return { ton: 'info', texte: 'Une reprise est en cours : l’état se met à jour seul.' }
  if (!e.source_lisible) return { ton: 'critique', texte: e.message_source }
  if (!e.derniere_reussie)
    return {
      ton: 'attention',
      texte: `Aucune reprise réussie : PRO ne reflète pas encore « ${e.base_source} ».`,
    }
  if (e.a_jour)
    return {
      ton: 'ok',
      texte: `Le miroir est à jour : « ${e.base_source} » n’a pas changé depuis la reprise du ${horodatage(e.derniere_reussie.debut)}.`,
    }
  return {
    ton: 'attention',
    texte: `Gestion MP a changé depuis la reprise du ${horodatage(e.derniere_reussie.debut)} : rafraîchir le miroir pour comparer les deux logiciels sur les mêmes données.`,
  }
}

/** Le pied de la fenêtre : « Annuler » et « Rafraîchir maintenant » (grisé avec sa raison). */
function PiedRafraichir({
  remplacer,
  manque,
  onLancer,
  onFermer,
}: {
  remplacer: boolean
  manque: string[]
  onLancer: () => Promise<void>
  onFermer: () => void
}) {
  return (
    <>
      <Bouton onClick={onFermer}>Annuler</Bouton>
      <Bouton
        variante={remplacer ? 'danger' : 'principal'}
        manque={manque}
        attente="Reprise demandée…"
        onClick={onLancer}
      >
        Rafraîchir maintenant
      </Bouton>
    </>
  )
}

function FenetreRafraichir({ e, onFermer }: { e: Etat; onFermer: () => void }) {
  const [remplacer, setRemplacer] = useState(false)
  const [mot, setMot] = useState('')
  const lancer = useEcriture(() =>
    api.post('/reprise', {
      mode: 'tout',
      remplacer_activite: remplacer,
      ...(remplacer ? { confirmation: mot.trim() } : {}),
    }),
  )
  const manque = [
    ...(e.activite_propre && !remplacer ? ['cocher « Remplacer l’activité saisie dans PRO »'] : []),
    ...(remplacer && mot.trim().toUpperCase() !== MOT_REMPLACER ? [`le mot ${MOT_REMPLACER}`] : []),
  ]
  const lancerReprise = async () => {
    await lancer.mutateAsync()
    dire('Reprise commencée : sauvegarde « avant reprise », puis la reprise.')
    onFermer()
  }
  return (
    <Fenetre
      titre="Rafraîchir le miroir de Gestion MP"
      onFermer={onFermer}
      pied={
        <PiedRafraichir remplacer={remplacer} manque={manque} onLancer={lancerReprise} onFermer={onFermer} />
      }
    >
      <ul className={styles.liste}>
        <li>{`Les référentiels et toute l’activité de « ${e.base_source} » sont repris dans « ${e.base} » (Gestion MP n’est que lu).`}</li>
        <li>
          Une sauvegarde « avant reprise » de PRO est faite d’abord : on peut y revenir (onglet Sauvegardes).
        </li>
        <li>Tout se fait en une transaction : si un contrôle n’est pas tenu, rien ne change.</li>
      </ul>
      {e.activite_propre ? (
        <Note ton="critique">
          PRO contient une activité saisie chez lui (elle ne vient pas de la dernière reprise) : elle sera
          remplacée par celle de Gestion MP.
        </Note>
      ) : null}
      <label className={styles.case}>
        <input type="checkbox" checked={remplacer} onChange={(x) => setRemplacer(x.target.checked)} />
        Remplacer l’activité saisie dans PRO
      </label>
      {remplacer ? (
        <Champ libelle={`Taper ${MOT_REMPLACER}`} obligatoire>
          <Saisie valeur={mot} max={20} onChange={setMot} autoFocus />
        </Champ>
      ) : null}
    </Fenetre>
  )
}

function CarteEtat({
  e,
  direction,
  onRafraichir,
}: {
  e: Etat
  direction: boolean
  onRafraichir: () => void
}) {
  const v = verdict(e)
  return (
    <Carte
      titre="Le miroir de Gestion MP"
      actions={
        direction ? (
          <Bouton
            variante="principal"
            grise={
              e.en_cours
                ? 'Une reprise est déjà en cours.'
                : e.source_lisible
                  ? undefined
                  : 'La base de Gestion MP ne se lit pas.'
            }
            onClick={onRafraichir}
          >
            Rafraîchir le miroir…
          </Bouton>
        ) : null
      }
    >
      <Note ton={v.ton}>{v.texte}</Note>
      {e.activite_propre ? (
        <Note ton="attention">
          PRO contient une activité saisie chez lui : un rafraîchissement la remplacerait (confirmation
          REMPLACER).
        </Note>
      ) : null}
      <p className={styles.note}>
        {`Source : ${e.base_source} (lue seulement) → ${e.base}. Signature actuelle : `}
        <span className={styles.code}>{e.signature_source ? e.signature_source.slice(0, 16) : '—'}</span>
        {' ; dernière reprise : '}
        <span className={styles.code}>{e.derniere_reussie?.empreinte_source?.slice(0, 16) ?? '—'}</span>
        {
          '. En ligne de commande : make miroir ; comparer les deux logiciels : outils/comparer_avec_gestion_mp.py.'
        }
      </p>
    </Carte>
  )
}

export function Reprise() {
  const { role } = useSession()
  const lu = useLecture<Etat>('/reprise', undefined, {
    refetchInterval: (q) => (q.state.data?.en_cours ? PAS_DU_MIROIR : false),
  })
  const [rafraichir, setRafraichir] = useState(false)
  const [rapport, setRapport] = useState<Execution | null>(null)
  if (lu.isPending) return <Chargement quoi="l’état du miroir" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const e = lu.data
  return (
    <>
      <CarteEtat e={e} direction={role === 'direction'} onRafraichir={() => setRafraichir(true)} />
      <Carte titre="Les dernières reprises" serre remplir>
        <DataTable<Execution>
          libelle="Reprises"
          lignes={e.executions}
          colonnes={colonnes(setRapport)}
          cle={(x) => String(x.id)}
          recherche={false}
          triInitial={{ cle: 'debut', sens: -1 }}
          vide="Aucune reprise pour le moment."
        />
      </Carte>
      {rafraichir ? <FenetreRafraichir e={e} onFermer={() => setRafraichir(false)} /> : null}
      {rapport ? (
        <Fenetre
          titre={`Rapport de la reprise du ${horodatage(rapport.debut)}`}
          onFermer={() => setRapport(null)}
        >
          <pre className={styles.code}>{rapport.rapport}</pre>
        </Fenetre>
      ) : null}
    </>
  )
}
