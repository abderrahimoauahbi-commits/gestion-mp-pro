/**
 * L'encart « Nouvelle ligne » / « Modifier la ligne RÉF » de la fenêtre d'opération (ECRANS-PRO
 * partie 6) : matière, lot (ou lot à créer, case « Lot interne » — numéro donné à la validation),
 * magasins, sens, quantité en kg, bobines ou palettes, prix et devise d'une ouverture. « Ajouter la
 * ligne » est grisé avec ce qui manque ; « Annuler » demande si l'encart est rempli (an. 25).
 */
import { useEffect, useState } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { Nombre } from '../../composants/saisie/Nombre'
import { Prix } from '../../composants/saisie/Prix'
import { Quantite } from '../../composants/saisie/Quantite'
import { Saisie } from '../../composants/saisie/Saisie'
import { Segments } from '../../composants/saisie/Segments'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { SelecteurMatiere } from '../../composants/saisie/SelecteurMatiere'
import { kg, prixUnite } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { choixMatiere } from '../inventaire/matieres'
import {
  ENCART_VIERGE,
  encartDe,
  encartRempli,
  ligneDeLEncart,
  lotACreer,
  manqueEncart,
  NOUVEAU_LOT,
  sensImpose,
  type EtatEncart,
} from './encart'
import styles from './Operations.module.css'
import { aucunLot, destinations, optionDePlace, placesDeLots, placesProposees } from './places'
import type { LigneSaisie } from './saisie'
import type { DeviseFiche, LotSolde, MagasinFiche, MatiereResume, MotifLu, TypeOperation } from './types'

export interface EncartProps {
  type: TypeOperation
  motif: MotifLu | undefined
  date: string
  matieres: readonly MatiereResume[]
  magasins: readonly MagasinFiche[]
  devises: readonly DeviseFiche[]
  /** Le fournisseur des lignes déjà posées (retour au fournisseur). */
  fournisseur: string | null
  ligne: LigneSaisie | null
  onPoser: (l: LigneSaisie) => void
  onAnnuler: () => void
  onRempli: (rempli: boolean) => void
}

let rang = 0

/** L'état de l'encart, ses lectures et ce qui en découle. */
function useEncart(p: EncartProps) {
  const [e, setE] = useState<EtatEncart>(() => (p.ligne ? encartDe(p.ligne, p.type) : ENCART_VIERGE))
  const m = p.matieres.find((x) => x.id === e.matiere)
  const lots = useLecture<LotSolde[]>(e.matiere == null || p.type === 'ouverture' ? null : '/lots', {
    matiere: e.matiere,
    date: p.date || undefined,
    non_nuls: p.type === 'retour_machine' ? undefined : true,
  })
  const toutes = placesDeLots(lots.data ?? [])
  const places = placesProposees(toutes, p.type, p.motif, p.fournisseur)
  const place = places.find((x) => x.cle === e.place)
  const rempli = encartRempli(e)
  const { onRempli } = p
  useEffect(() => onRempli(rempli), [rempli, onRempli])
  const poser = (modif: Partial<EtatEncart>) => setE((x) => ({ ...x, ...modif }))
  const nom = (id: number | null) => p.magasins.find((g) => g.id === id)?.code ?? ''
  const poserLigne = () => {
    if (!m) return
    const cle = p.ligne?.cle ?? `n${(rang += 1)}`
    const lot = (id: number) => lots.data?.find((l) => l.lot_id === id)?.lot ?? ''
    p.onPoser(ligneDeLEncart(p.type, e, m, place, { magasin: nom, lot }, cle))
  }
  return { e, poser, m, lots, toutes, places, place, rempli, poserLigne }
}

type Encart = ReturnType<typeof useEncart>

