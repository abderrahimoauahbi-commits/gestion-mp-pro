/**
 * Les gestes d'une réception (ECRANS-PRO 4.17) : corriger et supprimer un brouillon, le valider
 * (ce que la validation fera est dit avant le « Oui »), imprimer les étiquettes, compléter ou
 * corriger la facture, réclamer au fournisseur, annuler une réception validée (motif exigé). Chaque
 * bouton grisé dit pourquoi : la raison vient de la fiche du serveur (`actions`).
 */
import { BoutonImprimer } from '../../composants/documents/BoutonImprimer'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer, MOTIF_MIN } from '../../composants/saisie/Confirmer'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import { lotsDe, questionValidation } from './calculFiche'
import { Reglement } from './Reglement'
import { raisonReception, type ReceptionFiche } from './types'

export interface Navigation {
  corriger: () => void
  reclamer: () => void
  supprimee: () => void
  validee: () => void
}

const bloque = (raison: string | undefined) => (raison ? [raison] : undefined)

function Brouillon({ r, nav, sale }: { r: ReceptionFiche; nav: Navigation; sale: boolean }) {
  const ecrire = useEcriture((envoi: () => Promise<unknown>) => envoi())
  const valider = raisonReception(r, 'valider')
  return (
    <>
      <Bouton
        titre="Rouvre la saisie de ce brouillon"
        blocages={bloque(raisonReception(r, 'modifier'))}
        onClick={nav.corriger}
      >
        Corriger
      </Bouton>
      <Confirmer
        variante="danger"
        blocages={bloque(raisonReception(r, 'supprimer'))}
        titre="Rien n’est entré en stock : le brouillon s’efface"
        question="Supprimer ce brouillon ?"
        oui="Oui, supprimer"
        onOui={async () => {
          await ecrire.mutateAsync(() => api.supprimer(`/receptions/${r.id}?version=${r.version}`))
          dire('Brouillon supprimé.')
          nav.supprimee()
        }}
      >
        Supprimer le brouillon
      </Confirmer>
      <Confirmer
        variante="principal"
        manque={sale ? ['enregistrez d’abord la facture'] : undefined}
        blocages={bloque(valider)}
        titre="Écrit les lots, les entrées en stock et les prix payés ; la réception reçoit son numéro"
        question={questionValidation(r)}
        oui="Oui, valider"
        onOui={async () => {
          await ecrire.mutateAsync(() => api.post(`/receptions/${r.id}/valider`, { version: r.version }))
          nav.validee()
        }}
      >
        Valider la réception
      </Confirmer>
    </>
  )
}

function Etiquettes({ r }: { r: ReceptionFiche }) {
  const etiquettes = raisonReception(r, 'etiquettes')
  return r.lots.length && !etiquettes ? (
    <BoutonImprimer
      route="/documents/etiquettes"
      parametres={{ lots: lotsDe(r) }}
      libelle="Imprimer les étiquettes des lots"
    />
  ) : (
    <Bouton grise={etiquettes ?? 'Aucun lot : toutes les lignes sont refusées.'}>
      Imprimer les étiquettes des lots
    </Bouton>
  )
}

function Annuler({ r }: { r: ReceptionFiche }) {
  const ecrire = useEcriture((envoi: () => Promise<unknown>) => envoi())
  return (
    <Confirmer
      motif="exige"
      motifMin={MOTIF_MIN}
      variante="danger"
      blocages={bloque(raisonReception(r, 'annuler'))}
      titre="Chaque entrée est contre-passée par un mouvement inverse, à la même date ; tout reste tracé"
      question="Annuler ? Les entrées seront contre-passées."
      libelleMotif="Motif"
      exempleMotif="ex. saisie en double"
      motifMax={300}
      oui="Oui, annuler (contre-passation)"
      onOui={async (motif) => {
        await ecrire.mutateAsync(() => api.post(`/receptions/${r.id}/annuler`, { version: r.version, motif }))
        dire(`Réception ${r.numero ?? ''} annulée : ses entrées sont contre-passées.`)
      }}
    >
      Annuler (contre-passation)
    </Confirmer>
  )
}

function Validee({
  r,
  nav,
  panneau,
  onPanneau,
}: {
  r: ReceptionFiche
  nav: Navigation
  panneau: boolean
  onPanneau: () => void
}) {
  return (
    <>
      <Etiquettes r={r} />
      {panneau ? null : (
        <Bouton
          blocages={bloque(raisonReception(r, 'facture'))}
          titre="La facture se complète ou se corrige sans toucher au stock"
          onClick={onPanneau}
        >
          {r.facture ? 'Corriger la facture' : 'Compléter la facture'}
        </Bouton>
      )}
      <Reglement r={r} />
      <Bouton
        blocages={bloque(raisonReception(r, 'reclamer'))}
        titre="Un défaut constaté (qualité, manque, bobines, retard) : ouvrir une réclamation, lot et quantité préremplis"
        onClick={nav.reclamer}
      >
        Réclamer au fournisseur
      </Bouton>
      <Annuler r={r} />
    </>
  )
}

export function GestesReception(props: {
  r: ReceptionFiche
  nav: Navigation
  sale: boolean
  panneau: boolean
  onPanneau: () => void
}) {
  const { r } = props
  if (r.statut === 'brouillon') return <Brouillon r={r} nav={props.nav} sale={props.sale} />
  if (r.statut === 'validee')
    return <Validee r={r} nav={props.nav} panneau={props.panneau} onPanneau={props.onPanneau} />
  return null
}
