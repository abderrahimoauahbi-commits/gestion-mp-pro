/**
 * Commandes (`/commandes?onglet=brouillon|a_approuver|envoyee|confirmee|clos&filtre=retard&q=`,
 * ECRANS-PRO 4.5–4.14 ; direction, achats). La liste est **paginée au serveur** : la recherche, les
 * filtres liés (fournisseur, devise) et « en retard » sont poussés au serveur (mêmes chiffres
 * qu'avant). Les comptes par onglet, les indicateurs (tous les bons ouverts), le pied de totaux et
 * les options des filtres viennent de `/commandes/apercu`. L'état de livraison reste une colonne et
 * le filtre « en retard », mais n'est plus un mot de la recherche libre (convention PAGINATION4).
 *
 * Les fiches s'ouvrent en fenêtre par-dessus la liste, à adresse stable : `/commandes/:id?onglet=…`,
 * `/commandes/nouvelle` (et `?fournisseur=ID` pour la préparation). Fermer rend la liste avec son
 * onglet, sa recherche et ses filtres. Les anciens liens de Gestion MP (`?ouvrir=ID`, `?commande=ID`)
 * mènent aux nouveaux.
 */
import { useEffect, useMemo } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Erreur } from '../../composants/retour/Erreur'
import { Bouton } from '../../composants/saisie/Bouton'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse, type EtatTable } from '../../composants/tableaux/etatAdresse'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { kg, montant, nombre } from '../../lib/format'
import { useSession } from '../../lib/session'
import styles from '../plan-achat/achats.module.css'
import { Preparation } from '../plan-achat/Preparation'
import { useApresCreation } from '../plan-achat/apresCreation'
import { colonnesCommandes } from './colonnesCommandes'
import { useListeEtFiches, useOngletListe } from './adresse'
import { useApercuCommandes } from './donnees'
import { FicheCommande } from './FicheCommande'
import { IndicateursCommandes } from './IndicateursCommandes'
import { LIBELLES_ONGLETS, ONGLETS_COMMANDES, type OngletCommandes } from './liste'
import { NouvelleCommande } from './NouvelleCommande'
import type { ApercuCommandes, CommandeResume, OptionFournisseur } from './types'

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
const CLES_COMMANDES = ['fournisseur', 'devise'] as const

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

/** Les paramètres de la route 152 : l'onglet, « en retard », les filtres liés et la recherche. */
function parametres(onglet: OngletCommandes, retard: boolean, etat: EtatTable) {
  const choix = etat.choix.valeurs
  return {
    statut: onglet,
    filtre: retard ? 'retard' : undefined,
    fournisseur: choix.fournisseur || undefined,
    devise: choix.devise || undefined,
    q: etat.recherche.valeur.trim() || undefined,
  }
}

/** Le filtre fournisseur, dont les options (id → nom) viennent de l'aperçu du serveur. */
function filtreFournisseur(options: readonly OptionFournisseur[]): Filtre<CommandeResume> {
  const noms = new Map(options.map((o) => [String(o.id), o.nom]))
  return {
    cle: 'fournisseur',
    libelle: 'Fournisseur',
    valeur: (c) => String(c.fournisseur_id),
    libelleValeur: (v) => noms.get(v) ?? v,
    options: options.map((o) => String(o.id)),
  }
}

/** Le filtre devise, options venues de l'aperçu du serveur. */
function filtreDevise(devises: readonly string[]): Filtre<CommandeResume> {
  return { cle: 'devise', libelle: 'Devise', valeur: (c) => c.devise, options: [...devises] }
}

/** Le premier onglet qui a des bons (défaut de la liste), sinon les brouillons. */
function premierOnglet(a: ApercuCommandes | undefined): OngletCommandes {
  return (a && ONGLETS_COMMANDES.find((o) => a[o] > 0)) || 'brouillon'
}

/** Le pied du serveur : Σ kg, Σ montant par devise, Σ MAD de **tout** l'onglet (recherche comprise). */
function PiedServeur({
  colonnes,
  apercu,
}: {
  colonnes: readonly Colonne<CommandeResume>[]
  apercu?: ApercuCommandes
}) {
  const visibles = colonnes.filter((c) => !c.cache)
  const texte = (cle: string): string | null => {
    if (!apercu) return null
    if (cle === 'quantite') return kg(apercu.quantite)
    if (cle === 'montant') return apercu.montants.map((m) => montant(m.montant_estime, m.devise)).join(' · ')
    if (cle === 'montant_mad') return montant(apercu.montant_estime_mad, 'MAD')
    return null
  }
  return (
    <tr>
      {visibles.map((c, i) => {
        const v = texte(c.cle)
        return (
          <td key={c.cle} className={c.droite ? 'nombre' : undefined}>
            {v ?? (i === 0 ? 'Total' : '')}
          </td>
        )
      })}
    </tr>
  )
}

