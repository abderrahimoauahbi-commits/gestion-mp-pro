/**
 * Les cours du dossier (ECRANS-PRO 5.8) : pour chaque devise autre que le MAD, « 1 USD = […] MAD
 * [Appliquer aux USD] » (le cours payé à la banque, pour toutes les marchandises de la devise ;
 * grisé avec sa raison tant qu'il n'est pas saisi), « Cours des bons (N) », et les notes calculées
 * par le serveur : cours éloignés, cours du jour en attendant la clôture, cours des bons, cours
 * disparates, pesée × prix contre la facture.
 */
import { useState } from 'react'

import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { messageNombre, Nombre } from '../../composants/saisie/Nombre'
import { cours, montantPrecis, nombre, part } from '../../lib/format'
import styles from './Importations.module.css'
import type { DossierFiche } from './types'
import type { GestesDossier } from './useDossier'

/** Les devises du dossier autres que le MAD, avec leur cours du jour (réglages). */
function devisesDu(d: DossierFiche): { devise: string; jour: number }[] {
  const vues = new Map<string, number>()
  for (const l of d.lignes) if (l.devise !== 'MAD' && !vues.has(l.devise)) vues.set(l.devise, l.cours_jour)
  return [...vues.entries()].map(([devise, jour]) => ({ devise, jour }))
}

function CoursDevise({
  devise,
  jour,
  g,
  blocage,
}: {
  devise: string
  jour: number
  g: GestesDossier
  blocage: string | null
}) {
  const [valeur, setValeur] = useState<number | null>(null)
  const borne = messageNombre(valeur, { min: 0.0001, max: 1000, decimales: 4 })
  return (
    <span
      className={styles.rangee}
      title={`Le cours payé à la banque pour toutes les marchandises en ${devise} du dossier`}
    >
      <span>1 {devise} =</span>
      <span className={styles.etroit}>
        <Nombre
          valeur={valeur}
          onChange={setValeur}
          decimales={4}
          min={0}
          max={1000}
          placeholder={`${cours(jour)} (jour)`}
          libelle={`Cours payé pour 1 ${devise}`}
        />
      </span>
      <span>MAD</span>
      <Bouton
        taille="petit"
        manque={valeur == null ? ['Saisissez le cours'] : []}
        blocages={blocage ? [blocage] : []}
        grise={borne || undefined}
        onClick={async () => {
          if (valeur == null) return
          await g.cours(devise, valeur)
          setValeur(null)
          dire(`Cours ${cours(valeur)} MAD appliqué à toutes les marchandises en ${devise}.`)
        }}
      >
        Appliquer aux {devise}
      </Bouton>
    </span>
  )
}

/** Les notes des cours, calculées par le serveur. */
function NotesCours({ d }: { d: DossierFiche }) {
  const auJour = d.lignes.filter((l) => l.devise !== 'MAD' && l.cours == null).length
  const f = d.ecart_facture
  return (
    <>
      {d.cours_eloignes ? (
        <Note ton="critique">
          {nombre(d.cours_eloignes)} ligne(s) à un cours éloigné de plus de 5 % du cours du jour : vérifier
          l’avis de la banque.
        </Note>
      ) : null}
      {auJour && d.statut === 'ouvert' ? (
        <Note>
          {nombre(auJour)} marchandise(s) en devise sans cours payé : elles sont comptées au cours du jour des
          réglages (*). La clôture l’écrira sur la ligne ; la réouverture le rendra vide.
        </Note>
      ) : null}
      {d.lignes_cours_bon ? (
        <Note>
          {nombre(d.lignes_cours_bon)} marchandise(s) au cours de leur bon : celui des réglages le jour de la
          confirmation des prix, pas celui payé à la banque.
        </Note>
      ) : null}
      {d.cours_disparates.map((c) => (
        <Note key={c.devise} ton="critique">
          Les marchandises en {c.devise} n’ont pas toutes le même cours (
          {c.cours.map((x) => cours(x)).join(' et ')} MAD) — un second camion arrivé après une clôture ?
          Vérifier l’avis de la banque.
        </Note>
      ))}
      {f && !f.hors_tolerance && f.ecart ? (
        <Note>
          Chaque marchandise entre à sa <strong>pesée × son prix</strong> (
          {montantPrecis(f.montant, f.devise)} facturés, {montantPrecis(f.recu, f.devise)} reçus, écart{' '}
          {part(f.part)}) : l’écart à la facture ne change pas le coût.
        </Note>
      ) : null}
    </>
  )
}

export function CoursDevises({
  d,
  g,
  modifiable,
}: {
  d: DossierFiche
  g: GestesDossier
  modifiable: boolean
}) {
  const devises = devisesDu(d)
  const auBon = d.lignes.filter((l) => l.cours_bon != null && l.cours !== l.cours_bon).length
  return (
    <>
      {modifiable && devises.length ? (
        <div className={styles.rangee}>
          {devises.map((x) => (
            <CoursDevise key={x.devise} devise={x.devise} jour={x.jour} g={g} blocage={d.actions.cours} />
          ))}
          {auBon ? (
            <Bouton
              taille="petit"
              titre="Remettre sur chaque ligne le cours figé de son bon de commande à la confirmation des prix"
              blocages={d.actions.cours ? [d.actions.cours] : []}
              onClick={async () => {
                await g.coursDesBons()
                dire('Cours figés des bons remis sur les lignes.')
              }}
            >
              Cours des bons ({nombre(auBon)})
            </Bouton>
          ) : null}
        </div>
      ) : null}
      <NotesCours d={d} />
    </>
  )
}
