/**
 * Ma journée, sans écran, sur des réponses relevées au vrai serveur (base d'essai du lot F1) :
 * l'ordre exact des tâches des achats (ECRANS-PRO partie 1), le document s'il est seul, la liste
 * filtrée sinon, les brouillons que chaque rôle peut ouvrir, les arrivées de la semaine.
 */
import { describe, expect, it } from 'vitest'

import cockpitJson from '../cockpit/essais/cockpit.json'
import commandesJson from '../cockpit/essais/commandes.json'
import retardsJson from '../cockpit/essais/retards.json'
import attenteJson from './essais/attente.json'
import brouillonsAchatsJson from './essais/brouillons-achats.json'
import brouillonsAlimJson from './essais/brouillons-alimentation.json'
import inventairesJson from './essais/inventaires.json'
import reclamationsJson from './essais/reclamations.json'
import signalementsJson from './essais/signalements.json'
import {
  arriveesSemaine,
  retardsDe,
  besoinsTries,
  brouillonsVisibles,
  quelques,
  tachesAchats,
  tachesAValider,
  texteAlerte,
  unOuListe,
  type SourcesAchats,
} from './taches'
import type {
  Brouillons,
  Cockpit,
  CommandeResume,
  EnAttente,
  InventaireResume,
  PageSignalements,
  ReclamationResume,
} from './types'

const cockpit: Cockpit = cockpitJson
const commandes: CommandeResume[] = commandesJson
const retards: CommandeResume[] = retardsJson
const attente: EnAttente = attenteJson
const signalements: PageSignalements = signalementsJson
const reclamations: ReclamationResume[] = reclamationsJson
const inventaires: InventaireResume[] = inventairesJson
const brouillonsAchats: Brouillons = brouillonsAchatsJson
const brouillonsAlim: Brouillons = brouillonsAlimJson

const sources = (autres: Partial<SourcesAchats> = {}): SourcesAchats => ({
  role: 'achats',
  cockpit,
  commandes,
  retards,
  attente,
  besoins: signalements.elements,
  reclamations,
  inventaires,
  ...autres,
})

describe('Ma journée des achats — « À faire »', () => {
  it('suit l’ordre exact de ECRANS-PRO : besoins (urgents d’abord), alerte, retards, prix, brouillons, factures, sans facture, inventaires, réclamations, contrôles', () => {
    const t = tachesAchats(sources())
    expect(t.map((x) => x.cle)).toEqual([
      'besoin-1',
      'besoin-2',
      'alerte',
      'retards',
      'prix',
      'brouillons',
      'factures',
      'sans-facture',
      'inventaire-1',
      'reclamations',
      'controles',
    ])
    // Le besoin urgent passe devant le plus récent.
    expect(signalements.elements[0]?.id).toBe(2)
    expect(t[0]?.besoin?.urgence).toBe('urgente')
  })

  it('un document seul s’ouvre lui-même ; plusieurs : la liste filtrée', () => {
    const t = Object.fromEntries(tachesAchats(sources()).map((x) => [x.cle, x]))
    expect(t.retards?.vers).toBe(`/commandes/${retards[0]?.id}`)
    expect(t.brouillons?.vers).toMatch(/^\/commandes\/\d+$/)
    expect(t['inventaire-1']?.vers).toBe('/inventaires/1')
    expect(t.reclamations?.vers).toBe(`/reclamations/${reclamations[0]?.id}`)
    expect(t.factures?.vers).toBe('/importations?onglet=rattacher')
    expect(t.alerte?.vers).toBe('/plan-achat')
    expect(t.controles?.vers).toBe('/analyse?onglet=controles')
    const deux = retards.map((c, i) => ({ ...c, id: c.id + i * 100 }))
    const t2 = tachesAchats(sources({ retards: [...deux, ...deux.map((c) => ({ ...c, id: c.id + 1 }))] }))
    expect(t2.find((x) => x.cle === 'retards')?.vers).toBe('/commandes?filtre=retard')
    expect(t2.find((x) => x.cle === 'retards')?.titre).toBe('2 commande(s) en retard')
  })

  it('les comptes sont ceux du serveur (H-07 : « N en rupture ou critiques », les urgentes à part)', () => {
    const t = tachesAchats(sources())
    expect(t.find((x) => x.cle === 'alerte')?.titre).toBe(`${cockpit.alerte_rouge} en rupture ou critiques`)
    expect(t.find((x) => x.cle === 'controles')?.titre).toBe(
      `${cockpit.controles.a_corriger} contrôle(s) à corriger`,
    )
    expect(texteAlerte(3, 2)).toBe('3 en rupture ou critiques, et 2 urgente(s)')
    expect(texteAlerte(0, 2)).toBe('2 matière(s) urgente(s)')
  })

  it('rien n’attend : aucune tâche', () => {
    const vide = { ...cockpit, alerte_rouge: 0, controles: { ...cockpit.controles, a_corriger: 0 } }
    vide.stock = { ...vide.stock, urgents: 0 }
    expect(
      tachesAchats({
        role: 'achats',
        cockpit: vide,
        commandes: [],
        retards: [],
        besoins: [],
        reclamations: [],
        inventaires: [],
      }),
    ).toEqual([])
  })

  it('un lien vers un écran que le rôle ne peut ouvrir n’est pas un lien', () => {
    expect(unOuListe('alimentation', 1, () => '/commandes/3', '/commandes')).toBeNull()
    expect(unOuListe('achats', 1, () => '/commandes/3', '/commandes')).toBe('/commandes/3')
    expect(unOuListe('achats', 2, () => '/commandes/3', '/commandes?filtre=retard')).toBe(
      '/commandes?filtre=retard',
    )
  })

  it('« quelques » : quatre, puis le reste compté', () => {
    expect(quelques([1, 2, 3, 4, 5, 6], String)).toBe('1 — 2 — 3 — 4 — … (+2)')
    expect(besoinsTries(signalements.elements).map((b) => b.id)).toEqual([1, 2])
  })
})

