/**
 * La fiche d'une réclamation en fenêtre (`/reclamations/:id?onglet=reponse|pieces|historique`,
 * ECRANS-PRO 4.24) : ce qui est en cause, la réponse du fournisseur et ce qui est obtenu ; clore
 * avec l'issue (confirmé), rouvrir (motif au journal). Sur une close, l'issue est en lecture ; la
 * réponse et l'avoir obtenu se complètent encore (l'avoir arrive après la clôture).
 */
import { Link } from 'react-router'

import { Historique } from '../../composants/documents/Historique'
import { PiecesJointes } from '../../composants/documents/PiecesJointes'
import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer, MOTIF_MIN } from '../../composants/saisie/Confirmer'
import { Nombre } from '../../composants/saisie/Nombre'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { Zone } from '../../composants/saisie/Zone'
import { api } from '../../lib/api'
import { useOngletAdresse } from '../../lib/adresse'
import { formule } from '../../lib/aide'
import { date, kg, montant, nombre, VIDE } from '../../lib/format'
import { useEcriture } from '../../lib/requetes'
import { memeForme, useFormeFiche, type FormeFiche } from '../commandes/useFormeFiche'
import styles from '../plan-achat/achats.module.css'
import { useMotifs, useReclamation } from './donnees'
import type { ReclamationFiche } from './types'

const VOLETS = ['reponse', 'pieces', 'historique'] as const
type Volet = (typeof VOLETS)[number]

interface FormeReponse {
  issue: string
  montant: number | null
  reponse: string
}

const versForme = (r: ReclamationFiche): FormeReponse => ({
  issue: r.issue ?? '',
  montant: r.montant_obtenu || null,
  reponse: r.reponse,
})

function IndicateursReclamation({ r }: { r: ReclamationFiche }) {
  const ouverte = r.statut === 'ouverte'
  return (
    <Indicateurs libelle="Indicateurs de la réclamation">
      <Kpi
        titre="Motif"
        valeur={r.motif_libelle}
        formule={formule('reclamation_motif')}
        detail={`ouverte le ${date(r.ouverte_le)} par ${r.cree_par || '—'}`}
      />
      <Kpi
        titre="En cause"
        valeur={r.quantite ? kg(r.quantite) : VIDE}
        formule={formule('reclamation_en_cause')}
        detail={
          r.reception_id ? (
            <>
              <Link to={`/receptions/${r.reception_id}`}>réception {r.reception || 'Brouillon'}</Link>
              {r.lot_id ? (
                <>
                  {' · '}
                  <Link to={`/lots/${r.lot_id}`}>lot {r.lot}</Link>
                </>
              ) : null}
            </>
          ) : (
            'sans réception'
          )
        }
      />
      <Kpi
        titre="Demandé / obtenu"
        valeur={`${r.montant_demande ? montant(r.montant_demande, r.devise) : VIDE} / ${r.montant_obtenu ? montant(r.montant_obtenu, r.devise) : VIDE}`}
        formule={formule('reclamation_montants')}
      />
      <Kpi
        titre="Durée"
        valeur={`${nombre(r.jours)} j`}
        formule={formule('reclamation_duree')}
        ton={ouverte && r.jours > 30 ? 'critique' : undefined}
        detail={ouverte ? 'depuis l’ouverture' : `close le ${date(r.close_le)}`}
      />
    </Indicateurs>
  )
}

function VoletReponse({ r, f }: { r: ReclamationFiche; f: FormeFiche<FormeReponse, ReclamationFiche> }) {
  const motifs = useMotifs()
  const close = r.statut !== 'ouverte'
  return (
    <div className={styles.volet}>
      <Grille colonnes={2}>
        <Champ
          libelle="Issue"
          aide={
            close ? 'close : elle garde son issue (la rouvrir pour la reprendre)' : 'obligatoire pour clore'
          }
        >
          {close ? (
            <Badge famille="issue_reclamation" valeur={r.issue} />
          ) : (
            <Selecteur<string>
              valeur={f.forme.issue || null}
              placeholder="— pas encore —"
              options={(motifs.data?.reclamation_issues ?? []).map((i) => ({ id: i.code, titre: i.libelle }))}
              onChange={(issue) => f.maj({ issue: issue ?? '' })}
            />
          )}
        </Champ>
        <Champ libelle={`Montant obtenu (${r.devise})`} aide="avoir, remise">
          <Nombre
            valeur={f.forme.montant}
            onChange={(montant) => f.maj({ montant })}
            min={0}
            decimales={2}
            unite={r.devise}
          />
        </Champ>
      </Grille>
      <Champ libelle="Réponse du fournisseur" large>
        <Zone
          valeur={f.forme.reponse}
          onChange={(reponse) => f.maj({ reponse })}
          max={4000}
          placeholder="ce qu’il a répondu, ce qui est convenu (avoir n°, remplacement par le prochain conteneur…)"
        />
      </Champ>
    </div>
  )
}

type Forme = FormeFiche<FormeReponse, ReclamationFiche>
type Ecrire = (envoi: () => Promise<ReclamationFiche>) => Promise<ReclamationFiche>

