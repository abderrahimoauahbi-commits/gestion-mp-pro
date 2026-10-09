/**
 * Stock › À valider (`/stock?onglet=a-valider`) : tous les brouillons qui feront bouger le stock
 * (réceptions, ordres, opérations), du plus ancien au plus récent, avec ce qui les ferait refuser
 * (`blocages` du serveur) et qui les valide (`valide_par`). « Tout valider (N) » ne compte **que ce
 * qui sera validé** (P2-12, H-23) : les brouillons que le rôle peut valider et que rien ne bloque ;
 * il n'envoie qu'eux, à leur version, et dit ce qui est passé et ce qui est resté en brouillon.
 */
import { useState } from 'react'
import { Link } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Confirmer } from '../../composants/saisie/Confirmer'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { api } from '../../lib/api'
import { formule } from '../../lib/aide'
import { date, horodatage, nombre } from '../../lib/format'
import { permis } from '../../lib/droits'
import { useEcriture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Role } from '../../lib/types'
import { Double } from './cellules'
import { useBrouillons } from './donnees'
import styles from './stock.module.css'
import type { Brouillon, Brouillons, ResultatValidationGroupee } from './types'

export const CLES_A_VALIDER = ['genre', 'auteur', 'refuses'] as const

/** Ce que « Tout valider » enverra : permis au rôle, sans blocage annoncé. */
export const seraValide = (b: Brouillon) => b.peut_valider && !b.blocages.length

const GENRES: Record<string, string> = { reception: 'Réceptions', ordre: 'Ordres', operation: 'Opérations' }

function colonnes(role: Role): Colonne<Brouillon>[] {
  return [
    { cle: 'date', titre: 'Date', valeur: (b) => b.date, rendu: (b) => date(b.date) },
    {
      cle: 'libelle',
      titre: 'Document',
      valeur: (b) => b.libelle,
      rendu: (b) => <Double haut={b.libelle} bas="Brouillon" />,
    },
    { cle: 'resume', titre: 'Contenu', valeur: (b) => b.resume },
    {
      cle: 'quantite',
      titre: 'Quantité (kg)',
      droite: true,
      valeur: (b) => b.quantite,
      rendu: (b) => nombre(b.quantite, 1),
    },
    {
      cle: 'par',
      titre: 'Par',
      valeur: (b) => b.cree_par,
      rendu: (b) => <Double haut={b.cree_par} bas={b.cree_le ? horodatage(b.cree_le) : undefined} />,
    },
    {
      cle: 'validation',
      titre: 'À la validation',
      valeur: (b) => (b.blocages.length ? 1 : 0),
      recherche: (b) => [...b.blocages, b.valide_par],
      rendu: (b) => (
        <span>
          {b.blocages.length ? (
            <ul className={styles.blocages}>
              {b.blocages.map((x) => (
                <li key={x}>sera refusé : {x}</li>
              ))}
            </ul>
          ) : (
            <Badge ton="ok">passera</Badge>
          )}
          {!b.peut_valider ? (
            <span className={styles.dessous}>{b.raison || `validé par ${b.valide_par}`}</span>
          ) : null}
        </span>
      ),
    },
    {
      cle: 'ouvrir',
      titre: '',
      triable: false,
      exporte: false,
      rendu: (b) =>
        permis(role, b.lien) ? (
          <Link to={b.lien} title="Ouvrir le brouillon pour le corriger ou le valider seul">
            Ouvrir
          </Link>
        ) : null,
    },
  ]
}

/** Le bilan de « Tout valider » : ce qui est passé, ce qui est resté en brouillon et pourquoi. */
function Bilan({ r, role }: { r: ResultatValidationGroupee; role: Role }) {
  const restes = [...r.refuses, ...r.ignores]
  return (
    <Note ton={restes.length ? 'attention' : 'ok'}>
      {r.valides.length} brouillon(s) validé(s)
      {r.valides.length ? ` : ${r.valides.map((x) => x.numero).join(', ')}` : ''}.
      {restes.length ? ` ${restes.length} resté(s) en brouillon :` : ''}
      {restes.length ? (
        <ul className={styles.blocages}>
          {restes.map((x) => (
            <li key={`${x.genre}${x.id}`}>
              {permis(role, x.lien) ? <Link to={x.lien}>{x.libelle}</Link> : x.libelle} du {date(x.date)} —{' '}
              {x.raison}
            </li>
          ))}
        </ul>
      ) : null}
    </Note>
  )
}

