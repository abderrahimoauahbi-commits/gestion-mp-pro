/**
 * Importations › En attente de dossier (ECRANS-PRO 5.3) : bascule « Factures reçues » /
 * « Réceptions sans facture » et case « Fournisseurs marocains » dans l'adresse (`?vue=`,
 * `&locaux=1`). Une facture ouvre son dossier (ou rejoint le sien : second camion) ; une réception
 * sans facture attend que sa facture soit saisie sur sa fiche.
 */
import { Link } from 'react-router'

import { Bascule } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api } from '../../lib/api'
import { date, kg, nombre, VIDE } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import { ChoixFacture } from './ChoixFacture'
import type { EtatPage } from './etatPage'
import styles from './Importations.module.css'
import type { DossierFiche, EnAttente as Attente, FactureARattacher, ReceptionSansFacture } from './types'

const INFOBULLE =
  'Tant qu’une arrivée n’est dans aucun dossier, son coût est le seul prix de la facture : ses frais (droits, fret, transitaire…) manquent au coût moyen du stock.'

const arreter = (e: { stopPropagation: () => void }) => e.stopPropagation()

const colonnesReceptions: Colonne<ReceptionSansFacture>[] = [
  {
    cle: 'reception',
    titre: 'Réception',
    rendu: (r) => (
      <Link to={`/receptions/${r.reception_id}`} onClick={arreter}>
        <strong>{r.reception}</strong>
      </Link>
    ),
  },
  { cle: 'fournisseur', titre: 'Fournisseur' },
  { cle: 'date', titre: 'Reçue le', rendu: (r) => date(r.date) },
  { cle: 'numero_bl', titre: 'BL', rendu: (r) => r.numero_bl || VIDE },
  { cle: 'lots', titre: 'Lots', droite: true, aide: 'Les lots distincts de la réception' },
  { cle: 'quantite', titre: 'Poids', droite: true, unite: 'kg', total: true, rendu: (r) => kg(r.quantite) },
  {
    cle: 'valeurs',
    titre: 'Valeur',
    droite: true,
    aide: 'Une ligne par devise : les devises ne s’additionnent pas',
    valeur: (r) => r.valeurs.map((v) => `${v.valeur} ${v.devise}`).join(' '),
    rendu: (r) => (
      <span className={styles.valeur}>
        {r.valeurs.map((v) => (
          <span key={v.devise}>
            {nombre(v.valeur, 2)} {v.devise}
          </span>
        ))}
      </span>
    ),
  },
  {
    cle: 'saisir',
    titre: '',
    triable: false,
    exporte: false,
    valeur: () => '',
    rendu: (r) => (
      <Link to={`/receptions/${r.reception_id}`} onClick={arreter}>
        Saisir la facture
      </Link>
    ),
  },
]

/** « Ouvrir son dossier » ou « Ajouter au dossier 12/26 » : le geste d'une facture qui attend. */
export function useOuvrirOuRattacher(page: Pick<EtatPage, 'ouvrir' | 'remplacerPar'>, remplacer = false) {
  const ecrire = useEcriture((faire: () => Promise<DossierFiche>) => faire())
  return async (f: FactureARattacher, localConfirme: boolean) => {
    if (f.dossier_id != null) {
      const id = f.dossier_id
      const lu = await api.get<DossierFiche>(`/dossiers/${id}`)
      const d = await ecrire.mutateAsync(() =>
        api.post<DossierFiche>(`/dossiers/${id}/rattacher`, {
          version: lu.version,
          facture_id: f.facture_id,
        }),
      )
      const devises = d.cours_disparates.map((c) => c.devise).join(', ')
      dire(
        `Facture ${f.numero} : le second camion rejoint le dossier ${d.numero}.` +
          (devises
            ? ` Ses marchandises n’ont pas le même cours que les premières (${devises}) : vérifier l’avis de la banque.`
            : ''),
      )
      return (remplacer ? page.remplacerPar : page.ouvrir)(d.id)
    }
    const d = await ecrire.mutateAsync(() =>
      api.post<DossierFiche>('/dossiers', { facture_id: f.facture_id, local_confirme: localConfirme }),
    )
    dire(`Facture ${f.numero} : dossier ${d.numero} ouvert.`)
    return (remplacer ? page.remplacerPar : page.ouvrir)(d.id)
  }
}

