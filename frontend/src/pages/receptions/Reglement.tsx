/**
 * Le règlement de la facture d'une réception (ECRANS-PRO 4.17, route 229 `PUT echeancier/paiement`) :
 * « Marquer réglée » à une date bornée par la date de la facture et aujourd'hui ; « Annuler le
 * règlement » par la direction seule, avec un motif (la facture redevient due).
 */
import { useState } from 'react'

import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer, MOTIF_MIN } from '../../composants/saisie/Confirmer'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { api } from '../../lib/api'
import { date } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import { useEcriture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Schema } from '../../lib/types'
import styles from '../plan-achat/achats.module.css'
import type { ReceptionFiche } from './types'

/** Le corps de la route 229 (lot D8) : le jour du règlement, ou vide avec un motif pour l'annuler. */
type Paiement = Schema<'Paiement'>
type Facture = NonNullable<ReceptionFiche['facture']>

export const RESERVE_DIRECTION =
  'Ce règlement ne s’annule que par la direction : la facture redeviendrait due. Lui demander de le faire, en disant pourquoi.'

/** Le corps de la route 229 pour une facture. */
export function corpsPaiement(f: Facture, payeeLe: string | null, motif?: string): Paiement {
  return { genre: 'facture', id: f.id, payee_le: payeeLe, version: f.version, motif: motif ?? '' }
}

function MarquerReglee({ f }: { f: Facture }) {
  const [jour, setJour] = useState(aujourdhui())
  const ecrire = useEcriture((c: Paiement) => api.put('/echeancier/paiement', c))
  return (
    <Confirmer
      titre="La facture est payée : elle sort de l’échéancier et de l’« échu, non réglé »"
      question={
        <>
          Réglée le{' '}
          <span className={styles.dateEnLigne}>
            <DateChamp
              valeur={jour}
              onChange={setJour}
              libelle="Réglée le"
              min={f.date ?? undefined}
              raisonMin="le règlement ne précède pas la facture"
            />
          </span>
        </>
      }
      oui="Oui, réglée"
      onOui={async () => {
        await ecrire.mutateAsync(corpsPaiement(f, jour))
        dire(`Facture ${f.numero} réglée le ${date(jour)}.`)
      }}
    >
      Marquer réglée
    </Confirmer>
  )
}

function AnnulerReglement({ f }: { f: Facture }) {
  const { role } = useSession()
  const ecrire = useEcriture((c: Paiement) => api.put('/echeancier/paiement', c))
  if (role !== 'direction') return <Bouton grise={RESERVE_DIRECTION}>Annuler le règlement</Bouton>
  return (
    <Confirmer
      motif="exige"
      motifMin={MOTIF_MIN}
      variante="neutre"
      titre="La facture redevient due : elle revient dans l’échéancier"
      question={`Annuler le règlement du ${date(f.payee_le)} ?`}
      libelleMotif="Pourquoi annuler le règlement"
      motifMax={300}
      oui="Oui, annuler le règlement"
      onOui={async (motif) => {
        await ecrire.mutateAsync(corpsPaiement(f, null, motif))
        dire(`Règlement de la facture ${f.numero} annulé.`)
      }}
    >
      Annuler le règlement
    </Confirmer>
  )
}

export function Reglement({ r }: { r: ReceptionFiche }) {
  const f = r.facture
  if (!f?.numero || r.statut !== 'validee') return null
  return f.payee_le ? <AnnulerReglement f={f} /> : <MarquerReglee f={f} />
}