describe('« À valider »', () => {
  it('achats : réceptions, ordres, opérations — la fiche si le brouillon est seul, l’onglet sinon', () => {
    const t = tachesAValider('achats', brouillonsVisibles('achats', brouillonsAchats))
    expect(t.map((x) => [x.cle, x.vers])).toEqual([
      ['valider-reception', '/receptions?onglet=brouillon'],
      ['valider-ordre', '/ordres/4'],
      ['valider-operation', '/operations/1'],
    ])
    expect(t[0]?.titre).toBe('2 réception(s) en brouillon')
    expect(t[2]?.detail).toMatch(/Dont 1 serait refusé à la validation/)
  })

  it('alimentation : ni réception, ni opération qu’elle ne peut ouvrir', () => {
    const avecAjustement: Brouillons = {
      ...brouillonsAlim,
      lignes: [...brouillonsAlim.lignes, { ...brouillonsAlim.lignes[0]!, type: 'ajustement', id: 9 }],
    }
    const vus = brouillonsVisibles('alimentation', avecAjustement)
    expect(vus.map((x) => `${x.genre}:${x.type}`)).toEqual(['operation:transfert', 'ordre:ordre'])
    const t = tachesAValider('alimentation', vus)
    expect(t.map((x) => x.vers)).toEqual(['/ordres/4', '/operations/1'])
  })

  it('plusieurs brouillons d’un genre : l’onglet des brouillons', () => {
    const deux = [...brouillonsAchats.ordres, { ...brouillonsAchats.ordres[0]!, id: 7 }]
    expect(tachesAValider('achats', deux)[0]?.vers).toBe('/sorties?onglet=brouillon')
  })
})

describe('Arrivées attendues dans les 7 jours, retards', () => {
  it('les arrivées sont celles que le serveur date sous 7 jours, la plus proche d’abord', () => {
    const base = commandes.find((c) => c.parti && c.statut !== 'annulee')!
    const bon = (id: number, arrivee: string | null, sous7: boolean): CommandeResume => ({
      ...base,
      id,
      arrivee_attendue: arrivee,
      arrivee_sous_7_jours: sous7,
    })
    const liste = [
      bon(1, '2026-10-12', true),
      bon(2, '2026-10-07', true),
      bon(3, '2026-10-06', false),
      bon(5, '2026-10-15', true),
      // Une date dans la semaine que le serveur n'a pas retenue (bon soldé…) : l'écran ne la reprend pas.
      bon(6, '2026-10-09', false),
      bon(8, '2026-10-10', true),
    ]
    expect(arriveesSemaine(liste).map((c) => c.id)).toEqual([2, 8, 1, 5])
  })

  it('les retards sont les bons que le serveur dit en retard', () => {
    expect(retardsDe(commandes).map((c) => c.id)).toEqual(retards.map((c) => c.id))
  })
})
