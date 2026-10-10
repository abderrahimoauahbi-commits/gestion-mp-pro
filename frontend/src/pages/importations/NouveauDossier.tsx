/**
 * Nouveau dossier d'importation (`/dossiers/nouveau?onglet=facture|main`, ECRANS-PRO 5.5) : depuis la
 * facture reçue (`ChoixFacture` : toute la marchandise qu'elle a apportée entre au dossier, libellé
 * et date d'arrivée posés par le serveur), ou, pour un dossier d'avant la mise en service, à la main
 * (son vrai numéro, sa date d'arrivée exigée, ses marchandises saisies ensuite). La fenêtre est
 * gardée dès qu'un champ de la saisie à la main est rempli.
 */
import { useState } from 'react'
import { Link } from 'react-router'

import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ, erreurDuChamp } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Saisie } from '../../composants/saisie/Saisie'
import { Zone } from '../../composants/saisie/Zone'
import { useOngletAdresse } from '../../lib/adresse'
import { api } from '../../lib/api'
import { nombre } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import { ChoixFacture } from './ChoixFacture'
import { actionFacture, blocageClos, useOuvrirOuRattacher } from './EnAttente'
import type { EtatPage } from './etatPage'
import styles from './Importations.module.css'
import type { DossierFiche, EnAttente } from './types'

const ONGLETS = ['facture', 'main'] as const

interface SaisieMain {
  numero: string
  libelle: string
  date_arrivee: string
  banque: string
  commentaire: string
}

const VIDE: SaisieMain = { numero: '', libelle: '', date_arrivee: '', banque: '', commentaire: '' }

function DepuisLaFacture({ page, clos }: { page: EtatPage; clos: (id: number) => boolean }) {
  const lu = useLecture<EnAttente>('/dossiers/a-rattacher')
  const choisir = useOuvrirOuRattacher(page, true)
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  if (!lu.data) return <Chargement quoi="les factures reçues" />
  const sans = lu.data.sans_facture.length
  return (
    <div className={styles.pile}>
      <Note uneLigne="Un dossier, une facture. Choisir le fournisseur, taper le numéro de facture : toute la marchandise qu’elle a apportée entre au dossier, le libellé et la date d’arrivée se remplissent seuls. Il ne restera qu’à saisir les frais.">
        Un dossier, une facture. Choisir le fournisseur, taper le numéro de facture : toute la marchandise
        qu’elle a apportée entre au dossier, le libellé et la date d’arrivée se remplissent seuls. Il ne
        restera qu’à saisir les frais.
      </Note>
      <ChoixFacture
        factures={lu.data.factures}
        action={actionFacture}
        onChoisir={choisir}
        blocages={blocageClos(clos)}
        hauteur="fenetre"
      />
      {sans ? (
        <Note>
          {nombre(sans)} réception(s) attendent leur facture : elle se saisit sur la réception (onglet{' '}
          <Link to="/importations?onglet=rattacher&vue=receptions">« En attente de dossier »</Link>), puis
          elle ouvre son dossier ici.
        </Note>
      ) : null}
    </div>
  )
}

/** La saisie à la main est gardée au changement d'onglet ; elle rend la fenêtre « sale ». */
const estSale = (s: SaisieMain) => Object.values(s).some((x) => x.trim())

/** Les champs d'un dossier saisi à la main. */
function ChampsMain({
  s,
  poser,
  refus,
}: {
  s: SaisieMain
  poser: (cle: keyof SaisieMain) => (v: string) => void
  refus: unknown
}) {
  return (
    <Grille colonnes={3}>
      <Champ
        libelle="Numéro"
        aide="vide : le suivant (NN/AA) ; un ancien dossier garde le sien"
        erreur={erreurDuChamp(refus, 'numero')}
      >
        <Saisie valeur={s.numero} onChange={poser('numero')} max={16} placeholder="automatique" />
      </Champ>
      <Champ libelle="Date d’arrivée" obligatoire erreur={erreurDuChamp(refus, 'date_arrivee')}>
        <DateChamp valeur={s.date_arrivee} onChange={poser('date_arrivee')} />
      </Champ>
      <Champ libelle="Banque">
        <Saisie valeur={s.banque} onChange={poser('banque')} max={32} placeholder="AWB, BMCI…" />
      </Champ>
      <Champ libelle="Libellé" large>
        <Saisie
          valeur={s.libelle}
          onChange={poser('libelle')}
          max={160}
          autoFocus
          placeholder="Fournisseur, n° de facture, conteneur…"
        />
      </Champ>
      <Champ libelle="Observations" large>
        <Zone
          valeur={s.commentaire}
          onChange={poser('commentaire')}
          max={2000}
          lignes={2}
          placeholder="Transitaire, n° de DUM, observations…"
        />
      </Champ>
    </Grille>
  )
}

/** La saisie à la main : la note et les champs. L'action « Ouvrir le dossier… » est au pied de la fenêtre. */
function ALaMain({
  s,
  poser,
  refus,
}: {
  s: SaisieMain
  poser: (cle: keyof SaisieMain) => (v: string) => void
  refus: unknown
}) {
  return (
    <div className={styles.pile}>
      <Note>
        Pour un dossier d’avant la mise en service seulement : il garde son vrai numéro, et ses marchandises
        se saisissent à la main. Toute arrivée depuis la mise en service a sa réception, donc sa facture :
        elle s’ouvre « Depuis la facture reçue ».
      </Note>
      <ChampsMain s={s} poser={poser} refus={refus} />
    </div>
  )
}

function Annuler() {
  const fermer = useFermerFenetre()
  return <Bouton onClick={fermer}>Annuler</Bouton>
}

export function NouveauDossier({ page, clos }: { page: EtatPage; clos: (id: number) => boolean }) {
  const [onglet, choisir] = useOngletAdresse(ONGLETS, 'facture')
  const [s, setS] = useState<SaisieMain>(VIDE)
  const sale = estSale(s)
  const attente = useLecture<EnAttente>('/dossiers/a-rattacher')
  const ecrire = useEcriture((corps: SaisieMain) => api.post<DossierFiche>('/dossiers', corps))
  const poser = (cle: keyof SaisieMain) => (v: string) => setS({ ...s, [cle]: v })
  const ouvrir = async () => {
    const d = await ecrire.mutateAsync({ ...s, numero: s.numero.trim() })
    setS(VIDE)
    dire(`Dossier ${d.numero} ouvert : ses marchandises se saisissent à la main.`)
    page.remplacerPar(d.id, 'main')
  }
  return (
    <Fenetre
      titre="Nouveau dossier d’importation"
      taille="tresLarge"
      sale={sale}
      onFermer={() => page.fermer()}
      pied={
        <>
          <Annuler />
          {onglet === 'main' ? (
            <Bouton
              variante="principal"
              manque={s.date_arrivee ? [] : ['la date d’arrivée']}
              attente="Ouverture…"
              onClick={ouvrir}
            >
              Ouvrir le dossier à saisir à la main
            </Bouton>
          ) : null}
        </>
      }
    >
      <Onglets
        libelle="Ouvrir un dossier"
        actif={onglet}
        onChange={choisir}
        onglets={[
          {
            cle: 'facture',
            libelle: 'Depuis la facture reçue',
            compte: attente.data?.factures.length ?? null,
          },
          { cle: 'main', libelle: 'Dossier d’avant la mise en service', court: 'À la main', sale },
        ]}
      />
      {onglet === 'facture' ? (
        <DepuisLaFacture page={page} clos={clos} />
      ) : (
        <ALaMain s={s} poser={poser} refus={ecrire.error} />
      )}
    </Fenetre>
  )
}
