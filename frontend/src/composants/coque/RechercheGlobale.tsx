/**
 * La recherche globale (rôles métier) : matières, lots, ordres, commandes, réceptions, dossiers,
 * fournisseurs, qualités — GET /recherche?q= (route 56, filtrée par rôle au serveur, jamais de prix)
 * dès deux caractères, puis filtrée encore par les droits d'écran : un résultat ne mène jamais à un
 * écran refusé. Tout au clavier : « / » ou Ctrl K pour y aller, ↑ ↓ pour choisir, Entrée pour
 * ouvrir, Échap pour fermer.
 */
import { useEffect, useId, useRef, useState, type KeyboardEvent, type RefObject } from 'react'
import { useNavigate } from 'react-router'

import { messageErreur } from '../../lib/api'
import { permis } from '../../lib/droits'
import { useLecture } from '../../lib/requetes'
import type { ResultatRecherche } from '../../lib/types-provisoires-s2'
import type { Role } from '../../lib/types'
import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import { proteger } from './garde'
import styles from './RechercheGlobale.module.css'

/** Le nom de chaque genre de résultat, dans l'ordre d'affichage. */
export const GENRES: Readonly<Record<string, string>> = {
  matiere: 'Matières',
  lot: 'Lots',
  ordre: 'Ordres',
  commande: 'Commandes',
  reception: 'Réceptions',
  dossier: 'Dossiers d’importation',
  fournisseur: 'Fournisseurs',
  qualite: 'Qualités',
}

/** Le délai avant d'interroger le serveur pendant la frappe (ms). */
export const DELAI_RECHERCHE = 200

/** Les résultats permis au rôle, rangés par genre (ordre de `GENRES`, puis les autres). */
export function rangerResultats(liste: readonly ResultatRecherche[], role: Role): ResultatRecherche[] {
  const ordre = Object.keys(GENRES)
  const rang = (g: string) => (ordre.includes(g) ? ordre.indexOf(g) : ordre.length)
  return liste.filter((r) => permis(role, r.lien)).sort((a, b) => rang(a.genre) - rang(b.genre))
}

/** « / » (hors d'un champ) ou Ctrl/⌘ K : aller à la recherche. */
function useRaccourci(champ: RefObject<HTMLInputElement | null>) {
  useEffect(() => {
    const touche = (e: globalThis.KeyboardEvent) => {
      const cible = e.target instanceof HTMLElement ? e.target : null
      const dansUnChamp = cible?.closest('input, textarea, select, [contenteditable="true"]')
      if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !dansUnChamp)) {
        e.preventDefault()
        champ.current?.focus()
      }
    }
    document.addEventListener('keydown', touche)
    return () => document.removeEventListener('keydown', touche)
  }, [champ])
}

function useFrappeDifferee(q: string): string {
  const [differe, setDiffere] = useState(q)
  useEffect(() => {
    const t = setTimeout(() => setDiffere(q.trim()), DELAI_RECHERCHE)
    return () => clearTimeout(t)
  }, [q])
  return differe
}

function Etat({ q, enCours, erreur, vide }: { q: string; enCours: boolean; erreur: unknown; vide: boolean }) {
  let texte = ''
  if (q.trim().length < 2) texte = 'Tapez au moins deux caractères.'
  else if (erreur) texte = messageErreur(erreur)
  else if (enCours) texte = 'Recherche…'
  else if (vide) texte = 'Rien ne correspond.'
  return texte ? <div className={styles.etat}>{texte}</div> : null
}

interface PanneauProps {
  id: string
  resultats: readonly ResultatRecherche[]
  actif: number
  onActif: (i: number) => void
  onChoisir: (r: ResultatRecherche) => void
}

/** La liste des résultats, rangés par genre (un titre de genre au premier de chacun). */
function Liste({ id, resultats, actif, onActif, onChoisir }: PanneauProps) {
  return (
    <ul id={`${id}-liste`} role="listbox" aria-label="Résultats de la recherche" className={styles.liste}>
      {resultats.map((r, i) => {
        const tete = i === 0 || resultats[i - 1]?.genre !== r.genre ? (GENRES[r.genre] ?? r.genre) : null
        return (
          <li
            key={`${r.genre}-${r.id}`}
            id={`${id}-${i}`}
            role="option"
            aria-selected={i === actif}
            className={classes(styles.option, i === actif && styles.optionActive)}
            onMouseDown={(e) => e.preventDefault()}
            onMouseEnter={() => onActif(i)}
            onClick={() => onChoisir(r)}
          >
            {tete ? <span className={styles.genre}>{tete}</span> : null}
            <span className={styles.titre}>{r.titre}</span>
            {r.sous_titre ? <span className={styles.sous}>{r.sous_titre}</span> : null}
          </li>
        )
      })}
    </ul>
  )
}

