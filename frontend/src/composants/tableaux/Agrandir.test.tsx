/** Essais d'« Agrandir » : le tableau passe en plein écran et en revient ; Échap le réduit sans fermer la fenêtre. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Fenetre } from '../mise-en-page/Fenetre'
import { CadreAgrandissable } from './Cadre'
import { DataTable } from './DataTable'

const lignes = [{ id: 1, nom: 'Jute 30/1' }]
const colonnes = [{ cle: 'nom', titre: 'Référence', valeur: (x: { nom: string }) => x.nom }]

describe('Agrandir', () => {
  it('un tableau s’ouvre en grand, garde ses lignes, puis se réduit', async () => {
    render(<DataTable libelle="Lignes" lignes={lignes} colonnes={colonnes} cle={(x) => x.id} />)
    const tableau = screen.getByRole('table', { name: 'Lignes' })
    const boite = tableau.closest('[class]')?.parentElement?.parentElement
    await userEvent.click(screen.getByRole('button', { name: '⤢ Agrandir' }))
    expect(screen.getByRole('button', { name: '✕ Réduire' })).toHaveAttribute('aria-pressed', 'true')
    expect(boite?.className).toMatch(/grand/)
    expect(screen.getByText('Jute 30/1')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '✕ Réduire' }))
    expect(screen.getByRole('button', { name: '⤢ Agrandir' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('dans une fenêtre, Échap réduit le tableau sans fermer la fenêtre', async () => {
    const fermer = vi.fn()
    render(
      <Fenetre titre="Saisie" onFermer={fermer}>
        <CadreAgrandissable>
          <table aria-label="Lignes du camion">
            <tbody>
              <tr>
                <td>Jute 30/1</td>
              </tr>
            </tbody>
          </table>
        </CadreAgrandissable>
      </Fenetre>,
    )
    await userEvent.click(screen.getByRole('button', { name: '⤢ Agrandir' }))
    await userEvent.keyboard('{Escape}')
    expect(screen.getByRole('button', { name: '⤢ Agrandir' })).toBeInTheDocument()
    expect(fermer).not.toHaveBeenCalled()
  })
})
