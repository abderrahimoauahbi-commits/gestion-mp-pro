/**
 * Analyse › Contrôles (`/analyse?onglet=controles`) : les 38 contrôles de cohérence, leur
 * synthèse, quoi faire pour chacun ; un contrôle non conforme s'ouvre en fenêtre à adresse stable
 * (`&controle=Cxx`) avec **tout** son détail, page par page (route 235). La pastille du menu et le
 * compteur de l'onglet comptent les contrôles à corriger (`a_corriger`, sans « pour information »).
 * Adresse : `cq` (recherche), `toutes` (montrer aussi les conformes).
 */
import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router'

import { Carte } from '../../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../../composants/retour/Badge'
import { Chargement } from '../../../composants/retour/Chargement'
import { Erreur } from '../../../composants/retour/Erreur'
import { Kpi } from '../../../composants/retour/Kpi'
import { Note } from '../../../composants/retour/Note'
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { avecParametre } from '../../../lib/adresse'
import { formule } from '../../../lib/aide'
import { date, kg, nombre, part, VIDE } from '../../../lib/format'
import { statut, type Ton } from '../../../lib/statuts'
import { useEtatListe } from '../../catalogue/etatListe'
import styles from '../analyse.module.css'
import { Case, Criteres } from '../briques'
import { useControles, useSoldes } from '../donnees'
import type { ControleResume, Controles as C, ControleSoldes } from '../types'
import { DetailControle } from './DetailControle'

const RANG: Readonly<Record<string, number>> = { bloquant: 0, avertissement: 1, information: 2 }

export const libelleGravite = (g: string) => statut('controle', g).libelle

/** Le ton du nombre d'anomalies : critique si bloquant, neutre si pour information, sinon attention. */
export function tonControle(c: ControleResume): Ton {
  if (c.garanti) return 'neutre'
  if (c.conforme) return 'ok'
  if (c.gravite === 'bloquant') return 'critique'
  if (c.gravite === 'information') return 'neutre'
  return 'attention'
}

/** Non conformes d'abord, puis par gravité. */
export function trierControles(liste: readonly ControleResume[]): ControleResume[] {
  return [...liste].sort(
    (a, b) => Number(a.conforme) - Number(b.conforme) || (RANG[a.gravite] ?? 3) - (RANG[b.gravite] ?? 3),
  )
}

const COLONNES: readonly Colonne<ControleResume>[] = [
  { cle: 'code', titre: 'Code', rendu: (c) => <span className={styles.code}>{c.code}</span> },
  { cle: 'libelle', titre: 'Ce qui est vérifié' },
  {
    cle: 'gravite',
    titre: 'Gravité',
    valeur: (c) => libelleGravite(c.gravite),
    rendu: (c) => <Badge famille="controle" valeur={c.gravite} />,
  },
  {
    cle: 'anomalies',
    titre: 'Anomalies',
    droite: true,
    rendu: (c) =>
      c.garanti ? (
        <span className={styles.note} title={c.garanti}>
          garanti par la base
        </span>
      ) : c.conforme ? (
        <Badge ton="ok">OK</Badge>
      ) : (
        <Badge ton={tonControle(c)}>{nombre(c.anomalies)}</Badge>
      ),
  },
  {
    cle: 'quoi_faire',
    titre: 'Quoi faire',
    rendu: (c) =>
      c.garanti ? (
        <span className={styles.note}>{`Ne peut pas sonner : ${c.garanti}`}</span>
      ) : c.conforme ? (
        VIDE
      ) : (
        c.quoi_faire
      ),
  },
]

function IndicateursControles({ c, soldes }: { c: C; soldes: ReturnType<typeof useSoldes> }) {
  const s = c.synthese
  const so = soldes.data
  return (
    <Indicateurs libelle="Indicateurs des contrôles">
      <Kpi
        titre="Score"
        valeur={part(s.score, 0)}
        ton={s.bloquants ? 'critique' : s.a_corriger ? 'attention' : 'ok'}
        detail={`${nombre(s.conformes)} conformes sur ${nombre(s.total)} vérifiés${s.garantis ? ` · ${nombre(s.garantis)} garantis par la base` : ''}`}
        exact={`Au ${date(c.date_reference)}`}
        formule={formule('controles_score')}
      />
      <Kpi
        titre="À corriger"
        valeur={nombre(s.a_corriger)}
        ton={s.a_corriger ? 'attention' : 'ok'}
        detail={`contrôles à revoir · ${nombre(s.anomalies - s.a_corriger)} pour information`}
        formule={formule('controles_anomalies')}
      />
      <Kpi
        titre="Bloquants"
        valeur={nombre(s.bloquants)}
        ton={s.bloquants ? 'critique' : 'ok'}
        detail={s.bloquants ? 'le pilotage en est faussé' : 'aucun'}
        formule={formule('controles_bloquants')}
      />
      <Kpi
        titre="Soldes et journal"
        valeur={soldes.isPending ? '…' : so ? (so.conforme ? 'Concordants' : 'Écart !') : VIDE}
        ton={so ? (so.conforme ? 'ok' : 'critique') : undefined}
        detail={
          so
            ? so.conforme
              ? `${nombre(so.lots)} soldes = journal`
              : `${nombre(so.ecarts.length)} écart(s), ${nombre(so.negatifs)} solde(s) négatif(s)`
            : undefined
        }
        formule={formule('controles_soldes')}
      />
    </Indicateurs>
  )
}

