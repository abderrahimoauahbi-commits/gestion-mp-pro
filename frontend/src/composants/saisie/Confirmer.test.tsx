/** Essais de Confirmer : sur place (jamais de boîte du navigateur), motif exigé, envoi, Échap. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ErreurApi } from '../../lib/api'
import { Fenetre } from '../mise-en-page/Fenetre'
import { Messages } from '../retour/Messages'
import { Confirmer } from './Confirmer'

describe('Confirmer', () => {
  it('pose la question sur place : « question · Non · Oui, … », sans boîte du navigateur', async () => {
    const confirm = vi.spyOn(window, 'confirm')
    const oui = vi.fn()
    render(
      <Confirmer question="Retirer ce document ?" oui="Oui, retirer" variante="danger" onOui={oui}>
        Retirer
      </Confirmer>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Retirer' }))
    const groupe = screen.getByRole('group', { name: 'Confirmation' })
    expect(groupe).toHaveTextContent('Retirer ce document ?')
    expect(screen.getByRole('button', { name: 'Non' })).toHaveFocus()
    await userEvent.click(screen.getByRole('button', { name: 'Non' }))
    expect(oui).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Retirer' }))
    await userEvent.click(screen.getByRole('button', { name: 'Oui, retirer' }))
    expect(oui).toHaveBeenCalledWith('')
    expect(screen.queryByRole('group', { name: 'Confirmation' })).toBeNull()
    expect(confirm).not.toHaveBeenCalled()
  })

  it('un motif exigé grise « Oui » avec la raison, puis part avec la confirmation', async () => {
    const oui = vi.fn()
    render(
      <Confirmer question="Annuler cette réception ?" oui="Oui, annuler" motif="exige" onOui={oui}>
        Annuler (contre-passation)
      </Confirmer>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Annuler (contre-passation)' }))
    const bouton = screen.getByRole('button', { name: 'Oui, annuler' })
    expect(bouton).toBeDisabled()
    expect(bouton).toHaveAttribute('data-raison', 'À renseigner : le motif.')
    const champ = screen.getByRole('textbox', { name: 'Motif (obligatoire)' })
    expect(champ).toHaveFocus()
    await userEvent.type(champ, 'Bobines mouillées')
    await userEvent.click(bouton)
    expect(oui).toHaveBeenCalledWith('Bobines mouillées')
  })

  it('un motif trop court (motifMin) grise « Oui » avec la longueur attendue, sous son propre nom', async () => {
    const oui = vi.fn()
    render(
      <Confirmer
        question="Renvoyer aux achats ?"
        oui="Oui, renvoyer"
        motif="exige"
        motifMin={3}
        libelleMotif="Motif du renvoi aux achats"
        exempleMotif="ex. attendre la baisse annoncée"
        onOui={oui}
      >
        Renvoyer aux achats…
      </Confirmer>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Renvoyer aux achats…' }))
    const champ = screen.getByRole('textbox', { name: 'Motif du renvoi aux achats' })
    expect(champ).toHaveAttribute('placeholder', 'ex. attendre la baisse annoncée')
    await userEvent.type(champ, ' ok ')
    const bouton = screen.getByRole('button', { name: 'Oui, renvoyer' })
    expect(bouton).toBeDisabled()
    expect(bouton).toHaveAttribute('data-raison', 'À renseigner : un motif de 3 caractères au moins.')
    await userEvent.type(champ, 'é')
    await userEvent.click(bouton)
    expect(oui).toHaveBeenCalledWith('ok é')
  })

  it('pendant l’envoi « Oui » est occupé ; un refus est dit et la question reste', async () => {
    render(
      <>
        <Messages />
        <Confirmer
          question="Clore ?"
          oui="Oui, clore"
          onOui={() => Promise.reject(new ErreurApi('Ce dossier est déjà clos.', 409))}
        >
          Clore
        </Confirmer>
      </>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Clore' }))
    await userEvent.click(screen.getByRole('button', { name: 'Oui, clore' }))
    expect(await screen.findByText('Ce dossier est déjà clos.')).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Confirmation' })).toBeInTheDocument()
  })

  it('Échap revient au bouton sans fermer la fenêtre autour', async () => {
    const fermer = vi.fn()
    render(
      <Fenetre titre="Fiche" onFermer={fermer}>
        <Confirmer question="Supprimer ce brouillon ?" oui="Oui, supprimer" onOui={() => {}}>
          Supprimer
        </Confirmer>
      </Fenetre>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer' }))
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('group', { name: 'Confirmation' })).toBeNull()
    expect(fermer).not.toHaveBeenCalled()
  })

  it('le bouton de départ porte les raisons de griser', () => {
    render(
      <Confirmer
        question="Valider ?"
        oui="Oui, valider"
        onOui={() => {}}
        blocages={['un inventaire est ouvert sur ce magasin']}
      >
        Valider
      </Confirmer>,
    )
    expect(screen.getByRole('button', { name: 'Valider' })).toHaveAttribute(
      'data-raison',
      'Sera refusé : un inventaire est ouvert sur ce magasin.',
    )
  })
})
