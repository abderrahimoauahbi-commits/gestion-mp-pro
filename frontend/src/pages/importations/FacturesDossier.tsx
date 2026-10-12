/**
 * Fiche dossier › Factures du dossier (ECRANS-PRO 5.6, lot PLUSIEURS-FACTURES) : un dossier — une
 * déclaration en douane, un arrivage — regroupe une ou plusieurs factures (décision de Mohamed du
 * 12/10/2026) ; une facture n'est que dans un seul dossier. Une ligne par facture : numéro,
 * fournisseur, date, montant dans sa devise (jamais additionnés entre devises), échéance, réceptions
 * (liens), rapprochement avec ce qu'elle a apporté (C36), et « Retirer » — grisé avec la raison du
 * serveur quand il ne se peut pas (un frais vise sa marchandise, dossier clos). « Ajouter une
 * facture » ouvre une fenêtre qui reprend `ChoixFacture` : les factures reçues qui n'attendent
 * encore aucun dossier (la liste « En attente ») ; toute leur marchandise entre au dossier.
 */
import { useState } from 'react'
import { Link } from 'react-router'

import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { date, kg, montantPrecis, nombre, part, VIDE } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { ChoixFacture } from './ChoixFacture'
import styles from './Importations.module.css'
import type { DossierFiche, EnAttente, FactureDossier } from './types'
import type { GestesDossier } from './useDossier'

const arreter = (e: { stopPropagation: () => void }) => e.stopPropagation()

/** « conforme », « +20,0 % » (hors tolérance), ou rien à rapprocher. */
function Rapprochement({ f }: { f: FactureDossier }) {
  const e = f.ecart
  if (!e) return <span className={styles.note}>{f.montant == null ? 'montant non saisi' : VIDE}</span>
  const titre = `${montantPrecis(e.montant, e.devise)} facturés pour ${montantPrecis(e.recu, e.devise)} reçus (pesée × prix)`
  return e.hors_tolerance ? (
    <span title={titre}>
      <Badge ton="attention">écart {part(e.part)}</Badge>
    </span>
  ) : (
    <span title={titre}>conforme</span>
  )
}

function Receptions({ f }: { f: FactureDossier }) {
  if (!f.receptions.length) return <>{VIDE}</>
  return (
    <span className={styles.liens}>
      {f.receptions.map((r) => (
        <Link key={r.id} to={`/receptions/${r.id}`} onClick={arreter}>
          {r.numero}
        </Link>
      ))}
    </span>
  )
}

/** « Retirer » : confirmé, ou grisé avec la raison du serveur. */
function Retirer({ d, f, g }: { d: DossierFiche; f: FactureDossier; g: GestesDossier }) {
  return (
    <Confirmer
      taille="petit"
      variante="danger"
      blocages={f.retrait ? [f.retrait] : []}
      titre={`Retirer la facture ${f.numero} du dossier : sa marchandise attendra de nouveau son dossier`}
      question={`Retirer la facture ${f.numero} du dossier ${d.numero} ? Sa marchandise (${nombre(f.lignes)} ligne(s)) en sort et attendra de nouveau son dossier ; les frais restent au dossier et se répartissent sur ce qui reste.`}
      oui="Oui, retirer la facture"
      onOui={async () => {
        await g.retirerFacture(f.id)
        dire(
          `Facture ${f.numero} retirée du dossier ${d.numero} : sa marchandise attend de nouveau son dossier.`,
        )
      }}
    >
      Retirer
    </Confirmer>
  )
}

