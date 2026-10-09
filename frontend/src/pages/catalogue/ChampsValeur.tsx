/**
 * Les champs d'une valeur de classification, selon sa liste : code (dans la longueur de la
 * colonne de la matière, en majuscules pour une composition et un type de fil — P7-19),
 * libellé, famille, composition détaillée, valeur et unité d'un titrage, observations. Servent à
 * la fenêtre de l'onglet Classification et au panneau d'ajout de la fiche matière (une seule
 * déclaration).
 */
import { Grille } from '../../composants/mise-en-page/Grille'
import { Champ } from '../../composants/saisie/Champ'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { Zone } from '../../composants/saisie/Zone'
import { COMMENTAIRE_MAX, LONGUEURS } from './bornes'
import type { DefinitionListe, Liste, Valeur } from './types'

export interface FormeValeur {
  code: string
  libelle: string
  famille: string
  composition_detaillee: string
  valeur: string
  unite: string
  commentaire: string
  actif: boolean
}

export const UNITES_TITRAGE = ['Dtex', 'Deniers', 'Nm', 'Tex', 'Nec'] as const

/** La forme d'une valeur lue, ou d'une valeur nouvelle (code tapé, active). */
export function versFormeValeur(v: Valeur | null, code = ''): FormeValeur {
  return {
    code: v?.code ?? code,
    libelle: v?.libelle ?? '',
    famille: v?.famille ?? '',
    composition_detaillee: v?.composition_detaillee ?? '',
    valeur: v?.valeur ?? '',
    unite: v?.unite ?? '',
    commentaire: v?.commentaire ?? '',
    actif: v?.actif ?? true,
  }
}

/** Le code tel qu'il s'écrit dans sa liste (majuscules pour composition et type de fil). */
export function codeEcrit(d: DefinitionListe, code: string): string {
  return d.majuscules ? code.toUpperCase() : code
}

/** Le corps de `POST`/`PUT /classification/{liste}` (seuls les champs de la liste comptent). */
export function corpsValeur(d: DefinitionListe, f: FormeValeur) {
  return {
    code: codeEcrit(d, f.code.trim()),
    libelle: f.libelle.trim(),
    famille: f.famille.trim(),
    composition_detaillee: f.composition_detaillee.trim(),
    valeur: f.valeur.trim(),
    unite: f.unite.trim(),
    commentaire: f.commentaire.trim(),
    actif: f.actif,
  }
}

const AIDES_FAMILLE: Record<string, string> = {
  compositions: 'Synthétique, Naturel, Intrant',
  couleurs: 'Rouges, Beiges, Gris…',
}

/** Les champs de texte d'une valeur : libellé, aide (selon la liste), longueur. */
const TEXTES: readonly {
  cle: 'libelle' | 'famille' | 'composition_detaillee' | 'valeur'
  libelle: string
  max: number
  aide: Partial<Record<Liste, string>>
}[] = [
  {
    cle: 'libelle',
    libelle: 'Libellé',
    max: LONGUEURS.LIBELLE,
    aide: {
      compositions: 'Polypropylène, Polyester…',
      'types-fil': 'Frisé, Shrink, Filament…',
      couleurs: 'comme l’atelier la nomme',
    },
  },
  { cle: 'famille', libelle: 'Famille', max: LONGUEURS.FAMILLE, aide: AIDES_FAMILLE },
  {
    cle: 'composition_detaillee',
    libelle: 'Composition détaillée',
    max: LONGUEURS.COMPOSITION_DETAILLEE,
    aide: { compositions: '« 100 % polypropylène »' },
  },
  {
    cle: 'valeur',
    libelle: 'Valeur',
    max: LONGUEURS.VALEUR_TITRAGE,
    aide: { titrages: 'lue dans le code si vide' },
  },
]

interface ChampsProps {
  d: DefinitionListe
  forme: FormeValeur
  onChange: (modif: Partial<FormeValeur>) => void
}

/** La modification d'un champ de texte. */
function texte(cle: (typeof TEXTES)[number]['cle'], v: string): Partial<FormeValeur> {
  const m: Partial<FormeValeur> = {}
  m[cle] = v
  return m
}

/** Le code, dans la longueur de sa colonne, en majuscules s'il le faut. */
function ChampCode({ d, forme, onChange }: ChampsProps) {
  return (
    <Champ
      libelle="Code"
      obligatoire
      aide={
        d.liste === 'titrages' ? 'valeur et unité : « 2900 Dtex »' : 'tel qu’il s’écrit dans la référence'
      }
    >
      <Saisie
        valeur={forme.code}
        onChange={(v) => onChange({ code: codeEcrit(d, v) })}
        max={d.longueur}
        autoFocus
      />
    </Champ>
  )
}

/** L'unité d'un titrage, dans la liste des unités connues. */
function ChampUnite({ forme, onChange }: ChampsProps) {
  const unites = [...new Set([...UNITES_TITRAGE, forme.unite].filter(Boolean))]
  return (
    <Champ libelle="Unité" aide="Dtex, Deniers, Nm, Tex, Nec">
      <Selecteur<string>
        valeur={forme.unite || null}
        options={unites.map((u) => ({ id: u, titre: u }))}
        onChange={(v) => onChange({ unite: v ?? '' })}
        placeholder="lue dans le code si vide"
      />
    </Champ>
  )
}

/** Les observations et l'état (fenêtre de la classification). */
function ChampsFin({ forme, onChange }: ChampsProps) {
  return (
    <>
      <Champ libelle="Observations" large>
        <Zone
          valeur={forme.commentaire}
          onChange={(v) => onChange({ commentaire: v })}
          max={COMMENTAIRE_MAX}
        />
      </Champ>
      <Champ libelle="État" groupe large>
        <Interrupteur
          valeur={forme.actif}
          onChange={(v) => onChange({ actif: v })}
          libelle="Active (proposée pour une nouvelle matière)"
        />
      </Champ>
    </>
  )
}

export function ChampsValeur({
  familles = [],
  complet = true,
  ...p
}: ChampsProps & {
  /** Les familles déjà employées dans la liste (dites dans l'aide). */
  familles?: readonly string[]
  /** Observations et état (fenêtre de la classification) ; le panneau d'ajout s'en passe. */
  complet?: boolean
}) {
  const { d, forme, onChange } = p
  return (
    <Grille colonnes={2}>
      <ChampCode {...p} />
      {TEXTES.filter((t) => d.champs.includes(t.cle)).map((t) => (
        <Champ
          key={t.cle}
          libelle={t.libelle}
          aide={
            t.cle === 'famille' && familles.length
              ? `déjà employées : ${familles.join(', ')}`
              : t.aide[d.liste]
          }
        >
          <Saisie valeur={forme[t.cle]} onChange={(v) => onChange(texte(t.cle, v))} max={t.max} />
        </Champ>
      ))}
      {d.champs.includes('unite') ? <ChampUnite {...p} /> : null}
      {complet ? <ChampsFin {...p} /> : null}
    </Grille>
  )
}
