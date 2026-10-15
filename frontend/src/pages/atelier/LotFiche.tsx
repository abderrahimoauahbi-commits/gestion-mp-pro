/**
 * La fiche d'un lot à l'atelier (`/atelier/lots/:id`, arrivée du QR `/lot/:id`) : ce qui reste,
 * où, les ordres servis, ce qu'il a vécu (30 mouvements puis « charger les suivants ») ;
 * « Déplacer ce lot », « Imprimer l'étiquette » (100 × 70 mm, nouvel onglet) ; sur un fond de lot
 * (reste sous le seuil de rebut, marqué), « Mettre au rebut » par magasin, hors quarantaine
 * (lot FOND-DE-LOT ; aucun montant). « Lot introuvable » sur un 404 seulement ; une coupure dit
 * « Pas de réseau » (an. 3). Aucun prix (an. 27).
 */
import { useState } from 'react'
import { Link, useParams } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { BoutonImprimer } from '../../composants/documents/BoutonImprimer'
import { Badge } from '../../composants/retour/Badge'
import { Bouton } from '../../composants/saisie/Bouton'
import { date, kgEtMetres, nombre, poidsBobine } from '../../lib/format'
import { permis } from '../../lib/droits'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { bobinesApprochees } from '../../lib/unites'
import { marqueFond, soldesFonds } from '../stock/fonds'
import { BoutonRebut } from '../stock/Rebut'
import { attente, Fiche, LienBouton, Ligne, NoteAtelier } from './briques'
import { estIntrouvable, qte } from './commun'
import styles from './atelier.module.css'
import { ChargerSuivants } from './Ordres'
import type { LotFiche as Lot, MouvementLigne } from './types'

const PAGE_MOUVEMENTS = 30

/** Un seul libellé de quarantaine : « Quarantaine », jamais « Quarantaine quarantaine » (REGLES 6.4). */
export function libelleMagasin(m: { magasin: string; type: string }): { nom: string; quarantaine: boolean } {
  const quarantaine = m.type === 'quarantaine'
  return { nom: m.magasin, quarantaine: quarantaine && !/quarantaine/i.test(m.magasin) }
}

/** Les mouvements du plus récent au plus ancien. */
export const recents = (m: readonly MouvementLigne[]) =>
  [...m].sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id)

/**
 * Le n° du document d'un mouvement : un ordre mène à sa fiche de l'atelier, une opération
 * (transfert, retour) à sa fiche quand le rôle peut l'ouvrir ; le reste se lit tel quel.
 */
export function NumeroMouvement({ m }: { m: MouvementLigne }) {
  const { role } = useSession()
  if (!m.document_numero) return null
  const vers =
    m.document === 'ordre' && m.document_id != null
      ? `/atelier/ordres/${m.document_id}`
      : m.document === 'operation' && m.document_id != null && permis(role, `/operations/${m.document_id}`)
        ? `/operations/${m.document_id}`
        : null
  return vers ? <Link to={vers}>{m.document_numero}</Link> : <>{m.document_numero}</>
}

function Mouvements({ l }: { l: Lot }) {
  const [nb, setNb] = useState(PAGE_MOUVEMENTS)
  const liste = recents(l.mouvements)
  return (
    <Fiche titre="Ce qu’il a vécu">
      {l.reception ? (
        <NoteAtelier>
          Reçu le {date(l.reception.date)} ({l.reception.numero}
          {l.reception.bl ? `, BL ${l.reception.bl}` : ''}) — pesé {qte(l.reception.pesee)}
        </NoteAtelier>
      ) : null}
      {liste.slice(0, nb).map((m) => (
        <div key={m.id} className={styles.ligne}>
          <span>
            {date(m.date)} · {m.libelle}
            <br />
            <span className={styles.note}>
              <NumeroMouvement m={m} />
              {m.document_numero ? ' · ' : ''}
              {[m.magasin, m.auteur ? `par ${m.auteur}` : ''].filter(Boolean).join(' · ')}
            </span>
          </span>
          <span className={styles.valeur}>
            {m.quantite > 0 ? '+' : '−'}
            {kgEtMetres(Math.abs(m.quantite), l.kg_par_ml, true)}
          </span>
        </div>
      ))}
      <ChargerSuivants
        montres={Math.min(nb, liste.length)}
        total={liste.length}
        onCharger={() => setNb(nb + PAGE_MOUVEMENTS)}
      />
    </Fiche>
  )
}

