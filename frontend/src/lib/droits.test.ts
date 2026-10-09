/** Les droits d'écran : arrivée par rôle et par appareil, refus d'un écran ou d'un onglet, retour après connexion. */
import { describe, expect, it } from 'vitest'

import { ecranParChemin } from '../routes'
import { accueilDe, destinationApresConnexion, ongletsPermis, permis, refus, rolesDe } from './droits'

describe('droits d’écran', () => {
  it('arrivée : direction → Cockpit, achats → Ma journée, alimentation → atelier au téléphone, administrateur → Administration', () => {
    expect(accueilDe('direction', false)).toBe('/cockpit')
    expect(accueilDe('direction', true)).toBe('/cockpit')
    expect(accueilDe('achats', true)).toBe('/accueil')
    expect(accueilDe('alimentation', false)).toBe('/accueil')
    expect(accueilDe('alimentation', true)).toBe('/atelier')
    expect(accueilDe('administrateur', false)).toBe('/administration')
  })

  it('un onglet réservé est refusé (alimentation : transferts et retours des machines seulement)', () => {
    expect(refus('alimentation', '/operations?onglet=transfert')).toBeNull()
    expect(refus('alimentation', '/operations?onglet=retour_machine')).toBeNull()
    expect(refus('alimentation', '/operations?onglet=ouverture')).toBe('reservee')
    expect(refus('alimentation', '/catalogue?onglet=fournisseurs')).toBe('reservee')
    expect(refus('achats', '/operations?onglet=ouverture')).toBeNull()
    const ops = ecranParChemin('/operations')
    expect(ops && ongletsPermis(ops, 'alimentation').map((o) => o.cle)).toEqual([
      'transfert',
      'retour_machine',
    ])
  })

  it('distingue l’écran réservé de l’adresse inconnue', () => {
    expect(refus('achats', '/cockpit')).toBe('reservee')
    expect(refus('achats', '/n-existe-pas')).toBe('inconnue')
    expect(permis('administrateur', '/stock')).toBe(false)
    expect(rolesDe('/cockpit')).toBe('Direction')
  })

  it('après la connexion : l’adresse demandée si elle est sûre et permise, sinon l’arrivée du rôle', () => {
    expect(destinationApresConnexion('achats', '/commandes?onglet=brouillon', false)).toBe(
      '/commandes?onglet=brouillon',
    )
    expect(destinationApresConnexion('achats', '/cockpit', false)).toBe('/accueil')
    expect(destinationApresConnexion('direction', '//ailleurs.example/x', false)).toBe('/cockpit')
    expect(destinationApresConnexion('direction', '/connexion', false)).toBe('/cockpit')
    expect(destinationApresConnexion('alimentation', null, true)).toBe('/atelier')
  })
})
