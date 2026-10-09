/**
 * Administration › Serveur (`/administration?onglet=serveur`, route 4, relue toutes les 60 s) : la
 * version, la base, l'adresse sur le réseau, les sauvegardes, qui est connecté ; l'installation
 * (réglée dans le fichier de lancement, pas ici), les tâches de fond et les sessions ouvertes.
 */
import { useState } from 'react'

import { Bascule } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Definitions } from '../../composants/mise-en-page/Definitions'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { formule } from '../../lib/aide'
import { horodatage, nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import styles from './administration.module.css'
import { taille } from './Sauvegardes'

type Etat = Schema<'EtatServeur'>
type Tache = Schema<'TacheEtat'>
type SessionsCompte = Schema<'SessionsCompte'>

const TACHES: readonly Colonne<Tache>[] = [
  { cle: 'nom', titre: 'Tâche' },
  {
    cle: 'etat',
    titre: 'État',
    rendu: (t) => (
      <Badge ton={t.etat === 'ok' ? 'ok' : t.etat === 'echec' ? 'critique' : 'neutre'}>
        {t.etat === 'echec' ? 'en échec' : t.etat}
      </Badge>
    ),
  },
  { cle: 'dernier_essai_le', titre: 'Dernier passage', rendu: (t) => horodatage(t.dernier_essai_le) },
  { cle: 'dernier_succes_le', titre: 'Dernier succès', rendu: (t) => horodatage(t.dernier_succes_le) },
  { cle: 'duree_ms', titre: 'Durée', droite: true, rendu: (t) => `${nombre(t.duree_ms)} ms` },
  { cle: 'erreur', titre: 'Erreur', rendu: (t) => <span className={styles.detail}>{t.erreur}</span> },
]

const SESSIONS: readonly Colonne<SessionsCompte>[] = [
  { cle: 'nom', titre: 'Compte' },
  { cle: 'role', titre: 'Rôle' },
  { cle: 'vu_le', titre: 'Dernière activité', rendu: (s) => horodatage(s.vu_le) },
  { cle: 'nb', titre: 'Sessions', droite: true },
  { cle: 'appareils', titre: 'Appareils', droite: true },
  { cle: 'expire_le', titre: 'Expire le', rendu: (s) => horodatage(s.expire_le) },
]

function IndicateursServeur({ e }: { e: Etat }) {
  const connectes = e.sessions.length
  return (
    <Indicateurs libelle="Indicateurs du serveur">
      <Kpi
        titre="Version de Gestion MP PRO"
        valeur={e.application}
        detail={`schéma de base n° ${e.base.schema ?? '—'} · Python ${e.python}`}
        formule={formule('serveur_version')}
      />
      <Kpi
        titre="Base de données"
        valeur={e.base.nom}
        exact={`${e.base.hote}:${e.base.port}`}
        ton={e.base.schema === e.base.schema_attendu ? undefined : 'critique'}
        detail={`PostgreSQL ${e.base.version} · ${taille(e.base.taille_octets)}`}
        formule={formule('serveur_base')}
      />
      <Kpi
        titre="Adresse sur le réseau"
        valeur={e.reseau.adresse}
        detail={`${e.machine} · ${e.systeme}`}
        formule={formule('serveur_reseau')}
      />
      <Kpi
        titre="Sauvegardes"
        valeur={e.sauvegardes.outils ? `${nombre(e.sauvegardes.nb)} conservée(s)` : 'arrêtées'}
        ton={e.sauvegardes.outils && !e.sauvegardes.alerte ? 'ok' : 'critique'}
        detail={
          e.sauvegardes.derniere ? `dernière le ${horodatage(e.sauvegardes.derniere)}` : 'aucune encore'
        }
        formule={formule('sauvegarde_derniere')}
      />
      <Kpi
        titre="Connectés"
        valeur={nombre(connectes)}
        detail="comptes avec une session ouverte"
        formule={formule('serveur_connectes')}
      />
    </Indicateurs>
  )
}

function Installation({ e }: { e: Etat }) {
  const outils = Object.entries(e.outils)
  const manque = outils.some(([, chemin]) => !chemin)
  return (
    <Definitions
      colonnes={2}
      items={[
        ['Base', `${e.base.nom} (${e.base.hote}, port ${nombre(e.base.port)})`],
        [
          'Serveur',
          `${e.reseau.https ? 'HTTPS' : 'réseau sans chiffrement'} · écoute ${e.reseau.ecoute}:${e.reseau.port}`,
        ],
        [
          'Tâches de fond',
          e.taches_actives
            ? e.porteur_ici
              ? 'actives, portées par ce processus'
              : 'actives, portées par un autre processus'
            : 'arrêtées',
        ],
        ['Durée d’une session', `${nombre(e.session_jours)} jours sans se reconnecter`],
        ['Dossier des sauvegardes', e.sauvegardes.dossier],
        ['Copie de sécurité', e.sauvegardes.copie ?? 'aucune'],
        [
          'Outils PostgreSQL',
          manque
            ? 'pg_dump ou pg_restore introuvable : les sauvegardes ne se font pas'
            : outils.map(([n]) => n).join(', '),
        ],
        ['Conservation', e.sauvegardes.politique],
      ]}
    />
  )
}

export function Serveur() {
  const lu = useLecture<Etat>('/serveur', undefined, { refetchInterval: 60_000 })
  const [vue, setVue] = useState<'installation' | 'taches' | 'sessions'>('installation')
  if (lu.isPending) return <Chargement quoi="l’état du serveur" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const e = lu.data
  return (
    <>
      <IndicateursServeur e={e} />
      <Carte
        titre="L’installation"
        sous="Ces réglages se changent dans le fichier de lancement du serveur (variables GESTIONMPPRO_…), pas ici."
        actions={
          <Bascule
            libelle="Vue du serveur"
            vues={[
              { cle: 'installation', libelle: 'Installation' },
              { cle: 'taches', libelle: `Tâches de fond (${nombre(e.taches.length)})` },
              { cle: 'sessions', libelle: `Sessions ouvertes (${nombre(e.sessions.length)})` },
            ]}
            valeur={vue}
            onChange={setVue}
          />
        }
        serre
        remplir
        className={styles.carteListe}
      >
        {vue === 'installation' ? (
          <div className={styles.apercu}>
            <Installation e={e} />
          </div>
        ) : vue === 'taches' ? (
          <DataTable<Tache>
            libelle="Tâches de fond"
            lignes={e.taches}
            colonnes={TACHES}
            cle={(t) => t.nom}
            recherche={false}
            vide="Aucune tâche."
          />
        ) : (
          <DataTable<SessionsCompte>
            libelle="Sessions ouvertes"
            lignes={e.sessions}
            colonnes={SESSIONS}
            cle={(s) => `${s.nom}-${s.role}`}
            recherche={false}
            vide="Personne n’est connecté."
          />
        )}
      </Carte>
    </>
  )
}