function colonnes(d: DossierFiche, g: GestesDossier): Colonne<FactureDossier>[] {
  const liste: Colonne<FactureDossier>[] = [
    {
      cle: 'numero',
      titre: 'Facture',
      rendu: (f) => (
        <span className={styles.valeur}>
          <strong>{f.numero}</strong>
          {f.liberee_le ? <span className={styles.note}>libérée</span> : null}
        </span>
      ),
    },
    { cle: 'fournisseur', titre: 'Fournisseur' },
    { cle: 'date', titre: 'Date', rendu: (f) => date(f.date) },
    {
      cle: 'montant',
      titre: 'Montant',
      droite: true,
      aide: 'Dans la devise de la facture : les devises ne s’additionnent pas',
      rendu: (f) => (f.montant == null ? VIDE : montantPrecis(f.montant, f.devise)),
    },
    {
      cle: 'echeance',
      titre: 'Échéance',
      rendu: (f) => (f.payee_le ? `réglée le ${date(f.payee_le)}` : f.echeance ? date(f.echeance) : VIDE),
    },
    { cle: 'receptions', titre: 'Réceptions', triable: false, rendu: (f) => <Receptions f={f} /> },
    {
      cle: 'ecart',
      titre: 'Rapprochement',
      aide: 'La facture rapprochée de la marchandise qu’elle a apportée, pesée × prix (contrôle C36)',
      triable: false,
      valeur: (f) => (f.ecart ? f.ecart.part : ''),
      rendu: (f) => <Rapprochement f={f} />,
    },
  ]
  if (d.statut === 'annule') return liste
  return [
    ...liste,
    {
      cle: 'retirer',
      titre: '',
      triable: false,
      exporte: false,
      valeur: () => '',
      rendu: (f) => (
        <span onClick={arreter}>
          <Retirer d={d} f={f} g={g} />
        </span>
      ),
    },
  ]
}

/** La fenêtre « Ajouter une facture » : les factures reçues qui n'attendent encore aucun dossier. */
function FenetreAjout({ d, g, fermer }: { d: DossierFiche; g: GestesDossier; fermer: () => void }) {
  const lu = useLecture<EnAttente>('/dossiers/a-rattacher')
  const libres = (lu.data?.factures ?? []).filter((f) => f.dossier_id == null)
  return (
    <Fenetre titre={`Ajouter une facture au dossier ${d.numero}`} taille="tresLarge" onFermer={fermer}>
      <div className={styles.pile}>
        <Note uneLigne="Une facture reçue qui n’est encore dans aucun dossier : toute la marchandise qu’elle a apportée entre au dossier, dans sa devise. Une facture n’est que dans un seul dossier.">
          Une facture reçue qui n’est encore dans aucun dossier : toute la marchandise qu’elle a apportée
          entre au dossier, dans sa devise. Une facture n’est que dans un seul dossier.
        </Note>
        {lu.isError ? (
          <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
        ) : !lu.data ? (
          <Chargement quoi="les factures reçues" />
        ) : (
          <ChoixFacture
            factures={libres}
            hauteur="fenetre"
            ajout
            action={() => 'Ajouter au dossier'}
            blocages={() => (d.actions.ajouter_facture ? [d.actions.ajouter_facture] : [])}
            onChoisir={async (f, localConfirme) => {
              await g.ajouterFacture(f.facture_id, localConfirme)
              dire(
                `Facture ${f.numero} ajoutée au dossier ${d.numero} : ${nombre(f.lots)} lot(s), ${kg(f.quantite)}.`,
              )
              fermer()
            }}
          />
        )}
      </div>
    </Fenetre>
  )
}

/** Le bloc « Factures du dossier » de la fiche (absent d'un dossier saisi à la main ou repris). */
export function FacturesDossier({ d, g }: { d: DossierFiche; g: GestesDossier }) {
  const [ajout, setAjout] = useState(false)
  if (!d.factures.length && (d.a_la_main || d.repris)) return null
  const titre =
    d.factures.length > 1 ? `Factures du dossier (${nombre(d.factures.length)})` : 'Facture du dossier'
  return (
    <section className={styles.pile} aria-label="Factures du dossier">
      <span className={styles.rangee}>
        <strong>{titre}</strong>
        {d.statut !== 'annule' ? (
          <Bouton
            taille="petit"
            blocages={d.actions.ajouter_facture ? [d.actions.ajouter_facture] : []}
            titre="Une autre facture du même arrivage (même conteneur, même déclaration) : sa marchandise entre au dossier"
            onClick={() => setAjout(true)}
          >
            Ajouter une facture
          </Bouton>
        ) : null}
      </span>
      {d.factures.length ? (
        <DataTable
          libelle="Factures du dossier"
          lignes={d.factures}
          colonnes={colonnes(d, g)}
          cle={(f) => f.id}
          recherche={false}
          hauteur="fenetre"
        />
      ) : (
        <Vide>
          Plus aucune facture dans ce dossier : « Ajouter une facture » y fait entrer la marchandise d’une
          facture reçue.
        </Vide>
      )}
      {ajout ? <FenetreAjout d={d} g={g} fermer={() => setAjout(false)} /> : null}
    </section>
  )
}
