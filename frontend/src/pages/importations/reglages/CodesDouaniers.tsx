/**
 * Réglages › Codes douaniers (ECRANS-PRO 5.21) : `/reglages?onglet=codes&q=`, monté sans `Page`
 * sous les onglets de la page Réglages. La position du tarif douanier et son taux de droits, le
 * nombre de matières qui la portent (lien vers elles au catalogue). Recherche à la frappe sur le
 * code et le libellé (`?q=`), filtre État (`?etat=actif|désactivé`), tri par code ; une ligne ouvre
 * le code en fenêtre (`&code=ID`, `&code=nouveau`). La direction écrit ; les achats lisent.
 */
import { useMemo } from 'react'

import { Carte } from '../../../composants/mise-en-page/Carte'
import { Fenetre } from '../../../composants/mise-en-page/Fenetre'
import { Badge } from '../../../composants/retour/Badge'
import { Chargement } from '../../../composants/retour/Chargement'
import { Erreur } from '../../../composants/retour/Erreur'
import { Note } from '../../../composants/retour/Note'
import { Bouton } from '../../../composants/saisie/Bouton'
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { comparer, trouve, type Filtre } from '../../../composants/tableaux/filtrage'
import { ErreurApi } from '../../../lib/api'
import { part } from '../../../lib/format'
import { useLecture } from '../../../lib/requetes'
import { useSession } from '../../../lib/session'
import { useEtatListe } from '../../catalogue/etatListe'
import type { CodeDouanier } from '../types'
import { FenetreCode } from './FenetreCode'
import { useFenetreAdresse, type FenetreAdresse } from './fenetreAdresse'
import { lienMatieres } from './formeCode'
import styles from './reglages.module.css'

const etatDe = (c: CodeDouanier) => (c.actif ? 'actif' : 'désactivé')

const COLONNES: readonly Colonne<CodeDouanier>[] = [
  { cle: 'code', titre: 'Code', rendu: (c) => <span className={styles.code}>{c.code}</span> },
  { cle: 'libelle', titre: 'Libellé' },
  { cle: 'taux_droits', titre: 'Taux de droits', droite: true, rendu: (c) => part(c.taux_droits, 1) },
  {
    cle: 'nb_matieres',
    titre: 'Matières',
    aide: 'Les matières du catalogue qui portent ce code',
    droite: true,
    lien: (c) => (c.nb_matieres ? lienMatieres(c.code) : null),
  },
  {
    cle: 'etat',
    titre: 'État',
    valeur: etatDe,
    rendu: (c) => <Badge ton={c.actif ? 'ok' : 'neutre'}>{etatDe(c)}</Badge>,
  },
]

const FILTRES: readonly Filtre<CodeDouanier>[] = [{ cle: 'etat', libelle: 'État', valeur: etatDe }]

/** La fenêtre demandée par l'adresse : un code, un nouveau (direction seule), ou rien. */
function FenetreDemandee({
  fen,
  codes,
  ecrit,
}: {
  fen: FenetreAdresse
  codes: readonly CodeDouanier[] | undefined
  ecrit: boolean
}) {
  const commun = { ecrit, volet: fen.volet, onVolet: fen.choisirVolet, onFermer: fen.fermer }
  if (fen.nouveau && ecrit) return <FenetreCode key="nouveau" code={null} {...commun} />
  if (fen.id == null) return null
  const code = codes?.find((c) => c.id === fen.id)
  if (code) return <FenetreCode key={code.id} code={code} {...commun} />
  return (
    <Fenetre titre="Code douanier" onFermer={fen.fermer}>
      {codes ? (
        <Erreur erreur={new ErreurApi('Code douanier introuvable.', 404, 'introuvable')} />
      ) : (
        <Chargement quoi="le code douanier" />
      )}
    </Fenetre>
  )
}

export function CodesDouaniers() {
  const { role } = useSession()
  const ecrit = role === 'direction'
  const lu = useLecture<CodeDouanier[]>('/codes-douaniers')
  const fen = useFenetreAdresse('code')
  const etat = useEtatListe('q', ['etat'])
  const q = etat.recherche.valeur
  const lignes = useMemo(
    () =>
      (lu.data ?? []).filter((c) => trouve([c.code, c.libelle], q)).sort((a, b) => comparer(a.code, b.code)),
    [lu.data, q],
  )
  const actions = ecrit ? (
    <Bouton variante="principal" icone="plus" onClick={() => fen.ouvrir('nouveau')}>
      Nouveau code
    </Bouton>
  ) : null
  return (
    <Carte
      titre="Codes douaniers"
      sous="Les positions du tarif douanier et leur taux de droits : de quoi prévoir et vérifier les droits d’un dossier."
      actions={actions}
      serre
      remplir
    >
      <div className={styles.tete}>
        <Note>
          La position du tarif douanier et son taux de droits. Chaque matière porte son code (fiche matière,
          au catalogue) : un dossier d’importation en déduit les droits attendus — taux × valeur en douane
          (achat + fret + assurance) — et signale l’écart avec la quittance. Un code désactivé compte comme «
          sans code ».
        </Note>
      </div>
      {lu.isPending ? <Chargement quoi="les codes douaniers" /> : null}
      {lu.isError ? <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} /> : null}
      {lu.data ? (
        <DataTable<CodeDouanier>
          libelle="Codes douaniers"
          lignes={lignes}
          colonnes={COLONNES}
          filtres={FILTRES}
          cle={(c) => c.id}
          recherche={etat.recherche}
          choix={etat.choix}
          placeholder="Code, libellé…"
          cliquable={(c) => fen.ouvrir(c.id)}
          vide={
            lu.data.length
              ? 'Aucun code ne correspond.'
              : ecrit
                ? 'Aucun code douanier. « Nouveau code » : 5402.47.00.00 (fils de polypropylène), son taux de droits…'
                : 'Aucun code douanier.'
          }
        />
      ) : null}
      <FenetreDemandee fen={fen} codes={lu.data} ecrit={ecrit} />
    </Carte>
  )
}
