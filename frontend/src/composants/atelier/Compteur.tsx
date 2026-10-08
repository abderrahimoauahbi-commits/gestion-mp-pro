/**
 * Le compteur de l'atelier : « − », le nombre, « + », en cibles de 44 px et champ de 46 px en
 * 16 px (pas de zoom d'iOS), clavier décimal. Le pas suit la quantité (`pasPour` : 0,1 kg sous
 * 10 kg, 1 kg sous 100 kg, puis 10 kg ; une bobine ; une palette) ; − et + ramènent au multiple
 * du pas (2,37 → 2,4 ou 2,3). Les bornes valent aussi à la frappe (message sous le champ) ; un
 * « − » ou un « + » grisé dit pourquoi.
 */
import { useId } from 'react'

import { arrondi, nombre } from '../../lib/format'
import { pasPour, type Unite } from '../../lib/unites'
import { Icone } from '../mise-en-page/Icone'
import { messageNombre, useFrappeNombre } from '../saisie/Nombre'
import styles from './Compteur.module.css'

/** Le multiple du pas juste au-dessus (sens 1) ou juste au-dessous (sens −1). */
export function pasSuivant(valeur: number, pas: number, sens: 1 | -1): number {
  const n = valeur / pas
  const k = sens > 0 ? Math.floor(n + 1e-9) + 1 : Math.ceil(n - 1e-9) - 1
  return arrondi(k * pas, 3)
}

export interface CompteurProps {
  valeur: number | null
  onChange: (valeur: number | null) => void
  libelle: string
  /** L'unité dite à droite, et qui règle le pas (kg, bobine, palette). */
  unite?: Unite
  /** Un pas fixe (sinon celui de l'unité). */
  pas?: number
  min?: number
  max?: number
  decimales?: number
}

const ABREGES: Record<Unite, string> = { kg: 'kg', bobine: 'bob.', palette: 'pal.' }

function BoutonPas({
  sens,
  pas,
  raison,
  onClick,
}: {
  sens: 1 | -1
  pas: number
  raison?: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      className={styles.pas}
      aria-label={`${sens > 0 ? 'Plus' : 'Moins'} ${nombre(pas, 0, 3)}`}
      disabled={Boolean(raison)}
      title={raison}
      data-raison={raison}
      onClick={onClick}
    >
      <Icone nom={sens > 0 ? 'plus' : 'moins'} taille={20} />
    </button>
  )
}

export function Compteur({
  valeur,
  onChange,
  libelle,
  unite = 'kg',
  pas,
  min = 0,
  max,
  decimales,
}: CompteurProps) {
  const id = useId()
  const frappe = useFrappeNombre(valeur, onChange)
  const v = valeur ?? 0
  const lePas = pas ?? pasPour(v, unite)
  const dec = decimales ?? (unite === 'kg' ? 3 : unite === 'palette' ? 2 : 0)
  const message = messageNombre(frappe.lu, { min, max, decimales: dec })
  const changer = (sens: 1 | -1) => {
    frappe.oublier()
    onChange(Math.min(max ?? Infinity, Math.max(min, pasSuivant(v, lePas, sens))))
  }
  return (
    <div className={styles.compteur}>
      <div className={styles.rangee}>
        <BoutonPas
          sens={-1}
          pas={lePas}
          raison={v <= min ? `Déjà au minimum (${nombre(min, 0, 3)}).` : undefined}
          onClick={() => changer(-1)}
        />
        <input
          {...frappe.proprietes}
          className={styles.champ}
          aria-label={libelle}
          aria-invalid={message ? true : undefined}
          aria-describedby={message ? id : undefined}
          value={frappe.texte ?? (valeur == null ? '' : nombre(valeur, 0, dec))}
        />
        <BoutonPas
          sens={1}
          pas={lePas}
          raison={max != null && v >= max ? `Déjà au maximum (${nombre(max, 0, 3)}).` : undefined}
          onClick={() => changer(1)}
        />
        <span className={styles.unite}>{ABREGES[unite]}</span>
      </div>
      {message ? (
        <span id={id} className={styles.message}>
          {message}
        </span>
      ) : null}
    </div>
  )
}
