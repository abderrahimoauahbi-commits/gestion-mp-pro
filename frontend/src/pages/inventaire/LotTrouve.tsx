/**
 * L'encart « Lot trouvé » de la fenêtre de comptage (ECRANS-PRO partie 6) : un lot trouvé sur
 * place, que le théorique ne connaissait pas. Le lot n'est **pas** créé ici : la ligne garde sa
 * matière et son numéro (ou la case « Lot interne », numéro `LOT-AAAA-NNNN` donné à la
 * validation), et le lot naît à la validation (an. 19, (c)). Les bobines se pèsent au poids du
 * lot s'il existe déjà, sinon à celui du catalogue ; l'aide dit lequel.
 */
import { useEffect, useState } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Grille } from '../../composants/mise-en-page/Grille'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { SelecteurMatiere } from '../../composants/saisie/SelecteurMatiere'
import { api } from '../../lib/api'
import { metres, nombre } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import { JUSTIFICATION_MINIMUM } from './calculComptage'
import { choixMatiere } from './matieres'
import type { InventaireFiche, LotSolde, MagasinFiche, MatiereResume } from './types'

export interface SaisieLot {
  matiere: number | null
  numero: string
  interne: boolean
  magasin: number | null
  bobines: number | null
  compte: number | null
  justification: string
}

/** Ce qu'il manque pour ajouter le lot trouvé (raison du bouton grisé). */
export function manqueLotTrouve(s: SaisieLot): string[] {
  const manque: string[] = []
  if (s.matiere == null) manque.push('la matière')
  if (!s.interne && !s.numero.trim()) manque.push('le numéro de lot (ou cocher Lot interne)')
  if (s.magasin == null) manque.push('le magasin')
  if (s.compte == null || s.compte <= 0) manque.push('le poids compté')
  if (s.justification.trim().length < JUSTIFICATION_MINIMUM)
    manque.push('la justification (3 caractères au moins)')
  return manque
}

export interface Poids {
  poids: number
  source: string
}

/** Le poids d'une bobine : celui du lot s'il existe déjà, sinon celui du catalogue. */
export function poidsDeBobine(
  m: MatiereResume | undefined,
  lots: readonly LotSolde[] | undefined,
  s: Pick<SaisieLot, 'numero' | 'interne'>,
): Poids | null {
  const numero = s.numero.trim().toLowerCase()
  const lot = s.interne || !numero ? undefined : lots?.find((l) => l.lot.trim().toLowerCase() === numero)
  if (lot && lot.poids_bobine > 0) return { poids: lot.poids_bobine, source: 'poids du lot' }
  const catalogue = m?.poids_bobine ?? 0
  return catalogue > 0 ? { poids: catalogue, source: 'poids du catalogue' } : null
}

/** La saisie de l'encart, ses lectures et son envoi. */
function useLotTrouve(fiche: InventaireFiche, onSale: (sale: boolean) => void, onFermer: () => void) {
  const [s, setS] = useState<SaisieLot>({
    matiere: null,
    numero: '',
    interne: false,
    magasin: fiche.magasin_id,
    bobines: null,
    compte: null,
    justification: '',
  })
  const matieres = useLecture<MatiereResume[]>('/matieres', { actif: true })
  const magasins = useLecture<MagasinFiche[]>('/magasins')
  const lots = useLecture<LotSolde[]>(s.matiere == null ? null : '/lots', { matiere: s.matiere })
  const m = matieres.data?.find((x) => x.id === s.matiere)
  const rempli = s.matiere != null || Boolean(s.numero || s.justification) || s.compte != null
  useEffect(() => onSale(rempli), [rempli, onSale])
  const envoi = useEcriture(() =>
    api.post<InventaireFiche>(`/inventaires/${fiche.id}/lots-trouves`, {
      version: fiche.version,
      matiere_id: s.matiere,
      lot_numero: s.interne ? '' : s.numero.trim(),
      lot_interne: s.interne,
      magasin_id: s.magasin,
      compte: s.compte,
      bobines: s.bobines,
      justification: s.justification.trim(),
    }),
  )
  return {
    s,
    poser: (modif: Partial<SaisieLot>) => setS((x) => ({ ...x, ...modif })),
    m,
    matieres: matieres.data ?? [],
    magasins: (magasins.data ?? []).filter((g) => g.actif),
    poids: poidsDeBobine(m, lots.data, s),
    rempli,
    ajouter: async () => {
      await envoi.mutateAsync()
      dire('Lot trouvé ajouté au comptage.')
      onSale(false)
      onFermer()
    },
  }
}

