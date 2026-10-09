/**
 * Fiche d'ordre (`/ordres/:id`, fenêtre sur `/sorties`) : qui, où, ce qu'on tisse, le prévu par la
 * recette, le sorti net (retours déduits), l'écart ; ce qui ferait refuser un brouillon ; les lots
 * sortis ou à sortir, et le prévu face au sorti matière par matière. Gestes (direction,
 * alimentation) : supprimer, modifier, valider un brouillon ; faire un retour, annuler un ordre
 * validé (contre-passation, retours compris).
 */
import { useNavigate } from 'react-router'

import { Historique } from '../../composants/documents/Historique'
import { LienDocument } from '../../composants/documents/LienDocument'
import { Bascule, useVueAdresse } from '../../composants/mise-en-page/Bascule'
import { Definitions } from '../../composants/mise-en-page/Definitions'
import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Blocages } from '../../composants/saisie/Blocages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { api } from '../../lib/api'
import { formule } from '../../lib/aide'
import { date, horodatage, kg, kgEtMetres, m2, nombreSigne } from '../../lib/format'
import { permis } from '../../lib/droits'
import { useEcriture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { adresseSuivi } from '../stock/navigation'
import styles from '../stock/stock.module.css'
import { useOrdre, type OrdreFiche } from './donnees'
import { EcartRecette, tonEcart } from './ecart'
import { LotsDeLOrdre, PrevuParMatiere } from './VuesOrdre'

export const titreOrdre = (o: Pick<OrdreFiche, 'numero' | 'date'>) =>
  o.numero ? `${o.numero} — ${date(o.date)}` : `Brouillon du ${date(o.date)}`

function IndicateursOrdre({ o }: { o: OrdreFiche }) {
  const brouillon = o.statut === 'brouillon'
  return (
    <Indicateurs libelle="Indicateurs de l’ordre">
      <Kpi
        titre="Fabrication"
        valeur={o.qualites.length ? m2(o.m2) : 'hors recette'}
        detail={
          o.qualites.map((q) => `${q.qualite} ${m2(q.m2)}`).join(' · ') || 'échantillons, série spéciale'
        }
        formule={formule('fabrication_ordre')}
      />
      <Kpi
        titre="Prévu par la recette"
        valeur={o.prevu ? kg(o.prevu) : brouillon ? 'à la validation' : '—'}
        formule={formule('prevu_recette')}
      />
      <Kpi
        titre={brouillon ? 'À sortir' : 'Sorti net'}
        valeur={kg(brouillon ? o.total : o.net)}
        detail={o.revenu ? `${kg(o.total)} sortis, dont ${kg(o.revenu)} revenus` : undefined}
        formule={formule('sorti_net')}
      />
      <Kpi
        titre="Écart"
        valeur={<EcartRecette relatif={o.ecart_relatif} />}
        detail={o.ecart != null ? `${nombreSigne(o.ecart, 1)} kg` : undefined}
        ton={tonEcart(o.ecart_relatif)}
        formule={formule('ecart_recette')}
      />
    </Indicateurs>
  )
}

function Qui({ o }: { o: OrdreFiche }) {
  return (
    <Definitions
      colonnes={3}
      items={[
        ['Magasin', o.magasin],
        ['Métier', o.metier],
        ['Par', `${o.cree_par}${o.cree_le ? ` le ${horodatage(o.cree_le)}` : ''}`],
        ...(o.valide_par
          ? ([
              ['Validé par', `${o.valide_par}${o.valide_le ? ` le ${horodatage(o.valide_le)}` : ''}`],
            ] as const)
          : []),
        ...(o.annule_par
          ? ([
              [
                'Annulé par',
                `${o.annule_par}${o.annule_le ? ` le ${horodatage(o.annule_le)}` : ''}${o.annulation_motif ? ` : « ${o.annulation_motif} »` : ''}`,
              ],
            ] as const)
          : []),
        ['Commentaire', o.commentaire],
      ]}
    />
  )
}

function GestesBrouillon({
  o,
  onModifier,
  onFermer,
}: {
  o: OrdreFiche
  onModifier: () => void
  onFermer: () => void
}) {
  const supprimer = useEcriture(() => api.supprimer(`/ordres/${o.id}?version=${o.version}`))
  const valider = useEcriture(() => api.post<OrdreFiche>(`/ordres/${o.id}/valider`, { version: o.version }))
  return (
    <>
      <Confirmer
        variante="danger"
        question="Supprimer ce brouillon ?"
        oui="Oui, supprimer"
        titre="Supprimer le brouillon : rien n’a bougé au stock"
        onOui={async () => {
          await supprimer.mutateAsync()
          dire('Brouillon supprimé.')
          onFermer()
        }}
      >
        Supprimer
      </Confirmer>
      <Bouton titre="Rouvrir la saisie : qualités, lots, quantités" onClick={onModifier}>
        Modifier
      </Bouton>
      <Confirmer
        variante="principal"
        blocages={o.blocages}
        question={`Sortir ${kg(o.total)} du stock ?`}
        oui="Oui, valider"
        titre="Valider : le stock sort et l’ordre reçoit son numéro"
        onOui={async () => {
          const v = await valider.mutateAsync()
          dire(`Ordre ${v.numero ?? ''} validé : le stock est sorti.`)
        }}
      >
        Valider la sortie
      </Confirmer>
    </>
  )
}

function GestesValide({ o }: { o: OrdreFiche }) {
  const navigate = useNavigate()
  const annuler = useEcriture((motif: string) =>
    api.post<OrdreFiche>(`/ordres/${o.id}/annuler`, { version: o.version, motif }),
  )
  const retours = o.retours.map((r) => r.numero).filter(Boolean)
  return (
    <>
      <Bouton
        titre="Ce qui revient des machines, lot par lot"
        onClick={() => navigate(`/ordres/${o.id}/retour`)}
      >
        Faire un retour
      </Bouton>
      <Confirmer
        variante="danger"
        motif="facultatif"
        question={
          retours.length
            ? `Annuler l’ordre et ses retours (${retours.join(', ')}) ? La matière sortie revient en stock, une seule fois, à la date de l’ordre.`
            : 'Annuler l’ordre ? Toute sa matière revient en stock, à la date de l’ordre.'
        }
        oui="Oui, annuler (contre-passation)"
        titre="Annuler (contre-passation) : une écriture inverse remet la matière en stock"
        onOui={async (motif) => {
          const r = await annuler.mutateAsync(motif)
          dire(r.message || 'Ordre annulé.')
        }}
      >
        Annuler (contre-passation)
      </Confirmer>
    </>
  )
}

function Gestes({
  o,
  onModifier,
  onFermer,
}: {
  o: OrdreFiche
  onModifier: () => void
  onFermer: () => void
}) {
  const { role } = useSession()
  const navigate = useNavigate()
  const fermer = useFermerFenetre()
  const ecrit = role === 'direction' || role === 'alimentation'
  return (
    <>
      {o.numero ? (
        <Bouton
          titre="Quelles matières et quels lots sont partis dans cet ordre, et d’où ils venaient"
          onClick={() => navigate(adresseSuivi({ ordre: o.id }, `/ordres/${o.id}`))}
        >
          Traçabilité de l’ordre
        </Bouton>
      ) : null}
      <span className={styles.pousse} />
      {ecrit && o.statut === 'brouillon' ? (
        <GestesBrouillon o={o} onModifier={onModifier} onFermer={onFermer} />
      ) : null}
      {ecrit && o.statut === 'valide' ? <GestesValide o={o} /> : null}
      <Bouton onClick={fermer}>Fermer</Bouton>
    </>
  )
}

function Corps({ o }: { o: OrdreFiche }) {
  const { role } = useSession()
  const [vue, setVue] = useVueAdresse(['lots', 'matieres', 'historique'] as const, 'lots')
  const brouillon = o.statut === 'brouillon'
  return (
    <>
      <Qui o={o} />
      <IndicateursOrdre o={o} />
      <Blocages blocages={o.blocages} titre="Sera refusé à la validation :" />
      <div className={styles.rangee}>
        <Bascule
          vues={[
            { cle: 'lots', libelle: `${brouillon ? 'Lots à sortir' : 'Lots sortis'} (${o.lignes.length})` },
            {
              cle: 'matieres',
              libelle: `Prévu par la recette et sorti net, par matière (${o.par_matiere.length})`,
            },
            { cle: 'historique', libelle: 'Historique' },
          ]}
          valeur={vue}
          onChange={setVue}
          libelle="Vue de l’ordre"
        />
        {o.retours.length ? (
          <span className={styles.note}>
            Retours :{' '}
            {o.retours.map((r, i) => (
              <span key={`${r.numero}${i}`}>
                {i ? ' · ' : ''}
                {r.id != null && permis(role, `/operations/${r.id}`) ? (
                  <LienDocument genre="operation" id={r.id} numero={r.numero} />
                ) : (
                  r.numero || 'retour repris de l’ERP Fil'
                )}{' '}
                du {date(r.date)} ({kgEtMetres(r.quantite)})
              </span>
            ))}
          </span>
        ) : null}
      </div>
      {vue === 'lots' ? <LotsDeLOrdre o={o} /> : null}
      {vue === 'matieres' ? (
        o.par_matiere.length ? (
          <PrevuParMatiere o={o} />
        ) : (
          <Note>{brouillon ? 'Calculé à la validation.' : 'Ordre hors recette : rien à comparer.'}</Note>
        )
      ) : null}
      {vue === 'historique' ? <Historique objet="ordre" id={o.id} /> : null}
      {o.message ? <Note>{o.message}</Note> : null}
    </>
  )
}

export function FicheOrdre({
  id,
  onFermer,
  onModifier,
}: {
  id: number
  onFermer: () => void
  onModifier: () => void
}) {
  const fiche = useOrdre(id)
  const o = fiche.data
  const titre = o ? (
    <>
      {titreOrdre(o)} <Badge famille="ordre" valeur={o.statut} />
    </>
  ) : (
    'Ordre'
  )
  return (
    <Fenetre
      titre={titre}
      sous={o?.qualites.map((q) => `${q.qualite} — ${q.nom}`).join(' · ') || undefined}
      taille="tresLarge"
      onFermer={onFermer}
      pied={o ? <Gestes o={o} onModifier={onModifier} onFermer={onFermer} /> : undefined}
    >
      {fiche.isPending ? <Chargement quoi="l’ordre" /> : null}
      {fiche.isError ? <Erreur erreur={fiche.error} onReessayer={() => void fiche.refetch()} /> : null}
      {o ? <Corps o={o} /> : null}
    </Fenetre>
  )
}
