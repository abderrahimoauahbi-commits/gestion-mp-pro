/// <reference types="node" />
/** La barre latérale : le menu du rôle, les pastilles, l'entrée active, et le menu qui tient en 1366 × 768. */
import { screen, within } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import { monterDansSession } from '../../essais/monter'
import { menuDe } from '../../lib/droits'
import type { Role } from '../../lib/types'
import { BarreLaterale } from './BarreLaterale'

const ICI = dirname(fileURLToPath(import.meta.url))
const css = readFileSync(join(ICI, 'BarreLaterale.module.css'), 'utf8')
const jetons = readFileSync(join(ICI, '../../styles/jetons.css'), 'utf8')
const px = (texte: string, nom: string) => Number(new RegExp(`${nom}:\\s*(\\d+)px`).exec(texte)?.[1])

const compteurs = { alerte_rouge: 7, anomalies: 3, a_approuver: 2, receptions_brouillon: 4 }

describe('BarreLaterale', () => {
  it('montre le menu du rôle, groupe par groupe', () => {
    monterDansSession(<BarreLaterale role="achats" compteurs={compteurs} actif="/accueil" />, 'achats')
    const nav = screen.getByRole('navigation', { name: 'Menu principal' })
    expect(within(nav).getByRole('link', { name: 'Ma journée' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).queryByRole('link', { name: 'Cockpit' })).toBeNull()
    expect(within(nav).queryByRole('link', { name: 'Administration' })).toBeNull()
    expect(within(nav).getAllByRole('link')).toHaveLength(16)
  })

  it('pastilles : alerte rouge au Stock pour l’alimentation aussi ; bons à approuver pour la direction seule', () => {
    monterDansSession(
      <BarreLaterale role="alimentation" compteurs={compteurs} actif={null} />,
      'alimentation',
    )
    expect(screen.getByLabelText('7 — en rupture ou critiques')).toBeInTheDocument()
    expect(screen.queryByLabelText(/bon\(s\) à approuver/)).toBeNull()
  })

  it('la pastille de l’Analyse mène aux Contrôles ; celle des Commandes compte les bons à approuver', () => {
    monterDansSession(<BarreLaterale role="direction" compteurs={compteurs} actif={null} />, 'direction')
    const analyse = screen.getByRole('link', { name: /^Analyse/ })
    expect(analyse).toHaveAttribute('href', '/analyse?onglet=controles')
    expect(analyse).toHaveAttribute(
      'title',
      'Prix, fournisseurs, valorisation, coût de revient, contrôles — 3 contrôle(s) à corriger',
    )
    expect(screen.getByLabelText('2 — bon(s) à approuver')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^Stock, lots/ })).toHaveAttribute('href', '/stock')
  })

  it('sans anomalie, l’Analyse mène à son premier onglet', () => {
    monterDansSession(<BarreLaterale role="achats" compteurs={{ anomalies: 0 }} actif={null} />, 'achats')
    expect(screen.getByRole('link', { name: 'Analyse' })).toHaveAttribute('href', '/analyse')
  })

  it.each<Role>(['direction', 'achats', 'alimentation', 'administrateur'])(
    'le menu de « %s » tient sans défiler en 1366 × 768',
    (role) => {
      const menu = menuDe(role)
      const entrees = menu.reduce((n, g) => n + g.entrees.length, 0)
      const hauteur =
        px(jetons, '--entete') +
        2 * px(css, '--marge-groupes') +
        menu.length * px(css, '--hauteur-groupe') +
        entrees * px(css, '--hauteur-lien')
      expect(hauteur).toBeLessThanOrEqual(768)
    },
  )
})
