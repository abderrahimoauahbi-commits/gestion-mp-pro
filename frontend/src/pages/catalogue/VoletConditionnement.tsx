/**
 * Volet « Conditionnement et stock » de la fiche matière : poids d'une bobine au catalogue,
 * bobines par palette, stock minimum, couverture minimum, groupe d'équivalence. Les bornes du
 * serveur sont contrôlées à la frappe (P7-20). Le stock se tient toujours en kilos.
 */
import { Grille } from '../../composants/mise-en-page/Grille'
import { Champ } from '../../composants/saisie/Champ'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { kg } from '../../lib/format'
import { BORNES_MATIERE, LONGUEURS } from './bornes'
import { uniteDeduite, type FormeMatiere } from './formeMatiere'
import styles from './catalogue.module.css'

type ChampNombre = 'poids_bobine' | 'bobines_palette' | 'stock_min' | 'couv_min_mois'

const NOMBRES: readonly {
  cle: ChampNombre
  libelle: string
  aide: string
  decimales: number
  unite?: string
}[] = [
  {
    cle: 'poids_bobine',
    libelle: 'kg / bobine',
    aide: 'au catalogue ; le poids mesuré du lot sert aux sorties en bobines',
    decimales: 4,
    unite: 'kg',
  },
  {
    cle: 'bobines_palette',
    libelle: 'Bobines par palette',
    aide: 'avec le poids d’une bobine : la palette devient l’unité d’achat déduite',
    decimales: 0,
  },
  {
    cle: 'stock_min',
    libelle: 'Stock minimum',
    aide: 'sous ce seuil, la matière est signalée',
    decimales: 3,
    unite: 'kg',
  },
  {
    cle: 'couv_min_mois',
    libelle: 'Couverture minimum',
    aide: 'mois de consommation à garder d’avance (60 au plus)',
    decimales: 2,
    unite: 'mois',
  },
]

/** La modification d'un nombre de la forme. */
function avecNombre(cle: ChampNombre, v: number | null): Partial<FormeMatiere> {
  const m: Partial<FormeMatiere> = {}
  m[cle] = v
  return m
}

export function VoletConditionnement({
  forme,
  maj,
  groupes,
}: {
  forme: FormeMatiere
  maj: (modif: Partial<FormeMatiere>) => void
  /** Les groupes d'équivalence déjà employés au catalogue. */
  groupes: readonly string[]
}) {
  const palette = uniteDeduite(forme)
  const employes = groupes.length
    ? ` ; déjà employés : ${groupes.slice(0, 8).join(', ')}${groupes.length > 8 ? '…' : ''}`
    : ''
  return (
    <div className={styles.volet}>
      <Grille colonnes={2}>
        {NOMBRES.map((n) => (
          <Champ
            key={n.cle}
            libelle={n.libelle}
            aide={
              n.cle === 'bobines_palette' && palette.unite === 'Palette'
                ? `une palette ≈ ${kg(palette.contenance)}`
                : n.aide
            }
          >
            <Nombre
              valeur={forme[n.cle]}
              onChange={(v) => maj(avecNombre(n.cle, v))}
              min={0}
              max={BORNES_MATIERE[n.cle][1]}
              decimales={n.decimales}
              unite={n.unite}
            />
          </Champ>
        ))}
        <Champ
          libelle="Groupe d’équivalence"
          large
          aide={`des matières interchangeables portent le même groupe${employes}`}
        >
          <Saisie
            valeur={forme.groupe_equiv}
            onChange={(v) => maj({ groupe_equiv: v })}
            max={LONGUEURS.GROUPE_EQUIV}
          />
        </Champ>
      </Grille>
    </div>
  )
}
