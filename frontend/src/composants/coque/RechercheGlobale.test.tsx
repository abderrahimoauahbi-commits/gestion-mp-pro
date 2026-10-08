/** La recherche globale : au clavier, dès deux caractères, résultats filtrés par les droits d'écran. */
import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterDansSession } from '../../essais/monter'
import { RechercheGlobale, rangerResultats } from './RechercheGlobale'

afterEach(() => vi.unstubAllGlobals())

const RESULTATS = [
  { genre: 'commande', id: 412, titre: 'BC-2026-0412', sous_titre: 'HASIRCI', lien: '/commandes/nouvelle' },
  {
    genre: 'matiere',
    id: 12,
    titre: 'PP FRZ-2900 Dtex-Red',
    sous_titre: 'IMP FRISÉ ROUGE',
    lien: '/stock?onglet=matieres',
  },
  { genre: 'lot', id: 884, titre: 'Lot GLO260914-884', lien: '/lots/884' },
]

describe('RechercheGlobale', () => {
  it('range par genre et retire ce que le rôle ne peut pas ouvrir', () => {
    expect(rangerResultats(RESULTATS, 'direction').map((r) => r.genre)).toEqual([
      'matiere',
      'lot',
      'commande',
    ])
    expect(rangerResultats(RESULTATS, 'alimentation').map((r) => r.genre)).toEqual(['matiere', 'lot'])
  })

  it('« / » y mène ; ↓ puis Entrée ouvre le résultat ; la recherche part dès deux caractères', async () => {
    const appels = fauxServeur({ 'GET /recherche': { corps: RESULTATS } })
    const { routeur } = monterDansSession(<RechercheGlobale role="achats" />, 'achats', '/accueil')
    const champ = screen.getByRole('combobox', { name: 'Recherche globale' })
    fireEvent.keyDown(document.body, { key: '/' })
    expect(champ).toHaveFocus()
    await userEvent.type(champ, 'f')
    expect(await screen.findByText('Tapez au moins deux caractères.')).toBeInTheDocument()
    await userEvent.type(champ, 'rz')
    expect(await screen.findByRole('option', { name: /PP FRZ-2900/ })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(appels.filter((a) => a.chemin.startsWith('/recherche'))).toHaveLength(1)
    expect(appels[0]?.chemin).toBe('/recherche?q=frz')
    await userEvent.keyboard('{ArrowDown}')
    expect(screen.getByRole('option', { name: /Lot GLO260914-884/ })).toHaveAttribute('aria-selected', 'true')
    await userEvent.keyboard('{Enter}')
    await waitFor(() => expect(routeur.state.location.pathname).toBe('/lots/884'))
    expect(champ).toHaveValue('')
  })

  it('dit quand rien ne correspond ; Échap ferme', async () => {
    fauxServeur({ 'GET /recherche': { corps: [] } })
    monterDansSession(<RechercheGlobale role="direction" />, 'direction')
    const champ = screen.getByRole('combobox', { name: 'Recherche globale' })
    await userEvent.type(champ, 'zzz')
    expect(await screen.findByText('Rien ne correspond.')).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(champ).toHaveAttribute('aria-expanded', 'false')
  })
})
