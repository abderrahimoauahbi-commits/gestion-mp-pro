/**
 * La fiche d'une réception en fenêtre (`/receptions/:id?onglet=lignes|reclamations|pieces|
 * historique`, ECRANS-PRO 4.17–4.21) : relue à l'ouverture, au retour sur l'onglet et toutes les
 * 30 s pour un brouillon (le serveur le remet à jour) ; le panneau de facture garde sa saisie.
 */
import { useState } from 'react'

import { Historique } from '../../composants/documents/Historique'
import { PiecesJointes } from '../../composants/documents/PiecesJointes'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import { api } from '../../lib/api'
import { useOngletAdresse } from '../../lib/adresse'
import { useEcriture } from '../../lib/requetes'
import { useFormeFiche, memeForme } from '../commandes/useFormeFiche'
import styles from '../plan-achat/achats.module.css'
import { corpsFacture, versFormeFacture } from './calculFiche'
import { useReception } from './donnees'
import { BandeauxReception, IndicateursReception, QuiQuand } from './EnTeteReception'
import { GestesReception, type Navigation } from './GestesReception'
import { PanneauFacture } from './PanneauFacture'
import type { ReceptionFiche } from './types'
import { VoletLignesReception } from './VoletLignesReception'
import { VoletReclamationsReception } from './VoletReclamationsReception'

const VOLETS = ['lignes', 'reclamations', 'pieces', 'historique'] as const
type Volet = (typeof VOLETS)[number]

function useFacture(r: ReceptionFiche, fermer: () => void) {
  const f = useFormeFiche(r, versFormeFacture, memeForme)
  const ecrire = useEcriture(() =>
    api.put<ReceptionFiche>(`/receptions/${r.id}/facture`, corpsFacture(f.forme, f.initiale, f.version)),
  )
  const enregistrer = async () => {
    const numero = f.forme.numero.trim()
    f.repartir(await ecrire.mutateAsync())
    dire(numero ? `Facture ${numero} enregistrée.` : 'Facture détachée de la réception.')
    fermer()
  }
  return { f, enregistrer }
}

/** « Annuler » et « Enregistrer la facture » du panneau de facture. */
function BoutonsFacture({
  facture,
  onFermer,
}: {
  facture: ReturnType<typeof useFacture>
  onFermer: () => void
}) {
  return (
    <>
      <Bouton
        onClick={() => {
          facture.f.reprendre()
          onFermer()
        }}
      >
        Annuler
      </Bouton>
      <Bouton
        variante="principal"
        attente="Enregistrement…"
        grise={facture.f.sale ? undefined : 'Rien n’a changé.'}
        onClick={facture.enregistrer}
      >
        Enregistrer la facture
      </Bouton>
    </>
  )
}

export type NavFiche = Omit<Navigation, 'validee'> & { ouvrirReclamation: (id: number) => void }

function Ecrite({ r, onFermer, nav }: { r: ReceptionFiche; onFermer: () => void; nav: NavFiche }) {
  const [volet, choisir] = useOngletAdresse<Volet>(VOLETS, 'lignes')
  const [panneau, setPanneau] = useState(false)
  const [validee, setValidee] = useState(false)
  const facture = useFacture(r, () => setPanneau(false))
  const sale = panneau && facture.f.sale
  return (
    <Fenetre
      titre={
        <span className={styles.rangeeCentree}>
          Réception — {r.numero ?? 'Brouillon'} · {r.fournisseur}{' '}
          <Badge famille="document" valeur={r.statut} />
        </span>
      }
      sous={<QuiQuand r={r} />}
      taille="tresLarge"
      sale={sale}
      onFermer={onFermer}
      pied={
        <div className={styles.pied}>
          {panneau ? <BoutonsFacture facture={facture} onFermer={() => setPanneau(false)} /> : null}
          <span className={styles.pousse} />
          <GestesReception
            r={r}
            nav={{ ...nav, validee: () => setValidee(true) }}
            sale={sale}
            panneau={panneau}
            onPanneau={() => setPanneau(true)}
          />
        </div>
      }
    >
      <IndicateursReception r={r} />
      <BandeauxReception r={r} vientDEtreValidee={validee} />
      {panneau ? <PanneauFacture r={r} f={facture.f} /> : null}
      <Onglets<Volet>
        libelle="Volets de la réception"
        actif={volet}
        onChange={choisir}
        onglets={[
          { cle: 'lignes', libelle: 'Lignes pesées', compte: r.lignes.length },
          { cle: 'reclamations', libelle: 'Réclamations', compte: r.reclamations.length },
          { cle: 'pieces', libelle: 'Pièces jointes', court: 'Pièces' },
          { cle: 'historique', libelle: 'Historique' },
        ]}
      />
      {volet === 'lignes' ? <VoletLignesReception r={r} /> : null}
      {volet === 'reclamations' ? (
        <VoletReclamationsReception r={r} onOuvrir={nav.ouvrirReclamation} />
      ) : null}
      {volet === 'pieces' ? <PiecesJointes objet="reception" id={r.id} /> : null}
      {volet === 'historique' ? <Historique objet="reception" id={r.id} /> : null}
    </Fenetre>
  )
}

export function FicheReception({ id, onFermer, nav }: { id: number; onFermer: () => void; nav: NavFiche }) {
  const lu = useReception(id)
  if (lu.data) return <Ecrite r={lu.data} onFermer={onFermer} nav={nav} />
  return (
    <Fenetre titre="Réception" onFermer={onFermer} taille="tresLarge">
      {lu.isError && lu.error.statut === 404 ? <Vide>Cette réception n’existe plus.</Vide> : null}
      {lu.isError && lu.error.statut !== 404 ? (
        <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
      ) : null}
      {lu.isPending ? <Chargement quoi="la réception" /> : null}
    </Fenetre>
  )
}
