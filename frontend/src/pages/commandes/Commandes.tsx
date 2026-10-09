/**
 * Commandes (`/commandes?onglet=brouillon|a_approuver|envoyee|confirmee|clos&filtre=retard&q=`,
 * ECRANS-PRO 4.5–4.14 ; direction, achats). Les fiches s'ouvrent en fenêtre par-dessus la liste, à
 * adresse stable : `/commandes/:id?onglet=…`, `/commandes/nouvelle` (et `?fournisseur=ID` pour la
 * préparation, en pile). Fermer rend la liste avec son onglet, sa recherche et ses filtres. Les
 * anciens liens de Gestion MP (`?ouvrir=ID`, `?commande=ID`) mènent aux nouveaux.
 */
import { useEffect, useMemo } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Bouton } from '../../composants/saisie/Bouton'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { champsCherches } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { passe, trouve } from '../../composants/tableaux/filtrage'
import { nombre } from '../../lib/format'
import { useSession } from '../../lib/session'
import styles from '../plan-achat/achats.module.css'
import { Preparation } from '../plan-achat/Preparation'
import { useApresCreation } from '../plan-achat/apresCreation'
import { CHERCHES, colonnesCommandes, filtresCommandes } from './colonnesCommandes'
import { useListeEtFiches, useOngletListe } from './adresse'
import { useCommandes } from './donnees'
import { FicheCommande } from './FicheCommande'
import { IndicateursCommandes } from './IndicateursCommandes'
import {
  enRetard,
  LIBELLES_ONGLETS,
  ongletDe,
  ONGLETS_COMMANDES,
  premierOnglet,
  type OngletCommandes,
} from './liste'
import { NouvelleCommande } from './NouvelleCommande'
import type { CommandeResume } from './types'

const VIDES: Record<OngletCommandes, string> = {
  brouillon: 'Aucun brouillon. Préparez un bon depuis le plan d’achat ou avec « Nouvelle commande ».',
  a_approuver: 'Aucun bon ici.',
  envoyee: 'Aucun bon ici.',
  confirmee: 'Aucun bon ici.',
  clos: 'Aucun bon ici.',
}

/** Les anciennes adresses de Gestion MP (`?ouvrir=ID`, `?commande=ID`) : la nouvelle, ou `null`. */
export function adresseNouvelle(pathname: string, params: URLSearchParams): string | null {
  if (pathname !== '/commandes') return null
  const id = params.get('ouvrir') ?? params.get('commande')
  return id && /^\d+$/.test(id) ? `/commandes/${id}` : null
}

const JETABLES = ['fournisseur'] as const

function useNavigationCommandes() {
  const { ouvrir, fermer } = useListeEtFiches('/commandes', JETABLES)
  return {
    ouvrir: (c: CommandeResume, volet?: string) => ouvrir(`/commandes/${c.id}`, volet),
    fermer,
    nouvelle: () => ouvrir('/commandes/nouvelle'),
    preparer: (fid: number) => ouvrir('/commandes/nouvelle', undefined, { fournisseur: String(fid) }),
    retourNouvelle: () => ouvrir('/commandes/nouvelle'),
  }
}

/** Ce que l'adresse ouvre par-dessus la liste. */
function FenetresOuvertes({ nav }: { nav: ReturnType<typeof useNavigationCommandes> }) {
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const id = Number(useParams().id)
  const cree = useApresCreation()
  const fournisseur = Number(params.get('fournisseur')) || null
  if (pathname === '/commandes/nouvelle')
    return (
      <>
        <NouvelleCommande onFermer={nav.fermer} onPreparer={nav.preparer} />
        {fournisseur ? (
          <Preparation fournisseurId={fournisseur} onFermer={nav.retourNouvelle} onCree={cree} />
        ) : null}
      </>
    )
  return id ? <FicheCommande key={id} id={id} onFermer={nav.fermer} /> : null
}