/** La liste paginée d'un onglet : sa carte, son pied et ses filtres (aperçu du serveur). */
type Vue = {
  nav: ReturnType<typeof useNavigationCommandes>
  table: EtatTable
  onglet: OngletCommandes
  retard: boolean
  liste: ReturnType<typeof useListePaginee<CommandeResume>>
  apercu?: ApercuCommandes
  colonnes: Colonne<CommandeResume>[]
  filtres: Filtre<CommandeResume>[]
  poserRetard: (v: boolean) => void
}

/** La carte de l'onglet : la liste paginée, son pied et ses filtres (aperçu du serveur). */
function CarteCommandes({ v }: { v: Vue }) {
  const { onglet, liste, apercu, colonnes, table } = v
  const q = table.recherche.valeur
  return (
    <Carte
      titre={<span title={LIBELLES_ONGLETS[onglet].aide}>{LIBELLES_ONGLETS[onglet].libelle}</span>}
      serre
      remplir
      className={styles.carteListe}
    >
      <DataTable<CommandeResume>
        libelle={`Commandes — ${LIBELLES_ONGLETS[onglet].libelle}`}
        serveur
        lignes={liste.lignes}
        total={liste.total}
        chargerPlus={liste.chargerPlus}
        colonnes={colonnes}
        filtres={v.filtres}
        cle={(c) => c.id}
        recherche={table.recherche}
        choix={table.choix}
        pied={liste.lignes.length ? <PiedServeur colonnes={colonnes} apercu={apercu} /> : undefined}
        placeholder="N°, fournisseur, référence, conteneur…"
        cliquable={(c) => v.nav.ouvrir(c)}
        exporter={{
          route: '/export/commandes',
          parametres: { statut: onglet, filtre: v.retard ? 'retard' : undefined },
        }}
        outils={<Interrupteur valeur={v.retard} onChange={v.poserRetard} libelle="En retard seulement" />}
        vide={
          liste.requete.isPending
            ? 'Chargement…'
            : q.trim()
              ? 'Aucun bon de cet onglet ne correspond (voir les autres onglets).'
              : VIDES[onglet]
        }
      />
    </Carte>
  )
}

function Liste({ defaut }: { defaut: OngletCommandes }) {
  const nav = useNavigationCommandes()
  const [params, setParams] = useSearchParams()
  const retard = params.get('filtre') === 'retard'
  const [onglet, choisir] = useOngletListe<OngletCommandes>('/commandes', ONGLETS_COMMANDES, defaut)
  const table = useEtatTableAdresse([...CLES_COMMANDES])
  const parms = parametres(onglet, retard, table)
  const liste = useListePaginee<CommandeResume>('/commandes', parms)
  const apercu = useApercuCommandes(parms).data
  const colonnes = useMemo(() => colonnesCommandes(nav.ouvrir), [nav.ouvrir])
  const filtres = useMemo<Filtre<CommandeResume>[]>(
    () => [filtreFournisseur(apercu?.fournisseurs ?? []), filtreDevise(apercu?.devises ?? [])],
    [apercu?.fournisseurs, apercu?.devises],
  )
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
  const vue: Vue = { nav, table, onglet, retard, liste, apercu, colonnes, filtres, poserRetard }
  const q = table.recherche.valeur
  return (
    <>
      <Onglets<OngletCommandes>
        libelle="Onglets des commandes"
        actif={onglet}
        onChange={choisir}
        onglets={ONGLETS_COMMANDES.map((o) => ({
          cle: o,
          libelle: LIBELLES_ONGLETS[o].libelle,
          compte: apercu ? apercu[o] : null,
        }))}
        apres={
          q.trim() ? (
            <span className={styles.note}>{nombre(apercu?.total ?? 0)} bon(s) trouvé(s), tous onglets</span>
          ) : null
        }
      />
      <CarteCommandes v={vue} />
    </>
  )
}

export default function Commandes() {
  const { role } = useSession()
  const nav = useNavigationCommandes()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const apercu = useApercuCommandes({})
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
      {apercu.isError ? <Erreur erreur={apercu.error} onReessayer={() => void apercu.refetch()} /> : null}
      {apercu.data ? <IndicateursCommandes i={apercu.data.indicateurs} role={role} /> : null}
      <Liste defaut={premierOnglet(apercu.data)} />
      <FenetresOuvertes nav={nav} />
    </Page>
  )
}
