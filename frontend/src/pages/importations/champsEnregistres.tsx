/**
 * Les champs de la fiche d'un dossier qui s'enregistrent **en les quittant** (ou par Entrée),
 * comme dans Gestion MP (ECRANS-PRO 5.6) : le texte tapé reste local jusque-là ; une valeur changée
 * ailleurs (relue du serveur) remplace l'affichage tant qu'on ne tape pas dans ce champ ; un refus
 * est dit et la valeur enregistrée revient. `vide` : ce que vaut un champ vidé (`null` pour un
 * cours, « cours du jour ») ; `videInterdit` : le message quand le vider n'est pas permis.
 */
import { useState, type FocusEvent, type KeyboardEvent, type ReactNode } from 'react'

import { direErreur, dire } from '../../composants/retour/Messages'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Nombre, type BornesNombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import styles from './Importations.module.css'

/** Entrée enregistre (le champ est quitté). */
function entree(e: KeyboardEvent) {
  if (e.key === 'Enter' && e.target instanceof HTMLElement) e.target.blur()
}

/** L'enveloppe : quitter le champ (vers ailleurs que lui-même) enregistre. */
function Enveloppe({ children, onQuitter }: { children: ReactNode; onQuitter: () => void }) {
  const quitter = (e: FocusEvent<HTMLSpanElement>) => {
    if (e.relatedTarget instanceof Node && e.currentTarget.contains(e.relatedTarget)) return
    onQuitter()
  }
  return (
    <span className={styles.cellule} onBlur={quitter} onKeyDown={entree}>
      {children}
    </span>
  )
}

/** Le brouillon local d'un champ et son envoi au départ. */
function useBrouillon<T>(serveur: T, enregistrer: (v: T) => Promise<unknown>, egal: (a: T, b: T) => boolean) {
  const [brouillon, setBrouillon] = useState<{ v: T } | null>(null)
  const quitter = async () => {
    if (!brouillon) return
    const v = brouillon.v
    if (egal(v, serveur)) {
      setBrouillon(null)
      return
    }
    try {
      await enregistrer(v)
    } catch (e) {
      direErreur(e)
    } finally {
      setBrouillon(null)
    }
  }
  return { valeur: brouillon ? brouillon.v : serveur, poser: (v: T) => setBrouillon({ v }), quitter }
}

export interface TexteEnregistreProps {
  valeur: string
  onEnregistrer: (v: string) => Promise<unknown>
  max?: number
  placeholder?: string
  libelle: string
  desactive?: boolean
}

export function TexteEnregistre(p: TexteEnregistreProps) {
  const b = useBrouillon(
    p.valeur,
    (v) => p.onEnregistrer(v.trim()),
    (a, c) => a.trim() === c.trim(),
  )
  return (
    <Enveloppe onQuitter={() => void b.quitter()}>
      <Saisie
        valeur={b.valeur}
        onChange={b.poser}
        max={p.max}
        placeholder={p.placeholder}
        libelle={p.libelle}
        desactive={p.desactive}
      />
    </Enveloppe>
  )
}

export interface NombreEnregistreProps extends BornesNombre {
  valeur: number | null
  onEnregistrer: (v: number | null) => Promise<unknown>
  libelle: string
  placeholder?: string
  unite?: string
  desactive?: boolean
  /** Vider n'est pas permis : la valeur revient et ce message est dit. */
  videInterdit?: string
}

export function NombreEnregistre(p: NombreEnregistreProps) {
  const envoyer = async (v: number | null) => {
    if (v == null && p.videInterdit) {
      dire(p.videInterdit, 'attention')
      return
    }
    if (v != null && ((p.min != null && v < p.min) || (p.max != null && v > p.max))) return
    await p.onEnregistrer(v)
  }
  const b = useBrouillon(p.valeur, envoyer, (a, c) => a === c)
  return (
    <Enveloppe onQuitter={() => void b.quitter()}>
      <Nombre
        valeur={b.valeur}
        onChange={b.poser}
        libelle={p.libelle}
        placeholder={p.placeholder}
        unite={p.unite}
        desactive={p.desactive}
        min={p.min}
        max={p.max}
        decimales={p.decimales}
      />
    </Enveloppe>
  )
}

export interface DateEnregistreeProps {
  valeur: string | null
  onEnregistrer: (v: string | null) => Promise<unknown>
  libelle: string
  futurPermis?: boolean
  desactive?: boolean
}

export function DateEnregistree(p: DateEnregistreeProps) {
  const b = useBrouillon(
    p.valeur ?? '',
    (v) => p.onEnregistrer(v || null),
    (a, c) => a === c,
  )
  return (
    <Enveloppe onQuitter={() => void b.quitter()}>
      <DateChamp
        valeur={b.valeur}
        onChange={b.poser}
        libelle={p.libelle}
        futurPermis={p.futurPermis}
        desactive={p.desactive}
      />
    </Enveloppe>
  )
}
