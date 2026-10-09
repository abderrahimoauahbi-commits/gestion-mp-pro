/**
 * Les deux vues du suivi : le prévu par la recette et le sorti net d'un ordre, matière par matière ;
 * les mouvements (le plus récent en haut), où un lot, un ordre ou une matière se suit d'un clic.
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import { Note } from '../../composants/retour/Note'
import { Vide } from '../../composants/retour/Vide'
import { Cadre } from '../../composants/tableaux/Cadre'
import { date, nombre, VIDE } from '../../lib/format'
import { useSession } from '../../lib/session'
import type { Schema } from '../../lib/types'
import { ecartRelatif } from '../sorties/ecart'
import { TablePrevuSorti } from '../sorties/VuesOrdre'
import { Signe } from './cellules'
import { lienMouvement } from './MouvementsDuLot'
import type { Suivi } from './donnees'
import styles from './stock.module.css'
import type { EtapeTracee, Tracabilite } from './types'

type Consommation = Schema<'ConsommationOrdre'>

function Lien({ texte, titre, onClick }: { texte: string; titre: string; onClick: () => void }) {
  return (
    <button type="button" className={styles.lien} title={titre} onClick={onClick}>
      {texte}
    </button>
  )
}

export function ParMatiere({
  ordre,
  onSuivre,
  idMatiere,
}: {
  ordre: Consommation
  onSuivre: (s: Suivi) => void
  idMatiere: ReadonlyMap<string, number>
}) {
  const lignes = ordre.references.map((r) => ({
    ...r,
    matiere_id: r.matiere_id ?? idMatiere.get(r.reference) ?? null,
  }))
  return (
    <>
      <Note>
        Tissé sous cet ordre : {ordre.qualites.map((q) => `${q.qualite} — ${nombre(q.m2)} m²`).join(' · ')}.
        Matière par matière, ce que prévoyaient les recettes et ce qui est sorti net.
      </Note>
      <TablePrevuSorti
        lignes={lignes}
        totaux={{ ...ordre, ecart_relatif: ordre.ecart_relatif ?? ecartRelatif(ordre.net, ordre.prevu) }}
        onSuivre={(matiere) => onSuivre({ matiere })}
      />
    </>
  )
}

/** Un lot, un ordre ou une matière qu'on suit d'un clic, sauf celui qu'on suit déjà. */
function Suivable({
  texte,
  cible,
  titre,
  onSuivre,
}: {
  texte: string
  cible: Suivi | null
  titre: string
  onSuivre: (s: Suivi) => void
}) {
  if (!texte) return <span className={styles.nul}>{VIDE}</span>
  return cible ? <Lien texte={texte} titre={titre} onClick={() => onSuivre(cible)} /> : <>{texte}</>
}

function Libelle({ m }: { m: EtapeTracee }) {
  const marque = m.annulation ? 'annulation' : m.annule ? 'annulé' : ''
  return (
    <>
      {m.libelle}
      {marque ? (
        <>
          {' '}
          <Badge ton="neutre">{marque}</Badge>
        </>
      ) : null}
    </>
  )
}

interface Liens {
  suivi: Suivi
  onSuivre: (s: Suivi) => void
}

/** Le document d'une étape, lien vers sa fiche quand le rôle peut l'ouvrir (ids servis depuis RESTES3). */
function DocumentEtape({ m }: { m: EtapeTracee }) {
  const { role } = useSession()
  const vers = lienMouvement(
    { document: m.document_type ?? '', document_id: m.document_id, ordre_id: null },
    role,
  )
  return vers ? <Link to={vers}>{m.document}</Link> : <>{m.document}</>
}

function Mouvement({ m, l }: { m: EtapeTracee; l: Liens }) {
  const matiere = m.matiere_id != null && l.suivi.matiere !== m.matiere_id ? m.matiere_id : undefined
  const ordre = m.ordre_id ?? undefined
  return (
    <tr>
      <td className={styles.nowrap}>{date(m.date)}</td>
      <td>
        <Libelle m={m} />
      </td>
      <td className={styles.mono}>
        <DocumentEtape m={m} />
      </td>
      <td>
        <Suivable
          texte={m.reference}
          cible={matiere ? { matiere } : null}
          titre="Suivre cette matière"
          onSuivre={l.onSuivre}
        />
      </td>
      <td className={styles.droite}>
        <Signe v={m.quantite} neutre={m.type === 'TRANSFERT'} />
      </td>
      <td className={styles.nowrap}>
        <Suivable
          texte={m.lot}
          cible={m.lot_id && l.suivi.lot !== m.lot_id ? { lot: m.lot_id } : null}
          titre="Suivre ce lot"
          onSuivre={l.onSuivre}
        />
      </td>
      <td className={styles.nowrap}>
        <Suivable
          texte={m.ordre}
          cible={ordre && l.suivi.ordre !== ordre ? { ordre } : null}
          titre="Suivre cet ordre"
          onSuivre={l.onSuivre}
        />
      </td>
      <td className={styles.note}>{[m.magasin_source, m.magasin_destination].filter(Boolean).join(' → ')}</td>
      <td className={styles.note}>{m.utilisateur}</td>
    </tr>
  )
}

export function PasDuSuivi({
  t,
  suivi,
  onSuivre,
}: {
  t: Tracabilite
  suivi: Suivi
  onSuivre: (s: Suivi) => void
}) {
  if (!t.mouvements.length) return <Vide>Aucun mouvement.</Vide>
  const lignes = [...t.mouvements].reverse()
  return (
    <>
      <Note>
        Le plus récent en haut. Cliquer un lot, un ordre ou une matière suit la matière de l’autre côté.
      </Note>
      <Cadre hauteur="fenetre">
        <table className={styles.tableSimple} aria-label="Mouvements suivis">
          <thead>
            <tr>
              <th>Date</th>
              <th>Mouvement</th>
              <th>Document</th>
              <th>Référence</th>
              <th className={styles.droite}>Quantité (kg)</th>
              <th>Lot</th>
              <th>Ordre</th>
              <th>Magasin</th>
              <th>Par</th>
            </tr>
          </thead>
          <tbody>
            {lignes.map((m, i) => (
              <Mouvement key={m.id ?? `r${i}`} m={m} l={{ suivi, onSuivre }} />
            ))}
          </tbody>
        </table>
      </Cadre>
    </>
  )
}
