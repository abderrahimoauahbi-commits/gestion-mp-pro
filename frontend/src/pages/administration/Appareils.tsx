/**
 * Administration › Appareils (`/administration?onglet=appareils`) : les appareils enrôlés (les
 * téléphones de l'atelier qui montrent les visages à la connexion). « Nouvel appareil » donne un
 * QR à usage unique, valable 15 minutes, à viser **depuis l'appareil** (page `/enroler`) ; un
 * appareil perdu se retire ici (ses sessions se ferment) — Tailscale le retire du réseau.
 */
import { useState } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Saisie } from '../../composants/saisie/Saisie'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api } from '../../lib/api'
import { horodatage, nombre } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import styles from './administration.module.css'
import { svgEnImage } from './qr'

type Appareil = Schema<'AppareilFiche'>
type Enrolement = Schema<'Enrolement'>

function Retirer({ a }: { a: Appareil }) {
  const ecrire = useEcriture(() => api.supprimer(`/appareils/${a.id}`))
  return (
    <Confirmer
      taille="petit"
      variante="danger"
      titre="Retirer cet appareil : ses sessions se ferment, il ne montre plus les visages"
      question="Retirer cet appareil ?"
      oui="Oui, retirer"
      onOui={async () => {
        await ecrire.mutateAsync()
        dire(`Appareil « ${a.nom} » retiré.`)
      }}
    >
      Retirer
    </Confirmer>
  )
}

const etat = (a: Appareil) =>
  !a.actif ? (
    <Badge ton="neutre">retiré</Badge>
  ) : a.enrole ? (
    <Badge ton="ok">enrôlé</Badge>
  ) : (
    <Badge ton="attention">{`QR valable jusqu’au ${horodatage(a.enrolement_expire_le)}`}</Badge>
  )

const COLONNES: readonly Colonne<Appareil>[] = [
  { cle: 'nom', titre: 'Appareil', rendu: (a) => <strong>{a.nom}</strong> },
  {
    cle: 'etat',
    titre: 'État',
    valeur: (a) => (a.actif ? (a.enrole ? 'enrôlé' : 'à enrôler') : 'retiré'),
    rendu: etat,
  },
  { cle: 'enrole_le', titre: 'Enrôlé le', rendu: (a) => horodatage(a.enrole_le) },
  { cle: 'vu_le', titre: 'Dernière activité', rendu: (a) => horodatage(a.vu_le) },
  { cle: 'sessions_ouvertes', titre: 'Sessions', droite: true, rendu: (a) => nombre(a.sessions_ouvertes) },
  { cle: 'cree_par', titre: 'Créé par', rendu: (a) => `${a.cree_par} · ${horodatage(a.cree_le)}` },
  {
    cle: 'geste',
    titre: '',
    triable: false,
    exporte: false,
    rendu: (a) => (a.actif ? <Retirer a={a} /> : null),
  },
]

function NouvelAppareil({ onFermer }: { onFermer: () => void }) {
  const [nom, setNom] = useState('')
  const [fait, setFait] = useState<Enrolement | null>(null)
  const ecrire = useEcriture(() => api.post<Enrolement>('/appareils', { nom: nom.trim() }))
  if (fait) {
    return (
      <Fenetre titre={`Enrôler « ${fait.nom} »`} onFermer={onFermer}>
        <Note>
          Depuis l’appareil, viser ce QR (ou ouvrir le lien). Il sert une fois, jusqu’au{' '}
          {horodatage(fait.expire_le)}.
        </Note>
        <img className={styles.qr} alt={`QR d’enrôlement de ${fait.nom}`} src={svgEnImage(fait.qr_svg)} />
        <span className={styles.code}>{fait.lien}</span>
      </Fenetre>
    )
  }
  return (
    <Fenetre
      titre="Nouvel appareil"
      onFermer={onFermer}
      sale={Boolean(nom.trim())}
      pied={
        <Bouton
          variante="principal"
          manque={nom.trim().length < 2 ? ['le nom de l’appareil (2 caractères au moins)'] : []}
          onClick={async () => setFait(await ecrire.mutateAsync())}
        >
          Créer et montrer le QR
        </Bouton>
      }
    >
      <Champ libelle="Nom de l’appareil" aide="ex. « Téléphone de l’atelier 2 »" obligatoire>
        <Saisie valeur={nom} max={80} onChange={setNom} autoFocus />
      </Champ>
    </Fenetre>
  )
}

export function Appareils() {
  const lu = useLecture<Appareil[]>('/appareils')
  const [nouveau, setNouveau] = useState(false)
  if (lu.isPending) return <Chargement quoi="les appareils" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  return (
    <Carte
      titre="Les appareils enrôlés"
      actions={
        <Bouton variante="principal" icone="plus" onClick={() => setNouveau(true)}>
          Nouvel appareil
        </Bouton>
      }
      serre
      remplir
      className={styles.carteListe}
    >
      <Note>
        Un appareil enrôlé ouvre l’écran de connexion sur les visages. Un appareil perdu se retire ici ;
        Tailscale le retire du réseau.
      </Note>
      <DataTable<Appareil>
        libelle="Appareils"
        lignes={lu.data}
        colonnes={COLONNES}
        cle={(a) => a.id}
        recherche={false}
        triInitial={{ cle: 'nom', sens: 1 }}
        vide="Aucun appareil enrôlé."
      />
      {nouveau ? <NouvelAppareil onFermer={() => setNouveau(false)} /> : null}
    </Carte>
  )
}
