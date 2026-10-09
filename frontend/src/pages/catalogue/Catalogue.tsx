/**
 * « Matières, classification, fournisseurs » (`/catalogue?onglet=matieres|classification|fournisseurs`),
 * le référentiel des achats. Les fiches s'ouvrent en fenêtre par-dessus leur liste, à adresse
 * stable (R1) : `/matieres/:id`, `/matieres/nouvelle`, `/fournisseurs/:id`, `/fournisseurs/nouveau`,
 * `/catalogue/tableur` ; fermer rend la liste avec son onglet, sa recherche et ses filtres. Les
 * anciennes adresses de Gestion MP (`?matiere=12`, `?fournisseur=3`, `?fournisseur_filtre=3`)
 * mènent aux nouvelles.
 *
 * Direction et achats : les trois onglets. Alimentation : les matières, en lecture, sans prix.
 */
import { useCallback, useEffect } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { ongletsPermis } from '../../lib/droits'
import { useSession } from '../../lib/session'
import type { Role } from '../../lib/types'
import { ECRANS } from '../../routes'
import { useClassification, useFournisseurs, useMatieres } from './donnees'
import { FicheFournisseur } from './FicheFournisseur'
import { FicheMatiere } from './FicheMatiere'
import { OngletClassification } from './OngletClassification'
import { OngletFournisseurs } from './OngletFournisseurs'
import { OngletMatieres } from './OngletMatieres'
import { Tableur } from './Tableur'
import { LISTES } from './types'

type OngletCatalogue = 'matieres' | 'classification' | 'fournisseurs'

/** Ce que l'adresse ouvre par-dessus la liste. */
export type Ouvert =
  | { genre: 'matiere'; id: number | null }
  | { genre: 'fournisseur'; id: number | null }
  | { genre: 'tableur' }
  | null

export function ouvertDe(chemin: string): Ouvert {
  const m = /^\/(matieres|fournisseurs)\/(\d+|nouvelle|nouveau)$/.exec(chemin)
  if (m) {
    const id = /^\d+$/.test(m[2] ?? '') ? Number(m[2]) : null
    return m[1] === 'matieres' ? { genre: 'matiere', id } : { genre: 'fournisseur', id }
  }
  return chemin === '/catalogue/tableur' ? { genre: 'tableur' } : null
}

/** Les paramètres de la liste dessous : sans ceux de la fiche (son onglet). */
function parametresListe(search: string, onglet: OngletCatalogue): string {
  const p = new URLSearchParams(search)
  p.delete('onglet')
  if (onglet !== 'matieres') p.set('onglet', onglet)
  const texte = p.toString()
  return texte ? `?${texte}` : ''
}

/** Les anciennes adresses de Gestion MP (R1) : la nouvelle, ou `null`. */
export function adresseNouvelle(params: URLSearchParams): string | null {
  const matiere = params.get('matiere')
  if (matiere) return `/matieres/${matiere === 'nouvelle' ? 'nouvelle' : matiere}`
  if (params.get('onglet') === 'fournisseurs' && params.get('fournisseur'))
    return `/fournisseurs/${params.get('fournisseur')}`
  const filtre = params.get('fournisseur_filtre')
  return filtre ? `/catalogue?fournisseur=${filtre}` : null
}

function useNavigationCatalogue(onglet: OngletCatalogue) {
  const navigate = useNavigate()
  const { search } = useLocation()
  const ouvrir = useCallback(
    (base: 'matieres' | 'fournisseurs' | 'catalogue/tableur', id?: number | 'nouvelle' | 'nouveau') => {
      const p = new URLSearchParams(search)
      p.delete('onglet')
      const texte = p.toString()
      navigate(`/${base}${id == null ? '' : `/${id}`}${texte ? `?${texte}` : ''}`)
    },
    [navigate, search],
  )
  const fermer = useCallback(
    () => navigate(`/catalogue${parametresListe(search, onglet)}`),
    [navigate, search, onglet],
  )
  const remplacer = useCallback(
    (adresse: string) => {
      const p = new URLSearchParams(search)
      p.delete('onglet')
      const texte = p.toString()
      navigate(`${adresse}${texte ? `?${texte}` : ''}`, { replace: true })
    },
    [navigate, search],
  )

  return { ouvrir, fermer, remplacer }
}

