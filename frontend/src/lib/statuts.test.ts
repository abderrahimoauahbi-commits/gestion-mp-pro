/** Essais de la table unique des statuts. */
import { describe, expect, it } from 'vitest'

import { cleStock, numeroOuEtat, statut, STATUTS, STOCK_EN_ALERTE, type Famille } from './statuts'

const TONS = ['ok', 'attention', 'urgent', 'critique', 'rupture', 'neutre', 'accent']

describe('Table des statuts', () => {
  it('chaque statut a un libellé non vide, sans émoticône, et un ton connu', () => {
    for (const [famille, table] of Object.entries(STATUTS)) {
      for (const [valeur, { libelle, ton }] of Object.entries(table)) {
        expect(libelle, `${famille}.${valeur}`).toMatch(/\S/)
        expect(libelle, `${famille}.${valeur}`).not.toMatch(/\p{Extended_Pictographic}/u)
        expect(TONS, `${famille}.${valeur}`).toContain(ton)
      }
    }
  })

  it('reprend toutes les valeurs des énumérations du modèle', () => {
    const attendu: Partial<Record<Famille, string[]>> = {
      commande: ['brouillon', 'a_approuver', 'envoyee', 'confirmee', 'soldee', 'annulee'],
      document: ['brouillon', 'validee', 'annulee'],
      ordre: ['brouillon', 'valide', 'annule'],
      qualite_reception: ['conforme', 'reserve', 'refuse'],
      inventaire: ['ouvert', 'valide', 'abandonne', 'annule'],
      dossier: ['ouvert', 'clos', 'annule'],
      reclamation: ['ouverte', 'close'],
      issue_reclamation: ['avoir', 'remplacement', 'remise', 'refusee', 'abandonnee'],
      decision: [
        'demande_approbation',
        'approbation',
        'renvoi',
        'version_retablie',
        'approbation_plus_necessaire',
        'retour_brouillon',
        'rouverture',
      ],
      courriel: ['en_attente', 'envoye', 'abandonne'],
      notification: ['info', 'succes', 'alerte', 'danger'],
    }
    for (const [famille, valeurs] of Object.entries(attendu)) {
      expect(Object.keys(STATUTS[famille as Famille]).sort(), famille).toEqual([...valeurs].sort())
    }
  })

  it('un seul libellé par statut : jamais « Brouillon / Brouillon »', () => {
    expect(statut('commande', 'brouillon')).toEqual({ libelle: 'Brouillon', ton: 'neutre' })
    expect(statut('commande', 'a_approuver').libelle).toBe('À approuver')
    expect(statut('document', 'annulee')).toEqual({ libelle: 'Annulée', ton: 'rupture' })
    expect(statut('ordre', 'valide').libelle).toBe('Validé')
    expect(statut('lot', 'partiel').libelle).toBe('En partie en quarantaine')
    expect(statut('inventaire', 'ouvert')).toEqual({ libelle: 'Comptage en cours', ton: 'attention' })
    expect(statut('inventaire', 'annule')).toEqual({ libelle: 'Annulé', ton: 'neutre' })
  })

  it('une valeur inconnue se montre telle quelle, en neutre ; un vide « — »', () => {
    expect(statut('commande', 'perdue')).toEqual({ libelle: 'perdue', ton: 'neutre' })
    expect(statut('commande', null)).toEqual({ libelle: '—', ton: 'neutre' })
  })
})

describe('Statuts de stock', () => {
  it('lit les libellés du moteur, même avec émoticône', () => {
    expect(cleStock('⚫ RUPTURE')).toBe('RUPTURE')
    expect(cleStock('🔴 CRITIQUE')).toBe('CRITIQUE')
    expect(cleStock('🟠 URGENT')).toBe('URGENT')
    expect(cleStock('🟡 ATTENTION')).toBe('ATTENTION')
    expect(cleStock('🟢 OK')).toBe('OK')
    expect(cleStock('⚪ NON CONSOMMÉE')).toBe('NON_CONSOMMEE')
    expect(cleStock('BOOKING')).toBeNull()
    expect(cleStock(null)).toBeNull()
  })

  it('« en alerte » = les quatre premiers', () => {
    expect(STOCK_EN_ALERTE).toEqual(['RUPTURE', 'CRITIQUE', 'URGENT', 'ATTENTION'])
    expect(statut('stock', 'NON_CONSOMMEE').libelle).toBe('NON CONSOMMÉE')
  })
})

describe('Numéro ou état', () => {
  it('« Brouillon » tant qu’il n’y a pas de numéro, « À approuver » pour un bon soumis', () => {
    expect(numeroOuEtat('BC-2026-0012')).toBe('BC-2026-0012')
    expect(numeroOuEtat(null)).toBe('Brouillon')
    expect(numeroOuEtat(null, 'a_approuver')).toBe('À approuver')
  })
})