type Encart = ReturnType<typeof useLotTrouve>

/** Le numéro (ou « Lot interne ») et le magasin. */
function ChampsDuLot({ e, fiche }: { e: Encart; fiche: InventaireFiche }) {
  const { s, poser } = e
  return (
    <>
      <Champ
        libelle="Numéro de lot"
        aide={s.interne ? 'numéro donné à la validation (LOT-AAAA-NNNN)' : 'Celui de l’étiquette'}
      >
        <Saisie
          valeur={s.interne ? '' : s.numero}
          onChange={(v) => poser({ numero: v })}
          max={80}
          desactive={s.interne}
        />
      </Champ>
      <Champ libelle="Lot interne" groupe aide="Le lot n’a pas d’étiquette lisible">
        <Interrupteur valeur={s.interne} onChange={(v) => poser({ interne: v })} libelle="Lot interne" />
      </Champ>
      <Champ libelle="Magasin" aide={fiche.magasin_id ? 'Celui de l’inventaire' : undefined}>
        {fiche.magasin_id ? (
          <Saisie valeur={fiche.magasin} onChange={() => undefined} desactive />
        ) : (
          <Selecteur
            effacable={false}
            valeur={s.magasin}
            options={e.magasins.map((g) => ({ id: g.id, titre: g.code, sous: g.nom }))}
            onChange={(id) => poser({ magasin: id })}
            placeholder="Choisir…"
          />
        )}
      </Champ>
    </>
  )
}

function Champs({ e, fiche }: { e: Encart; fiche: InventaireFiche }) {
  const { s, poser, poids } = e
  const changerBobines = (b: number | null) =>
    poser({ bobines: b, compte: b == null || !poids ? s.compte : Math.round(b * poids.poids * 100) / 100 })
  const ml = e.m && s.compte ? metres(s.compte, e.m.kg_par_ml) : ''
  return (
    <Grille colonnes={3}>
      <Champ libelle="Matière" groupe large>
        <SelecteurMatiere
          matieres={e.matieres.map(choixMatiere)}
          valeur={s.matiere}
          onChange={(id) => poser({ matiere: id })}
        />
      </Champ>
      <ChampsDuLot e={e} fiche={fiche} />
      <Champ
        libelle="Bobines"
        aide={
          poids
            ? `× ${nombre(poids.poids, 2, 4)} kg (${poids.source})`
            : 'Poids de bobine inconnu : saisir le poids compté'
        }
      >
        <Nombre valeur={s.bobines} onChange={changerBobines} min={0} decimales={0} desactive={!poids} />
      </Champ>
      <Champ libelle="Compté (kg)" aide={ml ? `${ml}, à titre indicatif` : undefined}>
        <Nombre
          valeur={s.compte}
          onChange={(v) => poser({ compte: v, bobines: null })}
          min={0}
          decimales={3}
        />
      </Champ>
      <Champ
        libelle="Justification"
        large
        aide="Obligatoire : un lot hors du théorique est toujours un écart à expliquer"
      >
        <Saisie
          valeur={s.justification}
          onChange={(v) => poser({ justification: v })}
          max={300}
          placeholder="Palette retrouvée derrière le rayonnage B, étiquette arrachée…"
        />
      </Champ>
    </Grille>
  )
}

export function LotTrouve({
  fiche,
  onFermer,
  onSale,
}: {
  fiche: InventaireFiche
  onFermer: () => void
  onSale: (sale: boolean) => void
}) {
  const e = useLotTrouve(fiche, onSale, onFermer)
  const fermer = () => {
    onSale(false)
    onFermer()
  }
  return (
    <Carte
      titre="Un lot trouvé sur place, que le stock théorique ne connaissait pas"
      actions={
        <>
          {e.rempli ? (
            <Confirmer question="Abandonner ce lot trouvé ?" oui="Oui, abandonner" onOui={fermer}>
              Annuler
            </Confirmer>
          ) : (
            <Bouton onClick={fermer}>Annuler</Bouton>
          )}
          <Bouton variante="principal" manque={manqueLotTrouve(e.s)} onClick={e.ajouter} attente="Ajout…">
            Ajouter le lot au comptage
          </Bouton>
        </>
      }
    >
      <Champs e={e} fiche={fiche} />
    </Carte>
  )
}