/** Le clavier du champ : ↑ ↓ choisissent, Entrée ouvre, Échap ferme puis efface. */
function useClavier(
  nombre: number,
  ouvert: boolean,
  actions: { ouvrir: () => void; fermer: () => void; effacer: () => void; choisir: (i: number) => void },
) {
  const [actif, setActif] = useState(0)
  const clavier = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      actions.ouvrir()
      const pas = e.key === 'ArrowDown' ? 1 : -1
      setActif((a) => (nombre ? (a + pas + nombre) % nombre : 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      actions.choisir(actif)
    } else if (e.key === 'Escape') {
      e.stopPropagation()
      if (ouvert) actions.fermer()
      else actions.effacer()
    }
  }
  return { actif, setActif, clavier }
}

interface ChampRechercheProps {
  ref: RefObject<HTMLInputElement | null>
  id: string
  valeur: string
  montrer: boolean
  actif: string | undefined
  onFrappe: (v: string) => void
  onFocus: () => void
  onKeyDown: (e: KeyboardEvent<HTMLInputElement>) => void
}

/** Le champ (combobox) et le rappel de la touche « / ». */
function ChampRecherche({
  ref,
  id,
  valeur,
  montrer,
  actif,
  onFrappe,
  onFocus,
  onKeyDown,
}: ChampRechercheProps) {
  return (
    <>
      <input
        ref={ref}
        className={styles.champ}
        type="search"
        role="combobox"
        aria-label="Recherche globale"
        aria-expanded={montrer}
        aria-controls={`${id}-liste`}
        aria-autocomplete="list"
        aria-activedescendant={actif}
        placeholder="Rechercher partout…"
        title="Matières, lots, ordres, commandes, réceptions, dossiers, fournisseurs, qualités"
        value={valeur}
        onChange={(e) => onFrappe(e.target.value)}
        onFocus={onFocus}
        onKeyDown={onKeyDown}
      />
      <kbd className={styles.touche} aria-hidden="true">
        /
      </kbd>
    </>
  )
}

/** Les résultats de la frappe (différée), permis au rôle. */
function useResultats(q: string, role: Role) {
  const differe = useFrappeDifferee(q)
  const lecture = useLecture<ResultatRecherche[]>(differe.length >= 2 ? '/recherche' : null, { q: differe })
  return { differe, lecture, resultats: rangerResultats(lecture.data ?? [], role) }
}

export function RechercheGlobale({ role }: { role: Role }) {
  const id = useId()
  const champ = useRef<HTMLInputElement>(null)
  const naviguer = useNavigate()
  const [q, setQ] = useState('')
  const [ouvert, setOuvert] = useState(false)
  useRaccourci(champ)
  const { differe, lecture, resultats } = useResultats(q, role)
  const choisir = (r: ResultatRecherche | undefined) => {
    if (!r) return
    setQ('')
    setOuvert(false)
    champ.current?.blur()
    proteger(() => naviguer(r.lien))
  }
  const { actif, setActif, clavier } = useClavier(resultats.length, ouvert, {
    ouvrir: () => setOuvert(true),
    fermer: () => setOuvert(false),
    effacer: () => setQ(''),
    choisir: (i) => choisir(resultats[i]),
  })
  const montrer = ouvert && q.length > 0
  return (
    <div
      className={styles.recherche}
      onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setOuvert(false)}
    >
      <Icone nom="recherche" className={styles.loupe} />
      <ChampRecherche
        ref={champ}
        id={id}
        valeur={q}
        montrer={montrer}
        actif={montrer && resultats[actif] ? `${id}-${actif}` : undefined}
        onFrappe={(v) => {
          setQ(v)
          setActif(0)
          setOuvert(true)
        }}
        onFocus={() => setOuvert(true)}
        onKeyDown={clavier}
      />
      {montrer ? (
        <div className={styles.panneau}>
          <Etat
            q={q}
            enCours={lecture.isFetching || q.trim() !== differe}
            erreur={lecture.error}
            vide={!resultats.length}
          />
          <Liste id={id} resultats={resultats} actif={actif} onActif={setActif} onChoisir={choisir} />
        </div>
      ) : null}
    </div>
  )
}
