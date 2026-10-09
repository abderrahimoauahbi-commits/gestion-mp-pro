/**
 * Cockpit › « Ce qui attend une action », sans écran : la liste de Gestion MP (rouges, approbations,
 * retards, prix, réceptions, ordres et opérations en brouillon, inventaires, besoins, réclamations,
 * contrôles), dans cet ordre, avec les mêmes comptes, tons et textes ; puis l'état des sauvegardes.
 * Le compte de l'onglet est la somme des comptes affichés (une sauvegarde en défaut compte pour un).
 */
import { messageErreur } from '../../lib/api'
import { date, horodatage, montant, nombre } from '../../lib/format'
import type { Role } from '../../lib/types'
import { prixAConfirmer } from '../commandes/liste'
import {
  besoinsTries,
  brouillonsVisibles,
  quelques,
  siPermis,
  unOuListe,
  type Tache,
} from '../accueil/taches'
import type {
  Brouillons,
  Cockpit,
  CommandeResume,
  EtatSauvegardes,
  InventaireResume,
  ReclamationResume,
  SignalementFiche,
} from '../accueil/types'

export interface SourcesCockpit {
  role: Role
  cockpit: Cockpit
  commandes: readonly CommandeResume[]
  retards: readonly CommandeResume[]
  brouillons?: Brouillons
  inventaires: readonly InventaireResume[]
  besoins: readonly SignalementFiche[]
  reclamations: readonly ReclamationResume[]
}

/** Le montant d'un bon en MAD : celui des prix confirmés, sinon l'estimation au catalogue. */
export function montantMad(c: CommandeResume): { valeur: number; estime: boolean } {
  if (c.montant_mad > 0 || !c.montant_estime_mad) return { valeur: c.montant_mad, estime: false }
  return { valeur: c.montant_estime_mad, estime: true }
}

export const aApprouver = (commandes: readonly CommandeResume[]) =>
  commandes.filter((c) => c.statut === 'a_approuver')

const numero = (c: CommandeResume) => c.numero ?? 'À approuver'
const trois = <T>(l: readonly T[], t: (x: T) => string) => quelques(l, t, 3, ', ')

function commandes(s: SourcesCockpit): Tache[] {
  const { role, retards } = s
  const approuver = aApprouver(s.commandes)
  const prix = s.commandes.filter(prixAConfirmer)
  const fiche = (l: readonly CommandeResume[]) => () => `/commandes/${l[0]?.id}`
  const estime = (c: CommandeResume) => {
    const m = montantMad(c)
    return `${montant(m.valeur, 'MAD')}${m.estime ? ' estimé' : ''}`
  }
  return [
    {
      cle: 'approuver',
      compte: approuver.length,
      ton: 'attention',
      titre: 'Commandes à approuver',
      detail: trois(approuver, (c) => `${c.fournisseur}, ${estime(c)}`),
      vers: unOuListe(role, approuver.length, fiche(approuver), '/commandes?onglet=a_approuver'),
      lien: 'Commandes',
    },
    {
      cle: 'retards',
      compte: retards.length,
      ton: 'attention',
      titre: 'Commandes en retard de livraison',
      detail: trois(retards, (c) => `${numero(c)} (${c.fournisseur})`),
      vers: unOuListe(role, retards.length, fiche(retards), '/commandes?filtre=retard'),
      lien: 'Commandes',
    },
    {
      cle: 'prix',
      compte: prix.length,
      ton: 'attention',
      titre: 'Commandes dont les prix restent à confirmer',
      detail: trois(prix, (c) => `${numero(c)} (${c.fournisseur})`),
      vers: unOuListe(role, prix.length, fiche(prix), '/commandes?onglet=envoyee'),
      lien: 'Commandes',
    },
  ]
}

function brouillons(s: SourcesCockpit): Tache[] {
  const { role } = s
  const tous = brouillonsVisibles(role, s.brouillons)
  const de = (g: string) => tous.filter((x) => x.genre === g)
  const rec = de('reception')
  const ord = de('ordre')
  const ops = de('operation')
  const du = (x: (typeof tous)[number]) => `${x.resume || x.libelle} du ${date(x.date)}`
  const un = (l: typeof tous, liste: string) => unOuListe(role, l.length, () => l[0]?.lien ?? '', liste)
  return [
    {
      cle: 'receptions',
      compte: rec.length,
      ton: 'attention',
      titre: 'Réceptions en brouillon',
      detail: rec.length
        ? `Pesées non validées : la matière n'est pas encore en stock. ${trois(rec, du)}`
        : '',
      vers: un(rec, '/receptions?onglet=brouillon'),
      lien: 'Réceptions',
    },
    {
      cle: 'ordres',
      compte: ord.length,
      ton: 'attention',
      titre: 'Ordres de fabrication en brouillon',
      detail: ord.length ? `Fil préparé mais pas encore sorti du stock. ${trois(ord, du)}` : '',
      vers: un(ord, '/sorties?onglet=brouillon'),
      lien: 'Sorties',
    },
    {
      cle: 'operations',
      compte: ops.length,
      ton: 'attention',
      titre: 'Ouvertures, transferts, ajustements ou retours en brouillon',
      detail: trois(ops, (x) => `${x.libelle} du ${date(x.date)}`),
      vers: un(ops, `/operations?onglet=${ops[0]?.type ?? 'transfert'}`),
      lien: 'Opérations',
    },
  ]
}

