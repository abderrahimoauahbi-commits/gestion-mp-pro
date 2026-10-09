/**
 * Fenêtre « Historique des paramètres et des cours de change » (route 25 ; direction) : chaque
 * changement, le plus récent d'abord, avant → après **à la française** (« 10,85 », « 2 % » ;
 * P8-13), par qui et pourquoi. Chargée 500 par 500 ; la recherche affine ce qui est chargé.
 */
import { Fenetre } from '../../../composants/mise-en-page/Fenetre'
import { Erreur } from '../../../composants/retour/Erreur'
import { Note } from '../../../composants/retour/Note'
import { useListePaginee } from '../../../composants/tableaux/ChargerPlus'
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { horodatage } from '../../../lib/format'
import type { Schema } from '../../../lib/types'

type Changement = Schema<'ReglageHistorique'>

const COLONNES: readonly Colonne<Changement>[] = [
  { cle: 'quand', titre: 'Quand', rendu: (c) => horodatage(c.quand) },
  {
    cle: 'libelle',
    titre: 'Paramètre',
    recherche: (c) => [c.cle],
    rendu: (c) => (c.cle.startsWith('cours_') ? `Cours ${c.cle.slice(6)} → MAD` : c.libelle),
  },
  { cle: 'avant_lisible', titre: 'Avant', droite: true },
  { cle: 'apres_lisible', titre: 'Nouvelle valeur', droite: true },
  { cle: 'motif', titre: 'Motif' },
  { cle: 'par', titre: 'Par' },
]

export function HistoriqueParametres({ onFermer }: { onFermer: () => void }) {
  const p = useListePaginee<Changement>('/parametres/historique')
  return (
    <Fenetre titre="Historique des paramètres et des cours de change" taille="large" onFermer={onFermer}>
      <Note>Chaque changement, le plus récent d’abord.</Note>
      {p.requete.isError ? (
        <Erreur erreur={p.requete.error} onReessayer={() => void p.requete.refetch()} />
      ) : null}
      <DataTable<Changement>
        libelle="Historique des paramètres"
        lignes={p.lignes}
        colonnes={COLONNES}
        cle={(c) => c.id}
        placeholder="Paramètre, personne…"
        total={p.total}
        chargerPlus={p.chargerPlus}
        hauteur="fenetre"
        vide={p.requete.isPending ? 'Chargement…' : 'Aucun changement.'}
      />
    </Fenetre>
  )
}
