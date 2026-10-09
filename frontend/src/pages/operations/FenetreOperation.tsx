/**
 * La fenêtre d'une opération (`/operations/:id`, `/operations/nouvelle?type=`, ECRANS-PRO partie 6) :
 * titre « {type} — {n° / Brouillon / nouveau brouillon} », auteurs (création, validation,
 * annulation), liens d'ordre, de fournisseur et de lot (an. 12), date, motif, observations, lignes et
 * encart de ligne, blocages annoncés. Modifiable par qui a le droit du type tant que c'est un
 * brouillon (retours des machines compris pour la direction et l'alimentation, an. 24).
 */
import { useState } from 'react'

import { LienDocument } from '../../composants/documents/LienDocument'
import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Bouton } from '../../composants/saisie/Bouton'
import { Blocages } from '../../composants/saisie/Blocages'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { horodatage } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { EncartLigne } from './EncartLigne'
import { EnTeteSaisie } from './EnTeteSaisie'
import { LignesOperation } from './LignesOperation'
import styles from './Operations.module.css'
import { questionValider, type LigneSaisie } from './saisie'
import {
  libelleDuType,
  type DeviseFiche,
  type MagasinFiche,
  type MatiereResume,
  type Motifs,
  type OperationFiche,
  type TypeOperation,
} from './types'
import { useGestesOperation, useOperation, type Donnees } from './useOperation'

/** « Par {nom} le … · validée par … · annulée par … · ordre … · fournisseur … ». */
function Auteurs({ op }: { op: OperationFiche }) {
  const { role } = useSession()
  const morceaux = [`Par ${op.cree_par} le ${horodatage(op.cree_le)}`]
  if (op.validee_le) morceaux.push(`validée par ${op.validee_par} le ${horodatage(op.validee_le)}`)
  if (op.annulee_le) morceaux.push(`annulée par ${op.annulee_par} le ${horodatage(op.annulee_le)}`)
  if (!op.numero) morceaux.push('le numéro est donné à la validation')
  return (
    <span>
      {morceaux.join(' · ')}
      {op.ordre_id ? (
        <>
          {' · ordre '}
          <LienDocument genre="ordre" id={op.ordre_id} numero={op.ordre} />
        </>
      ) : null}
      {op.fournisseur_id ? (
        <>
          {' · fournisseur '}
          {role === 'alimentation' ? (
            op.fournisseur
          ) : (
            <LienDocument genre="fournisseur" id={op.fournisseur_id} numero={op.fournisseur} />
          )}
        </>
      ) : null}
    </span>
  )
}

interface PiedProps {
  op: OperationFiche | null
  x: ReturnType<typeof useOperation>
  g: ReturnType<typeof useGestesOperation>
  encartRempli: boolean
}

function Pied({ op, x, g, encartRempli }: PiedProps) {
  const fermer = useFermerFenetre()
  const enCours = encartRempli ? 'Une ligne est en cours de saisie : l’ajouter ou l’annuler.' : undefined
  return (
    <>
      {op?.statut === 'brouillon' && op.peut_agir ? (
        <Confirmer
          variante="danger"
          titre="Supprimer le brouillon : rien n’a bougé au stock"
          question="Supprimer ce brouillon ? Rien n’a encore bougé au stock."
          oui="Oui, supprimer"
          onOui={g.supprimer}
        >
          Supprimer le brouillon
        </Confirmer>
      ) : null}
      {op?.statut === 'validee' && op.peut_agir ? (
        <Confirmer
          variante="danger"
          question="Annuler ? Une écriture inverse remet le stock comme avant ; les deux restent aux mouvements, et l’annulation ne se défait pas."
          oui="Oui, annuler (contre-passation)"
          onOui={g.annuler}
        >
          Annuler (contre-passation)
        </Confirmer>
      ) : null}
      {op && !op.peut_agir && op.raison ? <span className={styles.note}>{op.raison}</span> : null}
      <span className={styles.pousse} />
      <Bouton onClick={fermer} titre="Fermer sans enregistrer">
        Fermer
      </Bouton>
      {x.modifiable ? (
        <>
          <Bouton
            onClick={g.enregistrer}
            manque={x.manque}
            grise={x.modifie || !op ? enCours : 'Rien de modifié.'}
            attente="Enregistrement…"
          >
            Enregistrer le brouillon
          </Bouton>
          <Confirmer
            variante="principal"
            manque={x.manque}
            blocages={x.blocages}
            grise={enCours}
            question={questionValider(x.s.lignes.length)}
            oui="Oui, valider"
            attente="Validation…"
            onOui={g.valider}
          >
            Valider : le stock bouge
          </Confirmer>
        </>
      ) : null}
    </>
  )
}

interface EditeurProps {
  d: Donnees & { matieres: MatiereResume[]; devises: DeviseFiche[] }
  op: OperationFiche | null
  type: TypeOperation
  onFermer: () => void
  onCree: (id: number) => void
}

