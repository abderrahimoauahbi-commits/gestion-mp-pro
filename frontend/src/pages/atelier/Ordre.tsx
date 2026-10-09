/**
 * Le détail d'un ordre à l'atelier (`/atelier/ordres/:id`) : identité, matière à sortir ou sortie
 * lot par lot (n° de lot touchable), retours, ce qui sera refusé ; gestes selon le statut (valider,
 * modifier, supprimer un brouillon ; faire un retour, annuler un validé). Un 404 dit « Ordre
 * introuvable » avec l'en-tête ; une coupure dit « Pas de réseau » (an. 3).
 */
import { Link, useLocation, useNavigate, useParams } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { LienDocument } from '../../composants/documents/LienDocument'
import { dire } from '../../composants/retour/Messages'
import { Badge } from '../../composants/retour/Badge'
import { Note } from '../../composants/retour/Note'
import { Vide } from '../../composants/retour/Vide'
import { Blocages } from '../../composants/saisie/Blocages'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { horodatage, kgEtMetres, m2 } from '../../lib/format'
import { api } from '../../lib/api'
import { permis } from '../../lib/droits'
import { useEcriture, useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { attente, Fiche, LienBouton, Ligne, NoteAtelier } from './briques'
import { dateLisible, estIntrouvable, qte, useNomMetier } from './commun'
import styles from './atelier.module.css'
import type { OrdreFiche } from './types'

/** Les retours d'un ordre, chacun lien vers sa fiche d'opération quand le rôle peut l'ouvrir. */
function Retours({ o }: { o: OrdreFiche }) {
  const { role } = useSession()
  return o.retours.map((r, i) => (
    <span key={`${r.numero}${i}`}>
      {i ? ', ' : ''}
      {r.id != null && permis(role, `/operations/${r.id}`) ? (
        <LienDocument genre="operation" id={r.id} numero={r.numero} />
      ) : (
        r.numero || `retour repris de l’ERP Fil du ${dateLisible(r.date)}`
      )}
    </span>
  ))
}

/** « Annuler tout l'ordre et ses retours (RET-…) ? … » : la question dit ce qui revient. */
export function questionAnnuler(o: OrdreFiche): string {
  if (!o.retours.length)
    return 'Annuler tout l’ordre ? Toute sa matière revient en stock, à la date de l’ordre.'
  const numeros = o.retours.map((r) => r.numero || `retour repris de l’ERP Fil du ${dateLisible(r.date)}`)
  return (
    `Annuler tout l’ordre et ses retours (${numeros.join(', ')}) ? La matière sortie revient en stock, ` +
    'une seule fois, à la date de l’ordre.'
  )
}

function Identite({ o }: { o: OrdreFiche }) {
  const nomMetier = useNomMetier()
  const par = [`créé par ${o.cree_par} le ${horodatage(o.cree_le)}`]
  if (o.valide_par) par.push(`validé par ${o.valide_par} le ${horodatage(o.valide_le)}`)
  if (o.annule_par) par.push(`annulé par ${o.annule_par} le ${horodatage(o.annule_le)}`)
  return (
    <Fiche>
      <Ligne libelle="Statut">
        <Badge famille="ordre" valeur={o.statut} />
      </Ligne>
      <Ligne libelle="Date">{dateLisible(o.date)}</Ligne>
      <Ligne libelle="Magasin">{o.magasin}</Ligne>
      {o.metier_id ? <Ligne libelle="Métier">{nomMetier(o.metier_id, o.metier)}</Ligne> : null}
      {o.qualites.length ? (
        o.qualites.map((q) => (
          <Ligne key={q.qualite_id} libelle={`${q.qualite} — ${q.nom}`}>
            {m2(q.m2)}
          </Ligne>
        ))
      ) : (
        <Ligne libelle="Fabrication">hors recette</Ligne>
      )}
      {o.commentaire ? <Ligne libelle="Observations">{o.commentaire}</Ligne> : null}
      <NoteAtelier>Par : {par.join(' ; ')}</NoteAtelier>
    </Fiche>
  )
}

function Matiere({ o }: { o: OrdreFiche }) {
  return (
    <Fiche titre={o.statut === 'brouillon' ? 'Matière à sortir' : 'Matière sortie'}>
      {o.lignes.map((l) => (
        <Ligne
          key={l.id}
          libelle={
            <>
              {l.reference} /{' '}
              <Link className={styles.lienTexte} to={`/atelier/lots/${l.lot_id}`}>
                lot {l.lot}
              </Link>
            </>
          }
        >
          {kgEtMetres(l.quantite, l.kg_par_ml, true)}
        </Ligne>
      ))}
      <Ligne libelle={<strong>Total</strong>}>
        <strong>{qte(o.total)}</strong>
      </Ligne>
      {o.revenu ? <Ligne libelle="dont revenu des machines">− {qte(o.revenu)}</Ligne> : null}
      {o.retours.length ? (
        <NoteAtelier>
          Retours faits sur cet ordre : <Retours o={o} />
        </NoteAtelier>
      ) : null}
    </Fiche>
  )
}

function GestesBrouillon({ o, ou }: { o: OrdreFiche; ou: string }) {
  const naviguer = useNavigate()
  const valider = useEcriture(() => api.post<OrdreFiche>(`/ordres/${o.id}/valider`, { version: o.version }))
  const supprimer = useEcriture(() => api.supprimer(`/ordres/${o.id}?version=${o.version}`))
  return (
    <div className={styles.gestes}>
      <Confirmer
        taille="atelier"
        variante="principal"
        grise={o.blocages.length ? 'Validation impossible pour l’instant (voir « Sera refusé »)' : undefined}
        question={`Sortir ${qte(o.total)} le ${ou} ? Le stock est débité tout de suite.`}
        oui="Oui, valider"
        onOui={async () => {
          await valider.mutateAsync()
          dire('Sortie validée.')
        }}
      >
        Valider la sortie
      </Confirmer>
      <LienBouton vers={`/atelier/envoyer?ordre=${o.id}`}>Modifier le brouillon</LienBouton>
      <Confirmer
        taille="atelier"
        variante="danger"
        question="Supprimer ce brouillon ? Rien n’est sorti du stock."
        oui="Oui, supprimer"
        onOui={async () => {
          await supprimer.mutateAsync()
          dire('Brouillon supprimé.')
          void naviguer('/atelier/ordres', { replace: true })
        }}
      >
        Supprimer le brouillon
      </Confirmer>
    </div>
  )
}

function Gestes({ o }: { o: OrdreFiche }) {
  const nomMetier = useNomMetier()
  const annuler = useEcriture((motif: string) =>
    api.post<OrdreFiche>(`/ordres/${o.id}/annuler`, { version: o.version, motif }),
  )
  const ou = [dateLisible(o.date), o.magasin, nomMetier(o.metier_id, o.metier)].filter(Boolean).join(' · ')
  if (o.statut === 'brouillon') return <GestesBrouillon o={o} ou={ou} />
  if (o.statut !== 'valide') return null
  return (
    <div className={styles.gestes}>
      <LienBouton principal vers={`/atelier/retour?ordre=${o.id}`}>
        Faire un retour sur cet ordre
      </LienBouton>
      <Confirmer
        taille="atelier"
        variante="danger"
        motif="facultatif"
        question={questionAnnuler(o)}
        oui="Oui, annuler (contre-passation)"
        onOui={async (motif) => {
          const r = await annuler.mutateAsync(motif)
          dire(r.message || 'Ordre annulé : la matière est revenue en stock.')
        }}
      >
        Annuler l’ordre (erreur de saisie)
      </Confirmer>
    </div>
  )
}

/** La note laissée par l'écran d'envoi (ordre qui ne se modifie plus). */
function noteDe(state: unknown): string {
  return typeof state === 'object' && state !== null && 'note' in state && typeof state.note === 'string'
    ? state.note
    : ''
}

export default function Ordre() {
  const { id } = useParams()
  const { state } = useLocation()
  const ordre = useLecture<OrdreFiche>(`/ordres/${id}`)
  const note = noteDe(state)
  if (ordre.isError && estIntrouvable(ordre.error))
    return (
      <EcranAtelier titre="Ordre introuvable" retour="/atelier/ordres">
        <Vide>Cet ordre n’existe pas (brouillon supprimé ?).</Vide>
      </EcranAtelier>
    )
  const o = ordre.data
  const titre = !o ? 'Ordre' : o.statut === 'brouillon' ? 'Brouillon' : (o.numero ?? 'Ordre')
  return (
    <EcranAtelier titre={titre} retour="/atelier/ordres">
      {attente([ordre], 'l’ordre') ??
        (o ? (
          <>
            {note ? <Note>{note}</Note> : null}
            <Identite o={o} />
            <Matiere o={o} />
            {o.blocages.length ? <Blocages blocages={o.blocages} /> : null}
            <Gestes o={o} />
          </>
        ) : null)}
    </EcranAtelier>
  )
}
