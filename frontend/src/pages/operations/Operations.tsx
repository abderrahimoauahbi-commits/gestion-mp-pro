/**
 * Ouvertures, transferts, ajustements (`/operations?onglet=…&q=&etat=`, ECRANS-PRO partie 6) : un
 * onglet par type d'opération (l'alimentation ne voit que les transferts et les retours des
 * machines), liste paginée au serveur avec recherche et filtre d'état gardés au changement
 * d'onglet (an. 23), « Tout valider… », export. La fenêtre d'une opération s'ouvre à adresse
 * stable : `/operations/:id` (lue directement, pose l'onglet de son type, an. 13–14) et
 * `/operations/nouvelle?type=` ; après le premier enregistrement, `/operations/:id` (an. 22).
 */
import { useState } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { avecParametre } from '../../lib/adresse'
import { ongletsPermis, permis } from '../../lib/droits'
import { nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { statut } from '../../lib/statuts'
import { ecranParChemin } from '../../routes'
import { colonnesOperations } from './colonnes'
import { FenetreOperation } from './FenetreOperation'
import { NouveauRetour } from './NouveauRetour'
import {
  NOTES,
  NOUVEAU,
  peutSaisir,
  TYPES,
  type Motifs,
  type OperationFiche,
  type TypeOperation,
} from './types'

export const SOUS_TITRE =
  'Chaque geste de stock a son document : ouvertures, transferts (dont quarantaine), ajustements, retours au fournisseur et retours des machines. Un brouillon se corrige ; validé, le stock bouge ; une opération validée ne s’efface pas, elle s’annule par une écriture inverse.'

const estType = (v: string | null | undefined): v is TypeOperation => TYPES.some((t) => t === v)

/** L'onglet : celui de l'adresse, ou le type de la fiche ouverte dessus (an. 13). */
function useOnglet(permisDuRole: readonly TypeOperation[], typeDeLaFiche: TypeOperation | null) {
  const [params, setParams] = useSearchParams()
  const demande = params.get('onglet')
  const premier = permisDuRole[0] ?? 'transfert'
  const onglet: TypeOperation =
    typeDeLaFiche ?? (estType(demande) && permisDuRole.includes(demande) ? demande : premier)
  const choisir = (o: TypeOperation) =>
    setParams((p) => avecParametre(p, 'onglet', o === premier ? null : o), { replace: true })
  return [onglet, choisir] as const
}

/** La fiche ouverte (`/operations/:id`, `/operations/nouvelle?type=`) et son type. */
function useFiche() {
  const { pathname } = useLocation()
  const { id } = useParams()
  const [params] = useSearchParams()
  const nouvelle = pathname === '/operations/nouvelle'
  const ficheId = id && /^\d+$/.test(id) ? Number(id) : null
  const lue = useLecture<OperationFiche>(ficheId == null ? null : `/operations/${ficheId}`)
  const typeNouveau = params.get('type')
  const type = nouvelle && estType(typeNouveau) ? typeNouveau : (lue.data?.type ?? null)
  return { nouvelle, ficheId, type }
}

/** Les adresses de la liste et des fenêtres, recherche et filtre gardés. */
function useAdresses(onglet: TypeOperation, premier: TypeOperation) {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const suite = (modif: Record<string, string | null>) => {
    let p = new URLSearchParams(params)
    for (const [cle, valeur] of Object.entries(modif)) p = avecParametre(p, cle, valeur)
    const texte = p.toString()
    return texte ? `?${texte}` : ''
  }
  const ongletListe = onglet === premier ? null : onglet
  return {
    ouvrir: (id: number) => navigate(`/operations/${id}${suite({ onglet: null, type: null })}`),
    nouvelle: (type: TypeOperation) => navigate(`/operations/nouvelle${suite({ onglet: null, type })}`),
    fermer: () => navigate(`/operations${suite({ onglet: ongletListe, type: null })}`),
    cree: (id: number) =>
      navigate(`/operations/${id}${suite({ onglet: null, type: null })}`, { replace: true }),
  }
}

/** Les gestes de l'en-tête : « Tout valider… (N) » et « Nouveau … » de l'onglet. */
function Actions({
  onglet,
  nouvelle,
  retour,
}: {
  onglet: TypeOperation
  nouvelle: () => void
  retour: () => void
}) {
  const { role } = useSession()
  const navigate = useNavigate()
  const motifs = useLecture<Motifs>('/motifs')
  const brouillons = useLecture<{ nombre: number }>('/brouillons')
  const n = brouillons.data?.nombre
  return (
    <>
      {permis(role, '/stock?onglet=a-valider') ? (
        <Bouton
          onClick={() => navigate('/stock?onglet=a-valider')}
          titre="Tous les brouillons (ordres et opérations), avec ce qui les bloquerait, et « Tout valider »"
        >
          Tout valider…{n != null ? ` (${nombre(n)})` : ''}
        </Bouton>
      ) : null}
      {peutSaisir(motifs.data, onglet, role) ? (
        <Bouton variante="principal" icone="plus" onClick={onglet === 'retour_machine' ? retour : nouvelle}>
          {NOUVEAU[onglet]}
        </Bouton>
      ) : null}
    </>
  )
}

function Liste({ onglet, ouvrir }: { onglet: TypeOperation; ouvrir: (id: number) => void }) {
  const { role, moi } = useSession()
  const etat = useEtatTableAdresse(['etat'])
  const filtreEtat = etat.choix.valeurs.etat
  const liste = useListePaginee<OperationFiche>('/operations', {
    type: onglet,
    statut: filtreEtat || undefined,
    q: etat.recherche.valeur.trim() || undefined,
  })
  if (liste.requete.isError)
    return <Erreur erreur={liste.requete.error} onReessayer={() => void liste.requete.refetch()} />
  return (
    <DataTable
      libelle="Opérations"
      serveur
      lignes={liste.lignes}
      total={liste.total}
      chargerPlus={liste.chargerPlus}
      colonnes={colonnesOperations(onglet, moi.voit_prix, (a) => permis(role, a))}
      cle={(o) => o.id}
      cliquable={(o) => ouvrir(o.id)}
      marquee={(o) => o.statut === 'brouillon' && o.blocages.length > 0}
      recherche={etat.recherche}
      choix={etat.choix}
      placeholder="Numéro, référence, lot, magasin, motif, personne…"
      filtres={[
        {
          cle: 'etat',
          libelle: 'État',
          valeur: (o) => o.statut,
          options: ['brouillon', 'validee', 'annulee'],
          libelleValeur: (v) => String(statut('document', v).libelle),
        },
      ]}
      exporter={{
        route: '/export/operations',
        parametres: { type: onglet, statut: filtreEtat || undefined },
      }}
      vide={
        liste.requete.isPending
          ? 'Chargement…'
          : etat.recherche.valeur || filtreEtat
            ? 'Aucune opération ne correspond.'
            : 'Aucune opération de ce type pour l’instant.'
      }
    />
  )
}

export default function Operations() {
  const { role } = useSession()
  const ecran = ecranParChemin('/operations')
  const permisDuRole = (ecran ? ongletsPermis(ecran, role) : []).map((o) => o.cle).filter(estType)
  const fiche = useFiche()
  const [onglet, choisir] = useOnglet(permisDuRole, fiche.type)
  const adresses = useAdresses(onglet, permisDuRole[0] ?? 'transfert')
  const [retour, setRetour] = useState(false)
  const onglets = (ecran ? ongletsPermis(ecran, role) : []).filter((o) => estType(o.cle))
  return (
    <Page titre="Ouvertures, transferts, ajustements">
      <EnTete
        titre="Ouvertures, transferts, ajustements"
        sous={SOUS_TITRE}
        actions={
          <Actions
            onglet={onglet}
            nouvelle={() => adresses.nouvelle(onglet)}
            retour={() => setRetour(true)}
          />
        }
      />
      <Onglets
        libelle="Types d’opération"
        actif={onglet}
        onChange={(o) => choisir(o)}
        onglets={onglets
          .map((o) => ({ cle: o.cle, libelle: o.libelle, court: o.court }))
          .filter((o): o is { cle: TypeOperation; libelle: string; court: string | undefined } =>
            estType(o.cle),
          )}
      />
      <Note uneLigne={NOTES[onglet]}>{NOTES[onglet]}</Note>
      <Carte remplir serre>
        <Liste onglet={onglet} ouvrir={adresses.ouvrir} />
      </Carte>
      {fiche.ficheId != null || fiche.nouvelle ? (
        <FenetreOperation
          id={fiche.ficheId}
          type={fiche.type ?? onglet}
          onFermer={adresses.fermer}
          onCree={adresses.cree}
        />
      ) : null}
      {retour ? <NouveauRetour onFermer={() => setRetour(false)} /> : null}
    </Page>
  )
}
