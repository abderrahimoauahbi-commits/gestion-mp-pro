/**
 * Le retour sur un ordre (`/atelier/retour?ordre=ID`) : lot par lot, ce qui revient (kg, bobines,
 * palettes ; une conversion arrondit **vers le bas**, on ne rend jamais plus que le sorti net,
 * an. 21, an. 24), le magasin, le motif, la date, les observations. La saisie est gardée (an. 17) ;
 * création et validation en une transaction (`valider: true`).
 */
import { useState } from 'react'

import { BandeauBlocages } from '../../composants/atelier/BandeauBlocages'
import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { useSaisieGardee } from '../../composants/atelier/saisieGardee'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import { Quantite } from '../../composants/saisie/Quantite'
import { api } from '../../lib/api'
import { kgEtMetres } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { aujourdhui } from '../../lib/heure'
import { toutRendre, versKg, type Conditionnement, type Unite } from '../../lib/unites'
import { attente, Fiche, LienBouton, Ligne } from './briques'
import { qte, sansDoublon, suspensions, useMagasins, useMotifs } from './commun'
import styles from './atelier.module.css'
import { ChampsRetour, GestesRetour } from './RetourChamps'
import type { LotSorti, OperationFiche, OrdreFiche } from './types'

export interface SaisieRetour {
  lignes: Record<string, { kg: number | null; unite: Unite }>
  magasin: number | null
  motif: number | null
  jour: string
  commentaire: string
}

const vide = (): SaisieRetour => ({
  lignes: {},
  magasin: null,
  motif: null,
  jour: aujourdhui(),
  commentaire: '',
})

const cond = (l: LotSorti): Conditionnement => ({
  poidsBobine: l.poids_bobine,
  bobinesPalette: l.bobines_palette,
  kgParMl: l.kg_par_ml,
})

/** Les lots qui dépassent ce qui est parti : « POIL (lot L-1), … ». */
export function depassements(lots: readonly LotSorti[], s: SaisieRetour): LotSorti[] {
  return lots.filter((l) => (s.lignes[l.lot_id]?.kg ?? 0) > l.sorti_net + 0.0005)
}

function CarteLot({
  l,
  s,
  poser,
}: {
  l: LotSorti
  s: SaisieRetour
  poser: (m: Partial<SaisieRetour>) => void
}) {
  const ligne = s.lignes[l.lot_id] ?? { kg: null, unite: 'kg' }
  const changer = (m: Partial<typeof ligne>) =>
    poser({ lignes: { ...s.lignes, [l.lot_id]: { ...ligne, ...m } } })
  const trop = (ligne.kg ?? 0) > l.sorti_net + 0.0005
  return (
    <Fiche titre={l.reference} ton={trop ? 'alerte' : undefined} libelle={`Lot ${l.lot}`}>
      <Ligne libelle={`lot ${l.lot}`}>Sorti net : {kgEtMetres(l.sorti_net, l.kg_par_ml, true)}</Ligne>
      <Quantite
        tactile
        libelle={`Revient du lot ${l.lot}`}
        kg={ligne.kg}
        unite={ligne.unite}
        onChange={(kg) => changer({ kg })}
        onUnite={(unite) => changer({ unite })}
        poidsBobine={l.poids_bobine}
        bobinesPalette={l.bobines_palette}
        kgParMl={l.kg_par_ml}
        borne={l.sorti_net}
      />
      <Bouton
        taille="atelier"
        onClick={() =>
          changer({ kg: versKg(toutRendre(cond(l), l.sorti_net, ligne.unite), ligne.unite, cond(l)) ?? 0 })
        }
      >
        Tout ce qui est parti
      </Bouton>
      {trop ? <Note ton="critique">On ne rend pas plus que ce qui est parti.</Note> : null}
    </Fiche>
  )
}

/** Les blocages du retour : ceux des lots sortis (inventaire), et du magasin de rangement. */
function useBlocagesRetour(
  lots: readonly LotSorti[],
  pris: readonly LotSorti[],
  nomMagasin: string,
): string[] {
  const { contexte } = useSession()
  return sansDoublon([
    ...lots.map((l) => l.blocage),
    ...suspensions(
      contexte.inventaires_ouverts,
      pris.map((l) => ({ id: l.matiere_id, reference: l.reference })),
      [nomMagasin],
    ),
  ])
}

