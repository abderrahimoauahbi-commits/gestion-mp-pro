/** Essais du Cadre : hauteur restante mesurée jusqu'au bas de la fenêtre, plancher, hauteur fixe en fenêtre. */
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Fenetre } from '../mise-en-page/Fenetre'
import { Cadre, hauteurRestante, PLANCHER } from './Cadre'

/** Pose la boîte d'un élément (jsdom ne calcule pas la mise en page). */
function boite(el: Element, haut: number, hauteur: number) {
  vi.spyOn(el, 'getBoundingClientRect').mockReturnValue({
    top: haut,
    bottom: haut + hauteur,
    height: hauteur,
    left: 0,
    right: 1000,
    width: 1000,
    x: 0,
    y: haut,
    toJSON: () => ({}),
  })
  Object.defineProperty(el, 'offsetHeight', { configurable: true, value: hauteur })
}

afterEach(() => vi.restoreAllMocks())

describe('Cadre', () => {
  it('prend la hauteur qui reste sous lui, moins ce qui le suit (note, marges, bords)', () => {
    vi.stubGlobal('innerHeight', 768)
    const { container } = render(
      <div id="carte">
        <div id="cadre" />
        <p id="note">Méthode</p>
      </div>,
    )
    container
      .querySelector<HTMLElement>('#carte')
      ?.setAttribute('style', 'padding-bottom: 16px; border-bottom: 1px solid')
    container.querySelector<HTMLElement>('#cadre')?.setAttribute('style', 'margin-bottom: 8px')
    container.querySelector<HTMLElement>('#note')?.setAttribute('style', 'margin-top: 4px')
    const cadre = container.querySelector('#cadre')
    const note = container.querySelector('#note')
    if (!(cadre instanceof HTMLElement) || !note) throw new Error('montage')
    boite(cadre, 300, 100)
    boite(note, 412, 20)
    // 768 − 300 (haut) − 8 (marge) − 20 − 4 (note) − 16 − 1 (bas de la carte) = 419
    expect(hauteurRestante(cadre)).toBe(419)
    vi.stubGlobal('innerHeight', 400)
    expect(hauteurRestante(cadre)).toBe(PLANCHER)
  })

  it('pose la hauteur mesurée en hauteur maximale ; dans une fenêtre, une hauteur fixe sans mesure', () => {
    vi.stubGlobal('innerHeight', 768)
    const { unmount } = render(
      <Cadre>
        <table aria-label="Lots" />
      </Cadre>,
    )
    const cadre = screen.getByRole('table').parentElement
    expect(cadre).toHaveAttribute('data-hauteur', 'page')
    expect(cadre?.style.maxHeight).toMatch(/px$/)
    unmount()
    render(
      <Fenetre titre="Fiche" onFermer={() => {}}>
        <Cadre>
          <table aria-label="Lignes" />
        </Cadre>
      </Fenetre>,
    )
    const dansFenetre = screen.getByRole('table', { name: 'Lignes' }).parentElement
    expect(dansFenetre).toHaveAttribute('data-hauteur', 'fenetre')
    expect(dansFenetre).toHaveClass('fenetre')
    expect(dansFenetre?.style.maxHeight).toBe('')
  })
})
