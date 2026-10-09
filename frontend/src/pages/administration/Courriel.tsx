/**
 * Administration › Courriel du lundi (`/administration?onglet=courriel`) : à qui il part (un seul
 * endroit, adresses contrôlées à la frappe et au serveur, P8-19), si le serveur sait l'envoyer,
 * la file des courriels (envoyés, en attente, abandonnés) et — pour la direction seule, car il
 * porte des montants — ce qu'il dirait aujourd'hui (P8-20).
 */
import { useState } from 'react'

import { Bascule } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { horodatage, nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Schema } from '../../lib/types'
import { adressesIllisibles } from '../reglages/parametres/logique'
import styles from './administration.module.css'
import { ChampTechnique, useReglageTechnique } from './Technique'

type Courriel = Schema<'CourrielFiche'>
type Apercu = Schema<'ApercuCourriel'>

const COLONNES: readonly Colonne<Courriel>[] = [
  { cle: 'cree_le', titre: 'Créé le', rendu: (c) => horodatage(c.cree_le) },
  { cle: 'genre', titre: 'Genre' },
  { cle: 'sujet', titre: 'Sujet' },
  { cle: 'destinataires', titre: 'À' },
  { cle: 'statut', titre: 'État', rendu: (c) => <Badge famille="courriel" valeur={c.statut} /> },
  { cle: 'essais', titre: 'Essais', droite: true },
  {
    cle: 'envoye_le',
    titre: 'Envoyé ou prochain essai',
    rendu: (c) =>
      c.envoye_le
        ? horodatage(c.envoye_le)
        : c.prochain_essai_le
          ? `prochain : ${horodatage(c.prochain_essai_le)}`
          : '—',
  },
  { cle: 'erreur', titre: 'Motif', rendu: (c) => <span className={styles.detail}>{c.erreur}</span> },
]

/** Le message après l'enregistrement des destinataires. */
export function messageDestinataires(valeur: string): string {
  const n = valeur.split(/[,;]/).filter((x) => x.trim()).length
  return n ? `Le courriel du lundi partira à ${nombre(n)} adresse(s).` : 'Plus de courriel du lundi.'
}

function File() {
  const p = useListePaginee<Courriel>('/courriels')
  return (
    <>
      {p.requete.isError ? (
        <Erreur erreur={p.requete.error} onReessayer={() => void p.requete.refetch()} />
      ) : null}
      <DataTable<Courriel>
        libelle="File des courriels"
        lignes={p.lignes}
        colonnes={COLONNES}
        cle={(c) => c.id}
        recherche={false}
        serveur
        total={p.total}
        chargerPlus={p.chargerPlus}
        vide={p.requete.isPending ? 'Chargement…' : 'Aucun courriel pour le moment.'}
      />
    </>
  )
}

function ApercuDuLundi({ a }: { a: Apercu | undefined }) {
  if (!a) return null
  return (
    <div className={styles.apercu}>
      <strong>Objet : {a.sujet}</strong>
      <pre className={styles.texte}>{a.texte}</pre>
    </div>
  )
}

export function CourrielDuLundi() {
  const { role } = useSession()
  const direction = role === 'direction'
  const { reglage } = useReglageTechnique('courriel_destinataires')
  const apercu = useLecture<Apercu>(direction ? '/courriel/apercu' : null)
  const [vue, setVue] = useState<'file' | 'apercu'>('file')
  const a = apercu.data
  return (
    <>
      <Carte titre="À qui, et comment">
        {reglage ? (
          <ChampTechnique
            key={reglage.version}
            r={reglage}
            placeholder="direction@usine.ma, achats@usine.ma"
            message={messageDestinataires}
          />
        ) : null}
        <div className={styles.rangee}>
          {a ? (
            <Badge ton={a.serveur_configure ? 'ok' : 'attention'}>
              {a.serveur_configure ? 'serveur d’envoi réglé' : 'serveur d’envoi non réglé'}
            </Badge>
          ) : null}
          <span className={styles.note}>
            {a && !a.serveur_configure
              ? ' Pour l’envoyer, la personne qui installe le serveur règle GESTIONMPPRO_SMTP_HOTE (et l’expéditeur) dans son fichier de lancement.'
              : ''}
          </span>
        </div>
        {reglage && adressesIllisibles(reglage.valeur).length ? (
          <Note ton="attention">{`Adresse(s) illisible(s), écartée(s) à l’envoi : ${adressesIllisibles(reglage.valeur).join(', ')}.`}</Note>
        ) : null}
      </Carte>
      <Carte
        titre={vue === 'file' ? 'La file des courriels' : 'Ce qu’il dirait aujourd’hui'}
        actions={
          direction ? (
            <Bascule
              libelle="Vue du courriel"
              vues={[
                { cle: 'file', libelle: 'File des courriels' },
                { cle: 'apercu', libelle: 'Aperçu du lundi' },
              ]}
              valeur={vue}
              onChange={setVue}
            />
          ) : null
        }
        serre
        remplir
        className={styles.carteListe}
      >
        {vue === 'file' || !direction ? <File /> : <ApercuDuLundi a={a} />}
      </Carte>
    </>
  )
}
