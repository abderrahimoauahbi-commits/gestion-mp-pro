/**
 * Ce qui attend une action, sans écran : la liste « À faire » de Ma journée (achats), dans l'ordre
 * exact de ECRANS-PRO partie 1, la carte « À valider » (achats et alimentation) et les arrivées des
 * sept prochains jours. Chaque tâche ouvre le document s'il est seul, la liste filtrée sinon, et
 * n'est un lien que si le rôle peut l'ouvrir (`permis`).
 *
 * Les comptes viennent du serveur : alerte rouge et urgentes du Cockpit (H-07 : « N en rupture ou
 * critiques » partout, les urgentes nommées à part), retards de `GET /commandes?filtre=retard`
 * (P1-11), contrôles à corriger (`a_corriger`, E-08). L'écran ne recompte rien d'autre que la
 * longueur des listes reçues.
 */
import { date, nombre } from '../../lib/format'
import { permis } from '../../lib/droits'
import { ajouterJours } from '../../lib/heure'
import type { Role } from '../../lib/types'
import { estClos, ongletDe, prixAConfirmer } from '../commandes/liste'
import type {
  Brouillon,
  Brouillons,
  Cockpit,
  CommandeResume,
  EnAttente,
  InventaireResume,
  ReclamationResume,
  SignalementFiche,
} from './types'

export type TonTache = 'critique' | 'attention' | 'ok'

export interface Tache {
  cle: string
  titre: string
  detail?: string
  /** Où mène la tâche ; `null` : le rôle ne peut pas l'ouvrir (le texte reste). */
  vers: string | null
  ton?: TonTache
  /** Le compte affiché à gauche (Cockpit). */
  compte?: number | string
  /** Le libellé du lien (Cockpit : « Plan d'achat → »). */
  lien?: string
  /** Un besoin signalé : « Traiter » ouvre sa fenêtre. */
  besoin?: SignalementFiche
}

/** Quatre éléments, puis « — … (+n) » (Gestion MP). */
export function quelques<T>(liste: readonly T[], texte: (x: T) => string, n = 4, sep = ' — '): string {
  const vus = liste.slice(0, n).map(texte).join(sep)
  return liste.length > n ? `${vus}${sep}… (+${liste.length - n})` : vus
}

/** L'adresse si le rôle peut l'ouvrir, sinon `null`. */
export const siPermis = (role: Role, adresse: string): string | null =>
  permis(role, adresse) ? adresse : null

/** Le document s'il est seul, la liste filtrée sinon ; la liste si le document ne s'ouvre pas. */
export function unOuListe(role: Role, n: number, document: () => string, liste: string): string | null {
  return (n === 1 ? siPermis(role, document()) : null) ?? siPermis(role, liste)
}

const numero = (c: CommandeResume) => c.numero ?? 'Brouillon'

/** Les besoins signalés en attente, les urgents d'abord, puis le plus récent. */
export function besoinsTries(liste: readonly SignalementFiche[]): SignalementFiche[] {
  return [...liste].sort(
    (a, b) => Number(b.urgence === 'urgente') - Number(a.urgence === 'urgente') || b.id - a.id,
  )
}

/** Une ligne « Besoin signalé » de Ma journée. */
export function tacheBesoin(x: SignalementFiche): Tache {
  return {
    cle: `besoin-${x.id}`,
    titre: `Besoin signalé${x.reference ? ` : ${x.reference}` : ''}`,
    detail: `« ${x.texte} » — ${x.par}, le ${date(x.quand.slice(0, 10))}`,
    vers: null,
    ton: x.urgence === 'urgente' ? 'critique' : undefined,
    besoin: x,
  }
}

/** « N en rupture ou critiques, et U urgente(s) » (H-07). */
export function texteAlerte(rouges: number, urgentes: number): string {
  if (!rouges) return `${nombre(urgentes)} matière(s) urgente(s)`
  return `${nombre(rouges)} en rupture ou critiques${urgentes ? `, et ${nombre(urgentes)} urgente(s)` : ''}`
}

export interface SourcesAchats {
  role: Role
  cockpit?: Cockpit
  commandes: readonly CommandeResume[]
  retards: readonly CommandeResume[]
  attente?: EnAttente
  besoins: readonly SignalementFiche[]
  reclamations: readonly ReclamationResume[]
  inventaires: readonly InventaireResume[]
}

