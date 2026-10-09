/**
 * La fenêtre de comptage d'un inventaire (`/inventaires/:id`, ECRANS-PRO partie 6) : en-tête,
 * gestes à place fixe, indicateurs, volets « Lots à compter » et « Pièces jointes »
 * (`?onglet=lots|pieces`). Saisie si l'inventaire est ouvert (direction, achats) ; lecture une
 * fois validé, abandonné ou annulé. Les saisies restent locales jusqu'à « Enregistrer le
 * comptage » ; « Valider » enregistre d'abord.
 */
import { useCallback, useMemo, useState } from 'react'

import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { api } from '../../lib/api'
import { nombre } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import {
  changer as changerBrouillon,
  corpsComptages,
  etatLigne,
  sansLesEnvoyes,
  totaux,
  type Brouillons,
} from './calculComptage'
import { enTeteDeFiche } from './enTeteFiche'
import { GestesComptage } from './GestesComptage'
import { IndicateursComptage } from './IndicateursComptage'
import { VoletsComptage } from './LotsACompter'
import { LotTrouve } from './LotTrouve'
import { statutInventaire, type InventaireFiche } from './types'

/** Les écritures de la fenêtre : enregistrer, valider (après avoir enregistré), abandonner, annuler. */
function useGestes(fiche: InventaireFiche, brouillons: Brouillons, oublier: (envoyes: Brouillons) => void) {
  const chemin = `/inventaires/${fiche.id}`
  const ecrire = useEcriture(async (faire: () => Promise<InventaireFiche>) => faire())
  const n = Object.keys(brouillons).length
  const enregistrerSeul = async () =>
    n ? api.put<InventaireFiche>(`${chemin}/comptages`, corpsComptages(fiche, brouillons)) : fiche
  const motive = (geste: string) => (motif: string) =>
    ecrire.mutateAsync(() =>
      api.post<InventaireFiche>(`${chemin}/${geste}`, { version: fiche.version, motif }),
    )
  return {
    enregistrer: async () => {
      await ecrire.mutateAsync(enregistrerSeul)
      oublier(brouillons)
      dire(`${nombre(n)} comptage(s) enregistré(s).`)
    },
    valider: async (ajustes: number) => {
      await ecrire.mutateAsync(async () => {
        const lue = await enregistrerSeul()
        oublier(brouillons)
        return api.post<InventaireFiche>(`${chemin}/valider`, { version: lue.version })
      })
      dire(`Inventaire validé : ${nombre(ajustes)} ajustement(s) écrit(s) au stock.`)
    },
    abandonner: async (motif: string) => {
      await motive('abandonner')(motif)
      oublier(brouillons)
      dire(`${fiche.numero} abandonné : les mouvements reprennent.`)
    },
    annuler: async (motif: string) => {
      await motive('annuler')(motif)
      dire(`Inventaire ${fiche.numero} annulé : ses ajustements sont contre-passés.`)
    },
  }
}

/** Les saisies locales de la fiche et ce qu'elles donnent ligne à ligne. */
function useSaisies(fiche: InventaireFiche) {
  const { moi } = useSession()
  const [brouillons, setBrouillons] = useState<Brouillons>({})
  // Oublier ce qui a été envoyé, mais pas ce qui a été tapé pendant l'envoi.
  const oublier = useCallback((envoyes: Brouillons) => setBrouillons((b) => sansLesEnvoyes(b, envoyes)), [])
  const etats = useMemo(
    () =>
      fiche.lignes.map((l) =>
        etatLigne(l, brouillons[l.id], fiche.tolerance, { nom: moi.nom, ouvreur: fiche.cree_par }),
      ),
    [fiche, brouillons, moi.nom],
  )
  return { brouillons, setBrouillons, oublier, etats, t: totaux(etats) }
}

function FicheComptage({ fiche, onFermer }: { fiche: InventaireFiche; onFermer: () => void }) {
  const { role, moi } = useSession()
  const { brouillons, setBrouillons, oublier, etats, t } = useSaisies(fiche)
  const [trouve, setTrouve] = useState(false)
  const [trouveSale, setTrouveSale] = useState(false)
  const gestes = useGestes(fiche, brouillons, oublier)
  const directionOuAchats = role === 'direction' || role === 'achats'
  const saisie = fiche.statut === 'ouvert' && directionOuAchats
  const statut = statutInventaire(fiche.statut)
  return (
    <Fenetre
      taille="tresLarge"
      sale={t.modifiees > 0 || trouveSale}
      onFermer={onFermer}
      titre={
        <>
          {fiche.numero} · {fiche.libelle}{' '}
          <Badge ton={statut.ton}>{enTeteDeFiche.badge(fiche, statut.libelle)}</Badge>
        </>
      }
      sous={enTeteDeFiche.ligne(fiche)}
    >
      <GestesComptage
        fiche={fiche}
        t={t}
        saisie={saisie}
        peutAnnuler={directionOuAchats}
        voitTheorique={role === 'direction'}
        trouveOuvert={trouve}
        onTrouve={() => setTrouve(!trouve)}
        gestes={{ ...gestes, valider: () => gestes.valider(t.ajustes) }}
      />
      <IndicateursComptage t={t} voitPrix={moi.voit_prix} />
      {saisie ? <NoteDeSaisie /> : null}
      {trouve && saisie ? (
        <LotTrouve fiche={fiche} onSale={setTrouveSale} onFermer={() => setTrouve(false)} />
      ) : null}
      <VoletsComptage
        fiche={fiche}
        etats={etats}
        saisie={saisie}
        modifiees={t.modifiees}
        changer={(l, modif) => setBrouillons((b) => changerBrouillon(b, l, modif))}
      />
    </Fenetre>
  )
}

const NOTE_SAISIE =
  'Saisir le poids compté en kg (ou les palettes et bobines : le poids se calcule au poids de bobine du lot). Une ligne laissée vide n’est pas comptée et ne sera pas ajustée. Un écart hors tolérance en rouge demande une justification.'

function NoteDeSaisie() {
  return (
    <Note uneLigne={NOTE_SAISIE}>
      Saisir le poids compté en kg (ou les palettes et bobines : le poids se calcule au poids de bobine du
      lot). Une ligne laissée vide n’est pas comptée et ne sera pas ajustée. Un écart hors tolérance{' '}
      <strong>en rouge</strong> demande une justification.
    </Note>
  )
}

export function Comptage({ id, onFermer }: { id: number; onFermer: () => void }) {
  const lecture = useLecture<InventaireFiche>(`/inventaires/${id}`)
  if (lecture.data) return <FicheComptage key={lecture.data.id} fiche={lecture.data} onFermer={onFermer} />
  return (
    <Fenetre titre="Inventaire" taille="tresLarge" onFermer={onFermer}>
      {lecture.isError ? (
        <Erreur erreur={lecture.error} onReessayer={() => void lecture.refetch()} />
      ) : (
        <Chargement quoi="l’inventaire" />
      )}
    </Fenetre>
  )
}
