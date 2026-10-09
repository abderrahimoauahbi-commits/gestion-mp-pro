/**
 * Cockpit › À faire et à valider (`/cockpit`) : le bandeau de l'alerte rouge (H-07), les commandes
 * à approuver (« Examiner » ouvre la fiche `/commandes/{id}`), puis tout ce qui attend une action,
 * chacun avec son lien ; un besoin signalé se traite sur place (`/cockpit?signalement=ID`).
 */
import { Link, useLocation, useNavigate } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Cadre } from '../../composants/tableaux/Cadre'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { date, montant, nombre } from '../../lib/format'
import { useSession } from '../../lib/session'
import { LigneTache, ListeTaches } from '../accueil/ListeTaches'
import { siPermis, type Tache } from '../accueil/taches'
import type { Cockpit, CommandeResume } from '../accueil/types'
import styles from './cockpit.module.css'
import { montantMad } from './aFaire'

/** Le bandeau : « N en rupture ou critiques (… RUPTURE, … CRITIQUE) — à suivre : U URGENT, A en ATTENTION. » */
export function BandeauAlerte({ cockpit }: { cockpit: Cockpit }) {
  const { role } = useSession()
  const s = cockpit.stock
  const plan = siPermis(role, '/plan-achat')
  const suivre = `${nombre(s.urgents)} URGENT, ${nombre(s.attentions)} en ATTENTION`
  if (!cockpit.alerte_rouge)
    return <Note ton="ok">Aucune rupture ni matière critique — à suivre : {suivre}.</Note>
  return (
    <Note ton="critique">
      <strong>{nombre(cockpit.alerte_rouge)} en rupture ou critiques</strong> ({nombre(s.ruptures)} en
      RUPTURE, {nombre(s.critiques)} CRITIQUE{s.critiques > 1 ? 'S' : ''}) — à suivre : {suivre}.{' '}
      {plan ? <Link to={plan}>Voir le plan d’achat →</Link> : null}
    </Note>
  )
}

const COLONNES: Colonne<CommandeResume>[] = [
  {
    cle: 'numero',
    titre: 'Bon',
    valeur: (c) => c.numero ?? 'À approuver',
    rendu: (c) => (
      <span className={styles.double}>
        {c.numero ?? 'À approuver'}
        <small>par {c.cree_par || '—'}</small>
      </span>
    ),
  },
  { cle: 'fournisseur', titre: 'Fournisseur' },
  {
    cle: 'date_commande',
    titre: 'Passée le',
    valeur: (c) => c.date_commande,
    rendu: (c) => date(c.date_commande),
  },
  {
    cle: 'montant',
    titre: 'Montant',
    droite: true,
    unite: (c) => c.devise,
    valeur: (c) => (c.montant > 0 || !c.montant_estime ? c.montant : c.montant_estime),
    rendu: (c) => {
      const estime = !(c.montant > 0 || !c.montant_estime)
      return (
        <span className={styles.double}>
          {montant(estime ? c.montant_estime : c.montant, c.devise)}
          {estime ? <small>estimé (catalogue)</small> : null}
        </span>
      )
    },
  },
  {
    cle: 'mad',
    titre: 'Montant MAD',
    droite: true,
    unite: 'MAD',
    total: true,
    valeur: (c) => montantMad(c).valeur,
    rendu: (c) => montant(montantMad(c).valeur, 'MAD'),
  },
]

function colonnes(examiner: (c: CommandeResume) => void): Colonne<CommandeResume>[] {
  return [
    ...COLONNES,
    {
      cle: 'examiner',
      titre: '',
      exporte: false,
      triable: false,
      rendu: (c) => (
        <Bouton
          taille="petit"
          variante="principal"
          titre="Ouvrir le bon pour le relire, puis l’approuver ou le renvoyer aux achats"
          onClick={() => examiner(c)}
        >
          Examiner
        </Bouton>
      ),
    },
  ]
}

export function OngletAFaire({
  cockpit,
  approuver,
  actions,
  sauvegarde,
  pret,
}: {
  cockpit: Cockpit
  approuver: readonly CommandeResume[]
  actions: readonly Tache[]
  sauvegarde: Tache | null
  pret: boolean
}) {
  const { role } = useSession()
  const navigate = useNavigate()
  const { pathname, search } = useLocation()
  // La fiche, fermée, ramène ici (ECRANS-PRO : « fermer revient au Cockpit »).
  const fiche = (c: CommandeResume) => {
    const vers = siPermis(role, `/commandes/${c.id}`)
    if (vers) navigate(vers, { state: { retour: `${pathname}${search}` } })
  }
  const toutes = siPermis(role, '/commandes?onglet=a_approuver')
  return (
    <>
      <BandeauAlerte cockpit={cockpit} />
      <div className={`${styles.deux} ${styles.large}`}>
        <Carte
          titre={`Commandes à approuver (${nombre(approuver.length)})`}
          actions={toutes ? <Link to={toutes}>Toutes les commandes →</Link> : null}
          serre
        >
          <DataTable
            lignes={approuver}
            colonnes={colonnes(fiche)}
            cle={(c) => c.id}
            cliquable={fiche}
            recherche={false}
            libelle="Commandes à approuver"
            vide="Aucune commande n’attend votre approbation."
          />
        </Carte>
        <Carte titre="Ce qui attend une action">
          <Cadre>
            {pret ? (
              <ListeTaches
                taches={actions}
                libelle="Ce qui attend une action"
                vide="Rien d’autre n’attend : tout est à jour."
                apres={sauvegarde ? <LigneTache t={sauvegarde} /> : null}
              />
            ) : null}
          </Cadre>
        </Carte>
      </div>
    </>
  )
}