function tachesCommandes({ role, commandes, retards }: SourcesAchats): Tache[] {
  const t: Tache[] = []
  const prix = commandes.filter(prixAConfirmer)
  const brouillons = commandes.filter((c) => c.statut === 'brouillon')
  const fiche = (l: readonly CommandeResume[]) => () => `/commandes/${l[0]?.id}`
  const liste = (l: readonly CommandeResume[]) => `/commandes?onglet=${l[0] ? ongletDe(l[0]) : 'envoyee'}`
  if (retards.length)
    t.push({
      cle: 'retards',
      titre: `${nombre(retards.length)} commande(s) en retard`,
      detail: `Relancer le fournisseur, noter l'ETA. ${quelques(retards, (c) => `${numero(c)} · ${c.fournisseur}`)}`,
      vers: unOuListe(role, retards.length, fiche(retards), '/commandes?filtre=retard'),
      ton: 'critique',
    })
  if (prix.length)
    t.push({
      cle: 'prix',
      titre: `${nombre(prix.length)} commande(s) attendent la confirmation des prix`,
      detail: quelques(prix, (c) => `${numero(c)} · ${c.fournisseur}`),
      vers: unOuListe(role, prix.length, fiche(prix), liste(prix)),
    })
  if (brouillons.length)
    t.push({
      cle: 'brouillons',
      titre: `${nombre(brouillons.length)} commande(s) en brouillon à envoyer`,
      detail: quelques(brouillons, (c) => c.fournisseur),
      vers: unOuListe(role, brouillons.length, fiche(brouillons), '/commandes?onglet=brouillon'),
    })
  return t
}

function tachesImportations({ role, attente }: SourcesAchats): Tache[] {
  const t: Tache[] = []
  const vers = siPermis(role, '/importations?onglet=rattacher')
  const factures = attente?.factures.length ?? 0
  const sansFacture = attente?.sans_facture.length ?? 0
  if (factures)
    t.push({
      cle: 'factures',
      titre: `${nombre(factures)} facture(s) reçue(s) sans dossier d'importation`,
      detail: "Un dossier par facture : l'ouvrir depuis la facture, puis saisir les frais.",
      vers,
    })
  if (sansFacture)
    t.push({
      cle: 'sans-facture',
      titre: `${nombre(sansFacture)} réception(s) importée(s) sans facture`,
      detail:
        'Saisir la facture sur la réception : sans elle, pas de dossier, donc pas de frais dans le coût.',
      vers,
    })
  return t
}

/** Une ligne par inventaire ouvert : chacun suspend son magasin (P1-10). */
export function tachesInventaires(role: Role, inventaires: readonly InventaireResume[]): Tache[] {
  return inventaires.map((i) => ({
    cle: `inventaire-${i.id}`,
    titre: `Inventaire ${i.numero} en cours`,
    detail: `${nombre(i.nb_comptees)} / ${nombre(i.nb_lignes)} lots comptés — ${
      i.magasin ? `le magasin ${i.magasin}` : 'le stock'
    } est suspendu jusqu'à la validation.`,
    vers: siPermis(role, `/inventaires/${i.id}`) ?? siPermis(role, '/inventaire'),
  }))
}

