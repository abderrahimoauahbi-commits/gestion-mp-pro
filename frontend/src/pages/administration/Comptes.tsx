/**
 * Administration › Comptes (`/administration?onglet=comptes`, fenêtre `&compte=ID|nouveau`) : qui
 * se connecte, avec quel rôle et quel code. Direction et administrateur technique. La recherche
 * (`q`) affine à la frappe ; un compte s'ouvre en fenêtre.
 */
import { useSearchParams } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { avecParametre } from '../../lib/adresse'
import { horodatage, nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import styles from './administration.module.css'
import { ROLES } from './compte'
import { FenetreCompte, type Compte } from './FenetreCompte'

const libelleRole = (c: Compte) => ROLES.find((r) => r.cle === c.role)?.libelle ?? c.role_libelle

const COLONNES: readonly Colonne<Compte>[] = [
  { cle: 'nom', titre: 'Nom', rendu: (c) => <strong>{c.nom}</strong> },
  {
    cle: 'identifiant',
    titre: 'Identifiant',
    rendu: (c) => <span className={styles.code}>{c.identifiant}</span>,
  },
  { cle: 'role', titre: 'Rôle', valeur: libelleRole },
  { cle: 'email', titre: 'Courriel' },
  {
    cle: 'vu_le',
    titre: 'Dernière activité',
    rendu: (c) => (c.vu_le ? horodatage(c.vu_le) : <span className={styles.note}>jamais connecté</span>),
  },
  { cle: 'sessions_ouvertes', titre: 'Sessions', droite: true, rendu: (c) => nombre(c.sessions_ouvertes) },
  {
    cle: 'actif',
    titre: 'État',
    valeur: (c) => (c.historique ? 'repris' : c.actif ? 'actif' : 'désactivé'),
    rendu: (c) =>
      c.historique ? (
        <Badge ton="neutre">repris de Gestion MP</Badge>
      ) : c.actif ? (
        <Badge ton="ok">actif</Badge>
      ) : (
        <Badge ton="neutre">désactivé</Badge>
      ),
  },
]

export function Comptes() {
  const lu = useLecture<Compte[]>('/utilisateurs')
  const [params, setParams] = useSearchParams()
  const etat = useEtatTableAdresse([])
  const ouvert = params.get('compte')
  const ouvrir = (v: string | null) => setParams((p) => avecParametre(p, 'compte', v))
  if (lu.isPending) return <Chargement quoi="les comptes" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const c = lu.data.find((x) => String(x.id) === ouvert)
  return (
    <Carte
      titre="Les comptes"
      actions={
        <Bouton variante="principal" icone="plus" onClick={() => ouvrir('nouveau')}>
          Nouveau compte
        </Bouton>
      }
      serre
      remplir
      className={styles.carteListe}
    >
      <Note>
        Chacun a son compte : tout ce qui s’enregistre porte son nom. Un compte désactivé ne se connecte plus,
        et ses sessions ouvertes sont fermées. Cliquer sur un compte pour le modifier ou lui remettre un code.
      </Note>
      <DataTable<Compte>
        libelle="Comptes"
        lignes={lu.data}
        colonnes={COLONNES}
        cle={(x) => x.id}
        recherche={etat.recherche}
        rechercheCachee={(x) => [x.role_libelle]}
        placeholder="Nom, identifiant, rôle…"
        triInitial={{ cle: 'nom', sens: 1 }}
        cliquable={(x) => ouvrir(String(x.id))}
        vide="Aucun compte."
      />
      {ouvert === 'nouveau' ? <FenetreCompte onFermer={() => ouvrir(null)} /> : null}
      {c ? <FenetreCompte key={`${c.id}-${c.version}`} c={c} onFermer={() => ouvrir(null)} /> : null}
    </Carte>
  )
}