/** Le lot (et le magasin de départ) parmi ceux proposés ; un lot à créer pour une matière retrouvée. */
function ChampLot({ p, x }: { p: EncartProps; x: Encart }) {
  const { e, poser } = x
  if (p.type === 'ouverture') return null
  const options =
    p.type === 'retour_machine'
      ? (x.lots.data ?? []).map((l) => ({ id: String(l.lot_id), titre: `Lot ${l.lot}`, sous: l.fournisseur }))
      : x.places.map((pl) => optionDePlace(pl, p.type))
  const avecNouveau =
    p.type === 'ajustement'
      ? [{ id: NOUVEAU_LOT, titre: 'Un lot qui n’est pas en stock (matière retrouvée)' }]
      : []
  const libelle = p.type === 'transfert' ? 'Lot et magasin de départ' : 'Lot'
  return (
    <Champ
      libelle={libelle}
      aide={
        e.matiere == null
          ? 'Choisir d’abord la matière'
          : x.lots.isPending
            ? 'Lecture des lots…'
            : options.length
              ? undefined
              : aucunLot(p.type, p.motif, x.toutes)
      }
    >
      <Selecteur
        effacable={false}
        valeur={e.place}
        options={[...options, ...avecNouveau]}
        onChange={(id) => {
          const pl = x.places.find((y) => y.cle === id)
          const vers = destinations(p.magasins, pl?.magasin_id ?? null, p.motif)[0]?.id ?? null
          poser({ place: id, kg: null, unite: 'kg', vers, sens: id === NOUVEAU_LOT ? '+' : e.sens })
        }}
        placeholder={e.matiere == null ? 'Choisir d’abord la matière' : 'Choisir le lot…'}
        desactive={e.matiere == null}
      />
    </Champ>
  )
}

/** Numéro de lot (ou « Lot interne ») et magasin d'un lot à créer ; magasin d'un retour des machines. */
function ChampsLotACreer({ p, x }: { p: EncartProps; x: Encart }) {
  const { e, poser } = x
  const actifs = p.magasins
    .filter((g) => g.actif)
    .map((g) => ({ id: g.id, titre: `${g.code}${g.type === 'quarantaine' ? ' (quarantaine)' : ''}` }))
  const magasin = (
    <Champ libelle="Magasin">
      <Selecteur
        effacable={false}
        valeur={e.magasin}
        options={actifs}
        onChange={(id) => poser({ magasin: id })}
        placeholder="Choisir…"
      />
    </Champ>
  )
  if (p.type === 'retour_machine') return magasin
  if (!lotACreer(p.type, e)) return null
  return (
    <>
      <Champ
        libelle="Numéro de lot"
        groupe
        aide={e.lot_interne ? 'numéro donné à la validation (LOT-AAAA-NNNN)' : 'Celui de l’étiquette'}
      >
        <span className={styles.pile}>
          <Saisie
            libelle="Numéro de lot"
            valeur={e.lot_interne ? '' : e.lot_numero}
            onChange={(v) => poser({ lot_numero: v })}
            max={80}
            desactive={e.lot_interne}
          />
          <Interrupteur
            valeur={e.lot_interne}
            onChange={(v) => poser({ lot_interne: v })}
            libelle="Lot interne"
          />
        </span>
      </Champ>
      {magasin}
    </>
  )
}

/** Vers le magasin (transfert) ; sens (ajustement). */
function ChampsSens({ p, x }: { p: EncartProps; x: Encart }) {
  const { e, poser } = x
  if (p.type === 'transfert') {
    const vers = destinations(p.magasins, x.place?.magasin_id ?? null, p.motif)
    return (
      <Champ libelle="Vers le magasin">
        <Selecteur
          effacable={false}
          valeur={e.vers}
          options={vers.map((g) => ({ id: g.id, titre: g.code }))}
          onChange={(id) => poser({ vers: id })}
          placeholder="Choisir…"
        />
      </Champ>
    )
  }
  if (p.type !== 'ajustement') return null
  const impose = sensImpose(p.type, e, p.motif)
  return (
    <Champ
      libelle="Sens"
      groupe
      aide={impose ? 'Une matière retrouvée s’ajoute au stock : « Retirer » est impossible' : undefined}
    >
      <Segments
        libelle="Sens"
        valeur={impose ? '+' : e.sens}
        onChange={(sens) => poser({ sens })}
        options={
          impose
            ? [{ valeur: '+', libelle: 'Ajouter au stock (+)' }]
            : [
                { valeur: '-', libelle: 'Retirer du stock (−)' },
                { valeur: '+', libelle: 'Ajouter au stock (+)' },
              ]
        }
      />
    </Champ>
  )
}

