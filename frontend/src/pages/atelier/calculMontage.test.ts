/**
 * Les calculs du montage, comme le serveur (lot D2) : bobines = mètres × bobines par mètre
 * (le remplissage des bobines n'y entre pas) ; poids = bobines × poids de bobine retenu ×
 * remplissage des bobines / 100 ; largeur occupée = Σ mètres ; métier arrêté = rien ; effet au
 * gramme ; texte unique « sur les métiers » ((a)) mot pour mot ; alerte 30 jours (1,1 × sorti +
 * 1 kg) ; raisons sous le bouton.
 */
import { describe, expect, it } from 'vitest'

import {
  alertesMontage,
  corpsEtage,
  effetDe,
  etageEnregistre,
  largeurDe,
  messageMontage,
  peser,
  poidsRetenu,
  raisonEtage,
  type FilSaisi,
} from './calculMontage'
import { donnees } from './essaiAtelier'

const fil = (m: Partial<FilSaisi> = {}): FilSaisi => ({
  matiere_id: 1,
  reference: 'POIL ROUGE 2900',
  designation: '',
  metres: 2,
  pourcentage: 50,
  commentaire: '',
  ...m,
})

describe('Calculs du montage', () => {
  it('poids et largeur comme le serveur ; un métier arrêté ne pèse rien', () => {
    const reglage = { actif: true, bobines_par_metre: 320 }
    // Largeur = Σ mètres : le remplissage des bobines ne la change pas (deux fils de 2 m = 4 m).
    expect(largeurDe([fil(), fil({ matiere_id: 2 })])).toBe(4)
    expect(peser(reglage, [fil()], () => 2.5)).toBe(800)
    expect(peser({ ...reglage, actif: false }, [fil()], () => 2.5)).toBe(0)
  })

  it('le poids de bobine retenu est celui du montage (le même qu’au téléphone, an. 11)', () => {
    const d = donnees()
    const m = d.METIERS.find((x) => x.id === 1)
    if (!m) throw new Error('fixture')
    expect(poidsRetenu(m, d.MATIERES_MONTAGE, 1)).toBe(2.4952)
    expect(poidsRetenu(m, [], 1)).toBe(m.fils[0]?.poids_bobine_utilise)
    expect(poidsRetenu(m, [], 99)).toBe(0)
  })

  it('l’effet d’un étage, au gramme, et le texte unique', () => {
    const m = { actif: true, bobines_par_metre: 320 }
    expect(effetDe({ avant: m, apres: m }, [], [fil()], () => 2.4952)).toBe(798.464)
    expect(messageMontage(true, 1000, 1798.464)).toBe(
      'Monter n’écrit aucun mouvement : ce fil est déjà sorti par un ordre. Le stock sur les métiers passe de ' +
        '1 000,0 à 1 798,5 kg (+798,5 kg) ; il compte dans le stock global, sa valeur, le disponible et le projeté.',
    )
    expect(messageMontage(true, 10, 10.04)).toBe('Le stock sur les métiers ne change pas.')
    expect(messageMontage(false, 10, 50)).toBe('Métier arrêté : rien n’est compté sur lui.')
  })

  it('alerte au-delà de 1,1 × ce qui est parti en 30 jours + 1 kg', () => {
    const d = donnees()
    const m = { actif: true, bobines_par_metre: 320 }
    const rouge = d.MATIERES_MONTAGE.find((x) => x.matiere_id === 1)
    if (!rouge) throw new Error('fixture')
    const matieres = [{ ...rouge, deja_monte: 0, sorti_30_j: 100 }]
    expect(
      alertesMontage(
        { avant: m, apres: m },
        [],
        [fil({ metres: 0.1, pourcentage: 100 })],
        matieres,
        () => 2.5,
      ),
    ).toEqual([])
    const [alerte] = alertesMontage(
      { avant: m, apres: m },
      [],
      [fil({ metres: 1, pourcentage: 100 })],
      matieres,
      () => 2.5,
    )
    expect(alerte).toBe(
      'POIL ROUGE 2900 : 800,0 kg sur les métiers pour 100,0 kg partis aux machines en 30 jours : vérifier ' +
        'qu’il est bien sorti par un ordre avant de le monter.',
    )
  })

  it('l’étage enregistré, sa version, le corps envoyé avec l’effet à confirmer', () => {
    const m = donnees().METIERS.find((x) => x.id === 1)
    if (!m) throw new Error('fixture')
    const e = etageEnregistre(m, 1)
    expect(e.version).toBe(m.etages_detail[0]?.version)
    expect(e.fils).toHaveLength(m.fils.filter((f) => f.etage === 1).length)
    expect(corpsEtage(e, 12.5)).toMatchObject({ version: e.version, confirme_effet_kg: 12.5 })
    expect(etageEnregistre(m, 2).fils).toEqual([])
  })

  it('la raison de griser « Enregistrer l’étage »', () => {
    expect(raisonEtage({ trop: true, sansMetres: [], modifie: true })).toBe('Plus large que la laize')
    expect(raisonEtage({ trop: false, sansMetres: [fil({ metres: 0 })], modifie: true })).toBe(
      'Saisir les mètres de : POIL ROUGE 2900',
    )
    expect(raisonEtage({ trop: false, sansMetres: [], modifie: false })).toBe('Aucune modification')
    expect(raisonEtage({ trop: false, sansMetres: [], modifie: true })).toBe('')
  })
})