/** La liste « À faire » de Ma journée (achats), dans l'ordre de ECRANS-PRO partie 1. */
export function tachesAchats(s: SourcesAchats): Tache[] {
  const { role, cockpit, reclamations } = s
  const t: Tache[] = besoinsTries(s.besoins).map(tacheBesoin)
  const rouges = cockpit?.alerte_rouge ?? 0
  const urgentes = cockpit?.stock.urgents ?? 0
  if (rouges || urgentes)
    t.push({
      cle: 'alerte',
      titre: texteAlerte(rouges, urgentes),
      detail: "Le plan d'achat dit quoi commander, à qui, combien.",
      vers: siPermis(role, '/plan-achat'),
      ton: rouges ? 'critique' : 'attention',
    })
  t.push(...tachesCommandes(s), ...tachesImportations(s), ...tachesInventaires(role, s.inventaires))
  if (reclamations.length)
    t.push({
      cle: 'reclamations',
      titre: `${nombre(reclamations.length)} réclamation(s) ouverte(s) chez les fournisseurs`,
      detail: `Relancer, noter la réponse, clore. ${quelques(
        reclamations,
        (r) => `${r.numero} · ${r.fournisseur} · ${r.motif_libelle || r.motif} (${r.jours} j)`,
      )}`,
      vers: unOuListe(
        role,
        reclamations.length,
        () => `/reclamations/${reclamations[0]?.id}`,
        '/receptions?onglet=reclamations',
      ),
    })
  const corriger = cockpit?.controles.a_corriger ?? 0
  if (corriger)
    t.push({
      cle: 'controles',
      titre: `${nombre(corriger)} contrôle(s) à corriger`,
      detail: "Chaque contrôle dit quoi faire et mène à l'écran où le corriger.",
      vers: siPermis(role, '/analyse?onglet=controles'),
      ton: cockpit?.controles.bloquants ? 'critique' : undefined,
    })
  return t
}

/** Les brouillons que ce rôle peut ouvrir (une opération : l'onglet de son type lui est-il permis ?). */
export function brouillonsVisibles(role: Role, b: Brouillons | undefined): Brouillons['lignes'] {
  if (!b) return []
  return b.lignes.filter((x) => x.genre !== 'operation' || permis(role, `/operations?onglet=${x.type}`))
}

const GENRES_A_VALIDER: readonly {
  genre: string
  titre: (n: string) => string
  note: string
  liste: (l: readonly Brouillon[]) => string
}[] = [
  {
    genre: 'reception',
    titre: (n) => `${n} réception(s) en brouillon`,
    note: "La matière n'est pas encore en stock.",
    liste: () => '/receptions?onglet=brouillon',
  },
  {
    genre: 'ordre',
    titre: (n) => `${n} ordre(s) de fabrication en brouillon`,
    note: "Le fil n'est pas encore sorti du stock.",
    liste: () => '/sorties?onglet=brouillon',
  },
  {
    genre: 'operation',
    titre: (n) => `${n} opération(s) en brouillon`,
    note: "Le stock n'a pas encore bougé.",
    liste: (l) => `/operations?onglet=${l[0]?.type ?? 'transfert'}`,
  },
]

/** La carte « À valider » : un groupe par genre, la fiche s'il est seul, l'onglet des brouillons sinon. */
export function tachesAValider(role: Role, lignes: readonly Brouillon[]): Tache[] {
  return GENRES_A_VALIDER.flatMap((g) => {
    const l = lignes.filter((x) => x.genre === g.genre)
    if (!l.length) return []
    const bloques = l.filter((x) => x.blocages.length).length
    const suite = bloques
      ? ` Dont ${nombre(bloques)} ${bloques > 1 ? 'seraient refusés' : 'serait refusé'} à la validation.`
      : ''
    return [
      {
        cle: `valider-${g.genre}`,
        titre: g.titre(nombre(l.length)),
        detail: `${g.note}${suite} ${quelques(l, (x) => `${x.resume || x.libelle} du ${date(x.date)}`)}`,
        vers: unOuListe(role, l.length, () => l[0]?.lien ?? '', g.liste(l)),
        ton: bloques ? 'attention' : undefined,
      },
    ]
  })
}

/** La date d'arrivée attendue : l'ETA, sinon la livraison prévue. */
export const arriveeDe = (c: CommandeResume) => c.expedition.eta ?? c.date_livraison_prevue ?? ''

/**
 * Les bons partis, ni soldés ni annulés, attendus d'hier à J+7 (ETA, sinon livraison prévue), le
 * plus proche d'abord : c'est lui qu'on prépare au quai.
 */
export function arriveesSemaine(commandes: readonly CommandeResume[], aujourdhui: string): CommandeResume[] {
  const debut = ajouterJours(aujourdhui, -1)
  const fin = ajouterJours(aujourdhui, 7)
  return commandes
    .filter((c) => {
      const a = arriveeDe(c)
      return c.parti && !estClos(c) && a !== '' && a >= debut && a <= fin
    })
    .sort((a, b) => arriveeDe(a).localeCompare(arriveeDe(b)) || a.id - b.id)
}