/** L'état de la liste : filtres, recherche, onglet, comptes par onglet (sur la recherche). */
function useListe(bons: readonly CommandeResume[]) {
  const [params, setParams] = useSearchParams()
  const nav = useNavigationCommandes()
  const etat = useEtatTableAdresse(['fournisseur', 'devise', 'livraison', 'filtre'])
  const retard = params.get('filtre') === 'retard'
  const noms = useMemo(() => new Map(bons.map((c) => [String(c.fournisseur_id), c.fournisseur])), [bons])
  const filtres = useMemo(() => filtresCommandes(noms), [noms])
  const colonnes = useMemo(() => colonnesCommandes(nav.ouvrir), [nav.ouvrir])
  const retenus = useMemo(() => (retard ? bons.filter(enRetard) : bons), [bons, retard])
  const q = etat.recherche.valeur
  const trouves = useMemo(
    () =>
      retenus.filter(
        (c) => passe(c, filtres, etat.choix.valeurs) && trouve(champsCherches(colonnes, c, CHERCHES), q),
      ),
    [retenus, filtres, etat.choix.valeurs, colonnes, q],
  )
  const [onglet, choisir] = useOngletListe<OngletCommandes>(
    '/commandes',
    ONGLETS_COMMANDES,
    premierOnglet(trouves),
  )
  const lignes = useMemo(() => retenus.filter((c) => ongletDe(c) === onglet), [retenus, onglet])
  const compte = (o: OngletCommandes) => trouves.filter((c) => ongletDe(c) === o).length
  const poserRetard = (v: boolean) =>
    setParams(
      (p) => {
        const s = new URLSearchParams(p)
        if (v) s.set('filtre', 'retard')
        else s.delete('filtre')
        return s
      },
      { replace: true },
    )
  return { nav, etat, retard, filtres, colonnes, trouves, onglet, choisir, lignes, compte, poserRetard, q }
}

function Liste({ bons }: { bons: readonly CommandeResume[] }) {
  const { nav, etat, retard, filtres, colonnes, trouves, onglet, choisir, lignes, compte, poserRetard, q } =
    useListe(bons)
  return (
    <>
      <Onglets<OngletCommandes>
        libelle="Onglets des commandes"
        actif={onglet}
        onChange={choisir}
        onglets={ONGLETS_COMMANDES.map((o) => ({
          cle: o,
          libelle: LIBELLES_ONGLETS[o].libelle,
          compte: compte(o),
        }))}
        apres={
          q.trim() ? (
            <span className={styles.note}>{nombre(trouves.length)} bon(s) trouvé(s), tous onglets</span>
          ) : null
        }
      />
      <Carte
        titre={<span title={LIBELLES_ONGLETS[onglet].aide}>{LIBELLES_ONGLETS[onglet].libelle}</span>}
        serre
        remplir
        className={styles.carteListe}
      >
        <DataTable<CommandeResume>
          libelle={`Commandes — ${LIBELLES_ONGLETS[onglet].libelle}`}
          lignes={lignes}
          colonnes={colonnes}
          filtres={filtres}
          cle={(c) => c.id}
          recherche={etat.recherche}
          choix={etat.choix}
          rechercheCachee={CHERCHES}
          placeholder="N°, fournisseur, référence, conteneur…"
          cliquable={(c) => nav.ouvrir(c)}
          exporter={{
            route: '/export/commandes',
            parametres: { statut: onglet, filtre: retard ? 'retard' : undefined },
          }}
          outils={<Interrupteur valeur={retard} onChange={poserRetard} libelle="En retard seulement" />}
          vide={q.trim() ? 'Aucun bon de cet onglet ne correspond (voir les autres onglets).' : VIDES[onglet]}
        />
      </Carte>
    </>
  )
}

export default function Commandes() {
  const { role } = useSession()
  const lu = useCommandes()
  const nav = useNavigationCommandes()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const ancienne = adresseNouvelle(pathname, params)
  useEffect(() => {
    if (ancienne) navigate(ancienne, { replace: true })
  }, [ancienne, navigate])
  return (
    <Page titre="Commandes">
      <EnTete
        titre="Commandes"
        sous="Un bon part sans prix, le fournisseur les confirme, puis il est reçu. Tant que rien n’est reçu, il se modifie."
        actions={
          <Bouton variante="principal" icone="plus" onClick={nav.nouvelle}>
            Nouvelle commande
          </Bouton>
        }
      />
      {lu.isError ? <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} /> : null}
      {lu.isPending ? <Chargement quoi="les commandes" /> : null}
      {lu.data ? <IndicateursCommandes bons={lu.data} role={role} /> : null}
      {lu.data ? <Liste bons={lu.data} /> : null}
      <FenetresOuvertes nav={nav} />
    </Page>
  )
}
