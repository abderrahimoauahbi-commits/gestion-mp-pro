/** Mon compte : courriel, changement de code (règle du rôle), apparence, appareils (direction, administrateur). */
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fauxServeur,
  moiDe,
  monterApp,
  prechargerPages,
  reponsesConnecte,
  stockageMemoire,
} from '../../essais/monter'
import { codeValable, manqueCode, regleDuCode } from './ChangerCode'
import { appliquerTheme, lireTheme } from './theme'

beforeAll(prechargerPages)
beforeEach(() => {
  stockageMemoire()
})
afterEach(() => vi.unstubAllGlobals())

describe('Mon compte', () => {
  it('la règle du code de chaque rôle', () => {
    expect(regleDuCode('alimentation')).toBe('Exactement 4 chiffres.')
    expect(codeValable('alimentation', '1234')).toBe(true)
    expect(codeValable('alimentation', '12345')).toBe(false)
    expect(codeValable('achats', '1234567')).toBe(false)
    expect(codeValable('direction', '12345678')).toBe(true)
    expect(codeValable('administrateur', '12345678901')).toBe(false)
    expect(manqueCode('achats', 'ancien', 'nouveaucode', 'autre')).toEqual([
      'le nouveau code retapé à l’identique',
    ])
  })

  it('change le code : l’ancien est envoyé, les champs se vident', async () => {
    const appels = fauxServeur({ ...reponsesConnecte('alimentation'), 'PUT /moi/code': { statut: 204 } })
    monterApp('/compte')
    await userEvent.type(await screen.findByLabelText('Code actuel'), '1111')
    await userEvent.type(screen.getByLabelText('Nouveau code'), '2222')
    await userEvent.type(screen.getByLabelText('Nouveau code, encore une fois'), '2222')
    await userEvent.click(screen.getByRole('button', { name: 'Changer mon code' }))
    await waitFor(() => expect(screen.getByLabelText('Code actuel')).toHaveValue(''))
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toEqual({ ancien: '1111', nouveau: '2222' })
  })

  it('enregistre le courriel avec la version de la fiche', async () => {
    const appels = fauxServeur({
      ...reponsesConnecte('achats'),
      'PUT /moi': { corps: moiDe('achats', { email: 'k@usine.ma', version: 2 }) },
    })
    monterApp('/compte')
    const bouton = await screen.findByRole('button', { name: 'Enregistrer le courriel' })
    expect(bouton).toHaveAttribute('data-raison', 'Rien n’a changé.')
    await userEvent.type(screen.getByLabelText('Courriel'), 'k@usine.ma')
    await userEvent.click(bouton)
    await waitFor(() => expect(appels.some((a) => a.methode === 'PUT')).toBe(true))
    expect(appels.find((a) => a.methode === 'PUT')?.corps).toEqual({ email: 'k@usine.ma', version: 1 })
  })

  it('montre les appareils à la direction, pas aux achats', async () => {
    fauxServeur({
      ...reponsesConnecte('direction'),
      'GET /appareils': {
        corps: [
          {
            id: 1,
            nom: 'Téléphone atelier 1',
            actif: true,
            enrole: true,
            enrole_le: '2026-10-01T09:00:00+01:00',
          },
          {
            id: 2,
            nom: 'Téléphone retiré',
            actif: false,
            enrole: true,
            enrole_le: '2026-09-01T09:00:00+01:00',
          },
        ],
      },
    })
    monterApp('/compte')
    expect(await screen.findByText('Téléphone atelier 1')).toBeInTheDocument()
    expect(screen.queryByText('Téléphone retiré')).toBeNull()
  })

  it('l’apparence se pose sur la page et se retient', () => {
    appliquerTheme('sombre', true)
    expect(document.documentElement).toHaveAttribute('data-theme', 'sombre')
    expect(lireTheme()).toBe('sombre')
    appliquerTheme('poste', true)
    expect(document.documentElement).not.toHaveAttribute('data-theme')
    expect(lireTheme()).toBe('poste')
  })
})