type EtatEncartOuvert = { ligne: LigneSaisie | null } | null

/** L'encart de ligne ouvert, ou « Ajouter une ligne ». */
function ZoneEncart({
  d,
  x,
  encart,
  setEncart,
  setEncartRempli,
}: {
  d: EditeurProps['d']
  x: ReturnType<typeof useOperation>
  encart: EtatEncartOuvert
  setEncart: (e: EtatEncartOuvert) => void
  setEncartRempli: (r: boolean) => void
}) {
  const s = x.s
  return encart ? (
    <EncartLigne
      key={encart.ligne?.cle ?? 'nouvelle'}
      type={s.type}
      motif={x.motif}
      date={s.date}
      matieres={d.matieres}
      magasins={d.magasins}
      devises={d.devises}
      fournisseur={
        s.type === 'retour_fournisseur'
          ? (s.lignes.find((l) => l.cle !== encart.ligne?.cle)?.fournisseur ?? null)
          : null
      }
      ligne={encart.ligne}
      onRempli={setEncartRempli}
      onPoser={(l) => {
        x.poserLigne(l)
        setEncart(null)
        setEncartRempli(false)
      }}
      onAnnuler={() => {
        setEncart(null)
        setEncartRempli(false)
      }}
    />
  ) : x.modifiable ? (
    <Bouton taille="petit" icone="plus" onClick={() => setEncart({ ligne: null })}>
      Ajouter une ligne
    </Bouton>
  ) : null
}

function Editeur({ d, op, type, onFermer, onCree }: EditeurProps) {
  const { moi } = useSession()
  const x = useOperation(d, op, type)
  const g = useGestesOperation(op, x.s, x.modifie, { cree: (o) => onCree(o.id), supprime: onFermer })
  const [encart, setEncart] = useState<EtatEncartOuvert>(
    x.modifiable && !op?.lignes.length ? { ligne: null } : null,
  )
  const [encartRempli, setEncartRempli] = useState(false)
  const s = x.s
  const titre = `${libelleDuType(d.motifs, s.type)} — ${op ? (op.numero ?? 'Brouillon') : 'nouveau brouillon'}`
  return (
    <Fenetre
      taille="tresLarge"
      sale={x.modifie || encartRempli}
      onFermer={onFermer}
      titre={
        <>
          {titre} {op && op.statut !== 'brouillon' ? <Badge famille="document" valeur={op.statut} /> : null}
        </>
      }
      sous={op ? <Auteurs op={op} /> : undefined}
      pied={<Pied op={op} x={x} g={g} encartRempli={encartRempli} />}
    >
      <div className={styles.fenetre}>
        <Blocages blocages={x.blocages} />
        <EnTeteSaisie x={x} />
        <ZoneEncart d={d} x={x} encart={encart} setEncart={setEncart} setEncartRempli={setEncartRempli} />
        <LignesOperation
          type={s.type}
          motif={x.motif}
          lignes={s.lignes}
          modifiable={x.modifiable}
          voitPrix={moi.voit_prix}
          enCours={encart ? (encart.ligne?.cle ?? 'nouvelle') : null}
          modifier={(l) => setEncart({ ligne: l })}
          retirer={x.retirer}
        />
      </div>
    </Fenetre>
  )
}

export function FenetreOperation({
  id,
  type,
  onFermer,
  onCree,
}: {
  id: number | null
  type: TypeOperation
  onFermer: () => void
  onCree: (id: number) => void
}) {
  const { moi } = useSession()
  const motifs = useLecture<Motifs>('/motifs')
  const magasins = useLecture<MagasinFiche[]>('/magasins')
  const matieres = useLecture<MatiereResume[]>('/matieres')
  const devises = useLecture<DeviseFiche[]>(moi.voit_prix ? '/devises' : null)
  const op = useLecture<OperationFiche>(id == null ? null : `/operations/${id}`)
  const erreur = motifs.error ?? magasins.error ?? matieres.error ?? op.error
  const pret = motifs.data && magasins.data && matieres.data && (id == null || op.data)
  if (!pret || !motifs.data || !magasins.data || !matieres.data) {
    return (
      <Fenetre titre="Opération" taille="tresLarge" onFermer={onFermer}>
        {erreur ? <Erreur erreur={erreur} /> : <Chargement quoi="l’opération" />}
      </Fenetre>
    )
  }
  const lue = op.data ?? null
  return (
    <Editeur
      key={lue ? `${lue.id}-${lue.version}` : `nouveau-${type}`}
      d={{
        motifs: motifs.data,
        magasins: magasins.data,
        matieres: matieres.data,
        devises: devises.data ?? [],
      }}
      op={lue}
      type={lue?.type ?? type}
      onFermer={onFermer}
      onCree={onCree}
    />
  )
}
