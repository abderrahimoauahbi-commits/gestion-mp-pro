/**
 * Inventaire (`/inventaire?onglet=cours|passes`, ECRANS-PRO partie 6 ; direction, achats) : les
 * inventaires en cours de comptage et les inventaires clos (validés, abandonnés, annulés), avec
 * recherche et filtre d'état dans l'adresse, export. Les fenêtres s'ouvrent par-dessus, à adresse
 * stable : `/inventaires/nouveau` (ouvrir) et `/inventaires/:id` (comptage). Sous une fiche, la
 * liste montre l'onglet de son état ; fermer y revient, recherche et filtre gardés.
 */
import type { UseQueryResult } from '@tanstack/react-query'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { avecParametre } from '../../lib/adresse'
import type { ErreurApi } from '../../lib/api'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { colonnesInventaires } from './colonnes'
import { Comptage } from './Comptage'
import { OuvrirInventaire } from './OuvrirInventaire'
import { statutInventaire, type InventaireResume } from './types'

type OngletListe = 'cours' | 'passes'

export const SOUS_TITRE =
  'On fige le stock théorique, on compte lot par lot, on valide : chaque écart devient un ajustement de stock tracé. Au-delà de la tolérance, un écart se justifie.'

const ongletDe = (statut: string | undefined): OngletListe =>
  statut && statut !== 'ouvert' ? 'passes' : 'cours'

/** L'onglet de la liste : celui de l'adresse, ou celui de l'état de la fiche ouverte dessus. */
function useOngletListe(liste: readonly InventaireResume[] | undefined, ficheId: number | null) {
  const [params, setParams] = useSearchParams()
  const demande = params.get('onglet')
  const fiche = ficheId == null ? undefined : liste?.find((i) => i.id === ficheId)
  const onglet: OngletListe =
    ficheId != null ? ongletDe(fiche?.statut) : demande === 'passes' ? 'passes' : 'cours'
  const choisir = (o: OngletListe) =>
    setParams((p) => avecParametre(p, 'onglet', o === 'cours' ? null : o), { replace: true })
  return [onglet, choisir] as const
}

/** Les adresses des fenêtres, recherche et filtre d'état gardés. */
function useFenetres(onglet: OngletListe) {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const suite = (o: OngletListe | null) => {
    const p = avecParametre(params, 'onglet', o === 'passes' ? 'passes' : null)
    const texte = p.toString()
    return texte ? `?${texte}` : ''
  }
  return {
    ouvrir: (id: number | 'nouveau') => navigate(`/inventaires/${id}${suite(onglet)}`),
    fermer: () => navigate(`/inventaire${suite(onglet)}`),
    ouvert: (id: number) => navigate(`/inventaires/${id}`),
  }
}

/** La liste d'un onglet : recherche et filtre d'état (onglet des clos), export, ligne qui ouvre la fiche. */
function Liste({
  onglet,
  liste,
  ouvrir,
}: {
  onglet: OngletListe
  liste: UseQueryResult<InventaireResume[], ErreurApi>
  ouvrir: (id: number) => void
}) {
  const { moi } = useSession()
  const etat = useEtatTableAdresse(['etat'])
  const tous = liste.data ?? []
  const lignes = tous.filter((i) => (onglet === 'cours') === (i.statut === 'ouvert'))
  const titre = onglet === 'cours' ? 'Inventaires en cours' : 'Inventaires clos'
  return (
    <Carte titre={titre} remplir serre>
      {liste.isPending ? <Chargement quoi="les inventaires" /> : null}
      {liste.isError ? <Erreur erreur={liste.error} onReessayer={() => void liste.refetch()} /> : null}
      {liste.data ? (
        <DataTable
          libelle={titre}
          lignes={lignes}
          colonnes={colonnesInventaires(onglet, moi.voit_prix)}
          cle={(i) => i.id}
          cliquable={(i) => ouvrir(i.id)}
          recherche={onglet === 'passes' ? etat.recherche : false}
          choix={etat.choix}
          placeholder="Numéro, libellé, magasin, personne…"
          rechercheCachee={(i) => [i.cree_par, i.valide_par, i.abandonne_par, i.annule_par, i.perimetre]}
          filtres={
            onglet === 'passes'
              ? [
                  {
                    cle: 'etat',
                    libelle: 'État',
                    valeur: (i) => i.statut,
                    libelleValeur: (v) => statutInventaire(v).libelle,
                  },
                ]
              : []
          }
          exporter={{
            route: '/export/inventaires',
            parametres: { statut: onglet === 'cours' ? 'ouvert' : (etat.choix.valeurs.etat ?? undefined) },
          }}
          vide={
            onglet === 'cours'
              ? 'Aucun inventaire en cours. « Ouvrir un inventaire » fige le stock d’un périmètre pour le compter.'
              : 'Aucun inventaire clos.'
          }
        />
      ) : null}
    </Carte>
  )
}

export default function Inventaire() {
  const { pathname } = useLocation()
  const { id } = useParams()
  const nouveau = pathname === '/inventaires/nouveau'
  const ficheId = id && /^\d+$/.test(id) ? Number(id) : null
  const liste = useLecture<InventaireResume[]>('/inventaires')
  const [onglet, choisir] = useOngletListe(liste.data, ficheId)
  const fenetres = useFenetres(onglet)
  const tous = liste.data ?? []
  const enCours = tous.filter((i) => i.statut === 'ouvert')
  const clos = tous.filter((i) => i.statut !== 'ouvert')
  return (
    <Page titre="Inventaire">
      <EnTete
        titre="Inventaire"
        sous={SOUS_TITRE}
        actions={
          <Bouton variante="principal" icone="plus" onClick={() => fenetres.ouvrir('nouveau')}>
            Ouvrir un inventaire
          </Bouton>
        }
      />
      <Onglets
        libelle="Onglets de l’inventaire"
        actif={onglet}
        onChange={choisir}
        onglets={[
          { cle: 'cours', libelle: 'En cours de comptage', compte: liste.data ? enCours.length : null },
          {
            cle: 'passes',
            libelle: 'Inventaires clos : validés, abandonnés et annulés',
            court: 'Inventaires clos',
            compte: liste.data ? clos.length : null,
          },
        ]}
      />
      {onglet === 'cours' ? (
        <Note>
          Tant qu’un inventaire est ouvert, les matières qu’il compte ne bougent plus dans son magasin (dans
          tous les magasins s’il est global) : réceptions, sorties, transferts et retours de ces matières
          attendent. Les autres matières continuent de bouger. Valider ou abandonner l’inventaire rend la
          main.
        </Note>
      ) : null}
      <Liste onglet={onglet} liste={liste} ouvrir={fenetres.ouvrir} />
      {nouveau ? (
        <OuvrirInventaire
          onFermer={fenetres.fermer}
          onOuvert={(i) => {
            dire('Inventaire ouvert : le théorique est figé.')
            fenetres.ouvert(i)
          }}
        />
      ) : null}
      {ficheId != null ? <Comptage id={ficheId} onFermer={fenetres.fermer} /> : null}
    </Page>
  )
}
