/**
 * Administration › Sauvegardes (`/administration?onglet=sauvegardes`) : les copies de cette base
 * (relues, pièces jointes comprises), leur conservation, « Sauvegarder maintenant », et revenir à
 * l'une d'elles — confirmé sur la ligne, puis lu et confirmé dans sa fenêtre (`Restauration`).
 * Une sauvegarde d'une autre base ne se restaure pas ici (grisé, avec la raison). Direction et
 * administrateur technique.
 */
import { useState } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api } from '../../lib/api'
import { formule } from '../../lib/aide'
import { horodatage, nombre } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import styles from './administration.module.css'
import { FenetreRestauration, type FichierSauvegarde } from './Restauration'

type Etat = Schema<'EtatSauvegardes'>

/** Une taille lisible (« 12,4 Mo »). */
export function taille(octets: number): string {
  if (octets >= 1024 ** 3) return `${nombre(octets / 1024 ** 3, 1)} Go`
  if (octets >= 1024 ** 2) return `${nombre(octets / 1024 ** 2, 1)} Mo`
  return `${nombre(octets / 1024, 0)} Ko`
}

/** « moins d'une heure », « 3 h », « 2 j » : l'âge de la dernière sauvegarde. */
export function depuis(heures: number): string {
  if (heures < 1) return 'moins d’une heure'
  return heures < 48 ? `${nombre(heures, 0)} h` : `${nombre(heures / 24, 0)} j`
}

function colonnes(e: Etat, restaurer: (f: FichierSauvegarde) => void): Colonne<FichierSauvegarde>[] {
  return [
    { cle: 'quand', titre: 'Faite le', rendu: (f) => horodatage(f.quand) },
    { cle: 'nature', titre: 'Nature' },
    { cle: 'nom', titre: 'Fichier', rendu: (f) => <span className={styles.code}>{f.nom}</span> },
    {
      cle: 'base',
      titre: 'Base',
      rendu: (f) =>
        f.autre_base ? (
          <Badge ton="attention">{f.base}</Badge>
        ) : (
          <span className={styles.note}>cette base</span>
        ),
    },
    { cle: 'taille', titre: 'Taille', droite: true, rendu: (f) => taille(f.taille) },
    {
      cle: 'geste',
      titre: '',
      triable: false,
      exporte: false,
      rendu: (f) => (
        <Confirmer
          taille="petit"
          variante="danger"
          grise={
            f.autre_base
              ? `Sauvegarde de la base « ${f.base} », pas de celle-ci (« ${e.base} ») : elle ne se restaure pas ici.`
              : undefined
          }
          titre="Remplacer toute la base par cette sauvegarde (l’état actuel est d’abord sauvegardé)"
          question={`Revenir à l’état du ${horodatage(f.quand)} ?`}
          oui="Oui, continuer…"
          onOui={() => restaurer(f)}
        >
          Restaurer…
        </Confirmer>
      ),
    },
  ]
}

function IndicateursSauvegardes({ e }: { e: Etat }) {
  return (
    <Indicateurs libelle="Indicateurs des sauvegardes">
      <Kpi
        titre="Dernière sauvegarde"
        valeur={e.derniere ? horodatage(e.derniere) : 'aucune'}
        ton={e.alerte || (e.age_h ?? 0) > 26 ? 'critique' : e.derniere ? 'ok' : 'attention'}
        detail={e.alerte || (e.age_h != null ? `il y a ${depuis(e.age_h)}` : undefined)}
        formule={formule('sauvegarde_derniere')}
      />
      <Kpi
        titre="Sauvegardes conservées"
        valeur={nombre(e.nb)}
        detail="14 jours, puis une par mois sur 12 mois"
        formule={formule('sauvegarde_conservees')}
      />
      <Kpi
        titre="Copie de sécurité"
        valeur={e.copie ? 'Oui' : 'Non'}
        ton={e.copie ? 'ok' : 'attention'}
        detail={e.copie || 'aucun second emplacement réglé sur le serveur'}
        formule={formule('sauvegarde_copie')}
      />
    </Indicateurs>
  )
}

export function Sauvegardes() {
  const lu = useLecture<Etat>('/sauvegardes')
  const [restaurer, setRestaurer] = useState<FichierSauvegarde | null>(null)
  const sauver = useEcriture(() => api.post<Etat>('/sauvegardes'))
  if (lu.isPending) return <Chargement quoi="les sauvegardes" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const e = lu.data
  const deCetteBase = e.fichiers.filter((f) => !f.autre_base).length
  return (
    <>
      <IndicateursSauvegardes e={e} />
      <Carte
        titre="Les sauvegardes"
        actions={
          <Bouton
            variante="principal"
            grise={
              e.outils
                ? undefined
                : 'pg_dump est introuvable sur le serveur : les sauvegardes ne se font pas.'
            }
            attente="Sauvegarde en cours…"
            onClick={async () => {
              await sauver.mutateAsync()
              dire('Sauvegarde faite.')
            }}
          >
            Sauvegarder maintenant
          </Bouton>
        }
        serre
        remplir
        className={styles.carteListe}
      >
        <Note uneLigne={`${e.politique} Dossier : ${e.dossier}${e.copie ? ` ; copie : ${e.copie}` : ''}.`}>
          {`Dossier : ${e.dossier}${e.copie ? `, recopié dans ${e.copie}` : ''}. Conservation : ${e.politique} Restaurer remplace toute la base ; l’état actuel est d’abord sauvegardé, la restauration se défait.`}
        </Note>
        <DataTable<FichierSauvegarde>
          libelle="Sauvegardes"
          lignes={e.fichiers}
          colonnes={colonnes(e, setRestaurer)}
          cle={(f) => f.nom}
          recherche={false}
          triInitial={{ cle: 'quand', sens: -1 }}
          vide="Aucune sauvegarde pour le moment."
        />
        {e.autres ? (
          <Note>{`${nombre(e.autres)} fichier(s) du dossier sont des sauvegardes d’autres bases (essais, démonstrations) : ils ne comptent pas pour celle-ci et ne s’y restaurent pas.`}</Note>
        ) : null}
        {e.nb > deCetteBase ? (
          <Note>{`Les ${nombre(deCetteBase)} plus récentes de cette base sont listées, sur ${nombre(e.nb)}.`}</Note>
        ) : null}
      </Carte>
      {restaurer ? <FenetreRestauration f={restaurer} onFermer={() => setRestaurer(null)} /> : null}
    </>
  )
}
