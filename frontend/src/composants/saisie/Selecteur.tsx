/**
 * Choisir dans une longue liste en tapant quelques mots (reprise de `ChoixRecherche` de Gestion
 * MP, P4) : recherche multi-mots sans accents, y compris sur des champs cachés (`recherche`) ;
 * clavier ↑ ↓ Entrée (Entrée choisit aussi un résultat unique), Échap ferme la liste sans
 * fermer la fenêtre qui la contient ; « Rien ne correspond. » Motif ARIA « combobox ».
 */
import {
  useId,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
  type MouseEvent,
} from 'react'

import { nombre } from '../../lib/format'
import { correspond, texteDe } from '../../lib/recherche'
import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import { attributsDuChamp, useChamp } from './Champ'
import styles from './Selecteur.module.css'

export interface OptionSelecteur<K extends string | number = number> {
  id: K
  titre: string
  sous?: string
  groupe?: string
  /** Du texte cherché sans être affiché (code, fournisseur, couleur…). */
  recherche?: string
}

export interface SelecteurProps<K extends string | number> {
  valeur: K | null
  options: readonly OptionSelecteur<K>[]
  onChange: (id: K | null, option?: OptionSelecteur<K>) => void
  placeholder?: string
  vide?: string
  effacable?: boolean
  libelle?: string
  desactive?: boolean
  /** Le nombre d'options montrées au plus (la recherche affine le reste). */
  limite?: number
}

/** Les options qui répondent à la recherche, dans leur ordre. */
export function filtrerOptions<K extends string | number>(options: readonly OptionSelecteur<K>[], q: string) {
  return options.filter((o) => correspond(texteDe([o.titre, o.sous, o.groupe, o.recherche]), q))
}

/** La liste ouverte, la recherche et l'option active, et ce que font les touches. */
function useListe<K extends string | number>(props: SelecteurProps<K>) {
  const [ouvert, setOuvert] = useState(false)
  const [q, setQ] = useState('')
  const [actif, setActif] = useState(0)
  const trouvees = useMemo(() => filtrerOptions(props.options, q), [props.options, q])
  const choisir = (o: OptionSelecteur<K> | null) => {
    props.onChange(o ? o.id : null, o ?? undefined)
    setOuvert(false)
    setQ('')
  }
  const clavier = (e: KeyboardEvent<HTMLInputElement>, montrees: number) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      setOuvert(true)
      setActif((a) => Math.max(0, Math.min(montrees - 1, a + (e.key === 'ArrowDown' ? 1 : -1))))
    } else if (e.key === 'Enter' && ouvert) {
      const o = trouvees.length === 1 ? trouvees[0] : trouvees[actif]
      if (o) {
        e.preventDefault()
        choisir(o)
      }
    } else if (e.key === 'Escape' && ouvert) {
      e.stopPropagation()
      e.nativeEvent.stopImmediatePropagation()
      setOuvert(false)
    }
  }
  const evenements = (montrees: number) => ({
    onFocus: () => {
      setOuvert(true)
      setActif(0)
    },
    onClick: () => setOuvert(true),
    onBlur: () => setOuvert(false),
    onChange: (e: ChangeEvent<HTMLInputElement>) => {
      setQ(e.target.value)
      setActif(0)
      setOuvert(true)
    },
    onKeyDown: (e: KeyboardEvent<HTMLInputElement>) => clavier(e, montrees),
  })
  return { ouvert, q, actif, setActif, trouvees, choisir, evenements }
}

interface ListeOptionsProps<K extends string | number> {
  id: string
  libelle?: string
  montrees: readonly OptionSelecteur<K>[]
  actif: number
  valeur: K | null
  effacer: boolean
  vide: string
  reste: number
  onChoisir: (o: OptionSelecteur<K> | null) => void
  onSurvol: (i: number) => void
}

/** La liste ouverte : « — Aucun — », les options (avec leur groupe), et ce qui n'est pas montré. */
function ListeOptions<K extends string | number>(p: ListeOptionsProps<K>) {
  let groupe: string | undefined
  // Les options retiennent le focus (mousedown) : le champ garde la main, la liste ne se ferme pas.
  const retenir = (e: MouseEvent) => e.preventDefault()
  return (
    <div className={styles.liste} role="listbox" id={`${p.id}-liste`} aria-label={p.libelle}>
      {p.effacer ? (
        <div
          role="option"
          aria-selected={false}
          className={styles.aucun}
          onMouseDown={retenir}
          onClick={() => p.onChoisir(null)}
        >
          — Aucun —
        </div>
      ) : null}
      {p.montrees.length === 0 ? <div className={styles.vide}>{p.vide}</div> : null}
      {p.montrees.map((o, i) => {
        const tete = o.groupe && o.groupe !== groupe ? o.groupe : null
        groupe = o.groupe
        return (
          <div key={String(o.id)} role="presentation">
            {tete ? (
              <div className={styles.groupe} role="presentation">
                {tete}
              </div>
            ) : null}
            <div
              id={`${p.id}-${i}`}
              role="option"
              aria-selected={i === p.actif}
              className={classes(
                styles.option,
                i === p.actif && styles.active,
                o.id === p.valeur && styles.choisie,
              )}
              onMouseDown={retenir}
              onMouseEnter={() => p.onSurvol(i)}
              onClick={() => p.onChoisir(o)}
            >
              <span>{o.titre}</span>
              {o.sous ? <small className={styles.sous}>{o.sous}</small> : null}
            </div>
          </div>
        )
      })}
      {p.reste > 0 ? (
        <div className={styles.vide}>… et {nombre(p.reste)} autres : précisez la recherche.</div>
      ) : null}
    </div>
  )
}

export function Selecteur<K extends string | number>(props: SelecteurProps<K>) {
  const {
    valeur,
    options,
    placeholder = 'Taper pour chercher…',
    vide = 'Rien ne correspond.',
    limite = 100,
  } = props
  const liens = useChamp()
  const id = useId()
  const champ = useRef<HTMLInputElement>(null)
  const l = useListe(props)
  const choisie = options.find((o) => o.id === valeur)
  const montrees = l.trouvees.slice(0, limite)
  const effacer = (props.effacable ?? true) && valeur != null
  return (
    <div className={styles.selecteur}>
      <div className={styles.saisie}>
        <input
          ref={champ}
          {...attributsDuChamp(liens, undefined, props.libelle)}
          role="combobox"
          aria-expanded={l.ouvert}
          aria-controls={`${id}-liste`}
          aria-autocomplete="list"
          aria-activedescendant={l.ouvert && montrees[l.actif] ? `${id}-${l.actif}` : undefined}
          className={styles.controle}
          autoComplete="off"
          disabled={props.desactive}
          placeholder={choisie ? choisie.titre : placeholder}
          value={l.ouvert ? l.q : (choisie?.titre ?? '')}
          {...l.evenements(montrees.length)}
        />
        <Icone nom="chevronBas" className={styles.chevron} />
      </div>
      {l.ouvert ? (
        <ListeOptions
          id={id}
          libelle={props.libelle}
          montrees={montrees}
          actif={l.actif}
          valeur={valeur}
          effacer={effacer}
          vide={vide}
          reste={l.trouvees.length - montrees.length}
          onChoisir={l.choisir}
          onSurvol={l.setActif}
        />
      ) : null}
    </div>
  )
}
