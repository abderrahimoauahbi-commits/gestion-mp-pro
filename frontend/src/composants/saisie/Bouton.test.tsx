/** Essais du bouton : jamais grisé sans raison, raison écrite à l'atelier, attente sur le bouton touché. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ErreurApi } from '../../lib/api'
import { Messages } from '../retour/Messages'
import { Bouton, raisonGrise } from './Bouton'

describe('Bouton', () => {
  it('actif : le titre dit ce que fait le geste, le nom reste le libellé', async () => {
    const clic = vi.fn()
    render(
      <Bouton titre="Annule la réception par contre-passation" onClick={clic}>
        Annuler (contre-passation)
      </Bouton>,
    )
    const b = screen.getByRole('button', { name: 'Annuler (contre-passation)' })
    expect(b).toBeEnabled()
    expect(b).toHaveAccessibleDescription('Annule la réception par contre-passation')
    await userEvent.click(b)
    expect(clic).toHaveBeenCalledTimes(1)
  })

  it('grisé : toujours avec sa raison (infobulle, description, data-raison)', async () => {
    const clic = vi.fn()
    render(
      <Bouton manque={['la date', 'le magasin']} blocages={['un inventaire est ouvert']} onClick={clic}>
        Valider
      </Bouton>,
    )
    const b = screen.getByRole('button', { name: 'Valider' })
    expect(b).toBeDisabled()
    const raison = 'À renseigner : la date, le magasin. Sera refusé : un inventaire est ouvert.'
    expect(b).toHaveAttribute('data-raison', raison)
    expect(b).toHaveAttribute('title', raison)
    expect(b).toHaveAccessibleDescription(raison)
    await userEvent.click(b)
    expect(clic).not.toHaveBeenCalled()
  })

  it('à l’atelier, la raison s’écrit sous le bouton, sans infobulle', () => {
    render(
      <Bouton taille="atelier" grise="1 ligne dépasse ce qui est parti.">
        Remettre en stock
      </Bouton>,
    )
    const b = screen.getByRole('button', { name: 'Remettre en stock' })
    expect(b).not.toHaveAttribute('title')
    const texte = screen.getByText('1 ligne dépasse ce qui est parti.')
    expect(texte).toBeVisible()
    expect(texte).toHaveClass('raison')
  })

  it('un geste qui attend le serveur affiche son attente sur le bouton touché, et dit le refus', async () => {
    let finir: (v?: unknown) => void = () => {}
    const promesse = new Promise((_ok, non) => {
      finir = () => non(new ErreurApi('Ce bon est clos.', 409, 'etat_incompatible'))
    })
    render(
      <>
        <Messages />
        <Bouton attente="Enregistrement…" onClick={() => promesse}>
          Enregistrer
        </Bouton>
        <Bouton>Autre</Bouton>
      </>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    const touche = screen.getByRole('button', { name: 'Enregistrement…' })
    expect(touche).toBeDisabled()
    expect(touche).toHaveAttribute('data-raison', 'Envoi en cours.')
    expect(screen.getByRole('button', { name: 'Autre' })).toBeEnabled()
    finir()
    expect(await screen.findByText('Ce bon est clos.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Enregistrer' })).toBeEnabled()
  })

  it('raisonGrise : vide quand rien ne grise', () => {
    expect(raisonGrise({})).toBe('')
    expect(raisonGrise({ blocages: ['date antérieure au dernier ordre.'] })).toBe(
      'Sera refusé : date antérieure au dernier ordre.',
    )
  })
})
