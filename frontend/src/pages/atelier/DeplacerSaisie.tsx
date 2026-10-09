/**
 * Déplacer un lot (`/atelier/deplacer?lot=ID`) : depuis, vers, combien (kg, bobines, palettes ;
 * plafonné au disponible, arrondi vers le bas), pourquoi, quand, observations. Vers une
 * quarantaine : motif imposé, observations obligatoires. Création et validation en une
 * transaction ; après un déplacement, la quantité est relue sur le nouveau disponible (an. 24).
 */
import { useState } from 'react'

import { BandeauBlocages } from '../../composants/atelier/BandeauBlocages'
import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { SegmentsTactiles } from '../../composants/atelier/SegmentsTactiles'
import { useSaisieGardee } from '../../composants/atelier/saisieGardee'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Quantite } from '../../composants/saisie/Quantite'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { api } from '../../lib/api'
import { useEcriture, useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { toutRendre, versKg, type Conditionnement } from '../../lib/unites'
import { attente, Fiche, LienBouton, NoteAtelier } from './briques'
import { qte, sansDoublon, suspensions, useBornesDate, useMagasins, useMotifs } from './commun'
import styles from './atelier.module.css'
import {
  arrivees,
  deplacementVide,
  lireDeplacement,
  motifQuarantaine,
  motifsAtelier,
  raisonDeplacer,
  type SaisieDeplacement,
} from './deplacement'
import type { LotFiche, MagasinFiche, OperationFiche } from './types'

type Poser = (m: Partial<SaisieDeplacement>) => void
type Lu = ReturnType<typeof lireDeplacement>

function OuEtCombien({
  l,
  s,
  poser,
  lu,
  mags,
}: {
  l: LotFiche
  s: SaisieDeplacement
  poser: Poser
  lu: Lu
  mags: MagasinFiche[]
}) {
  const c: Conditionnement = {
    poidsBobine: l.poids_bobine,
    bobinesPalette: l.bobines_palette,
    kgParMl: l.kg_par_ml,
  }
  return (
    <>
      <Champ libelle="Depuis">
        <Selecteur
          valeur={lu.depuis}
          effacable={false}
          options={lu.ds.map((m) => ({ id: m.magasin_id, titre: `${m.magasin} — ${qte(m.quantite)}` }))}
          onChange={(id) => poser({ depuis: id, kg: null, vers: s.vers === id ? null : s.vers })}
        />
      </Champ>
      <Champ libelle="Vers">
        <Selecteur
          valeur={s.vers}
          placeholder="Choisir…"
          options={arrivees(mags, lu.depuis)}
          onChange={(vers) => poser({ vers })}
        />
      </Champ>
      <Champ groupe libelle={`Quantité (disponible : ${qte(lu.dispo)})`}>
        <Quantite
          tactile
          libelle="Quantité à déplacer"
          kg={lu.kg}
          unite={s.unite}
          onChange={(kg) => poser({ kg: kg ?? 0 })}
          onUnite={(unite) => poser({ unite })}
          poidsBobine={l.poids_bobine}
          bobinesPalette={l.bobines_palette}
          kgParMl={l.kg_par_ml}
          borne={lu.dispo}
        />
      </Champ>
      <Bouton
        taille="atelier"
        onClick={() => poser({ kg: versKg(toutRendre(c, lu.dispo, s.unite), s.unite, c) ?? lu.dispo })}
      >
        {`Tout ce qui est dans ${lu.depart?.code ?? 'ce magasin'}`}
      </Bouton>
    </>
  )
}

function Pourquoi({ s, poser, quarantaine }: { s: SaisieDeplacement; poser: Poser; quarantaine: boolean }) {
  const motifs = useMotifs()
  const bornes = useBornesDate()
  const choix = motifsAtelier(motifs.data?.motifs ?? [])
  return (
    <>
      {quarantaine ? (
        <NoteAtelier>Pourquoi ? Mise en quarantaine (motif imposé).</NoteAtelier>
      ) : (
        <Champ groupe libelle="Pourquoi ?">
          <SegmentsTactiles
            libelle="Pourquoi ?"
            valeur={s.motif ?? choix[0]?.id ?? null}
            options={choix.map((m) => ({ valeur: m.id, libelle: m.libelle }))}
            onChange={(motif) => poser({ motif })}
          />
        </Champ>
      )}
      <Champ libelle="Date">
        <DateChamp valeur={s.jour} {...bornes} onChange={(jour) => poser({ jour })} />
      </Champ>
      <Champ
        libelle={quarantaine ? 'Observations (ce qui est douteux)' : 'Observations (facultatif)'}
        obligatoire={quarantaine}
      >
        <Saisie valeur={s.commentaire} max={300} onChange={(commentaire) => poser({ commentaire })} />
      </Champ>
    </>
  )
}

/** L'envoi du transfert, et ce qu'il dit une fois fait. */
function useEnvoi(l: LotFiche, s: SaisieDeplacement, poser: Poser, oublier: () => void) {
  const motifs = useMotifs()
  const [fait, setFait] = useState('')
  const envoi = useEcriture((corps: unknown) => api.post<OperationFiche>('/operations', corps))
  const envoyer = async (depuis: number, kg: number, quarantaine: boolean) => {
    const liste = motifs.data?.motifs ?? []
    const motif = quarantaine ? motifQuarantaine(liste)?.id : (s.motif ?? motifsAtelier(liste)[0]?.id)
    const r = await envoi.mutateAsync({
      type: 'transfert',
      date: s.jour,
      motif_id: motif,
      commentaire: s.commentaire.trim(),
      lignes: [
        {
          matiere_id: l.matiere_id,
          lot_id: l.lot_id,
          magasin_id: depuis,
          magasin_destination_id: s.vers,
          quantite: kg,
          unite: 'kg',
        },
      ],
      valider: true,
    })
    oublier()
    poser({ kg: null, vers: null, commentaire: '' })
    const texte = `Fait — ${r.numero ?? ''} : ${qte(r.total)} déplacés.`
    setFait(texte)
    dire(texte)
  }
  return { fait, envoyer }
}

/** Ce qui grise « Déplacer » : inventaire (bandeau), arrivée, quantité, observations. */
function useBlocages(l: LotFiche, lu: Lu): string[] {
  const { contexte } = useSession()
  const noms = [lu.depart?.nom ?? '', lu.vers?.nom ?? ''].filter(Boolean)
  return sansDoublon(
    suspensions(contexte.inventaires_ouverts, [{ id: l.matiere_id, reference: l.reference }], noms),
  )
}

function FormeDeplacement({ l, mags }: { l: LotFiche; mags: MagasinFiche[] }) {
  const [s, setS, oublier] = useSaisieGardee<SaisieDeplacement>(`deplacer:${l.lot_id}`, deplacementVide())
  const poser: Poser = (m) => setS((avant) => ({ ...avant, ...m }))
  const { fait, envoyer } = useEnvoi(l, s, poser, oublier)
  const lu = lireDeplacement(l, s, mags)
  const blocages = useBlocages(l, lu)
  const raison = raisonDeplacer({ ...lu, blocages, vers: s.vers, commentaire: s.commentaire })
  return (
    <EcranAtelier
      titre="Déplacer un lot"
      retour="/atelier/deplacer"
      enTete={<BandeauBlocages blocages={blocages} />}
    >
      <div className={styles.pile}>
        <Fiche titre={l.reference}>
          <NoteAtelier>lot {l.lot}</NoteAtelier>
        </Fiche>
        {fait ? (
          <Fiche ton="ok" titre={fait}>
            <LienBouton vers={`/atelier/lots/${l.lot_id}`}>Voir le lot</LienBouton>
          </Fiche>
        ) : null}
        {!lu.ds.length ? (
          <NoteAtelier>
            {l.quarantaine > 0.001
              ? 'Ce lot n’a pas de matière disponible à déplacer : il est en quarantaine, et seuls les achats ou la direction le libèrent.'
              : 'Ce lot n’a pas de matière disponible à déplacer.'}
          </NoteAtelier>
        ) : (
          <>
            <OuEtCombien l={l} s={s} poser={poser} lu={lu} mags={mags} />
            <Pourquoi s={s} poser={poser} quarantaine={lu.quarantaine} />
            <Confirmer
              taille="atelier"
              variante="principal"
              grise={raison || undefined}
              question={`Déplacer ${qte(lu.kg)} de ${lu.depart?.code ?? ''} vers ${lu.vers?.code ?? ''} ?`}
              oui="Oui, déplacer"
              attente="Enregistrement…"
              onOui={() => (lu.depuis == null ? undefined : envoyer(lu.depuis, lu.kg, lu.quarantaine))}
            >
              {`Déplacer ${qte(lu.kg)}`}
            </Confirmer>
          </>
        )}
      </div>
    </EcranAtelier>
  )
}

export function DeplacerSaisie({ id }: { id: number }) {
  const lot = useLecture<LotFiche>(`/lots/${id}`)
  const magasins = useMagasins()
  const motifs = useMotifs()
  const enAttente = attente([lot, magasins, motifs], 'le lot')
  if (enAttente || !lot.data || !magasins.data)
    return (
      <EcranAtelier titre="Déplacer un lot" retour="/atelier/deplacer">
        {enAttente}
      </EcranAtelier>
    )
  return <FormeDeplacement l={lot.data} mags={magasins.data} />
}