/** Quantité en kg, prix au kilo et devise d'un stock d'ouverture. */
function ChampsOuverture({ p, x }: { p: EncartProps; x: Encart }) {
  const { e, poser, m } = x
  return (
    <>
      <Champ libelle="Quantité (kg)">
        <Nombre valeur={e.kg} onChange={(v) => poser({ kg: v })} min={0} decimales={3} unite="kg" />
      </Champ>
      <Champ
        libelle="Prix d’achat / kg"
        groupe
        aide={m?.prix_kg != null ? `catalogue : ${prixUnite(m.prix_kg, m.devise ?? 'MAD', 'kg')}` : undefined}
      >
        <span className={styles.prixDevise}>
          <Prix
            libelle="Prix d’achat / kg"
            valeur={e.prix}
            onChange={(v) => poser({ prix: v })}
            devise={e.devise}
            unite="kg"
          />
          <Selecteur
            libelle="Devise"
            effacable={false}
            valeur={e.devise}
            options={p.devises
              .filter((d) => d.actif || d.code === e.devise)
              .map((d) => ({ id: d.code, titre: d.code, sous: d.nom }))}
            onChange={(id) => poser({ devise: id ?? 'MAD' })}
          />
        </span>
      </Champ>
    </>
  )
}

/** La quantité (kg, bobines, palettes ; kg seul pour une ouverture), prix et devise d'une ouverture. */
function ChampsQuantite({ p, x }: { p: EncartProps; x: Encart }) {
  const { e, poser, m, place } = x
  if (p.type === 'ouverture') return <ChampsOuverture p={p} x={x} />
  const sort = p.type !== 'retour_machine' && !(p.type === 'ajustement' && e.sens === '+')
  const borne = sort && place ? place.quantite : undefined
  const apres =
    p.type === 'ajustement' && place && e.kg != null ? place.quantite + (e.sens === '-' ? -e.kg : e.kg) : null
  return (
    <Champ libelle="Quantité" groupe aide={apres != null ? `stock du lot après : ${kg(apres)}` : undefined}>
      <Quantite
        libelle="Quantité"
        kg={e.kg}
        onChange={(v) => poser({ kg: v })}
        unite={e.unite}
        onUnite={(unite) => poser({ unite })}
        poidsBobine={place?.poids_bobine || m?.poids_bobine}
        bobinesPalette={place?.bobines_palette || m?.bobines_palette}
        kgParMl={m?.kg_par_ml}
        borne={borne}
      />
      {borne != null ? (
        <Bouton taille="petit" variante="fantome" onClick={() => poser({ kg: borne, unite: 'kg' })}>
          tout le lot : {kg(borne)}
        </Bouton>
      ) : null}
    </Champ>
  )
}

export function EncartLigne(p: EncartProps) {
  const x = useEncart(p)
  const { e, poser } = x
  const proposees =
    p.type === 'ouverture' || p.type === 'ajustement'
      ? p.matieres
      : p.matieres.filter((m) => (m.stock ?? 0) > 0 || p.type === 'retour_machine')
  return (
    <Carte
      className={styles.encart}
      titre={p.ligne ? `Modifier la ligne ${p.ligne.reference}` : 'Nouvelle ligne'}
      actions={
        <>
          {x.rempli ? (
            <Confirmer question="Abandonner cette ligne ?" oui="Oui, abandonner" onOui={p.onAnnuler}>
              Annuler
            </Confirmer>
          ) : (
            <Bouton onClick={p.onAnnuler}>Annuler</Bouton>
          )}
          <Bouton variante="principal" manque={manqueEncart(p.type, e, x.place)} onClick={x.poserLigne}>
            {p.ligne ? 'Enregistrer la ligne' : 'Ajouter la ligne'}
          </Bouton>
        </>
      }
    >
      <Grille colonnes={4}>
        <Champ libelle="Matière" groupe large>
          <SelecteurMatiere
            matieres={proposees.map(choixMatiere)}
            valeur={e.matiere}
            onChange={(id) => {
              const mat = p.matieres.find((y) => y.id === id)
              poser({
                ...ENCART_VIERGE,
                matiere: id,
                prix: mat?.prix_kg ?? null,
                devise: mat?.devise ?? 'MAD',
                sens: e.sens,
              })
            }}
          />
        </Champ>
        <ChampLot p={p} x={x} />
        <ChampsLotACreer p={p} x={x} />
        <ChampsSens p={p} x={x} />
        <ChampsQuantite p={p} x={x} />
      </Grille>
    </Carte>
  )
}