function Clore({ r, f, ecrire }: { r: ReclamationFiche; f: Forme; ecrire: Ecrire }) {
  const motifs = useMotifs()
  const libelleIssue =
    motifs.data?.reclamation_issues.find((i) => i.code === f.forme.issue)?.libelle ?? f.forme.issue
  return (
    <Confirmer
      variante="principal"
      manque={f.forme.issue ? undefined : ['l’issue (choisissez-la d’abord)']}
      titre="La réclamation est terminée"
      question={`Clore avec l’issue « ${libelleIssue} » ?`}
      oui="Oui, clore"
      onOui={async () => {
        const corps = {
          version: f.version,
          issue: f.forme.issue,
          montant_obtenu: f.forme.montant,
          reponse: f.forme.reponse.trim(),
        }
        f.repartir(await ecrire(() => api.post<ReclamationFiche>(`/reclamations/${r.id}/clore`, corps)))
        dire(`Réclamation close : ${libelleIssue}.`)
      }}
    >
      Clore la réclamation
    </Confirmer>
  )
}

function Rouvrir({ r, f, ecrire }: { r: ReclamationFiche; f: Forme; ecrire: Ecrire }) {
  return (
    <Confirmer
      motif="exige"
      motifMin={MOTIF_MIN}
      variante="neutre"
      titre="La réclamation redevient ouverte : on attend de nouveau le fournisseur"
      question="Rouvrir cette réclamation ?"
      libelleMotif="Pourquoi la rouvrir"
      motifMax={300}
      oui="Oui, rouvrir"
      onOui={async (motif) => {
        f.repartir(
          await ecrire(() =>
            api.post<ReclamationFiche>(`/reclamations/${r.id}/rouvrir`, { version: r.version, motif }),
          ),
        )
        dire('Réclamation rouverte.')
      }}
    >
      Rouvrir
    </Confirmer>
  )
}

function Gestes({ r, f }: { r: ReclamationFiche; f: Forme }) {
  const fermer = useFermerFenetre()
  const m = useEcriture((envoi: () => Promise<ReclamationFiche>) => envoi())
  const ecrire: Ecrire = (envoi) => m.mutateAsync(envoi)
  const reponseChangee = f.forme.reponse !== f.initiale.reponse || f.forme.montant !== f.initiale.montant
  return (
    <div className={styles.pied}>
      <Bouton
        variante="principal"
        attente="Enregistrement…"
        grise={reponseChangee ? undefined : 'Rien n’a changé.'}
        onClick={async () => {
          const corps = {
            version: f.version,
            reponse: f.forme.reponse.trim(),
            montant_obtenu: f.forme.montant,
          }
          f.repartir(await ecrire(() => api.put<ReclamationFiche>(`/reclamations/${r.id}`, corps)))
          dire('Réponse enregistrée.')
        }}
      >
        Enregistrer la réponse
      </Bouton>
      <span className={styles.pousse} />
      {r.statut === 'ouverte' ? (
        <Clore r={r} f={f} ecrire={ecrire} />
      ) : (
        <Rouvrir r={r} f={f} ecrire={ecrire} />
      )}
      <Bouton onClick={fermer}>Fermer</Bouton>
    </div>
  )
}

function Ecrite({ r, onFermer }: { r: ReclamationFiche; onFermer: () => void }) {
  const [volet, choisir] = useOngletAdresse<Volet>(VOLETS, 'reponse')
  const f = useFormeFiche(r, versForme, memeForme)
  return (
    <Fenetre
      titre={
        <span className={styles.rangeeCentree}>
          Réclamation {r.numero} — {r.fournisseur}{' '}
          {r.statut === 'ouverte' ? (
            <Badge famille="reclamation" valeur="ouverte" />
          ) : (
            <Badge ton="neutre">{`close : ${r.issue_libelle}`}</Badge>
          )}
        </span>
      }
      taille="large"
      sale={f.sale}
      onFermer={onFermer}
      pied={<Gestes r={r} f={f} />}
    >
      <IndicateursReclamation r={r} />
      {r.description ? <Note>Constaté : {r.description}</Note> : null}
      <Onglets<Volet>
        libelle="Volets de la réclamation"
        actif={volet}
        onChange={choisir}
        onglets={[
          { cle: 'reponse', libelle: 'Réponse du fournisseur', court: 'Réponse', sale: f.sale },
          { cle: 'pieces', libelle: 'Pièces jointes', court: 'Pièces' },
          { cle: 'historique', libelle: 'Historique' },
        ]}
      />
      {volet === 'reponse' ? <VoletReponse r={r} f={f} /> : null}
      {volet === 'pieces' ? <PiecesJointes objet="reclamation" id={r.id} /> : null}
      {volet === 'historique' ? <Historique objet="reclamation" id={r.id} /> : null}
    </Fenetre>
  )
}

export function FicheReclamation({ id, onFermer }: { id: number; onFermer: () => void }) {
  const lu = useReclamation(id)
  if (lu.data) return <Ecrite r={lu.data} onFermer={onFermer} />
  return (
    <Fenetre titre="Réclamation" onFermer={onFermer} taille="large">
      {lu.isError && lu.error.statut === 404 ? <Vide>Cette réclamation n’existe plus.</Vide> : null}
      {lu.isError && lu.error.statut !== 404 ? (
        <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
      ) : null}
      {lu.isPending ? <Chargement quoi="la réclamation" /> : null}
    </Fenetre>
  )
}
