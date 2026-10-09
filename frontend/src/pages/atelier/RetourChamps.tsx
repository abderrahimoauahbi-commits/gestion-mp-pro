/**
 * Les champs et les gestes du retour sur un ordre : magasin de rangement, motif (R1, R2, R4),
 * date (pas avant l'ordre, pas après aujourd'hui, pas dans la période close), observations ;
 * « Remettre X kg en stock » grisé avec sa raison écrite dessous (an. 9), « Effacer les quantités ».
 */
import { SegmentsTactiles } from '../../composants/atelier/SegmentsTactiles'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { date } from '../../lib/format'
import { magasinsCourants, qte, useBornesDate, useMagasins, useMotifs } from './commun'
import styles from './atelier.module.css'
import type { SaisieRetour } from './RetourSaisie'
import type { LotSorti, MotifLu, OrdreFiche } from './types'

/** « R1 · Reliquat de fin d'ordre ». */
export const libelleMotif = (m: MotifLu) => (m.code_r ? `${m.code_r} · ${m.libelle}` : m.libelle)

/** Le magasin courant : segments jusqu'à trois, sinon une liste ; rien s'il n'y en a qu'un. */
export function ChoixMagasin({
  libelle,
  valeur,
  onChange,
}: {
  libelle: string
  valeur: number | null
  onChange: (id: number) => void
}) {
  const magasins = useMagasins()
  const courants = magasinsCourants(magasins.data)
  if (courants.length <= 1) return null
  return (
    <Champ groupe libelle={libelle}>
      {courants.length <= 3 ? (
        <SegmentsTactiles
          libelle={libelle}
          valeur={valeur}
          options={courants.map((m) => ({ valeur: m.id, libelle: m.code }))}
          onChange={onChange}
        />
      ) : (
        <Selecteur
          valeur={valeur}
          effacable={false}
          options={courants.map((m) => ({ id: m.id, titre: m.code, sous: m.nom }))}
          onChange={(id) => id != null && onChange(id)}
        />
      )}
    </Champ>
  )
}

export function ChampsRetour({
  o,
  s,
  poser,
  magasin,
}: {
  o: OrdreFiche
  s: SaisieRetour
  poser: (m: Partial<SaisieRetour>) => void
  magasin: number
}) {
  const motifs = useMotifs()
  const bornes = useBornesDate()
  const choix = (motifs.data?.motifs ?? []).filter((m) => m.type === 'retour_machine')
  const min = bornes.min && bornes.min > o.date ? bornes.min : o.date
  const raisonMin = min === o.date ? `l’ordre est du ${date(o.date)}` : bornes.raisonMin
  return (
    <>
      <ChoixMagasin
        libelle="Ranger dans le magasin"
        valeur={magasin}
        onChange={(id) => poser({ magasin: id })}
      />
      <Champ libelle="Pourquoi revient-elle ?">
        <Selecteur
          valeur={s.motif ?? choix[0]?.id ?? null}
          effacable={false}
          options={choix.map((m) => ({ id: m.id, titre: libelleMotif(m) }))}
          onChange={(motif) => poser({ motif })}
        />
      </Champ>
      <Champ libelle="Date du retour">
        <DateChamp valeur={s.jour} min={min} raisonMin={raisonMin} onChange={(jour) => poser({ jour })} />
      </Champ>
      <Champ libelle="Observations (facultatif)">
        <Saisie
          valeur={s.commentaire}
          max={300}
          placeholder="Bobines entamées, arrêt du métier…"
          onChange={(commentaire) => poser({ commentaire })}
        />
      </Champ>
    </>
  )
}

/** La raison de griser « Remettre … en stock », dans l'ordre où on la lève. */
export function raisonRetour(e: {
  trop: readonly LotSorti[]
  aucun: boolean
  blocages: readonly string[]
  jour: string
}): string {
  if (e.trop.length)
    return `${e.trop.length} lot(s) dépassent ce qui est parti : ${e.trop
      .map((l) => `${l.reference} (lot ${l.lot})`)
      .join(', ')}`
  if (e.aucun) return 'Saisir ce qui revient, lot par lot.'
  if (e.blocages.length) return 'Un inventaire est en cours (voir le bandeau)'
  if (!e.jour) return 'Choisir la date du retour'
  return ''
}

export function GestesRetour(p: {
  total: number
  nomMagasin: string
  blocages: readonly string[]
  trop: readonly LotSorti[]
  aucun: boolean
  jour: string
  onEnregistrer: () => Promise<void>
  onEffacer: () => void
}) {
  const raison = raisonRetour(p)
  return (
    <div className={styles.gestes}>
      <Confirmer
        taille="atelier"
        variante="principal"
        grise={raison || undefined}
        question={`Remettre ${qte(p.total)} en stock (${p.nomMagasin}) ?`}
        oui="Oui, enregistrer le retour"
        attente="Enregistrement…"
        onOui={p.onEnregistrer}
      >
        {p.total > 0 ? `Remettre ${qte(p.total)} en stock` : 'Remettre en stock'}
      </Confirmer>
      {!p.aucun ? (
        <Confirmer
          taille="atelier"
          question="Effacer les quantités saisies ?"
          oui="Oui, effacer"
          onOui={p.onEffacer}
        >
          Effacer les quantités
        </Confirmer>
      ) : null}
    </div>
  )
}
