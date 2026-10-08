/**
 * Le cadre où défile un tableau, en-tête collant (A2, M45, M69) : il prend **la hauteur qui
 * reste** jusqu'au bas de la fenêtre du navigateur, en mesurant ce qui le suit (marges, voisins,
 * bords des parents) ; la page, elle, ne défile jamais. Plancher de 200 px. Dans une fenêtre
 * (`hauteur="fenetre"`, ou posé dans un `role="dialog"`), une hauteur fixe sans mesure.
 */
import { useLayoutEffect, useRef, useState, type ReactNode } from 'react'

import { classes } from '../mise-en-page/classes'
import styles from './Cadre.module.css'

/** Le plancher d'un cadre (px) : quelques lignes restent toujours visibles. */
export const PLANCHER = 200

const px = (v: string) => parseFloat(v) || 0

/** Ce qui occupe la hauteur sous l'élément jusqu'au bas de la page (marges, bords, voisins dessous). */
function hauteurDessous(el: HTMLElement): number {
  let dessous = 0
  for (let e: HTMLElement | null = el; e && e !== document.body; e = e.parentElement) {
    const cs = getComputedStyle(e)
    dessous += px(cs.marginBottom)
    if (e !== el) dessous += px(cs.paddingBottom) + px(cs.borderBottomWidth)
    const bas = e.getBoundingClientRect().bottom
    const ecart = e.parentElement ? px(getComputedStyle(e.parentElement).rowGap) : 0
    for (let n = e.nextElementSibling; n instanceof HTMLElement; n = n.nextElementSibling) {
      const ns = getComputedStyle(n)
      // Un voisin posé à côté (grille, flex en ligne) ou hors du flux ne prend pas de hauteur dessous.
      if (ns.position === 'absolute' || ns.position === 'fixed' || n.getBoundingClientRect().top < bas - 1)
        continue
      dessous += n.offsetHeight + ecart + px(ns.marginTop) + px(ns.marginBottom)
    }
  }
  return dessous
}

/** La hauteur qui reste à l'élément jusqu'au bas de la fenêtre du navigateur (au moins le plancher). */
export function hauteurRestante(el: HTMLElement, hauteurFenetre = window.innerHeight): number {
  const haut = el.getBoundingClientRect().top + window.scrollY
  return Math.max(PLANCHER, Math.round(hauteurFenetre - haut - hauteurDessous(el)))
}

export function Cadre({
  children,
  hauteur = 'page',
  className,
}: {
  children: ReactNode
  hauteur?: 'page' | 'court' | 'fenetre'
  className?: string
}) {
  const boite = useRef<HTMLDivElement>(null)
  const [mesure, setMesure] = useState<number | null>(null)
  const [enFenetre, setEnFenetre] = useState(hauteur === 'fenetre')
  useLayoutEffect(() => {
    setEnFenetre(hauteur === 'fenetre' || Boolean(boite.current?.closest('[role="dialog"]')))
  }, [hauteur])
  // Mesurée après chaque rendu (ce qui précède a pu changer de hauteur), au redimensionnement de
  // la fenêtre du navigateur, et quand la page change de taille.
  useLayoutEffect(() => {
    const el = boite.current
    if (!el || enFenetre) return
    const calculer = () =>
      setMesure((avant) => {
        const h = hauteurRestante(el)
        return avant === h ? avant : h
      })
    calculer()
    window.addEventListener('resize', calculer)
    const observateur = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(calculer)
    observateur?.observe(document.body)
    return () => {
      window.removeEventListener('resize', calculer)
      observateur?.disconnect()
    }
  })
  return (
    <div
      ref={boite}
      className={classes(styles.cadre, enFenetre ? styles.fenetre : styles[hauteur], className)}
      style={!enFenetre && mesure != null ? { maxHeight: mesure } : undefined}
      data-hauteur={enFenetre ? 'fenetre' : hauteur}
    >
      {children}
    </div>
  )
}
