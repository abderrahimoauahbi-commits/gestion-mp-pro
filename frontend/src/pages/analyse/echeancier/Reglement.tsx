/**
 * Les gestes de l'échéancier (route 229, `PUT echeancier/paiement`) : « Réglée… » note le
 * règlement d'une facture ou d'un frais à une date passée (au plus aujourd'hui, à l'heure de
 * l'usine) ; « Annuler le règlement » le défait — la direction seule, motif exigé (D4, D8).
 * Une échéance relue entre-temps refuse l'écriture (409, version).
 */
import { useState } from 'react'

import { dire } from '../../../composants/retour/Messages'
import { Confirmer } from '../../../composants/saisie/Confirmer'
import { DateChamp } from '../../../composants/saisie/DateChamp'
import { api } from '../../../lib/api'
import { date } from '../../../lib/format'
import { aujourdhui } from '../../../lib/heure'
import { useEcriture } from '../../../lib/requetes'
import type { EcheanceLigne, Paiement } from '../types'

const genreDe = (l: EcheanceLigne): Paiement['genre'] => (l.objet === 'frais' ? 'frais' : 'facture')

function usePaiement() {
  return useEcriture((p: Paiement) => api.put<EcheanceLigne>('/echeancier/paiement', p))
}

export function Reglee({ ligne }: { ligne: EcheanceLigne }) {
  const [jour, setJour] = useState(aujourdhui())
  const ecrire = usePaiement()
  return (
    <Confirmer
      taille="petit"
      titre="Payée : elle sort de l’échéancier et de l’« échu, non réglé »"
      question={
        <>
          Réglée le{' '}
          <DateChamp libelle="Date du règlement" valeur={jour} max={aujourdhui()} onChange={setJour} /> ?
        </>
      }
      oui="Oui, réglée"
      onOui={async () => {
        await ecrire.mutateAsync({
          genre: genreDe(ligne),
          id: ligne.id,
          payee_le: jour,
          version: ligne.version,
          motif: '',
        })
        dire(`${ligne.piece} réglée le ${date(jour)}.`)
      }}
    >
      Réglée…
    </Confirmer>
  )
}

export function AnnulerReglement({ ligne, direction }: { ligne: EcheanceLigne; direction: boolean }) {
  const ecrire = usePaiement()
  return (
    <Confirmer
      taille="petit"
      titre="La pièce redevient due : elle revient dans l’échéancier"
      grise={direction ? undefined : 'Annuler un règlement est réservé à la direction.'}
      question="Annuler le règlement ?"
      motif="exige"
      oui="Oui, annuler"
      onOui={async (motif) => {
        await ecrire.mutateAsync({
          genre: genreDe(ligne),
          id: ligne.id,
          payee_le: null,
          version: ligne.version,
          motif,
        })
        dire(`Règlement de ${ligne.piece} annulé : elle redevient due.`)
      }}
    >
      Annuler le règlement
    </Confirmer>
  )
}