function useCompteurs(ecrit: boolean) {
  const matieres = useMatieres()
  const c = useClassification(ecrit)
  const fournisseurs = useFournisseurs()
  const actifs = (l: readonly { actif: boolean }[] | undefined) => l?.filter((x) => x.actif).length
  const valeurs = c.data ? LISTES.reduce((n, d) => n + (actifs(c.data[d.cle]) ?? 0), 0) : undefined
  return { matieres: actifs(matieres.data), classification: valeurs, fournisseurs: actifs(fournisseurs.data) }
}

/** La fenêtre ouverte par l'adresse, par-dessus la liste. */
function FenetreOuverte({
  ouvert,
  ecrit,
  nav,
}: {
  ouvert: Ouvert
  ecrit: boolean
  nav: ReturnType<typeof useNavigationCatalogue>
}) {
  if (ouvert?.genre === 'matiere')
    return (
      <FicheMatiere
        key={ouvert.id ?? 'nouvelle'}
        id={ouvert.id}
        ecrit={ecrit}
        onFermer={nav.fermer}
        onCree={(id) => nav.remplacer(`/matieres/${id}`)}
      />
    )
  if (!ecrit) return null
  if (ouvert?.genre === 'fournisseur')
    return (
      <FicheFournisseur
        key={ouvert.id ?? 'nouveau'}
        id={ouvert.id}
        onFermer={nav.fermer}
        onCree={(id) => nav.remplacer(`/fournisseurs/${id}`)}
      />
    )
  return ouvert?.genre === 'tableur' ? <Tableur onFermer={nav.fermer} /> : null
}

const LIBELLES: Record<OngletCatalogue, string> = {
  matieres: 'Matières',
  classification: 'Classification',
  fournisseurs: 'Fournisseurs',
}

/** L'onglet de la liste : celui de l'adresse, ou celui que la fiche ouverte impose. */
function useOnglet(role: Role, ouvert: Ouvert) {
  const [params] = useSearchParams()
  const ecran = ECRANS.find((e) => e.chemin === '/catalogue')
  const permis = (ecran ? ongletsPermis(ecran, role) : [])
    .map((o) => o.cle)
    .filter((c): c is OngletCatalogue => c in LIBELLES)
  const demande = permis.find((p) => p === params.get('onglet')) ?? 'matieres'
  const onglet: OngletCatalogue = ouvert
    ? ouvert.genre === 'fournisseur'
      ? 'fournisseurs'
      : 'matieres'
    : demande
  return { permis, onglet }
}

export default function Catalogue() {
  const { role } = useSession()
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const ecrit = role === 'direction' || role === 'achats'
  const ouvert = ouvertDe(pathname)
  const { permis, onglet } = useOnglet(role, ouvert)
  const nav = useNavigationCatalogue(onglet)
  const navigate = useNavigate()
  const compteurs = useCompteurs(ecrit)
  const ancienne = adresseNouvelle(params)
  useEffect(() => {
    if (ancienne) navigate(ancienne, { replace: true })
  }, [ancienne, navigate])
  const choisir = (o: OngletCatalogue) =>
    navigate(`/catalogue${parametresListe(params.toString(), o)}`, { replace: true })
  return (
    <Page titre="Matières, classification, fournisseurs">
      <EnTete
        titre="Matières, classification, fournisseurs"
        sous="Le référentiel des achats : une nouvelle matière se crée ici, sa référence composée à partir de la classification. On ne supprime pas ce qui a un historique : on le désactive."
      />
      <Onglets<OngletCatalogue>
        libelle="Onglets du catalogue"
        actif={onglet}
        onChange={choisir}
        onglets={permis.map((cle) => ({
          cle,
          libelle: LIBELLES[cle],
          compte: compteurs[cle],
        }))}
      />
      {onglet === 'matieres' ? (
        <OngletMatieres
          voitPrix={ecrit}
          ecrit={ecrit}
          onOuvrir={(id) => nav.ouvrir('matieres', id)}
          onTableur={() => nav.ouvrir('catalogue/tableur')}
        />
      ) : null}
      {onglet === 'classification' && ecrit ? (
        <OngletClassification direction={role === 'direction'} />
      ) : null}
      {onglet === 'fournisseurs' && ecrit ? (
        <OngletFournisseurs onOuvrir={(id) => nav.ouvrir('fournisseurs', id)} />
      ) : null}
      <FenetreOuverte ouvert={ouvert} ecrit={ecrit} nav={nav} />
    </Page>
  )
}
