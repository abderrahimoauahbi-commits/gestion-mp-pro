/**
 * Réceptions (`/receptions?onglet=brouillon|validee|annulee|reclamations|bobines|pesees`,
 * ECRANS-PRO 4.15–4.27 ; direction, achats) : le poste de pesée. Les fiches s'ouvrent en fenêtre
 * par-dessus la liste, à adresse stable : `/receptions/:id`, `/receptions/nouvelle` (et
 * `?brouillon=ID` pour corriger), `/reclamations/:id`, `/reclamations/nouvelle?reception=&ligne=`,
 * la courbe d'une matière `?matiere=ID`. Les anciens liens (`?ouvrir=ID`, `?reception=ID`) mènent
 * aux nouveaux.
 */
import { useEffect, useMemo } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { champsCherches } from '../../composants/tableaux/colonnes'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { trouve } from '../../composants/tableaux/filtrage'
import { nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { useListeEtFiches, useOngletListe } from '../commandes/adresse'
import styles from '../plan-achat/achats.module.css'
import { CHERCHES, colonnesReceptions } from './colonnesReceptions'
import { CourbeBobine } from './CourbeBobine'
import { useReceptions, useReceptionsTrouvees, useReclamations } from './donnees'
import { FicheReception } from './FicheReception'
import { FicheReclamation } from './FicheReclamation'
import { NouvelleReclamation } from './NouvelleReclamation'
import { OngletBobines } from './OngletBobines'
import { OngletPesees } from './OngletPesees'
import { OngletReceptions } from './OngletReceptions'
import { OngletReclamations } from './OngletReclamations'
import { SaisieReception } from './SaisieReception'
import type { PagePesees, ReceptionFiche, ReceptionResume } from './types'

const ONGLETS = ['brouillon', 'validee', 'annulee', 'reclamations', 'bobines', 'pesees'] as const
type Onglet = (typeof ONGLETS)[number]
const FILTRES = [
  'fournisseur',
  'origine',
  'facture',
  'qualite',
  'motif',
  'issue',
  'magasin',
  'fournisseur_nom',
]
/** Ce que l'onglet quitté laisse dans l'adresse et qui ne vaut pas pour le suivant. */
const PROPRES_A_L_ONGLET = [...FILTRES, 'ecarts', 'etat', 'matiere']
const JETABLES = ['brouillon', 'reception', 'ligne', 'matiere'] as const

/** Les anciennes adresses de Gestion MP : la nouvelle, ou `null`. */
export function adresseNouvelle(pathname: string, params: URLSearchParams): string | null {
  if (pathname !== '/receptions') return null
  const id = params.get('ouvrir') ?? params.get('reception')
  return id && /^\d+$/.test(id) ? `/receptions/${id}` : null
}

/** Après l'enregistrement d'un camion : ce que dit l'écran (une réception, ou une par devise). */
export function apresEnregistrement(liste: readonly ReceptionFiche[]): string {
  if (liste.length > 1)
    return `Le camion portait ${liste.length} devises : ${liste.length} réceptions enregistrées en brouillon (${liste.map((r) => r.devise).join(', ')}), chacune avec sa facture. Relisez-les puis validez-les.`
  return 'Réception enregistrée en brouillon. Relisez-la puis validez-la : la marchandise entrera en stock et la réception recevra son numéro.'
}

function useNavigationReceptions() {
  const navigate = useNavigate()
  const { ouvrir, fermer } = useListeEtFiches('/receptions', JETABLES)
  return {
    navigate,
    fermer,
    ouvrir: (id: number, volet?: string) => ouvrir(`/receptions/${id}`, volet),
    nouvelle: () => ouvrir('/receptions/nouvelle'),
    corriger: (id: number) => ouvrir('/receptions/nouvelle', undefined, { brouillon: String(id) }),
    reclamation: (id: number) => ouvrir(`/reclamations/${id}`),
    reclamer: (reception?: number) =>
      ouvrir('/reclamations/nouvelle', undefined, reception ? { reception: String(reception) } : {}),
  }
}

type Nav = ReturnType<typeof useNavigationReceptions>

function FenetresOuvertes({ nav }: { nav: Nav }) {
  const { pathname } = useLocation()
  const [params, setParams] = useSearchParams()
  const id = Number(useParams().id) || null
  const nombreDe = (cle: string) => Number(params.get(cle)) || null
  if (pathname === '/receptions/nouvelle')
    return (
      <SaisieReception
        brouillon={nombreDe('brouillon')}
        onFermer={nav.fermer}
        onEnregistrees={(liste) => {
          dire(apresEnregistrement(liste))
          const premiere = liste[0]
          if (premiere) nav.navigate(`/receptions/${premiere.id}?liste=brouillon`)
        }}
      />
    )
  if (pathname === '/reclamations/nouvelle') {
    const reception = nombreDe('reception')
    return (
      <NouvelleReclamation
        reception={reception}
        ligne={nombreDe('ligne')}
        onFermer={reception ? () => nav.ouvrir(reception) : nav.fermer}
        onCree={nav.reclamation}
      />
    )
  }
  if (pathname.startsWith('/reclamations/') && id)
    return <FicheReclamation key={id} id={id} onFermer={nav.fermer} />
  if (id)
    return (
      <FicheReception
        key={id}
        id={id}
        onFermer={nav.fermer}
        nav={{
          corriger: () => nav.corriger(id),
          reclamer: () => nav.reclamer(id),
          supprimee: nav.fermer,
          ouvrirReclamation: nav.reclamation,
        }}
      />
    )
  const matiere = nombreDe('matiere')
  if (matiere)
    return (
      <CourbeBobine
        matiereId={matiere}
        onFermer={() =>
          setParams((p) => {
            const s = new URLSearchParams(p)
            s.delete('matiere')
            return s
          })
        }
      />
    )
  return null
}

function useComptes(receptions: readonly ReceptionResume[], q: string, trouvees: ReadonlySet<number> | null) {
  const reclamations = useReclamations()
  const pesees = useLecture<PagePesees>('/receptions/pesees', { limite: 1 })
  const colonnes = useMemo(() => colonnesReceptions(() => undefined), [])
  const retenues = receptions.filter(
    (r) => !q.trim() || trouvees?.has(r.id) || trouve(champsCherches(colonnes, r, CHERCHES), q),
  )
  const par = (s: string) => retenues.filter((r) => r.statut === s).length
  return {
    brouillon: par('brouillon'),
    validee: par('validee'),
    annulee: par('annulee'),
    reclamations: reclamations.data?.filter((r) => r.statut === 'ouverte').length,
    bobines: undefined,
    pesees: pesees.data?.total,
    trouvees: retenues.length,
  }
}

const LIBELLES: Record<Onglet, { libelle: string; court?: string }> = {
  brouillon: { libelle: 'Brouillons' },
  validee: { libelle: 'Validées' },
  annulee: { libelle: 'Annulées' },
  reclamations: { libelle: 'Réclamations ouvertes', court: 'Réclamations' },
  bobines: { libelle: 'Poids des bobines', court: 'Bobines' },
  pesees: { libelle: 'Archive des pesées', court: 'Pesées' },
}

/** Les deux écritures de l'adresse de la page : changer d'onglet, ouvrir la courbe d'une matière. */
function useGestesAdresse() {
  const { pathname } = useLocation()
  const [, setParams] = useSearchParams()
  /** Changer d'onglet garde la recherche et retire les filtres de l'onglet quitté (une seule écriture). */
  const changerOnglet = (o: Onglet) =>
    setParams(
      (p) => {
        const s = new URLSearchParams(p)
        for (const c of PROPRES_A_L_ONGLET) s.delete(c)
        s.set(pathname === '/receptions' ? 'onglet' : 'liste', o)
        return s
      },
      { replace: true },
    )
  const ouvrirCourbe = (m: number) =>
    setParams((p) => {
      const s = new URLSearchParams(p)
      s.set('matiere', String(m))
      return s
    })
  return { changerOnglet, ouvrirCourbe }
}

function Contenu({ receptions, nav }: { receptions: readonly ReceptionResume[]; nav: Nav }) {
  const { role } = useSession()
  const [params] = useSearchParams()
  const etat = useEtatTableAdresse(FILTRES)
  const q = etat.recherche.valeur
  const serveur = useReceptionsTrouvees(q)
  const trouvees = useMemo(
    () => (q.trim() && serveur.data ? new Set(serveur.data.map((r) => r.id)) : null),
    [q, serveur.data],
  )
  const comptes = useComptes(receptions, q, trouvees)
  const defaut: Onglet = receptions.some((r) => r.statut === 'brouillon') ? 'brouillon' : 'validee'
  const [onglet] = useOngletListe<Onglet>('/receptions', ONGLETS, defaut)
  const ecarts = params.get('ecarts') === '1'
  const poserEcarts = (v: boolean) => etat.choix.poser('ecarts', v ? '1' : null)
  const { changerOnglet, ouvrirCourbe } = useGestesAdresse()
  return (
    <>
      <Onglets<Onglet>
        libelle="Onglets des réceptions"
        actif={onglet}
        onChange={changerOnglet}
        onglets={ONGLETS.map((o) => ({ cle: o, ...LIBELLES[o], compte: comptes[o] }))}
        apres={
          q.trim() ? (
            <span className={styles.note}>{nombre(comptes.trouvees)} trouvée(s), tous onglets</span>
          ) : null
        }
      />
      {onglet === 'brouillon' || onglet === 'validee' || onglet === 'annulee' ? (
        <OngletReceptions
          statut={onglet}
          receptions={receptions}
          trouvees={trouvees}
          etat={etat}
          onOuvrir={(r) => nav.ouvrir(r.id)}
          onCorriger={(r) => nav.corriger(r.id)}
        />
      ) : null}
      {onglet === 'reclamations' ? (
        <OngletReclamations etat={etat} onOuvrir={nav.reclamation} onNouvelle={() => nav.reclamer()} />
      ) : null}
      {onglet === 'bobines' ? (
        <OngletBobines
          etat={etat}
          role={role}
          ecarts={ecarts}
          onEcarts={poserEcarts}
          onCourbe={ouvrirCourbe}
        />
      ) : null}
      {onglet === 'pesees' ? <OngletPesees etat={etat} ecarts={ecarts} onEcarts={poserEcarts} /> : null}
    </>
  )
}

export default function Receptions() {
  const lu = useReceptions()
  const nav = useNavigationReceptions()
  const [params] = useSearchParams()
  const { pathname } = useLocation()
  const ancienne = adresseNouvelle(pathname, params)
  const { navigate } = nav
  useEffect(() => {
    if (ancienne) navigate(ancienne, { replace: true })
  }, [ancienne, navigate])
  return (
    <Page titre="Réceptions">
      <EnTete
        titre="Réceptions"
        sous="Le poste de pesée. C’est le poids pesé qui entre en stock, à la validation."
        actions={
          <Bouton variante="principal" icone="plus" onClick={nav.nouvelle}>
            Nouvelle réception
          </Bouton>
        }
      />
      {lu.isError ? <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} /> : null}
      {lu.isPending ? <Chargement quoi="les réceptions" /> : null}
      {lu.data ? <Contenu receptions={lu.data} nav={nav} /> : null}
      <FenetresOuvertes nav={nav} />
    </Page>
  )
}
