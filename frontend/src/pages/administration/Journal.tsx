/**
 * Administration › Journal des actions (`/administration?onglet=journal`) : qui a fait quoi, sur
 * quoi, et quand — avec **l'avant et l'après**, champ par champ, à la française. Recherche au
 * serveur, sans accents, sur tous les mots (P8-22) ; filtres Qui, Quoi, Sur quoi, Du, Au dans
 * l'adresse (`jq`, `qui`, `quoi`, `sur`, `du`, `au`) ; chargé 500 par 500 ; l'export prend tout.
 * « Sur » mène à la fiche quand le rôle peut l'ouvrir. L'administrateur ne lit pas les prix des
 * changements (le serveur les vide).
 */
import { Carte } from '../../composants/mise-en-page/Carte'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { permis } from '../../lib/droits'
import { horodatage } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Role, Schema } from '../../lib/types'
import { useApresCalme } from '../analyse/controles/DetailControle'
import { ChoixListe, Criteres, DateFiltre } from '../analyse/briques'
import { useEtatListe } from '../catalogue/etatListe'
import styles from './administration.module.css'
import { changementsLisibles } from './changements'

type Ligne = Schema<'LigneJournal'>
type Valeurs = Schema<'ValeursJournal'>

/** L'adresse de la fiche d'un objet du journal (`null` : pas de fiche à ouvrir). */
export function ficheDe(objet: string, id: number | null | undefined): string | null {
  if (id == null) return null
  const bases: Readonly<Record<string, string>> = {
    commande: '/commandes/',
    reception: '/receptions/',
    reclamation: '/reclamations/',
    matiere: '/matieres/',
    fournisseur: '/fournisseurs/',
    qualite: '/qualites/',
    lot: '/lots/',
    ordre: '/ordres/',
    operation: '/operations/',
    inventaire: '/inventaires/',
    dossier: '/dossiers/',
    metier: '/metiers/',
    utilisateur: '/administration?onglet=comptes&compte=',
    magasin: '/reglages?onglet=magasins&magasin=',
  }
  const base = bases[objet]
  return base ? `${base}${id}` : null
}

function colonnes(role: Role): Colonne<Ligne>[] {
  return [
    { cle: 'quand', titre: 'Quand', rendu: (l) => horodatage(l.quand) },
    {
      cle: 'utilisateur',
      titre: 'Par',
      rendu: (l) => (
        <>
          {l.utilisateur}
          <span className={styles.dessous}>{l.role}</span>
        </>
      ),
    },
    { cle: 'action', titre: 'Action' },
    {
      cle: 'objet',
      titre: 'Sur',
      valeur: (l) => `${l.objet} ${l.numero || (l.objet_id ?? '')}`,
      lien: (l) => {
        const a = ficheDe(l.objet, l.objet_id)
        return a && permis(role, a) ? a : null
      },
    },
    { cle: 'detail', titre: 'Détail', rendu: (l) => <span className={styles.detail}>{l.detail}</span> },
    {
      cle: 'avant',
      titre: 'Avant',
      valeur: (l) => changementsLisibles(l.avant),
      rendu: (l) => <span className={styles.detail}>{changementsLisibles(l.avant)}</span>,
    },
    {
      cle: 'apres',
      titre: 'Après',
      valeur: (l) => changementsLisibles(l.apres),
      rendu: (l) => <span className={styles.detail}>{changementsLisibles(l.apres)}</span>,
    },
  ]
}

function Outils({
  etat,
  valeurs,
  n,
}: {
  etat: ReturnType<typeof useEtatListe>
  valeurs: Valeurs | undefined
  n: number
}) {
  const poser = (cle: string) => (v: string) => etat.choix.poser(cle, v || null)
  const du = etat.lire('du')
  const au = etat.lire('au')
  return (
    <>
      <ChoixListe
        libelle="Qui"
        valeur={etat.lire('qui')}
        options={[
          { valeur: '', libelle: 'Tout le monde' },
          ...(valeurs?.utilisateurs ?? []).map((u) => ({ valeur: String(u.id), libelle: u.nom })),
        ]}
        onChange={poser('qui')}
      />
      <ChoixListe
        libelle="Quoi"
        valeur={etat.lire('quoi')}
        options={[
          { valeur: '', libelle: 'Toutes les actions' },
          ...(valeurs?.actions ?? []).map((a) => ({ valeur: a, libelle: a })),
        ]}
        onChange={poser('quoi')}
      />
      <ChoixListe
        libelle="Sur quoi"
        valeur={etat.lire('sur')}
        options={[
          { valeur: '', libelle: 'Sur tout' },
          ...(valeurs?.objets ?? []).map((o) => ({ valeur: o, libelle: o })),
        ]}
        onChange={poser('sur')}
      />
      <DateFiltre libelle="Du" titre="À partir de ce jour">
        <DateChamp libelle="Du" valeur={du} max={au || undefined} onChange={poser('du')} />
      </DateFiltre>
      <DateFiltre libelle="Au" titre="Jusqu’à ce jour inclus">
        <DateChamp libelle="Au" valeur={au} min={du || undefined} onChange={poser('au')} />
      </DateFiltre>
      <Criteres nombre={n} onEffacer={etat.choix.effacer} />
    </>
  )
}

export function Journal() {
  const { role } = useSession()
  const etat = useEtatListe('jq', ['qui', 'quoi', 'sur', 'du', 'au'])
  const q = useApresCalme(etat.recherche.valeur.trim())
  const filtres = {
    q: q || undefined,
    utilisateur: etat.lire('qui') || undefined,
    action: etat.lire('quoi') || undefined,
    objet: etat.lire('sur') || undefined,
    du: etat.lire('du') || undefined,
    au: etat.lire('au') || undefined,
  }
  const p = useListePaginee<Ligne>('/journal', filtres)
  const valeurs = useLecture<Valeurs>('/journal/valeurs')
  const n = Object.keys(etat.choix.valeurs).length + (etat.recherche.valeur.trim() ? 1 : 0)
  return (
    <Carte
      titre={`Journal des actions — ${p.total.toLocaleString('fr-FR')} entrée(s)`}
      serre
      remplir
      className={styles.carteListe}
    >
      <Note uneLigne="Chaque connexion, création, validation, annulation, modification de réglage s’inscrit ici et ne s’efface pas. Les entrées se chargent 500 par 500 ; l’export les prend toutes.">
        Chaque connexion, création, validation, annulation, modification de réglage s’inscrit ici et ne
        s’efface pas ; l’export prend toutes les entrées qui répondent aux filtres.
      </Note>
      {p.requete.isError ? (
        <Erreur erreur={p.requete.error} onReessayer={() => void p.requete.refetch()} />
      ) : null}
      <DataTable<Ligne>
        libelle="Journal des actions"
        lignes={p.lignes}
        colonnes={colonnes(role)}
        cle={(l) => l.id}
        recherche={etat.recherche}
        placeholder="Mots cherchés partout…"
        serveur
        total={p.total}
        chargerPlus={p.chargerPlus}
        vide={
          p.requete.isPending
            ? 'Chargement…'
            : n
              ? 'Rien ne correspond à ces filtres.'
              : 'Le journal est vide.'
        }
        exporter={{ route: '/export/journal', parametres: { ...filtres, q: undefined } }}
        outils={<Outils etat={etat} valeurs={valeurs.data} n={n} />}
      />
    </Carte>
  )
}
