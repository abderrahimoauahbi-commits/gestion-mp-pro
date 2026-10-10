/**
 * Les cellules de saisie d'une ligne de camion (ECRANS-PRO 4.16) : référence et « + un autre lot »,
 * lot ou « Lot interne », reste à livrer et excédent, pesée et écart, bobines, prix, magasin.
 */
import { Badge } from '../../composants/retour/Badge'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { metres, nombre, part, partSignee, prixUnite, VIDE } from '../../lib/format'
import styles from '../plan-achat/achats.module.css'
import { bobines, ecartDe, enExcedent, type LigneSaisie, type Tolerances } from './calculSaisie'
import type { Magasin, Qualite } from './types'

export interface ContexteTable {
  lignes: readonly LigneSaisie[]
  tol: Tolerances
  magasins: readonly Magasin[]
  devises: readonly string[]
  modifier: (cle: string, m: Partial<LigneSaisie>) => void
  retirer: (l: LigneSaisie) => void
  ajouterLot: (l: LigneSaisie) => void
}

export const QUALITES: { valeur: Qualite; libelle: string; titre: string }[] = [
  { valeur: 'conforme', libelle: 'Conforme', titre: 'Entre en stock disponible' },
  { valeur: 'reserve', libelle: 'Sous réserve', titre: 'Entre en quarantaine, non utilisable' },
  { valeur: 'refuse', libelle: 'Refusé', titre: 'N’entre pas en stock ; le fournisseur la doit toujours' },
]

export function Reference({ l, x }: { l: LigneSaisie; x: ContexteTable }) {
  return (
    <span className={styles.cellule}>
      <span className={styles.ref} title={`${l.reference} — ${l.designation}`}>
        {l.reference}
      </span>
      <span className={styles.note}>{l.commande ? `bon ${l.commande}` : 'hors commande'}</span>
      <span className={styles.rangeeCentree}>
        {l.commande_ligne_id != null ? (
          <button
            type="button"
            className={styles.lien}
            title="Le camion apporte un autre lot de cette ligne du bon : une ligne de plus, même ligne de commande, son propre n° de lot et sa pesée"
            onClick={() => x.ajouterLot(l)}
          >
            + un autre lot
          </button>
        ) : null}
        <button
          type="button"
          className={styles.lien}
          title="Retirer cette ligne (absente du camion)"
          aria-label={`Retirer ${l.reference}`}
          onClick={() => x.retirer(l)}
        >
          retirer
        </button>
      </span>
    </span>
  )
}

export function Lot({ l, x }: { l: LigneSaisie; x: ContexteTable }) {
  if (l.qualite === 'refuse') return <>{VIDE}</>
  return (
    <span className={styles.cellule}>
      {l.lot_interne ? (
        <span className={styles.note}>numéroté à la validation</span>
      ) : (
        <Saisie
          valeur={l.lot_numero}
          onChange={(v) => x.modifier(l.cle, { lot_numero: v })}
          placeholder="n° de lot"
          libelle={`Lot du fournisseur de ${l.reference}`}
          className={styles.champCourt}
        />
      )}
      <Interrupteur
        valeur={l.lot_interne}
        onChange={(v) => x.modifier(l.cle, { lot_interne: v })}
        libelle="Lot interne"
      />
    </span>
  )
}

export function Reste({ l, x }: { l: LigneSaisie; x: ContexteTable }) {
  if (l.commande_ligne_id == null) return <>{VIDE}</>
  const plusieurs = x.lignes.filter((y) => y.commande_ligne_id === l.commande_ligne_id).length > 1
  return (
    <span className={styles.cellule}>
      {nombre(l.attendu)}
      {l.dejaRecu > 0 ? <span className={styles.note}>déjà reçu {nombre(l.dejaRecu)}</span> : null}
      {enExcedent(l, x.lignes, x.tol) ? (
        <span
          className={styles.critique}
          title={`Au-delà du reste à livrer plus ${part(x.tol.excedent, 0)} de la ligne : la validation sera refusée. Recevoir le surplus sur une ligne hors commande.`}
        >
          excédent refusé{plusieurs ? ' (tous lots)' : ''}
        </span>
      ) : null}
    </span>
  )
}