function Identite({ l }: { l: Lot }) {
  const { contexte } = useSession()
  return (
    <Fiche titre={l.reference} ton={l.quantite <= 0.001 ? 'alerte' : undefined}>
      <Badge famille="lot" valeur={l.statut} />
      {l.fond_de_lot ? (
        <>
          {' '}
          <Badge ton="attention">{marqueFond(contexte.seuil_rebut) || 'fond de lot'}</Badge>
        </>
      ) : null}
      <NoteAtelier>
        {[l.role, l.fournisseur, `entré le ${date(l.entre_le)}`].filter(Boolean).join(' · ')}
      </NoteAtelier>
      <Ligne libelle="Reste" grand>
        {kgEtMetres(l.quantite, l.kg_par_ml, true)}
      </Ligne>
      {l.poids_bobine ? (
        <Ligne libelle="Bobines">
          {`${bobinesApprochees(l.quantite, { poidsBobine: l.poids_bobine })} de ${poidsBobine(l.poids_bobine)}`}
        </Ligne>
      ) : null}
      {l.magasins.map((m) => {
        const x = libelleMagasin(m)
        return (
          <Ligne
            key={m.magasin_id}
            libelle={
              <>
                {x.nom} {x.quarantaine ? <Badge ton="critique">quarantaine</Badge> : null}{' '}
                {m.fond_de_lot ? <Badge ton="attention">fond de lot</Badge> : null}
              </>
            }
          >
            {qte(m.quantite)}
          </Ligne>
        )
      })}
      {l.historique.ordres.length ? (
        <div>
          Ordres servis :{' '}
          {l.historique.ordres.map((o, i) => (
            <span key={o.id}>
              {i ? ', ' : ''}
              <Link className={styles.lienTexte} to={`/atelier/ordres/${o.id}`}>
                {o.numero}
              </Link>
            </span>
          ))}
        </div>
      ) : null}
    </Fiche>
  )
}

export default function LotFiche() {
  const { id } = useParams()
  const lot = useLecture<Lot>(`/lots/${id}`)
  if (lot.isError && estIntrouvable(lot.error))
    return (
      <EcranAtelier titre="Lot introuvable" retour="/atelier/chercher">
        <NoteAtelier>Ce lot n’existe pas (étiquette d’une autre installation, ou lot supprimé).</NoteAtelier>
        <LienBouton principal vers="/atelier/chercher">
          Chercher un lot
        </LienBouton>
      </EcranAtelier>
    )
  const l = lot.data
  return (
    <EcranAtelier titre={l ? `Lot ${l.lot}` : 'Lot'}>
      {attente([lot], 'le lot') ??
        (l ? (
          <>
            <Identite l={l} />
            <div className={styles.gestes}>
              {l.disponible > 0.001 ? (
                <LienBouton principal vers={`/atelier/deplacer?lot=${l.lot_id}`}>
                  Déplacer ce lot
                </LienBouton>
              ) : (
                <Bouton taille="atelier" bloc grise="Rien de disponible hors quarantaine">
                  Déplacer ce lot
                </Bouton>
              )}
              <BoutonImprimer
                taille="atelier"
                route="/documents/etiquettes"
                parametres={{ lots: l.lot_id }}
                libelle="Imprimer l’étiquette"
                titre="L’étiquette 100 × 70 mm s’ouvre dans un nouvel onglet, prête à imprimer"
              />
              {soldesFonds(l).map((g) => (
                <BoutonRebut key={g.magasin_id} l={l} g={g} taille="atelier" />
              ))}
            </div>
            {soldesFonds(l).length ? (
              <NoteAtelier>
                Fond de lot : ce reste n’est plus proposé par « Envoyer aux machines ». « Mettre au rebut » le
                sort du stock (ajustement « Rebut », validé tout de suite).
              </NoteAtelier>
            ) : null}
            <Mouvements l={l} />
            <NoteAtelier>{`${nombre(l.mouvements.length)} mouvement(s) en tout.`}</NoteAtelier>
          </>
        ) : null)}
    </EcranAtelier>
  )
}