/** L'envoi du retour : création et validation en une transaction, puis la saisie remise à zéro. */
function useEnvoiRetour(o: OrdreFiche, garde: ReturnType<typeof useSaisieGardee<SaisieRetour>>) {
  const [s, setS, oublier] = garde
  const motifs = useMotifs()
  const [fait, setFait] = useState('')
  const envoi = useEcriture((corps: unknown) => api.post<OperationFiche>('/operations', corps))
  const enregistrer = async (pris: readonly LotSorti[], magasin: number) => {
    setFait('')
    const r = await envoi.mutateAsync({
      type: 'retour_machine',
      ordre_id: o.id,
      date: s.jour,
      motif_id: s.motif ?? motifs.data?.motifs.find((m) => m.type === 'retour_machine')?.id,
      commentaire: s.commentaire.trim(),
      lignes: pris.map((l) => ({
        matiere_id: l.matiere_id,
        lot_id: l.lot_id,
        magasin_id: magasin,
        quantite: s.lignes[l.lot_id]?.kg ?? 0,
        unite: 'kg',
      })),
      valider: true,
    })
    oublier()
    setS({ ...s, lignes: {}, commentaire: '' })
    const texte = `Retour enregistré — ${r.numero ?? ''} : ${qte(r.total)} remis en stock.`
    setFait(texte)
    dire(texte)
  }
  return { fait, enregistrer }
}

function Saisie({ o, lots }: { o: OrdreFiche; lots: LotSorti[] }) {
  const magasins = useMagasins()
  const garde = useSaisieGardee<SaisieRetour>(`retour:${o.id}`, vide())
  const [s, setS] = garde
  const poser = (m: Partial<SaisieRetour>) => setS((avant) => ({ ...avant, ...m }))
  const { fait, enregistrer } = useEnvoiRetour(o, garde)
  const magasin = s.magasin ?? o.magasin_id
  const nomMagasin = magasins.data?.find((m) => m.id === magasin)?.nom ?? ''
  const pris = lots.filter((l) => (s.lignes[l.lot_id]?.kg ?? 0) > 0)
  const blocages = useBlocagesRetour(lots, pris, nomMagasin)
  const total = pris.reduce((t, l) => t + (s.lignes[l.lot_id]?.kg ?? 0), 0)
  return (
    <EcranAtelier
      titre={`Retour — ${o.numero ?? 'ordre'}`}
      retour="/atelier/retour"
      enTete={<BandeauBlocages blocages={blocages} />}
    >
      <div className={styles.pile}>
        {fait ? (
          <Fiche ton="ok" titre={fait}>
            <LienBouton vers="/atelier">Revenir à l’accueil</LienBouton>
          </Fiche>
        ) : null}
        {!lots.length ? <Vide>Tout ce qui est parti sur cet ordre est déjà revenu.</Vide> : null}
        {lots.map((l) => (
          <CarteLot key={l.lot_id} l={l} s={s} poser={poser} />
        ))}
        {lots.length ? (
          <>
            <ChampsRetour o={o} s={s} poser={poser} magasin={magasin} />
            <GestesRetour
              total={total}
              nomMagasin={nomMagasin}
              blocages={blocages}
              trop={depassements(lots, s)}
              aucun={!pris.length}
              jour={s.jour}
              onEnregistrer={() => enregistrer(pris, magasin)}
              onEffacer={() => poser({ lignes: {} })}
            />
          </>
        ) : null}
      </div>
    </EcranAtelier>
  )
}

export function RetourSaisie({ id }: { id: number }) {
  const ordre = useLecture<OrdreFiche>(`/ordres/${id}`)
  const sortis = useLecture<LotSorti[]>(`/ordres/${id}/lots-sortis`)
  const magasins = useMagasins()
  const motifs = useMotifs()
  const enAttente = attente([ordre, sortis, magasins, motifs], 'les lots sortis')
  const o = ordre.data
  if (enAttente || !o || !sortis.data)
    return (
      <EcranAtelier titre={o ? `Retour — ${o.numero ?? 'ordre'}` : 'Retour — ordre'} retour="/atelier/retour">
        {enAttente}
      </EcranAtelier>
    )
  return <Saisie o={o} lots={sortis.data.filter((l) => l.sorti_net > 0.0005)} />
}