function suite(s: SourcesCockpit): Tache[] {
  const { role, inventaires, reclamations, cockpit } = s
  const besoins = besoinsTries(s.besoins)
  const c = cockpit.controles
  return [
    {
      cle: 'inventaires',
      compte: inventaires.length,
      ton: 'critique',
      titre:
        inventaires.length > 1
          ? 'Inventaires ouverts : magasins à l’arrêt'
          : 'Inventaire ouvert : magasin à l’arrêt',
      detail: inventaires
        .map(
          (i) =>
            `${i.numero} · ${i.magasin || 'tous les magasins'} : ${nombre(i.nb_comptees)} / ${nombre(
              i.nb_lignes,
            )} lots comptés — aucune réception, sortie ni transfert ne passe dans ce magasin avant sa validation ou son abandon`,
        )
        .join(' · '),
      vers: unOuListe(role, inventaires.length, () => `/inventaires/${inventaires[0]?.id}`, '/inventaire'),
      lien: 'Inventaire',
    },
    {
      cle: 'besoins',
      compte: besoins.length,
      ton: besoins.some((b) => b.urgence === 'urgente') ? 'critique' : 'attention',
      titre: 'Besoins signalés par l’atelier, non traités',
      detail: trois(besoins, (b) => `${b.reference ? `${b.reference} : ` : ''}${b.texte}`),
      vers: null,
      besoin: besoins[0],
    },
    {
      cle: 'reclamations',
      compte: reclamations.length,
      ton: 'attention',
      titre: 'Réclamations ouvertes chez les fournisseurs',
      detail: trois(reclamations, (r) => `${r.fournisseur} · ${r.motif_libelle || r.motif}`),
      vers: unOuListe(
        role,
        reclamations.length,
        () => `/reclamations/${reclamations[0]?.id}`,
        '/receptions?onglet=reclamations',
      ),
      lien: 'Réclamations',
    },
    {
      cle: 'controles',
      compte: c.a_corriger,
      ton: c.bloquants ? 'critique' : 'attention',
      titre: 'Contrôles en anomalie',
      detail: c.bloquants
        ? `${nombre(c.bloquants)} bloquant(s) : le pilotage en est faussé.`
        : 'Chaque contrôle dit quoi faire.',
      vers: siPermis(role, '/analyse?onglet=controles'),
      lien: 'Contrôles',
    },
  ]
}

/** Les tâches du Cockpit qui ont un compte, dans l'ordre de Gestion MP. */
export function actionsCockpit(s: SourcesCockpit): Tache[] {
  const { role, cockpit } = s
  const rouges: Tache = {
    cle: 'rouges',
    compte: cockpit.alerte_rouge,
    ton: 'critique',
    titre: 'Matières en rupture ou critiques',
    detail: "À commander sans attendre : le plan d'achat dit quoi, à qui, combien.",
    vers: siPermis(role, '/plan-achat'),
    lien: "Plan d'achat",
  }
  return [rouges, ...commandes(s), ...brouillons(s), ...suite(s)].filter((t) => Number(t.compte) > 0)
}

/** La ligne des sauvegardes : à jour, à vérifier (plus de 26 h, alerte du serveur) ou illisible. */
export function tacheSauvegarde(
  role: Role,
  etat: EtatSauvegardes | undefined,
  erreur: unknown,
): { tache: Tache; enAlerte: boolean } | null {
  const vers = siPermis(role, '/administration?onglet=sauvegardes')
  const base = { cle: 'sauvegarde', vers, lien: 'Sauvegardes' }
  if (erreur)
    return {
      tache: {
        ...base,
        compte: '!',
        ton: 'critique',
        titre: 'Sauvegardes : état illisible',
        detail: messageErreur(erreur),
      },
      enAlerte: true,
    }
  if (!etat) return null
  const enAlerte = Boolean(etat.alerte) || !(etat.age_h != null && etat.age_h <= 26)
  const detail =
    etat.alerte ||
    (etat.derniere
      ? `Dernière sauvegarde le ${horodatage(etat.derniere)} (il y a ${nombre(etat.age_h ?? 0)} h) · ${nombre(etat.nb)} conservée(s).`
      : "Aucune sauvegarde n'a encore été faite.")
  return {
    tache: {
      ...base,
      compte: enAlerte ? '!' : '✓',
      ton: enAlerte ? 'critique' : 'ok',
      titre: enAlerte ? 'Sauvegarde à vérifier' : 'Sauvegarde à jour',
      detail,
    },
    enAlerte,
  }
}

/** Le compte de l'onglet « À faire et à valider » : la somme des comptes, plus la sauvegarde en défaut. */
export function totalAFaire(actions: readonly Tache[], sauvegardeEnAlerte: boolean): number {
  return (
    actions.reduce((n, t) => n + (typeof t.compte === 'number' ? t.compte : 0), 0) +
    (sauvegardeEnAlerte ? 1 : 0)
  )
}