const FILTRES: Filtre<Brouillon>[] = [
  { cle: 'genre', libelle: 'Document', valeur: (x) => x.genre, libelleValeur: (g) => GENRES[g] ?? g },
  { cle: 'auteur', libelle: 'Par', valeur: (x) => x.cree_par },
]

function IndicateursAValider({ b }: { b: Brouillons }) {
  return (
    <Indicateurs>
      <Kpi
        titre="Brouillons"
        valeur={nombre(b.nombre)}
        detail="le stock n’a pas bougé"
        formule={formule('brouillons')}
      />
      <Kpi
        titre="Seraient refusés"
        valeur={nombre(b.bloques)}
        detail={b.bloques ? 'lot épuisé, stock insuffisant, date…' : 'aucun blocage annoncé'}
        ton={b.bloques ? 'critique' : 'ok'}
        formule={formule('brouillons_bloques')}
      />
      <Kpi
        titre="Que vous pouvez valider"
        valeur={nombre(b.validables)}
        detail="selon votre rôle, sans blocage"
        formule={formule('brouillons_validables')}
      />
    </Indicateurs>
  )
}

/** Le texte du bilan de « Tout valider », dit aussi en message. */
export function bilanTexte(r: ResultatValidationGroupee): string {
  const restes = r.refuses.length + r.ignores.length
  const numeros = r.valides.length ? ` : ${r.valides.map((x) => x.numero).join(', ')}` : ''
  return `${r.valides.length} brouillon(s) validé(s)${numeros}.${restes ? ` ${restes} resté(s) en brouillon.` : ''}`
}

/** « Tout valider (N) » : N = ce qui sera validé, et seulement cela part (à sa version). */
function ToutValider({
  partants,
  onBilan,
}: {
  partants: readonly Brouillon[]
  onBilan: (r: ResultatValidationGroupee) => void
}) {
  const valider = useEcriture((documents: { genre: string; id: number; version: number }[]) =>
    api.post<ResultatValidationGroupee>('/brouillons/valider', { documents }),
  )
  const toutValider = async () => {
    const r = await valider.mutateAsync(
      partants.map((x) => ({ genre: x.genre, id: x.id, version: x.version })),
    )
    onBilan(r)
    dire(bilanTexte(r), r.refuses.length + r.ignores.length ? 'attention' : 'succes')
  }
  return (
    <Confirmer
      variante="principal"
      grise={partants.length ? undefined : 'Aucun brouillon que votre rôle peut valider sans blocage.'}
      question={`Valider ${partants.length} brouillon(s), du plus ancien au plus récent ? Ceux qui sont refusés restent en brouillon.`}
      oui="Oui, tout valider"
      titre="Valide chaque brouillon que votre rôle permet et que rien ne bloque, dans l’ordre des dates ; le stock bouge pour chacun"
      onOui={toutValider}
    >
      Tout valider ({partants.length})
    </Confirmer>
  )
}

export function OngletAValider() {
  const { role } = useSession()
  const brouillons = useBrouillons()
  const table = useEtatTableAdresse(CLES_A_VALIDER)
  const [bilan, setBilan] = useState<ResultatValidationGroupee | null>(null)
  if (brouillons.isPending) return <Chargement quoi="les brouillons" />
  if (brouillons.isError)
    return <Erreur erreur={brouillons.error} onReessayer={() => void brouillons.refetch()} />
  const b = brouillons.data
  const seulementRefuses = table.choix.valeurs.refuses === '1'
  return (
    <>
      <IndicateursAValider b={b} />
      <Carte
        titre="À valider"
        actions={<ToutValider partants={b.lignes.filter(seraValide)} onBilan={setBilan} />}
        serre
        remplir
        className={styles.carteListe}
      >
        {bilan ? <Bilan r={bilan} role={role} /> : null}
        <DataTable<Brouillon>
          libelle="Brouillons à valider"
          lignes={b.lignes.filter((x) => !seulementRefuses || x.blocages.length)}
          colonnes={colonnes(role)}
          filtres={FILTRES}
          cle={(x) => `${x.genre}${x.id}`}
          recherche={table.recherche}
          choix={table.choix}
          marquee={(x) => x.blocages.length > 0}
          placeholder="Type, matière, motif, personne, raison…"
          vide={
            b.lignes.length
              ? 'Aucun brouillon ne correspond.'
              : 'Aucun brouillon : tout ce qui a été saisi est validé.'
          }
          outils={
            <label className={styles.case}>
              <input
                type="checkbox"
                checked={seulementRefuses}
                onChange={(e) => table.choix.poser('refuses', e.target.checked ? '1' : null)}
              />
              Seulement ceux qui seraient refusés
            </label>
          }
        />
      </Carte>
    </>
  )
}