export const actionFacture = (f: FactureARattacher) =>
  f.dossier ? `Ajouter au dossier ${f.dossier}` : 'Ouvrir son dossier'

/** Un dossier clos ne prend pas de second camion : « le rouvrir d'abord » (dit avant le clic). */
export const blocageClos = (clos: (id: number) => boolean) => (f: FactureARattacher) =>
  f.dossier_id != null && clos(f.dossier_id)
    ? [`Le dossier ${f.dossier ?? ''} est clos : le rouvrir d’abord`]
    : []

/** La case des fournisseurs marocains et la bascule factures / réceptions (dans l'adresse). */
function Choix({ page, a, vue }: { page: EtatPage; a: Attente | undefined; vue: 'factures' | 'receptions' }) {
  const locaux = a?.locaux.factures ?? 0
  return (
    <>
      <Interrupteur
        libelle={
          page.locaux ? 'Fournisseurs marocains montrés' : `Fournisseurs marocains (${nombre(locaux)})`
        }
        valeur={page.locaux}
        onChange={(v) => page.ecrire('locaux', v ? '1' : null)}
      />
      <Bascule
        libelle="Ce qui attend"
        valeur={vue}
        onChange={(v) => page.ecrire('vue', v)}
        vues={[
          { cle: 'factures', libelle: `Factures reçues (${nombre(a?.factures.length ?? 0)})` },
          { cle: 'receptions', libelle: `Réceptions sans facture (${nombre(a?.sans_facture.length ?? 0)})` },
        ]}
      />
    </>
  )
}

export function EnAttente({ page, clos }: { page: EtatPage; clos: (id: number) => boolean }) {
  const lu = useLecture<Attente>('/dossiers/a-rattacher', page.locaux ? { locaux: true } : undefined)
  const choisir = useOuvrirOuRattacher(page)
  const a = lu.data
  const vue =
    page.vue === 'factures' || page.vue === 'receptions'
      ? page.vue
      : a && !a.factures.length && a.sans_facture.length
        ? 'receptions'
        : 'factures'
  const actions = <Choix page={page} a={a} vue={vue} />
  return (
    <Carte
      titre={<span title={INFOBULLE}>En attente de dossier</span>}
      sous="Un fournisseur marocain facture en MAD, sans douane ni fret international : il n’a pas de dossier d’importation."
      actions={actions}
      serre
      remplir
    >
      {lu.isError ? (
        <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
      ) : !a ? (
        <Chargement quoi="ce qui attend un dossier" />
      ) : vue === 'factures' ? (
        <>
          <Note uneLigne="Un dossier, une facture : c’est à chaque livraison qu’on paie les droits, le fret et le transitaire. La facture ouvre son dossier avec toute la marchandise qu’elle a apportée ; un second camion de la même facture rejoint son dossier.">
            Un dossier, une facture : c’est à chaque livraison qu’on paie les droits, le fret et le
            transitaire. La facture ouvre son dossier avec toute la marchandise qu’elle a apportée ; un second
            camion de la même facture rejoint son dossier.
          </Note>
          <ChoixFacture
            factures={a.factures}
            action={actionFacture}
            onChoisir={choisir}
            blocages={blocageClos(clos)}
          />
        </>
      ) : (
        <>
          <Note uneLigne="Pas de dossier sans facture : saisir le numéro de la facture sur la réception (il se complète même après la validation), puis la facture ouvre son dossier ci-dessus.">
            Pas de dossier sans facture : saisir le numéro de la facture sur la réception (il se complète même
            après la validation), puis la facture ouvre son dossier ci-dessus.
          </Note>
          <DataTable
            libelle="Réceptions sans facture"
            lignes={[...a.sans_facture].sort((x, y) => y.date.localeCompare(x.date))}
            colonnes={colonnesReceptions}
            cle={(r) => r.reception_id}
            placeholder="Réception, fournisseur, BL…"
            vide="Toutes les réceptions de l’étranger ont leur facture."
          />
        </>
      )}
    </Carte>
  )
}