function AlerteSoldes({ s }: { s: ControleSoldes }) {
  return (
    <Note ton="critique">
      {`Le stock tenu ne retombe pas sur le journal des mouvements (${nombre(s.ecarts.length)} lot(s) en écart, ${nombre(s.negatifs)} solde(s) négatif(s)). Une écriture a contourné le chemin normal : prévenir l’administrateur technique avant toute nouvelle saisie.`}
      <ul className={styles.lignes}>
        {s.ecarts.slice(0, 8).map((e) => (
          <li key={`${e.lot_id}-${e.magasin_id}`}>
            <Link to={`/lots/${e.lot_id}`}>lot {e.lot}</Link>, magasin {e.magasin} : journal {kg(e.journal)},
            solde {kg(e.solde)}
          </li>
        ))}
      </ul>
    </Note>
  )
}

/** Le bandeau des bloquants, sur une ligne, au-dessus du tableau. */
function Bloquants({ codes }: { codes: readonly string[] }) {
  if (!codes.length) return null
  const texte = `${nombre(codes.length)} bloquant(s) : le pilotage est faussé tant que ${codes.join(', ')} n’${codes.length > 1 ? 'ont' : 'a'} pas été corrigé(s).`
  return (
    <Note ton="critique" uneLigne={texte}>
      {texte}
    </Note>
  )
}

function Detail({ code, c, onFermer }: { code: string; c: C; onFermer: () => void }) {
  return <DetailControle code={code} resume={c.controles.find((x) => x.code === code)} onFermer={onFermer} />
}

export function Controles() {
  const lu = useControles()
  const soldes = useSoldes()
  const [params, setParams] = useSearchParams()
  const etat = useEtatListe('cq', ['toutes'])
  const toutes = etat.lire('toutes') === '1'
  const ouvert = params.get('controle')
  const lignes = useMemo(
    () => trierControles((lu.data?.controles ?? []).filter((c) => toutes || !c.conforme)),
    [lu.data, toutes],
  )
  if (lu.isPending) return <Chargement quoi="les contrôles" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const ouvrir = (code: string | null) => setParams((p) => avecParametre(p, 'controle', code))
  const bloquants = lu.data.controles
    .filter((c) => !c.conforme && c.gravite === 'bloquant')
    .map((c) => c.code)
  const n = (etat.recherche.valeur.trim() ? 1 : 0) + (toutes ? 1 : 0)
  return (
    <>
      <IndicateursControles c={lu.data} soldes={soldes} />
      {soldes.data && !soldes.data.conforme ? <AlerteSoldes s={soldes.data} /> : null}
      <Carte
        titre={`Les contrôles — ${nombre(lignes.length)} affiché(s)`}
        serre
        remplir
        className={styles.carteListe}
      >
        <Bloquants codes={bloquants} />
        <DataTable<ControleResume>
          libelle="Contrôles de cohérence"
          lignes={lignes}
          colonnes={COLONNES}
          cle={(c) => c.code}
          recherche={etat.recherche}
          placeholder="Code, libellé, gravité… plusieurs mots"
          cliquable={(c) => (c.conforme ? undefined : ouvrir(c.code))}
          vide={
            toutes ? 'Aucun contrôle ne correspond.' : 'Aucune anomalie : tous les contrôles sont conformes.'
          }
          exporter={{ route: '/export/controles' }}
          outils={
            <>
              <Case valeur={!toutes} onChange={(v) => etat.choix.poser('toutes', v ? null : '1')}>
                seulement les anomalies
              </Case>
              <Criteres nombre={n} onEffacer={etat.choix.effacer} />
            </>
          }
        />
      </Carte>
      {ouvert ? <Detail code={ouvert} c={lu.data} onFermer={() => ouvrir(null)} /> : null}
    </>
  )
}
