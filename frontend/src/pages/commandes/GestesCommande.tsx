/**
 * Les gestes d'un bon (ECRANS-PRO 4.7) : imprimer (nouvel onglet), Excel pour le fournisseur,
 * envoyer — ou demander l'approbation au-delà du seuil —, approuver et renvoyer (direction),
 * supprimer, solder ou annuler, rouvrir. Chaque bouton grisé dit pourquoi : la raison vient de la
 * fiche du serveur (`actions`, `fin_possible`), jamais devinée.
 */
import { useState } from 'react'

import { BoutonImprimer } from '../../composants/documents/BoutonImprimer'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer, MOTIF_MIN } from '../../composants/saisie/Confirmer'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import { api } from '../../lib/api'
import { ajouterJours, aujourdhui } from '../../lib/heure'
import { kg, montant } from '../../lib/format'
import { useEcriture } from '../../lib/requetes'
import styles from '../plan-achat/achats.module.css'
import { useSession } from '../../lib/session'
import { apresEnvoi } from './messages'
import { raison, type CommandeFiche } from './types'

const SAISIE_EN_COURS = 'Enregistrez d’abord vos modifications'

/** Une écriture sur le bon, qui relit tout ensuite. */
export function useEcrireBon() {
  return useEcriture((envoi: () => Promise<unknown>) => envoi())
}

/** Le premier jour permis après la clôture de période (`null` sans clôture). */
function apresCloture(cloture: string | null | undefined): string | undefined {
  return cloture ? ajouterJours(cloture, 1) : undefined
}

function ChoixDate({
  valeur,
  onChange,
  libelle,
}: {
  valeur: string
  onChange: (v: string) => void
  libelle: string
}) {
  const { contexte } = useSession()
  return (
    <span className={styles.dateEnLigne}>
      <DateChamp
        valeur={valeur}
        onChange={onChange}
        libelle={libelle}
        min={apresCloture(contexte.date_cloture)}
        raisonMin={
          contexte.date_cloture ? `la période est close jusqu’au ${contexte.date_cloture}` : undefined
        }
      />
    </span>
  )
}

function Envoyer({ c, sale }: { c: CommandeFiche; sale: boolean }) {
  const envoyer = useEcriture((date: string | null) =>
    api.post<CommandeFiche>(`/commandes/${c.id}/envoyer`, { version: c.version, date }),
  )
  const [jour, setJour] = useState(aujourdhui())
  const auDela = c.approbation_requise
  const refus = raison(c, 'envoyer')
  return (
    <Confirmer
      variante="principal"
      manque={sale ? [SAISIE_EN_COURS] : undefined}
      blocages={refus ? [refus] : undefined}
      titre={
        auDela
          ? 'Le montant dépasse le seuil : le bon part d’abord à la direction'
          : 'Le bon reçoit son numéro et sa date : il est parti chez le fournisseur'
      }
      question={
        auDela ? (
          <>
            ≈ {montant(c.montant_estime_mad, 'MAD')} : au-delà du seuil de{' '}
            {montant(c.seuil_approbation, 'MAD')}, le bon attendra l’accord de la direction.
          </>
        ) : (
          <>
            Envoyé le <ChoixDate valeur={jour} onChange={setJour} libelle="Envoyé le" /> : le bon reçoit son
            numéro.
          </>
        )
      }
      oui={auDela ? 'Oui, demander l’approbation' : 'Oui, il est envoyé'}
      onOui={async () => dire(apresEnvoi(await envoyer.mutateAsync(auDela ? null : jour || null)))}
    >
      {auDela ? 'Envoyer, ou demander l’approbation' : 'Marquer comme envoyé'}
    </Confirmer>
  )
}

function Approuver({ c, sale }: { c: CommandeFiche; sale: boolean }) {
  const ecrire = useEcrireBon()
  const [jour, setJour] = useState(aujourdhui())
  const refus = raison(c, 'approuver')
  return (
    <Confirmer
      variante="principal"
      manque={sale ? [SAISIE_EN_COURS] : undefined}
      blocages={refus ? [refus] : undefined}
      titre="Le bon reçoit son numéro et part chez le fournisseur"
      question={
        <>
          Approuver {montant(c.montant_estime, c.devise)} chez {c.fournisseur}, envoyé le{' '}
          <ChoixDate valeur={jour} onChange={setJour} libelle="Envoyé le" /> ?
        </>
      }
      oui="Oui, approuver et envoyer"
      onOui={async () => {
        await ecrire.mutateAsync(() =>
          api.post(`/commandes/${c.id}/approuver`, { version: c.version, date: jour || null }),
        )
        dire(
          'Bon approuvé : il a reçu son numéro et est marqué comme envoyé. Les achats l’impriment et le transmettent.',
        )
      }}
    >
      Approuver et envoyer
    </Confirmer>
  )
}