export function Pese({ l, x }: { l: LigneSaisie; x: ContexteTable }) {
  const e = ecartDe(l, x.tol)
  return (
    <span className={styles.cellule}>
      <Nombre
        valeur={l.quantite_pesee}
        onChange={(v) => x.modifier(l.cle, { quantite_pesee: v })}
        min={0}
        decimales={3}
        libelle={`Pesé (kg) de ${l.reference}`}
        className={styles.champCourt}
      />
      {l.kgParMl && l.quantite_pesee ? (
        <span className={styles.note}>{metres(l.quantite_pesee, l.kgParMl)}</span>
      ) : null}
      {e ? (
        <span className={styles.note} title="Pesé moins annoncé BL (à défaut, moins le reste à livrer)">
          <Badge ton={e.hors ? 'critique' : 'ok'}>{partSignee(e.relatif)}</Badge> {e.kg > 0 ? '+' : ''}
          {nombre(e.kg, 0, 2)} kg
        </span>
      ) : null}
    </span>
  )
}

export function Bobines({ l, x }: { l: LigneSaisie; x: ContexteTable }) {
  const b = bobines(l)
  return (
    <span className={styles.cellule}>
      <Nombre
        valeur={l.bobines_en_plus}
        onChange={(v) => x.modifier(l.cle, { bobines_en_plus: v })}
        min={0}
        decimales={0}
        libelle={`Bobines en plus de ${l.reference}`}
        className={styles.champCourt}
      />
      {b.total ? <span className={styles.note}>= {nombre(b.total)} bobines</span> : null}
      {b.moyen ? (
        <span
          className={styles.note}
          title={
            l.poidsBobine
              ? `catalogue : ${nombre(l.poidsBobine, 2)} kg la bobine`
              : 'pas de poids de bobine au catalogue'
          }
        >
          <Badge
            ton={b.ecart != null && Math.abs(b.ecart) > x.tol.bobine ? 'attention' : 'ok'}
          >{`${nombre(b.moyen, 2)} kg`}</Badge>
          {b.ecart != null ? ` ${partSignee(b.ecart)}` : ''}
        </span>
      ) : l.poidsBobine ? (
        <span className={styles.note}>catalogue {nombre(l.poidsBobine, 2)} kg</span>
      ) : null}
    </span>
  )
}

export function Prix({ l, x }: { l: LigneSaisie; x: ContexteTable }) {
  if (l.prixConfirme)
    return (
      <span title="Le prix confirmé sur le bon : c’est lui qui sera payé">
        {prixUnite(l.prix, l.devise, 'kg')}
        <span className={styles.dessous}>confirmé</span>
      </span>
    )
  return (
    <span className={styles.cellule}>
      <Nombre
        valeur={l.prix}
        onChange={(v) => x.modifier(l.cle, { prix: v })}
        min={0}
        decimales={4}
        placeholder="prix"
        libelle={`Prix au kilo de ${l.reference}`}
        className={styles.champCourt}
      />
      {l.commande_ligne_id ? (
        <span className={styles.note}>{l.devise} / kg</span>
      ) : (
        <select
          className={styles.choix}
          aria-label={`Devise du prix de ${l.reference}`}
          value={l.devise}
          onChange={(e) => x.modifier(l.cle, { devise: e.target.value })}
        >
          {[...new Set([l.devise, ...x.devises])].map((d) => (
            <option key={d} value={d}>{`${d} / kg`}</option>
          ))}
        </select>
      )}
    </span>
  )
}

export function ChoixMagasin({ l, x }: { l: LigneSaisie; x: ContexteTable }) {
  if (l.qualite === 'refuse') return <span className={styles.note}>n’entre pas</span>
  if (l.qualite === 'reserve')
    return (
      <span className={styles.note}>
        {x.magasins.find((m) => m.actif && m.type === 'quarantaine')?.code ?? 'quarantaine'}
      </span>
    )
  return (
    <select
      className={styles.choix}
      aria-label={`Magasin de ${l.reference}`}
      value={l.magasin_id ?? ''}
      onChange={(e) => x.modifier(l.cle, { magasin_id: e.target.value ? Number(e.target.value) : null })}
    >
      <option value="">— choisir —</option>
      {x.magasins
        .filter((m) => m.actif && m.type !== 'quarantaine')
        .map((m) => (
          <option key={m.id} value={m.id}>
            {m.code}
          </option>
        ))}
    </select>
  )
}