function Renvoyer({ c }: { c: CommandeFiche }) {
  const ecrire = useEcrireBon()
  const refus = raison(c, 'renvoyer')
  return (
    <Confirmer
      motif="exige"
      motifMin={MOTIF_MIN}
      variante="danger"
      blocages={refus ? [refus] : undefined}
      titre={
        c.numero
          ? 'Le changement n’est pas accepté : le bon revient à sa version partie, avec votre motif'
          : 'Le bon redevient un brouillon, avec votre motif'
      }
      question="Renvoyer aux achats ? Les achats liront votre motif sur le bon."
      libelleMotif="Motif du renvoi aux achats"
      exempleMotif="ex. couper en deux livraisons, attendre la baisse annoncée…"
      motifMax={500}
      oui="Oui, renvoyer aux achats"
      onOui={async (motif) => {
        await ecrire.mutateAsync(() => api.post(`/commandes/${c.id}/renvoyer`, { version: c.version, motif }))
        dire(
          c.numero
            ? 'Changement refusé : le bon reste chez le fournisseur dans sa version partie, avec votre motif.'
            : 'Bon renvoyé aux achats : il redevient un brouillon, avec votre motif.',
        )
      }}
    >
      Renvoyer aux achats…
    </Confirmer>
  )
}

function Fin({ c, sale }: { c: CommandeFiche; sale: boolean }) {
  const ecrire = useEcrireBon()
  const annuler = c.fin_possible === 'annuler'
  const refus = raison(c, 'solder')
  return (
    <Confirmer
      variante="danger"
      motif="facultatif"
      manque={sale ? [SAISIE_EN_COURS] : undefined}
      blocages={refus ? [refus] : undefined}
      titre={
        annuler
          ? 'Annuler la commande : rien n’a été reçu, le bon garde son numéro'
          : 'Solder le bon : on n’attend plus le reste à livrer'
      }
      question={
        annuler
          ? 'Rien n’a été reçu : le bon sera annulé (il garde son numéro).'
          : `On n’attend plus le reste (${kg(c.reste_kg)}) : il sort des quantités commandées.`
      }
      oui={annuler ? 'Oui, annuler la commande' : 'Oui, solder'}
      onOui={async (motif) => {
        await ecrire.mutateAsync(() => api.post(`/commandes/${c.id}/solder`, { version: c.version, motif }))
        dire(annuler ? 'Commande annulée.' : 'Bon soldé.')
      }}
    >
      {annuler ? 'Annuler la commande' : 'Solder (ne plus attendre le reste)'}
    </Confirmer>
  )
}

function Rouvrir({ c }: { c: CommandeFiche }) {
  const ecrire = useEcrireBon()
  const refus = raison(c, 'rouvrir')
  return (
    <Confirmer
      blocages={refus ? [refus] : undefined}
      titre="Le bon attend de nouveau ce qui reste à livrer"
      question="Rouvrir ce bon ? Le reste redevient attendu."
      oui="Oui, rouvrir"
      onOui={async () => {
        await ecrire.mutateAsync(() => api.post(`/commandes/${c.id}/rouvrir`, { version: c.version }))
        dire('Bon rouvert : le reste est de nouveau attendu.')
      }}
    >
      Rouvrir le bon
    </Confirmer>
  )
}

function Supprimer({ c, onSupprime }: { c: CommandeFiche; onSupprime: () => void }) {
  const ecrire = useEcrireBon()
  const refus = raison(c, 'supprimer')
  return (
    <Confirmer
      variante="danger"
      blocages={refus ? [refus] : undefined}
      titre="Un bon qui n’est pas parti se supprime : il n’a pas encore de numéro"
      question="Supprimer définitivement ce brouillon ?"
      oui="Oui, supprimer"
      onOui={async () => {
        await ecrire.mutateAsync(() => api.supprimer(`/commandes/${c.id}?version=${c.version}`))
        dire('Brouillon supprimé.')
        onSupprime()
      }}
    >
      Supprimer le bon
    </Confirmer>
  )
}

/** Imprimer et l'Excel : un brouillon le dit sur le bouton ; sans raison sociale, l'Excel est grisé. */
function Documents({ c }: { c: CommandeFiche }) {
  const brouillon = !c.numero
  return (
    <>
      <BoutonImprimer
        route={`/documents/commandes/${c.id}/bon`}
        libelle={brouillon ? 'Imprimer (brouillon)' : 'Imprimer le bon'}
        titre={
          brouillon
            ? 'Brouillon — non envoyé : le bon n’a pas encore de numéro, à relire avant de l’envoyer'
            : 'Ouvre le bon prêt à imprimer ou à enregistrer en PDF (nouvel onglet)'
        }
      />
      {c.raison_sociale_reglee ? (
        <ExportExcel
          route={`/export/commandes/${c.id}/bon`}
          libelle={brouillon ? 'Excel (brouillon)' : 'Excel pour le fournisseur'}
        />
      ) : (
        <Bouton
          icone="telecharger"
          grise="La raison sociale de l’usine n’est pas réglée (Réglages › Paramètres › Société) : le bon ne part pas sans elle."
        >
          Excel pour le fournisseur
        </Bouton>
      )}
    </>
  )
}

export function GestesCommande({
  c,
  sale,
  onSupprime,
}: {
  c: CommandeFiche
  sale: boolean
  onSupprime: () => void
}) {
  const { role } = useSession()
  const clos = c.statut === 'soldee' || c.statut === 'annulee'
  return (
    <>
      <Documents c={c} />
      {c.statut === 'brouillon' ? <Envoyer c={c} sale={sale} /> : null}
      {c.statut === 'a_approuver' && role === 'direction' ? <Approuver c={c} sale={sale} /> : null}
      {c.statut === 'a_approuver' && role === 'direction' ? <Renvoyer c={c} /> : null}
      {!c.numero ? <Supprimer c={c} onSupprime={onSupprime} /> : null}
      {c.parti && !clos ? <Fin c={c} sale={sale} /> : null}
      {clos ? <Rouvrir c={c} /> : null}
    </>
  )
}
